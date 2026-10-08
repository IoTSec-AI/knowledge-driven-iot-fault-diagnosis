"""
Knowledge-Driven IoT Fault Diagnosis Assistant
================================================

MQTT Telemetry Receiver

Data flow:

Bharat Pi / ESP32
        |
        | MQTT
        v
Mosquitto Broker
        |
        v
telemetry_receiver.py
        |
        v
SQLite
        |
        v
Flask API
        |
        v
Dashboard

Arduino MQTT configuration:

Broker : localhost
Port   : 1883
Topic  : sic/iot/telemetry

Actual sensors:

1. DHT22 Temperature
2. DHT22 Humidity
3. PIR Motion
4. HC-SR04 Distance
5. LM393 Sound Detection
6. A3144 Hall-Effect Sensor / Motor RPM
7. INA219 auxiliary electrical measurement

Important:

- INA219 measures the small red LED + 10K resistor load.
- INA219 is NOT motor current measurement.
- LM393 is a digital threshold detector.
- PIR is a digital motion detector.
- No MPU6050.
- No DS18B20.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BACKEND_DIR = PROJECT_ROOT / "backend"

DATABASE_PATH = BACKEND_DIR / "telemetry.db"


# ============================================================
# MQTT CONFIGURATION
# ============================================================

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "sic/iot/telemetry"

DEVICE_ID = "bharatpi_01"


# ============================================================
# DATABASE SCHEMA
# ============================================================

REQUIRED_COLUMNS = {
    "timestamp": "TEXT",
    "device_id": "TEXT",

    "temperature": "REAL",
    "humidity": "REAL",

    "motion": "INTEGER",
    "pir_duration": "REAL",

    "distance": "REAL",

    "sound": "INTEGER",
    "sound_duration": "REAL",

    "hall_magnet": "INTEGER",
    "rpm": "REAL",

    "motor_running": "INTEGER",

    "voltage": "REAL",
    "current": "REAL",
    "power": "REAL",

    "fault_detected": "INTEGER",
    "fault_count": "INTEGER",

    "dht22_fault": "INTEGER",
    "hc_sr04_fault": "INTEGER",
    "pir_fault": "INTEGER",
    "lm393_fault": "INTEGER",
    "a3144_fault": "INTEGER",
    "ina219_fault": "INTEGER",

    "fault_summary": "TEXT",
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_database_connection() -> sqlite3.Connection:
    """
    Always open the same database used by app.py.

    The path is absolute and based on this Python file,
    so it does not depend on the directory from which
    the receiver is launched.
    """

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=10,
    )

    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database() -> None:
    """
    Create the telemetry table if necessary.

    Existing telemetry is preserved.
    Missing columns are added automatically.
    """

    BACKEND_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = get_database_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp TEXT,
                device_id TEXT,

                temperature REAL,
                humidity REAL,

                motion INTEGER,
                pir_duration REAL,

                distance REAL,

                sound INTEGER,
                sound_duration REAL,

                hall_magnet INTEGER,
                rpm REAL,

                motor_running INTEGER,

                voltage REAL,
                current REAL,
                power REAL,

                fault_detected INTEGER,
                fault_count INTEGER,

                dht22_fault INTEGER,
                hc_sr04_fault INTEGER,
                pir_fault INTEGER,
                lm393_fault INTEGER,
                a3144_fault INTEGER,
                ina219_fault INTEGER,

                fault_summary TEXT
            )
            """
        )

        cursor.execute(
            "PRAGMA table_info(telemetry)"
        )

        existing_columns = {
            row[1]
            for row in cursor.fetchall()
        }

        for column_name, column_type in REQUIRED_COLUMNS.items():

            if column_name not in existing_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE telemetry
                    ADD COLUMN {column_name} {column_type}
                    """
                )

                print(
                    f"Added database column: {column_name}"
                )

        connection.commit()

    finally:
        connection.close()


# ============================================================
# SAFE CONVERSION
# ============================================================

def safe_float(
    value,
    default=None,
):
    """
    Safely convert a value to float.
    """

    if value is None:
        return default

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value,
    default=0,
):
    """
    Safely convert a value to integer.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return 1 if value else 0

    try:
        return int(float(value))

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_bool(
    value,
) -> int:
    """
    Convert common boolean representations
    to SQLite-compatible 0 or 1.
    """

    if isinstance(value, bool):
        return 1 if value else 0

    if isinstance(value, (int, float)):
        return 1 if value != 0 else 0

    if isinstance(value, str):

        normalized = value.strip().lower()

        if normalized in {
            "true",
            "1",
            "yes",
            "on",
            "detected",
            "active",
        }:
            return 1

    return 0


# ============================================================
# FAULT NORMALIZATION
# ============================================================

def normalize_faults(
    data: dict,
) -> dict:
    """
    Preserve the explicit Arduino fault flags.

    The receiver does not invent sensor faults.
    """

    dht22_fault = safe_bool(
        data.get(
            "dht22_fault",
            False,
        )
    )

    hc_sr04_fault = safe_bool(
        data.get(
            "hc_sr04_fault",
            False,
        )
    )

    pir_fault = safe_bool(
        data.get(
            "pir_fault",
            False,
        )
    )

    lm393_fault = safe_bool(
        data.get(
            "lm393_fault",
            False,
        )
    )

    a3144_fault = safe_bool(
        data.get(
            "a3144_fault",
            False,
        )
    )

    ina219_fault = safe_bool(
        data.get(
            "ina219_fault",
            False,
        )
    )

    explicit_fault_detected = safe_bool(
        data.get(
            "fault_detected",
            False,
        )
    )

    explicit_fault_count = safe_int(
        data.get(
            "fault_count",
            0,
        )
    )

    calculated_fault_count = sum(
        (
            dht22_fault,
            hc_sr04_fault,
            pir_fault,
            lm393_fault,
            a3144_fault,
            ina219_fault,
        )
    )

    fault_count = max(
        explicit_fault_count,
        calculated_fault_count,
    )

    fault_detected = (
        1
        if (
            explicit_fault_detected
            or fault_count > 0
        )
        else 0
    )

    return {
        "fault_detected": fault_detected,
        "fault_count": fault_count,

        "dht22_fault": dht22_fault,
        "hc_sr04_fault": hc_sr04_fault,
        "pir_fault": pir_fault,
        "lm393_fault": lm393_fault,
        "a3144_fault": a3144_fault,
        "ina219_fault": ina219_fault,
    }


# ============================================================
# TELEMETRY EXTRACTION
# ============================================================

def extract_telemetry(
    data: dict,
) -> dict:
    """
    Convert the exact Arduino MQTT JSON payload
    into the SQLite telemetry structure.
    """

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "MQTT payload must be a JSON object."
        )

    timestamp = data.get(
        "timestamp"
    )

    if not timestamp:

        timestamp = datetime.now().isoformat(
            timespec="seconds"
        )

    device_id = data.get(
        "device_id",
        DEVICE_ID,
    )

    faults = normalize_faults(
        data
    )

    fault_summary = data.get(
        "fault_summary",
        "NONE",
    )

    if fault_summary is None:
        fault_summary = "NONE"

    return {

        # ----------------------------------------------------
        # Identity
        # ----------------------------------------------------

        "timestamp": timestamp,

        "device_id": device_id,

        # ----------------------------------------------------
        # DHT22
        # ----------------------------------------------------

        "temperature": safe_float(
            data.get(
                "temperature"
            )
        ),

        "humidity": safe_float(
            data.get(
                "humidity"
            )
        ),

        # ----------------------------------------------------
        # PIR
        # ----------------------------------------------------

        "motion": safe_int(
            data.get(
                "motion",
                0,
            )
        ),

        "pir_duration": safe_float(
            data.get(
                "pir_duration",
                0,
            ),
            0,
        ),

        # ----------------------------------------------------
        # HC-SR04
        # ----------------------------------------------------

        "distance": safe_float(
            data.get(
                "distance"
            )
        ),

        # ----------------------------------------------------
        # LM393
        # ----------------------------------------------------

        "sound": safe_int(
            data.get(
                "sound",
                0,
            )
        ),

        "sound_duration": safe_float(
            data.get(
                "sound_duration",
                0,
            ),
            0,
        ),

        # ----------------------------------------------------
        # A3144
        # ----------------------------------------------------

        "hall_magnet": safe_int(
            data.get(
                "hall_magnet",
                0,
            )
        ),

        "rpm": safe_float(
            data.get(
                "rpm"
            )
        ),

        # ----------------------------------------------------
        # Motor
        # ----------------------------------------------------

        "motor_running": safe_int(
            data.get(
                "motor_running",
                0,
            )
        ),

        # ----------------------------------------------------
        # INA219
        #
        # Auxiliary LED + 10K resistor load
        # ----------------------------------------------------

        "voltage": safe_float(
            data.get(
                "voltage"
            )
        ),

        "current": safe_float(
            data.get(
                "current"
            )
        ),

        "power": safe_float(
            data.get(
                "power"
            )
        ),

        # ----------------------------------------------------
        # Faults
        # ----------------------------------------------------

        "fault_detected": faults[
            "fault_detected"
        ],

        "fault_count": faults[
            "fault_count"
        ],

        "dht22_fault": faults[
            "dht22_fault"
        ],

        "hc_sr04_fault": faults[
            "hc_sr04_fault"
        ],

        "pir_fault": faults[
            "pir_fault"
        ],

        "lm393_fault": faults[
            "lm393_fault"
        ],

        "a3144_fault": faults[
            "a3144_fault"
        ],

        "ina219_fault": faults[
            "ina219_fault"
        ],

        "fault_summary": str(
            fault_summary
        ),
    }


# ============================================================
# SAVE TELEMETRY
# ============================================================

def save_telemetry(
    telemetry: dict,
) -> None:
    """
    Save one telemetry record to SQLite.
    """

    connection = get_database_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO telemetry (

                timestamp,
                device_id,

                temperature,
                humidity,

                motion,
                pir_duration,

                distance,

                sound,
                sound_duration,

                hall_magnet,
                rpm,

                motor_running,

                voltage,
                current,
                power,

                fault_detected,
                fault_count,

                dht22_fault,
                hc_sr04_fault,
                pir_fault,
                lm393_fault,
                a3144_fault,
                ina219_fault,

                fault_summary

            )
            VALUES (
                ?,
                ?,

                ?,
                ?,

                ?,
                ?,

                ?,

                ?,
                ?,

                ?,
                ?,

                ?,

                ?,
                ?,
                ?,

                ?,
                ?,

                ?,
                ?,
                ?,
                ?,
                ?,
                ?,

                ?
            )
            """,
            (
                telemetry["timestamp"],
                telemetry["device_id"],

                telemetry["temperature"],
                telemetry["humidity"],

                telemetry["motion"],
                telemetry["pir_duration"],

                telemetry["distance"],

                telemetry["sound"],
                telemetry["sound_duration"],

                telemetry["hall_magnet"],
                telemetry["rpm"],

                telemetry["motor_running"],

                telemetry["voltage"],
                telemetry["current"],
                telemetry["power"],

                telemetry["fault_detected"],
                telemetry["fault_count"],

                telemetry["dht22_fault"],
                telemetry["hc_sr04_fault"],
                telemetry["pir_fault"],
                telemetry["lm393_fault"],
                telemetry["a3144_fault"],
                telemetry["ina219_fault"],

                telemetry["fault_summary"],
            ),
        )

        connection.commit()

    finally:
        connection.close()


# ============================================================
# PRINT TELEMETRY
# ============================================================

def print_telemetry(
    telemetry: dict,
) -> None:

    print()
    print(
        "=================================================="
    )

    print(
        "             TELEMETRY RECEIVED"
    )

    print(
        "=================================================="
    )

    print(
        f"Timestamp      : "
        f"{telemetry['timestamp']}"
    )

    print(
        f"Device         : "
        f"{telemetry['device_id']}"
    )

    print()

    print(
        f"Temperature    : "
        f"{telemetry['temperature']}"
    )

    print(
        f"Humidity       : "
        f"{telemetry['humidity']}"
    )

    print(
        f"Motion         : "
        f"{telemetry['motion']}"
    )

    print(
        f"PIR Duration   : "
        f"{telemetry['pir_duration']} s"
    )

    print(
        f"Distance       : "
        f"{telemetry['distance']}"
    )

    print(
        f"Sound          : "
        f"{telemetry['sound']}"
    )

    print(
        f"Sound Duration : "
        f"{telemetry['sound_duration']} s"
    )

    print(
        f"Hall Magnet    : "
        f"{telemetry['hall_magnet']}"
    )

    print(
        f"Motor RPM      : "
        f"{telemetry['rpm']}"
    )

    print(
        f"Motor Running  : "
        f"{telemetry['motor_running']}"
    )

    print()

    print(
        f"INA219 Voltage : "
        f"{telemetry['voltage']}"
    )

    print(
        f"INA219 Current : "
        f"{telemetry['current']}"
    )

    print(
        f"INA219 Power   : "
        f"{telemetry['power']}"
    )

    print()

    print(
        f"Fault Detected : "
        f"{telemetry['fault_detected']}"
    )

    print(
        f"Fault Count    : "
        f"{telemetry['fault_count']}"
    )

    print(
        f"DHT22 Fault    : "
        f"{telemetry['dht22_fault']}"
    )

    print(
        f"HC-SR04 Fault  : "
        f"{telemetry['hc_sr04_fault']}"
    )

    print(
        f"PIR Fault      : "
        f"{telemetry['pir_fault']}"
    )

    print(
        f"LM393 Fault    : "
        f"{telemetry['lm393_fault']}"
    )

    print(
        f"A3144 Fault    : "
        f"{telemetry['a3144_fault']}"
    )

    print(
        f"INA219 Fault   : "
        f"{telemetry['ina219_fault']}"
    )

    print(
        f"Fault Summary  : "
        f"{telemetry['fault_summary']}"
    )

    print(
        "=================================================="
    )


# ============================================================
# MQTT CONNECT
# ============================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties,
):
    """
    Subscribe to the Arduino telemetry topic.
    """

    print()

    if reason_code == 0:

        print(
            "MQTT connection established."
        )

        print(
            f"Broker : "
            f"{MQTT_BROKER}:{MQTT_PORT}"
        )

        print(
            f"Topic  : "
            f"{MQTT_TOPIC}"
        )

        result, _ = client.subscribe(
            MQTT_TOPIC
        )

        if result == mqtt.MQTT_ERR_SUCCESS:

            print(
                "MQTT subscription: SUCCESS"
            )

        else:

            print(
                "MQTT subscription: FAILED"
            )

    else:

        print(
            "MQTT connection failed."
        )

        print(
            f"Reason code: {reason_code}"
        )


# ============================================================
# MQTT DISCONNECT
# ============================================================

def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties,
):
    print()

    print(
        "MQTT connection lost."
    )

    print(
        f"Reason code: {reason_code}"
    )


# ============================================================
# MQTT MESSAGE
# ============================================================

def on_message(
    client,
    userdata,
    message,
):
    """
    Receive one Arduino MQTT JSON payload.
    """

    try:

        payload = message.payload.decode(
            "utf-8"
        )

        print()
        print(
            "Raw MQTT payload received."
        )

        data = json.loads(
            payload
        )

        telemetry = extract_telemetry(
            data
        )

        save_telemetry(
            telemetry
        )

        print_telemetry(
            telemetry
        )

    except json.JSONDecodeError as error:

        print()
        print(
            "ERROR: Invalid MQTT JSON."
        )

        print(
            error
        )

        print(
            "Raw payload:"
        )

        print(
            message.payload.decode(
                "utf-8",
                errors="replace",
            )
        )

    except Exception as error:

        print()
        print(
            "ERROR processing telemetry:"
        )

        print(
            error
        )


# ============================================================
# MQTT CLIENT
# ============================================================

def create_mqtt_client():

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="python_telemetry_receiver",
    )

    client.on_connect = on_connect

    client.on_disconnect = on_disconnect

    client.on_message = on_message

    return client


# ============================================================
# MAIN
# ============================================================

def main():

    initialize_database()

    print()
    print(
        "=================================================="
    )

    print(
        "Knowledge-Driven IoT Fault Diagnosis Assistant"
    )

    print(
        "MQTT Telemetry Receiver"
    )

    print(
        "=================================================="
    )

    print(
        f"Broker   : "
        f"{MQTT_BROKER}:{MQTT_PORT}"
    )

    print(
        f"Topic    : "
        f"{MQTT_TOPIC}"
    )

    print(
        f"Database : "
        f"{DATABASE_PATH}"
    )

    print()

    client = create_mqtt_client()

    while True:

        try:

            print(
                "Connecting to MQTT broker..."
            )

            client.connect(
                MQTT_BROKER,
                MQTT_PORT,
                keepalive=60,
            )

            client.loop_forever()

        except KeyboardInterrupt:

            print()
            print(
                "Telemetry receiver stopped."
            )

            try:
                client.disconnect()
            except Exception:
                pass

            break

        except Exception as error:

            print()
            print(
                "MQTT connection error:"
            )

            print(
                error
            )

            print(
                "Retrying in 5 seconds..."
            )

            time.sleep(5)


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":
    main()