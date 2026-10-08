"""
Knowledge-Driven IoT Fault Diagnosis Assistant
Rule-based health and severity analysis.

Threshold source:
rag/knowledge_base.json
"""

from typing import Any


# ============================================================
# THRESHOLDS FROM knowledge_base.json
# ============================================================

TEMP_WARNING = 35.0
TEMP_CRITICAL = 45.0

HUMIDITY_WARNING = 70.0
HUMIDITY_CRITICAL = 85.0

PIR_WARNING_SECONDS = 10.0
PIR_CRITICAL_SECONDS = 30.0

DISTANCE_WARNING_MIN = 10.0
DISTANCE_WARNING_MAX = 20.0
DISTANCE_CRITICAL = 10.0

SOUND_WARNING_SECONDS = 2.0
SOUND_CRITICAL_SECONDS = 5.0

RPM_WARNING = 180.0


# ============================================================
# HELPERS
# ============================================================

def number(
    value: Any
):
    try:
        if value is None:
            return None

        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return None


def severity_rank(
    severity: str
):
    order = {
        "NORMAL": 0,
        "INFO": 1,
        "WARNING": 2,
        "CRITICAL": 3,
        "FAULT": 4
    }

    return order.get(
        str(severity).upper(),
        0
    )


# ============================================================
# TEMPERATURE
# ============================================================

def temperature_status(
    value
):

    value = number(value)

    if value is None:
        return "FAULT"

    if value > TEMP_CRITICAL:
        return "CRITICAL"

    if value > TEMP_WARNING:
        return "WARNING"

    return "NORMAL"


# ============================================================
# HUMIDITY
# ============================================================

def humidity_status(
    value
):

    value = number(value)

    if value is None:
        return "FAULT"

    if value > HUMIDITY_CRITICAL:
        return "CRITICAL"

    if value > HUMIDITY_WARNING:
        return "WARNING"

    return "NORMAL"


# ============================================================
# PIR
# ============================================================

def pir_status(
    duration
):

    duration = number(duration)

    if duration is None:
        return "NORMAL"

    if duration >= PIR_CRITICAL_SECONDS:
        return "CRITICAL"

    if duration >= PIR_WARNING_SECONDS:
        return "WARNING"

    return "NORMAL"


# ============================================================
# HC-SR04
# ============================================================

def distance_status(
    value
):

    value = number(value)

    if value is None:
        return "UNAVAILABLE"

    if value <= DISTANCE_CRITICAL:
        return "CRITICAL"

    if (
        value >= DISTANCE_WARNING_MIN
        and
        value <= DISTANCE_WARNING_MAX
    ):
        return "WARNING"

    return "NORMAL"


# ============================================================
# LM393
# ============================================================

def sound_status(
    duration
):

    duration = number(duration)

    if duration is None:
        return "NORMAL"

    if duration >= SOUND_CRITICAL_SECONDS:
        return "CRITICAL"

    if duration >= SOUND_WARNING_SECONDS:
        return "WARNING"

    return "NORMAL"


# ============================================================
# A3144
# ============================================================

def rpm_status(
    value
):

    value = number(value)

    if value is None:
        return "UNKNOWN"

    if value < RPM_WARNING:
        return "WARNING"

    return "NORMAL"


# ============================================================
# ANALYZE TELEMETRY
# ============================================================

def analyze_telemetry(
    telemetry
):

    temperature = telemetry.get(
        "temperature"
    )

    humidity = telemetry.get(
        "humidity"
    )

    pir_duration = telemetry.get(
        "pir_duration",
        0
    )

    distance = telemetry.get(
        "distance"
    )

    sound_duration = telemetry.get(
        "sound_duration",
        0
    )

    rpm = telemetry.get(
        "rpm"
    )


    statuses = {

        "temperature":
            temperature_status(
                temperature
            ),

        "humidity":
            humidity_status(
                humidity
            ),

        "pir":
            pir_status(
                pir_duration
            ),

        "distance":
            distance_status(
                distance
            ),

        "sound":
            sound_status(
                sound_duration
            ),

        "rpm":
            rpm_status(
                rpm
            ),

        "ina219":
            "INFO"
    }


    issues = []


    # --------------------------------------------------------
    # REAL SENSOR FAULTS
    # --------------------------------------------------------

    if telemetry.get(
        "dht22_fault",
        False
    ):

        issues.append({
            "sensor": "DHT22",
            "parameter": "Temperature/Humidity",
            "severity": "FAULT",
            "message":
                "DHT22 disconnected or unresponsive."
        })


    if telemetry.get(
        "hc_sr04_fault",
        False
    ):

        issues.append({
            "sensor": "HC-SR04",
            "parameter": "Distance",
            "severity": "FAULT",
            "message":
                "HC-SR04 echo signal unavailable after previous valid operation."
        })


    if telemetry.get(
        "a3144_fault",
        False
    ):

        issues.append({
            "sensor": "A3144",
            "parameter": "RPM",
            "severity": "FAULT",
            "message":
                "A3144 Hall signal lost."
        })


    if telemetry.get(
        "ina219_fault",
        False
    ):

        issues.append({
            "sensor": "INA219",
            "parameter": "I2C",
            "severity": "FAULT",
            "message":
                "INA219 is disconnected from the I2C bus."
        })


    # --------------------------------------------------------
    # TEMPERATURE
    # --------------------------------------------------------

    temp_status = statuses[
        "temperature"
    ]

    if temp_status in {
        "WARNING",
        "CRITICAL"
    }:

        issues.append({
            "sensor": "DHT22",
            "parameter": "Temperature",
            "severity": temp_status,
            "value": temperature,
            "message":
                f"Temperature is {temperature} °C."
        })


    # --------------------------------------------------------
    # HUMIDITY
    # --------------------------------------------------------

    humidity_state = statuses[
        "humidity"
    ]

    if humidity_state in {
        "WARNING",
        "CRITICAL"
    }:

        issues.append({
            "sensor": "DHT22",
            "parameter": "Humidity",
            "severity": humidity_state,
            "value": humidity,
            "message":
                f"Humidity is {humidity} % RH."
        })


    # --------------------------------------------------------
    # PIR
    # --------------------------------------------------------

    pir_state = statuses[
        "pir"
    ]

    if pir_state in {
        "WARNING",
        "CRITICAL"
    }:

        issues.append({
            "sensor": "PIR",
            "parameter": "Motion duration",
            "severity": pir_state,
            "value":
                pir_duration,
            "message":
                f"Continuous motion for {pir_duration} seconds."
        })


    # --------------------------------------------------------
    # HC-SR04
    # --------------------------------------------------------

    distance_state = statuses[
        "distance"
    ]

    if distance_state in {
        "WARNING",
        "CRITICAL"
    }:

        issues.append({
            "sensor": "HC-SR04",
            "parameter": "Distance",
            "severity": distance_state,
            "value": distance,
            "message":
                f"Measured distance is {distance} cm."
        })


    # --------------------------------------------------------
    # LM393
    # --------------------------------------------------------

    sound_state = statuses[
        "sound"
    ]

    if sound_state in {
        "WARNING",
        "CRITICAL"
    }:

        issues.append({
            "sensor": "LM393",
            "parameter": "Sound event duration",
            "severity": sound_state,
            "value":
                sound_duration,
            "message":
                f"Sound threshold persisted for {sound_duration} seconds."
        })


    # --------------------------------------------------------
    # RPM
    # --------------------------------------------------------

    rpm_state = statuses[
        "rpm"
    ]

    if rpm_state == "WARNING":

        issues.append({
            "sensor": "A3144",
            "parameter": "RPM",
            "severity": "WARNING",
            "value": rpm,
            "message":
                f"Motor RPM is {rpm}, below the 180 RPM warning threshold."
        })


    # --------------------------------------------------------
    # SYSTEM STATUS
    # --------------------------------------------------------

    highest = "NORMAL"

    for issue in issues:

        if (
            severity_rank(
                issue["severity"]
            )
            >
            severity_rank(
                highest
            )
        ):

            highest = issue[
                "severity"
            ]


    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = 100

    for issue in issues:

        severity = issue[
            "severity"
        ]

        if severity == "WARNING":
            score -= 10

        elif severity == "CRITICAL":
            score -= 25

        elif severity == "FAULT":
            score -= 35


    score = max(
        0,
        min(
            100,
            score
        )
    )


    if highest == "FAULT":
        overall_status = "FAULT"

    elif highest == "CRITICAL":
        overall_status = "CRITICAL"

    elif highest == "WARNING":
        overall_status = "WARNING"

    else:
        overall_status = "NORMAL"


    return {

        "status":
            overall_status,

        "score":
            score,

        "issues":
            issues,

        "statuses":
            statuses,

        "thresholds": {

            "temperature_warning":
                TEMP_WARNING,

            "temperature_critical":
                TEMP_CRITICAL,

            "humidity_warning":
                HUMIDITY_WARNING,

            "humidity_critical":
                HUMIDITY_CRITICAL,

            "pir_warning_seconds":
                PIR_WARNING_SECONDS,

            "pir_critical_seconds":
                PIR_CRITICAL_SECONDS,

            "distance_warning_min":
                DISTANCE_WARNING_MIN,

            "distance_warning_max":
                DISTANCE_WARNING_MAX,

            "distance_critical":
                DISTANCE_CRITICAL,

            "sound_warning_seconds":
                SOUND_WARNING_SECONDS,

            "sound_critical_seconds":
                SOUND_CRITICAL_SECONDS,

            "rpm_warning":
                RPM_WARNING
        }
    }


# ============================================================
# NORMALIZE HEALTH
# ============================================================

def normalize_health(
    result
):

    if not isinstance(
        result,
        dict
    ):

        return {
            "status": "UNKNOWN",
            "score": 0,
            "issues": []
        }

    return {
        "status":
            result.get(
                "status",
                "UNKNOWN"
            ),

        "score":
            result.get(
                "score",
                0
            ),

        "issues":
            result.get(
                "issues",
                []
            ),

        "statuses":
            result.get(
                "statuses",
                {}
            ),

        "thresholds":
            result.get(
                "thresholds",
                {}
            )
    }