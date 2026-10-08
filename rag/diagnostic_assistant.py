"""
Knowledge-Driven IoT Fault Diagnosis Assistant
================================================

Project:
Knowledge-Driven IoT Fault Diagnosis Assistant

Purpose:
- Analyze current IoT telemetry.
- Evaluate all actual sensors in the project.
- Retrieve relevant project knowledge using RAG.
- Send telemetry + sensor audit + retrieved knowledge to a local LLM.
- Generate an explainable diagnostic response.

Actual sensors:
1. DHT22 Temperature
2. DHT22 Humidity
3. PIR Motion
4. HC-SR04 Distance
5. LM393 Sound Detection
6. A3144 Hall-Effect / Motor RPM
7. INA219 auxiliary electrical measurement

Important:
- MPU6050 is NOT part of the current project.
- DS18B20 is NOT part of the current project.
- INA219 measures the small red LED + 10K resistor load.
- INA219 must NOT be interpreted as motor current or 12 V motor supply voltage.
- LM393 is a digital threshold detector, not a calibrated dB meter.
- PIR is a digital motion detector.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from openai import OpenAI


# ============================================================
# RAG IMPORT
# ============================================================

try:
    from .rag_engine import retrieve_knowledge
except ImportError:
    from rag.rag_engine import retrieve_knowledge


# ============================================================
# LOCAL LLM CONFIGURATION
# ============================================================

LM_STUDIO_URL = "http://localhost:1234/v1"

MODEL = "qwen/qwen3-vl-4b"

client = OpenAI(
    base_url=LM_STUDIO_URL,
    api_key="lm-studio",
)


# ============================================================
# PROJECT THRESHOLDS
# ============================================================
#
# These values match knowledge_base.json.
#
# DHT22:
#   Temperature:
#       > 35 C  = WARNING
#       > 45 C  = CRITICAL
#
#   Humidity:
#       > 70 %  = WARNING
#       > 85 %  = CRITICAL
#
# PIR:
#       >= 10 s = WARNING
#       >= 30 s = CRITICAL
#
# HC-SR04:
#       10-20 cm = WARNING
#       <= 10 cm = CRITICAL
#
# LM393:
#       >= 2 s = WARNING
#       >= 5 s = CRITICAL
#
# A3144:
#       < 180 RPM = WARNING
#
# INA219:
#       Informational only.
# ============================================================


TEMP_WARNING = 35.0
TEMP_CRITICAL = 45.0

HUMIDITY_WARNING = 70.0
HUMIDITY_CRITICAL = 85.0

PIR_WARNING_SECONDS = 10.0
PIR_CRITICAL_SECONDS = 30.0

DISTANCE_WARNING = 20.0
DISTANCE_CRITICAL = 10.0

SOUND_WARNING_SECONDS = 2.0
SOUND_CRITICAL_SECONDS = 5.0

RPM_WARNING = 180.0


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def to_float(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    """
    Safely convert a value to float.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return float(value)

    try:
        number = float(value)

        if not math.isfinite(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def to_int(
    value: Any,
    default: Optional[int] = None,
) -> Optional[int]:
    """
    Safely convert a value to integer.
    """

    if value is None:
        return default

    try:
        return int(float(value))

    except (TypeError, ValueError):
        return default


def fmt(
    value: Any,
    digits: int = 2,
    suffix: str = "",
) -> str:
    """
    Format a numeric value for diagnostic text.
    """

    number = to_float(value)

    if number is None:
        return "Unavailable"

    return f"{number:.{digits}f}{suffix}"


def is_truthy(value: Any) -> bool:
    """
    Convert common telemetry representations to boolean.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        normalized = value.strip().lower()

        return normalized in {
            "1",
            "true",
            "yes",
            "on",
            "detected",
            "active",
        }

    return False


def first_value(
    data: Dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    """
    Return the first existing non-None value from telemetry.
    """

    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return default


# ============================================================
# STATUS EVALUATION
# ============================================================

def temperature_status(
    value: Any,
    explicit_fault: bool = False,
) -> str:
    """
    Evaluate DHT22 temperature.
    """

    if explicit_fault:
        return "FAULT"

    temperature = to_float(value)

    if temperature is None:
        return "UNAVAILABLE"

    if temperature > TEMP_CRITICAL:
        return "CRITICAL"

    if temperature > TEMP_WARNING:
        return "WARNING"

    return "NORMAL"


def humidity_status(
    value: Any,
    explicit_fault: bool = False,
) -> str:
    """
    Evaluate DHT22 humidity.
    """

    if explicit_fault:
        return "FAULT"

    humidity = to_float(value)

    if humidity is None:
        return "UNAVAILABLE"

    if humidity > HUMIDITY_CRITICAL:
        return "CRITICAL"

    if humidity > HUMIDITY_WARNING:
        return "WARNING"

    return "NORMAL"


def distance_status(
    value: Any,
    explicit_fault: bool = False,
) -> str:
    """
    Evaluate HC-SR04 distance.

    Important:
    Missing distance is not automatically treated as a fault.
    An explicit hc_sr04_fault field is required for FAULT.
    """

    if explicit_fault:
        return "FAULT"

    distance = to_float(value)

    if distance is None or distance <= 0:
        return "UNAVAILABLE"

    if distance <= DISTANCE_CRITICAL:
        return "CRITICAL"

    if distance <= DISTANCE_WARNING:
        return "WARNING"

    return "NORMAL"


def rpm_status(
    value: Any,
    motor_running: bool,
    explicit_fault: bool = False,
) -> str:
    """
    Evaluate A3144 motor RPM.

    Low RPM is evaluated only when the motor is reported as running.
    """

    if explicit_fault:
        return "FAULT"

    rpm = to_float(value)

    if rpm is None:
        return "UNAVAILABLE"

    if motor_running and rpm < RPM_WARNING:
        return "WARNING"

    return "NORMAL"


def motion_status(
    motion: Any,
    duration: Any,
    explicit_fault: bool = False,
) -> str:
    """
    Evaluate PIR motion.

    PIR is a digital sensor. Its diagnostic thresholds are based
    on persistence duration, not a numerical motion level.
    """

    if explicit_fault:
        return "FAULT"

    if not is_truthy(motion):
        return "NORMAL"

    seconds = to_float(duration)

    if seconds is None:
        return "ACTIVE"

    if seconds >= PIR_CRITICAL_SECONDS:
        return "CRITICAL"

    if seconds >= PIR_WARNING_SECONDS:
        return "WARNING"

    return "ACTIVE"


def sound_status(
    sound: Any,
    duration: Any,
    explicit_fault: bool = False,
) -> str:
    """
    Evaluate LM393 sound threshold event.

    LM393 is a digital threshold detector.
    It is not treated as a calibrated sound-level meter.
    """

    if explicit_fault:
        return "FAULT"

    if not is_truthy(sound):
        return "NORMAL"

    seconds = to_float(duration)

    if seconds is None:
        return "ACTIVE"

    if seconds >= SOUND_CRITICAL_SECONDS:
        return "CRITICAL"

    if seconds >= SOUND_WARNING_SECONDS:
        return "WARNING"

    return "ACTIVE"


def ina219_status(
    explicit_fault: bool = False,
) -> str:
    """
    INA219 is informational in the current project.

    It measures the small red LED + 10K resistor load,
    not the motor's electrical supply.
    """

    if explicit_fault:
        return "FAULT"

    return "INFO"


# ============================================================
# SENSOR AUDIT
# ============================================================

def build_sensor_audit(
    telemetry: Dict[str, Any],
    health: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Build a complete audit of every actual project sensor.

    The audit deliberately includes normal sensors as well as
    abnormal sensors so that the LLM evaluates the complete
    system rather than focusing only on the first detected fault.
    """

    if not isinstance(telemetry, dict):
        telemetry = {}

    if not isinstance(health, dict):
        health = {}

    statuses = health.get("statuses", {})

    if not isinstance(statuses, dict):
        statuses = {}

    # --------------------------------------------------------
    # TELEMETRY VALUES
    # --------------------------------------------------------

    temperature = first_value(
        telemetry,
        "temperature",
        "temp",
    )

    humidity = first_value(
        telemetry,
        "humidity",
        "rh",
    )

    motion = first_value(
        telemetry,
        "motion",
        "pir",
        "pir_motion",
    )

    motion_duration = first_value(
        telemetry,
        "pir_duration",
        "motion_duration",
        "pir_duration_seconds",
    )

    distance = first_value(
        telemetry,
        "distance",
        "distance_cm",
    )

    sound = first_value(
        telemetry,
        "sound",
        "sound_detected",
        "lm393",
    )

    sound_duration = first_value(
        telemetry,
        "sound_duration",
        "sound_duration_seconds",
        "lm393_duration",
    )

    rpm = first_value(
        telemetry,
        "rpm",
        "motor_rpm",
    )

    motor_running = is_truthy(
        first_value(
            telemetry,
            "motor_running",
            "motor_status",
            default=False,
        )
    )

    voltage = first_value(
        telemetry,
        "voltage",
        "ina219_voltage",
        "bus_voltage",
    )

    current = first_value(
        telemetry,
        "current",
        "ina219_current",
        "current_mA",
    )

    power = first_value(
        telemetry,
        "power",
        "ina219_power",
        "power_mW",
    )

    # --------------------------------------------------------
    # EXPLICIT FAULT FLAGS FROM ESP32
    # --------------------------------------------------------

    dht_fault = is_truthy(
        telemetry.get("dht22_fault", False)
    )

    hc_sr04_fault = is_truthy(
        telemetry.get("hc_sr04_fault", False)
    )

    pir_fault = is_truthy(
        telemetry.get("pir_fault", False)
    )

    lm393_fault = is_truthy(
        telemetry.get("lm393_fault", False)
    )

    a3144_fault = is_truthy(
        telemetry.get("a3144_fault", False)
    )

    ina219_fault = is_truthy(
        telemetry.get("ina219_fault", False)
    )

    # --------------------------------------------------------
    # HEALTH STATUSES
    # --------------------------------------------------------

    temperature_health = statuses.get(
        "temperature"
    )

    humidity_health = statuses.get(
        "humidity"
    )

    motion_health = statuses.get(
        "motion"
    )

    distance_health = statuses.get(
        "distance"
    )

    sound_health = statuses.get(
        "sound"
    )

    rpm_health = statuses.get(
        "rpm"
    )

    ina219_health = statuses.get(
        "ina219"
    )

    # --------------------------------------------------------
    # BUILD SENSOR RECORDS
    # --------------------------------------------------------

    audit: List[Dict[str, Any]] = []

    # ========================================================
    # DHT22 TEMPERATURE
    # ========================================================

    temp_status = temperature_status(
        temperature,
        dht_fault,
    )

    if temperature_health:
        temp_status = str(
            temperature_health
        ).upper()

    audit.append(
        {
            "sensor": "DHT22",
            "parameter": "Temperature",
            "value": temperature,
            "unit": "°C",
            "status": temp_status,
            "threshold": (
                f"WARNING > {TEMP_WARNING:.0f} °C; "
                f"CRITICAL > {TEMP_CRITICAL:.0f} °C"
            ),
            "fault": dht_fault,
            "interpretation": (
                "Environmental temperature measurement."
            ),
        }
    )

    # ========================================================
    # DHT22 HUMIDITY
    # ========================================================

    humidity_state = humidity_status(
        humidity,
        dht_fault,
    )

    if humidity_health:
        humidity_state = str(
            humidity_health
        ).upper()

    audit.append(
        {
            "sensor": "DHT22",
            "parameter": "Humidity",
            "value": humidity,
            "unit": "% RH",
            "status": humidity_state,
            "threshold": (
                f"WARNING > {HUMIDITY_WARNING:.0f} % RH; "
                f"CRITICAL > {HUMIDITY_CRITICAL:.0f} % RH"
            ),
            "fault": dht_fault,
            "interpretation": (
                "Environmental relative-humidity measurement."
            ),
        }
    )

    # ========================================================
    # PIR MOTION
    # ========================================================

    motion_state = motion_status(
        motion,
        motion_duration,
        pir_fault,
    )

    if motion_health:
        motion_state = str(
            motion_health
        ).upper()

    motion_value = (
        "DETECTED"
        if is_truthy(motion)
        else "NONE"
    )

    audit.append(
        {
            "sensor": "PIR",
            "parameter": "Motion",
            "value": motion_value,
            "duration": motion_duration,
            "unit": "digital",
            "status": motion_state,
            "threshold": (
                f"WARNING >= {PIR_WARNING_SECONDS:.0f} s; "
                f"CRITICAL >= {PIR_CRITICAL_SECONDS:.0f} s"
            ),
            "fault": pir_fault,
            "interpretation": (
                "Digital motion detection. "
                "Persistence is evaluated using duration."
            ),
        }
    )

    # ========================================================
    # HC-SR04 DISTANCE
    # ========================================================

    distance_state = distance_status(
        distance,
        hc_sr04_fault,
    )

    if distance_health:
        distance_state = str(
            distance_health
        ).upper()

    audit.append(
        {
            "sensor": "HC-SR04",
            "parameter": "Distance",
            "value": distance,
            "unit": "cm",
            "status": distance_state,
            "threshold": (
                f"WARNING 10-20 cm; "
                f"CRITICAL <= {DISTANCE_CRITICAL:.0f} cm"
            ),
            "fault": hc_sr04_fault,
            "interpretation": (
                "Object distance in the monitored area."
            ),
        }
    )

    # ========================================================
    # LM393 SOUND
    # ========================================================

    sound_state = sound_status(
        sound,
        sound_duration,
        lm393_fault,
    )

    if sound_health:
        sound_state = str(
            sound_health
        ).upper()

    sound_value = (
        "THRESHOLD EXCEEDED"
        if is_truthy(sound)
        else "NORMAL"
    )

    audit.append(
        {
            "sensor": "LM393",
            "parameter": "Sound Event",
            "value": sound_value,
            "duration": sound_duration,
            "unit": "digital threshold",
            "status": sound_state,
            "threshold": (
                f"WARNING >= {SOUND_WARNING_SECONDS:.0f} s; "
                f"CRITICAL >= {SOUND_CRITICAL_SECONDS:.0f} s"
            ),
            "fault": lm393_fault,
            "interpretation": (
                "Digital sound-threshold event. "
                "Not a calibrated dB measurement."
            ),
        }
    )

    # ========================================================
    # A3144 MOTOR RPM
    # ========================================================

    rpm_state = rpm_status(
        rpm,
        motor_running,
        a3144_fault,
    )

    if rpm_health:
        rpm_state = str(
            rpm_health
        ).upper()

    audit.append(
        {
            "sensor": "A3144",
            "parameter": "Motor RPM",
            "value": rpm,
            "unit": "RPM",
            "status": rpm_state,
            "threshold": (
                f"WARNING < {RPM_WARNING:.0f} RPM "
                "when motor is running"
            ),
            "fault": a3144_fault,
            "interpretation": (
                "Hall-effect magnetic pulse measurement "
                "used to estimate motor rotation."
            ),
        }
    )

    # ========================================================
    # INA219
    # ========================================================

    ina_state = ina219_status(
        ina219_fault,
    )

    if ina219_health:
        ina_state = str(
            ina219_health
        ).upper()

    audit.append(
        {
            "sensor": "INA219",
            "parameter": "Auxiliary Electrical Load",
            "value": {
                "voltage": voltage,
                "current": current,
                "power": power,
            },
            "unit": {
                "voltage": "V",
                "current": "mA",
                "power": "mW",
            },
            "status": ina_state,
            "threshold": "Informational",
            "fault": ina219_fault,
            "interpretation": (
                "Measures the small red LED + 10K resistor "
                "load. It is NOT motor-current or 12 V "
                "motor-supply measurement."
            ),
        }
    )

    return audit


# ============================================================
# FORMAT SENSOR AUDIT
# ============================================================

def format_sensor_audit(
    sensor_audit: List[Dict[str, Any]],
) -> str:
    """
    Convert sensor audit records into a readable text block
    for the RAG query and LLM prompt.
    """

    lines: List[str] = []

    for item in sensor_audit:
        sensor = item.get(
            "sensor",
            "Unknown",
        )

        parameter = item.get(
            "parameter",
            "Unknown",
        )

        status = item.get(
            "status",
            "UNKNOWN",
        )

        value = item.get(
            "value"
        )

        unit = item.get(
            "unit",
            "",
        )

        threshold = item.get(
            "threshold",
            "None",
        )

        fault = item.get(
            "fault",
            False,
        )

        if isinstance(value, dict):
            value_text = (
                f"Voltage={fmt(value.get('voltage'), 4, ' V')}, "
                f"Current={fmt(value.get('current'), 4, ' mA')}, "
                f"Power={fmt(value.get('power'), 4, ' mW')}"
            )

        else:
            if isinstance(value, str):
                value_text = value

            elif value is None:
                value_text = "Unavailable"

            else:
                number = to_float(value)

                if number is not None:
                    value_text = (
                        f"{number:.2f}"
                    )

                else:
                    value_text = str(value)

            if unit and isinstance(unit, str):
                value_text += f" {unit}"

        duration = item.get(
            "duration"
        )

        duration_text = ""

        if duration is not None:
            duration_number = to_float(
                duration
            )

            if duration_number is not None:
                duration_text = (
                    f"; duration={duration_number:.1f} s"
                )

        interpretation = item.get(
            "interpretation",
            "",
        )

        lines.append(
            (
                f"- {sensor} | {parameter} | "
                f"value={value_text} | "
                f"status={status} | "
                f"fault={fault} | "
                f"threshold={threshold}"
                f"{duration_text} | "
                f"{interpretation}"
            )
        )

    return "\n".join(lines)


# ============================================================
# BUILD RAG QUERY
# ============================================================

def build_rag_query(
    telemetry: Dict[str, Any],
    sensor_audit: List[Dict[str, Any]],
    health: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a retrieval query containing all relevant sensor
    conditions rather than only abnormal sensors.
    """

    if not isinstance(telemetry, dict):
        telemetry = {}

    if not isinstance(health, dict):
        health = {}

    audit_text = format_sensor_audit(
        sensor_audit
    )

    health_status = health.get(
        "status",
        "UNKNOWN",
    )

    health_score = health.get(
        "score",
        "UNKNOWN",
    )

    fault_summary = telemetry.get(
        "fault_summary",
        "NONE",
    )

    return f"""
Knowledge-Driven IoT Fault Diagnosis Assistant project.

Retrieve project-specific diagnostic knowledge for the complete
current sensor state.

Health status:
{health_status}

Health score:
{health_score}

Fault summary:
{fault_summary}

Complete sensor audit:
{audit_text}

The diagnostic knowledge must cover:
- DHT22 temperature
- DHT22 humidity
- PIR motion
- HC-SR04 distance
- LM393 sound threshold
- A3144 motor RPM
- INA219 auxiliary electrical measurement

Do not introduce MPU6050.
Do not introduce DS18B20.
Do not invent vibration data.
Do not invent motor temperature.
Do not interpret INA219 as motor current or 12 V motor supply.

Use the project's documented thresholds and diagnostic rules.
""".strip()


# ============================================================
# RETRIEVE PROJECT KNOWLEDGE
# ============================================================

def retrieve_project_knowledge(
    query: str,
) -> List[Any]:
    """
    Call the project's existing RAG retrieval engine.

    This function supports several possible return formats
    from rag_engine.py.
    """

    try:
        result = retrieve_knowledge(
            query
        )

    except TypeError:
        try:
            result = retrieve_knowledge(
                query=query
            )

        except Exception as error:
            print(
                "RAG retrieval error:",
                error,
            )
            return []

    except Exception as error:
        print(
            "RAG retrieval error:",
            error,
        )
        return []

    if result is None:
        return []

    if isinstance(result, list):
        return result

    return [result]


# ============================================================
# FORMAT RETRIEVED KNOWLEDGE
# ============================================================

def format_retrieved_knowledge(
    knowledge: List[Any],
) -> str:
    """
    Convert retrieved RAG results into prompt text.
    """

    if not knowledge:
        return (
            "No additional retrieved project knowledge "
            "was returned."
        )

    sections: List[str] = []

    for index, item in enumerate(
        knowledge,
        start=1,
    ):
        if isinstance(item, str):
            sections.append(
                f"[Knowledge {index}]\n{item}"
            )
            continue

        if isinstance(item, dict):
            title = item.get(
                "title",
                item.get(
                    "name",
                    f"Knowledge {index}",
                ),
            )

            content = item.get(
                "content",
                item.get(
                    "text",
                    item.get(
                        "description",
                        "",
                    ),
                ),
            )

            sensor = item.get(
                "sensor",
                "",
            )

            parameter = item.get(
                "parameter",
                "",
            )

            condition = item.get(
                "condition",
                "",
            )

            severity = item.get(
                "severity",
                "",
            )

            header = (
                f"[Knowledge {index}] "
                f"{title}"
            )

            metadata = []

            if sensor:
                metadata.append(
                    f"Sensor: {sensor}"
                )

            if parameter:
                metadata.append(
                    f"Parameter: {parameter}"
                )

            if condition:
                metadata.append(
                    f"Condition: {condition}"
                )

            if severity:
                metadata.append(
                    f"Severity: {severity}"
                )

            metadata_text = ""

            if metadata:
                metadata_text = (
                    "\n"
                    + "\n".join(metadata)
                )

            sections.append(
                f"{header}"
                f"{metadata_text}\n"
                f"{content}"
            )

            continue

        sections.append(
            f"[Knowledge {index}]\n"
            f"{str(item)}"
        )

    return "\n\n".join(
        sections
    )


# ============================================================
# BUILD LLM PROMPT
# ============================================================

def build_llm_prompt(
    telemetry: Dict[str, Any],
    sensor_audit: List[Dict[str, Any]],
    retrieved_knowledge: List[Any],
    health: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build the final prompt for the local LLM.
    """

    if not isinstance(telemetry, dict):
        telemetry = {}

    if not isinstance(health, dict):
        health = {}

    audit_text = format_sensor_audit(
        sensor_audit
    )

    knowledge_text = format_retrieved_knowledge(
        retrieved_knowledge
    )

    health_status = health.get(
        "status",
        "UNKNOWN",
    )

    health_score = health.get(
        "score",
        "UNKNOWN",
    )

    fault_summary = telemetry.get(
        "fault_summary",
        "NONE",
    )

    device_id = telemetry.get(
        "device_id",
        "bharatpi_01",
    )

    prompt = f"""
You are the diagnostic reasoning component of a
Knowledge-Driven IoT Fault Diagnosis Assistant.

Analyze the current telemetry using ONLY:

1. Current telemetry.
2. The complete sensor audit.
3. Project knowledge retrieved through RAG.
4. The documented project thresholds.

Do not invent measurements, sensors, faults, causes, or thresholds.

============================================================
CURRENT SYSTEM
============================================================

Device:
{device_id}

Health status:
{health_status}

Health score:
{health_score}

Fault summary:
{fault_summary}

============================================================
CURRENT TELEMETRY
============================================================

{telemetry}

============================================================
COMPLETE SENSOR AUDIT
============================================================

{audit_text}

============================================================
RETRIEVED PROJECT KNOWLEDGE
============================================================

{knowledge_text}

============================================================
IMPORTANT SENSOR RULES
============================================================

DHT22:
- Temperature warning: > 35 °C.
- Temperature critical: > 45 °C.
- Humidity warning: > 70 % RH.
- Humidity critical: > 85 % RH.

PIR:
- PIR is a digital motion detector.
- Do not describe it as a numerical motion sensor.
- Persistent motion >= 10 seconds is WARNING.
- Persistent motion >= 30 seconds is CRITICAL.
- If duration is unavailable, do not invent a duration.

HC-SR04:
- Distance 10-20 cm is WARNING.
- Distance <= 10 cm is CRITICAL.
- Missing distance is unavailable unless the telemetry explicitly
  contains hc_sr04_fault=true.
- Do not automatically call an unavailable reading a fault.

LM393:
- It is a digital sound-threshold detector.
- It is NOT a calibrated dB sound-level meter.
- Sound event >= 2 seconds is WARNING.
- Sound event >= 5 seconds is CRITICAL.
- If duration is unavailable, do not invent a duration.

A3144:
- It detects magnetic pulses from the rotating motor.
- The expected geared-motor speed is approximately 200 RPM.
- RPM < 180 while the motor is running is WARNING.
- Do not claim motor temperature because there is no motor-temperature
  sensor in this project.
- Do not claim vibration because MPU6050 is not installed.

INA219:
- The current project configuration measures a small red LED
  and 10K ohm resistor load.
- INA219 values are informational.
- NEVER describe INA219 voltage as the 12 V motor supply voltage.
- NEVER describe INA219 current as motor current.
- NEVER infer motor electrical health from INA219 values alone.

FAULT FLAGS:
- Respect explicit Arduino fault fields.
- dht22_fault refers to DHT22 unresponsive/invalid readings.
- hc_sr04_fault refers to HC-SR04 echo failure after previous valid operation.
- a3144_fault refers to loss of Hall/RPM signal after previous valid operation.
- ina219_fault refers to loss of INA219 I2C presence.
- PIR and LM393 disconnection should not be invented merely from
  HIGH/LOW readings.

============================================================
REQUIRED REASONING
============================================================

Analyze ALL actual sensors.

Do not focus only on the first abnormal value.

For every actual sensor, determine whether it is:
- NORMAL
- WARNING
- CRITICAL
- FAULT
- ACTIVE
- INFO
- UNAVAILABLE

Explain meaningful relationships between sensors when supported
by the available telemetry.

Examples of valid multi-sensor reasoning:

- High humidity + normal temperature may indicate an environmental
  humidity condition rather than a temperature problem.

- Low RPM + motor_running=true + A3144 fault may indicate a possible
  Hall/magnet detection issue, but distinguish sensor fault from
  mechanical causes.

- Low RPM without an A3144 fault may indicate possible mechanical
  load, alignment, drive, or magnet-detection issues. Do not choose
  one cause as certain without evidence.

- Close HC-SR04 distance + persistent PIR motion can indicate that
  an object/person is present in the monitored area, but do not
  identify the object unless telemetry supports it.

- LM393 sound event + PIR motion can indicate simultaneous activity,
  but do not assume a specific source of the sound.

- A DHT22 warning should be discussed even if RPM or other sensors
  also have abnormalities.

============================================================
RESPONSE FORMAT
============================================================

Return exactly these five sections:

1. CURRENT CONDITION

Give a concise overall description of the current system condition.
Mention the overall health state and the most relevant sensor states.

2. DETECTED ABNORMALITIES

List every currently detected warning, critical condition, explicit
sensor fault, or unavailable value that materially affects diagnosis.

Do not invent abnormalities.

If no abnormality exists, state that the monitored sensors are
within the project's defined thresholds.

3. POSSIBLE INTERPRETATION

Reason across ALL actual sensors.

Discuss environmental, motion, distance, sound, motor RPM, and
auxiliary electrical information as applicable.

Clearly distinguish:
- measured fact
- project rule
- possible interpretation

Do not present a possible cause as a confirmed cause.

4. RECOMMENDED CHECKS

Give practical checks based only on the detected conditions.

For example:
- inspect DHT22 placement and wiring if DHT22 fault exists
- check HC-SR04 wiring and echo path if explicit HC-SR04 fault exists
- check Hall sensor alignment and magnet position if RPM is low
- check motor mechanical load if RPM is low
- inspect PIR event context if persistent motion exists
- check LM393 threshold potentiometer if sound events persist
- inspect the auxiliary LED/resistor wiring if INA219 has an I2C fault

Do not recommend checking a sensor that has no relevant abnormality
unless it helps verify a multi-sensor relationship.

5. CONFIDENCE NOTE

State how strongly the conclusion is supported by the available
telemetry and project knowledge.

Mention missing/unavailable values when they limit certainty.

Keep the answer concise, technical, and evidence-based.
""".strip()

    return prompt


# ============================================================
# GENERATE DIAGNOSIS
# ============================================================

def generate_diagnosis(
    telemetry: Dict[str, Any],
    health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main entry point used by backend/app.py.

    Parameters:
        telemetry:
            Latest telemetry dictionary.

        health:
            Normalized health information generated by the backend.

    Returns:
        Dictionary containing:
        - diagnosis
        - answer
        - sensor_audit
        - retrieved_knowledge
        - model
        - health
    """

    if not isinstance(telemetry, dict):
        telemetry = {}

    if not isinstance(health, dict):
        health = {}

    # --------------------------------------------------------
    # BUILD COMPLETE SENSOR AUDIT
    # --------------------------------------------------------

    sensor_audit = build_sensor_audit(
        telemetry,
        health,
    )

    # --------------------------------------------------------
    # BUILD RAG QUERY
    # --------------------------------------------------------

    rag_query = build_rag_query(
        telemetry,
        sensor_audit,
        health,
    )

    # --------------------------------------------------------
    # RETRIEVE PROJECT KNOWLEDGE
    # --------------------------------------------------------

    retrieved_knowledge = retrieve_project_knowledge(
        rag_query
    )

    # --------------------------------------------------------
    # BUILD LLM PROMPT
    # --------------------------------------------------------

    prompt = build_llm_prompt(
        telemetry,
        sensor_audit,
        retrieved_knowledge,
        health,
    )

    # --------------------------------------------------------
    # CALL LOCAL LLM
    # --------------------------------------------------------

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an evidence-based IoT "
                        "fault diagnosis assistant. "
                        "Use only the supplied telemetry, "
                        "project thresholds, and retrieved "
                        "project knowledge."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            max_tokens=1200,
        )

        diagnosis = (
            response.choices[0]
            .message
            .content
        )

        if not diagnosis:
            diagnosis = (
                "No diagnosis was generated by the local LLM."
            )

    except Exception as error:
        print(
            "Local LLM error:",
            error,
        )

        # ----------------------------------------------------
        # FALLBACK DIAGNOSIS
        # ----------------------------------------------------
        #
        # The dashboard still receives a useful explanation
        # if LM Studio is unavailable.
        # ----------------------------------------------------

        abnormal_items = [
            item
            for item in sensor_audit
            if item.get("status")
            in {
                "WARNING",
                "CRITICAL",
                "FAULT",
            }
        ]

        fallback_lines = []

        fallback_lines.append(
            "1. CURRENT CONDITION"
        )

        if abnormal_items:
            fallback_lines.append(
                "The system has one or more "
                "sensor conditions requiring attention."
            )
        else:
            fallback_lines.append(
                "The monitored sensors are within "
                "the project's defined diagnostic thresholds."
            )

        fallback_lines.append(
            ""
        )

        fallback_lines.append(
            "2. DETECTED ABNORMALITIES"
        )

        if abnormal_items:
            for item in abnormal_items:
                sensor = item.get(
                    "sensor",
                    "Unknown",
                )

                parameter = item.get(
                    "parameter",
                    "Unknown",
                )

                status = item.get(
                    "status",
                    "UNKNOWN",
                )

                value = item.get(
                    "value"
                )

                if isinstance(value, dict):
                    value_text = (
                        f"Voltage={fmt(value.get('voltage'), 4, ' V')}, "
                        f"Current={fmt(value.get('current'), 4, ' mA')}, "
                        f"Power={fmt(value.get('power'), 4, ' mW')}"
                    )
                elif value is None:
                    value_text = "Unavailable"
                else:
                    value_text = str(value)

                fallback_lines.append(
                    f"- {sensor} {parameter}: "
                    f"{status} ({value_text})"
                )
        else:
            fallback_lines.append(
                "- No warning, critical, or explicit "
                "sensor fault is currently detected."
            )

        fallback_lines.append(
            ""
        )

        fallback_lines.append(
            "3. POSSIBLE INTERPRETATION"
        )

        if abnormal_items:
            fallback_lines.append(
                "The condition should be interpreted using "
                "the documented project thresholds and the "
                "complete sensor audit. A confirmed root cause "
                "cannot be established from telemetry alone."
            )
        else:
            fallback_lines.append(
                "Current telemetry does not show a condition "
                "outside the project's defined thresholds."
            )

        fallback_lines.append(
            ""
        )

        fallback_lines.append(
            "4. RECOMMENDED CHECKS"
        )

        if abnormal_items:
            for item in abnormal_items:
                sensor = item.get(
                    "sensor",
                    "Unknown",
                )

                if sensor == "DHT22":
                    fallback_lines.append(
                        "- Check DHT22 wiring, placement, "
                        "and environmental conditions."
                    )

                elif sensor == "HC-SR04":
                    fallback_lines.append(
                        "- Check HC-SR04 wiring, sensor "
                        "orientation, and echo path."
                    )

                elif sensor == "PIR":
                    fallback_lines.append(
                        "- Check the physical context and "
                        "persistence of the detected motion."
                    )

                elif sensor == "LM393":
                    fallback_lines.append(
                        "- Check the sound event and adjust "
                        "the LM393 threshold potentiometer "
                        "if necessary."
                    )

                elif sensor == "A3144":
                    fallback_lines.append(
                        "- Check Hall sensor alignment, "
                        "magnet position, motor load, and "
                        "motor drive."
                    )

                elif sensor == "INA219":
                    fallback_lines.append(
                        "- Check INA219 I2C wiring and the "
                        "auxiliary LED/resistor measurement path."
                    )
        else:
            fallback_lines.append(
                "- Continue monitoring telemetry for changes."
            )

        fallback_lines.append(
            ""
        )

        fallback_lines.append(
            "5. CONFIDENCE NOTE"
        )

        fallback_lines.append(
            "The fallback assessment is based on the available "
            "telemetry and project-level thresholds. The local "
            "LLM was unavailable, so no LLM-generated reasoning "
            "was used."
        )

        diagnosis = "\n".join(
            fallback_lines
        )

    # --------------------------------------------------------
    # RETURN COMPLETE RESULT
    # --------------------------------------------------------

    return {
        "diagnosis": diagnosis,
        "answer": diagnosis,
        "sensor_audit": sensor_audit,
        "retrieved_knowledge": retrieved_knowledge,
        "model": MODEL,
        "health": health,
    }


# ============================================================
# OPTIONAL DIRECT TEST
# ============================================================

if __name__ == "__main__":
    print(
        "diagnostic_assistant.py loaded successfully."
    )

    print(
        f"LM Studio URL: {LM_STUDIO_URL}"
    )

    print(
        f"Model: {MODEL}"
    )