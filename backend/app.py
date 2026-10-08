"""
Knowledge-Driven IoT Fault Diagnosis Assistant
================================================

Data flow:

Arduino
   ↓
MQTT / Mosquitto
   ↓
telemetry_receiver.py
   ↓
SQLite telemetry.db
   ↓
Flask API
   ↓
Dashboard
   ↓
RAG + Local LLM

IMPORTANT:
- Arduino code is the source of truth.
- Do not invent sensors.
- Current sensors:
    DHT22
    PIR
    HC-SR04
    LM393
    A3144
    INA219 auxiliary measurement
- No MPU6050.
- No DS18B20.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BACKEND_DIR = PROJECT_ROOT / "backend"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

DATABASE_PATH = BACKEND_DIR / "telemetry.db"

KNOWLEDGE_BASE_PATH = (
    PROJECT_ROOT / "rag" / "knowledge_base.json"
)

# Make project root importable for RAG.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__,
    template_folder=str(
        DASHBOARD_DIR / "templates"
    ),
    static_folder=str(
        DASHBOARD_DIR / "static"
    ),
)


# ============================================================
# DATABASE
# ============================================================

def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=10,
    )

    connection.row_factory = sqlite3.Row

    return connection


def get_latest_telemetry() -> dict[str, Any] | None:

    if not DATABASE_PATH.exists():
        return None

    try:
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT *
                FROM telemetry
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        finally:
            connection.close()

        if row is None:
            return None

        return dict(row)

    except sqlite3.Error as error:

        print(
            f"[DATABASE] Latest telemetry error: {error}"
        )

        return None


def get_recent_telemetry(
    limit: int = 100,
) -> list[dict[str, Any]]:

    try:
        limit = int(limit)

    except (
        TypeError,
        ValueError,
    ):

        limit = 100

    limit = max(
        1,
        min(limit, 1000),
    )

    if not DATABASE_PATH.exists():
        return []

    try:

        connection = get_connection()

        try:

            rows = connection.execute(
                """
                SELECT *
                FROM telemetry
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        finally:

            connection.close()

        return [
            dict(row)
            for row in rows
        ]

    except sqlite3.Error as error:

        print(
            f"[DATABASE] History error: {error}"
        )

        return []


# ============================================================
# VALUE HELPERS
# ============================================================

def number(
    value: Any,
) -> float | None:

    if value is None:
        return None

    if value == "":
        return None

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return None


def truth(
    value: Any,
) -> bool:

    if isinstance(value, bool):
        return value

    if isinstance(
        value,
        (int, float),
    ):
        return value != 0

    return (
        str(value)
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
            "active",
            "detected",
        }
    )


# ============================================================
# ISSUE HELPER
# ============================================================

def add_issue(
    issues: list[dict[str, Any]],
    sensor: str,
    parameter: str,
    condition: str,
    value: Any,
    unit: str,
    severity: str,
    message: str,
) -> None:

    issues.append(
        {
            "sensor": sensor,
            "parameter": parameter,
            "condition": condition,
            "value": value,
            "unit": unit,
            "severity": severity,
            "message": message,
        }
    )


# ============================================================
# DATA QUALITY
# ============================================================

def build_data_quality(
    telemetry: dict[str, Any],
) -> dict[str, Any]:

    fields = [
        "temperature",
        "humidity",
        "motion",
        "distance",
        "sound",
        "rpm",
    ]

    missing = []

    for field in fields:

        if telemetry.get(field) is None:
            missing.append(field)

    valid = (
        len(fields)
        - len(missing)
    )

    score = round(
        valid / len(fields) * 100
    )

    return {
        "score": score,
        "valid_fields": valid,
        "total_fields": len(fields),
        "missing_fields": missing,
    }


# ============================================================
# HEALTH / RULE ENGINE
# ============================================================

def calculate_health(
    telemetry: dict[str, Any],
) -> dict[str, Any]:

    issues: list[
        dict[str, Any]
    ] = []

    temperature = number(
        telemetry.get(
            "temperature"
        )
    )

    humidity = number(
        telemetry.get(
            "humidity"
        )
    )

    distance = number(
        telemetry.get(
            "distance"
        )
    )

    rpm = number(
        telemetry.get(
            "rpm"
        )
    )

    pir_duration = number(
        telemetry.get(
            "pir_duration"
        )
    )

    sound_duration = number(
        telemetry.get(
            "sound_duration"
        )
    )

    # --------------------------------------------------------
    # Explicit Arduino faults
    # --------------------------------------------------------

    if truth(
        telemetry.get(
            "dht22_fault"
        )
    ):

        add_issue(
            issues,
            "DHT22",
            "Sensor",
            "Arduino fault",
            True,
            "",
            "CRITICAL",
            "DHT22 reported an invalid or unresponsive condition.",
        )

    if truth(
        telemetry.get(
            "hc_sr04_fault"
        )
    ):

        add_issue(
            issues,
            "HC-SR04",
            "Sensor",
            "Arduino fault",
            True,
            "",
            "CRITICAL",
            "HC-SR04 reported echo failure after previous valid operation.",
        )

    if truth(
        telemetry.get(
            "a3144_fault"
        )
    ):

        add_issue(
            issues,
            "A3144",
            "Hall signal",
            "Arduino fault",
            True,
            "",
            "CRITICAL",
            "A3144 Hall/RPM signal loss was reported.",
        )

    if truth(
        telemetry.get(
            "ina219_fault"
        )
    ):

        add_issue(
            issues,
            "INA219",
            "I2C",
            "Arduino fault",
            True,
            "",
            "CRITICAL",
            "INA219 is not detected on the I2C bus.",
        )

    # --------------------------------------------------------
    # DHT22
    # --------------------------------------------------------

    if temperature is not None:

        if temperature > 45:

            add_issue(
                issues,
                "DHT22",
                "Temperature",
                ">45 °C",
                temperature,
                "°C",
                "CRITICAL",
                "Temperature exceeds the critical threshold.",
            )

        elif temperature > 35:

            add_issue(
                issues,
                "DHT22",
                "Temperature",
                ">35 °C",
                temperature,
                "°C",
                "WARNING",
                "Temperature exceeds the warning threshold.",
            )

    if humidity is not None:

        if humidity > 85:

            add_issue(
                issues,
                "DHT22",
                "Humidity",
                ">85 % RH",
                humidity,
                "% RH",
                "CRITICAL",
                "Humidity exceeds the critical threshold.",
            )

        elif humidity > 70:

            add_issue(
                issues,
                "DHT22",
                "Humidity",
                ">70 % RH",
                humidity,
                "% RH",
                "WARNING",
                "Humidity exceeds the warning threshold.",
            )

    # --------------------------------------------------------
    # PIR
    # --------------------------------------------------------

    if pir_duration is not None:

        if pir_duration >= 30:

            add_issue(
                issues,
                "PIR",
                "Motion",
                ">=30 seconds",
                pir_duration,
                "s",
                "CRITICAL",
                "Motion has remained continuously active for at least 30 seconds.",
            )

        elif pir_duration >= 10:

            add_issue(
                issues,
                "PIR",
                "Motion",
                ">=10 seconds",
                pir_duration,
                "s",
                "WARNING",
                "Motion has remained continuously active for at least 10 seconds.",
            )

    # --------------------------------------------------------
    # HC-SR04
    # --------------------------------------------------------

    if distance is not None:

        if distance <= 10:

            add_issue(
                issues,
                "HC-SR04",
                "Distance",
                "<=10 cm",
                distance,
                "cm",
                "CRITICAL",
                "Object is inside the critical distance range.",
            )

        elif distance <= 20:

            add_issue(
                issues,
                "HC-SR04",
                "Distance",
                "10–20 cm",
                distance,
                "cm",
                "WARNING",
                "Object is inside the warning distance range.",
            )

    # --------------------------------------------------------
    # LM393
    # --------------------------------------------------------

    if sound_duration is not None:

        if sound_duration >= 5:

            add_issue(
                issues,
                "LM393",
                "Sound",
                ">=5 seconds",
                sound_duration,
                "s",
                "CRITICAL",
                "Sound threshold has remained active for at least 5 seconds.",
            )

        elif sound_duration >= 2:

            add_issue(
                issues,
                "LM393",
                "Sound",
                ">=2 seconds",
                sound_duration,
                "s",
                "WARNING",
                "Sound threshold has remained active for at least 2 seconds.",
            )

    # --------------------------------------------------------
    # A3144 / RPM
    # --------------------------------------------------------

    if (
        truth(
            telemetry.get(
                "motor_running"
            )
        )
        and rpm is not None
        and rpm < 180
    ):

        add_issue(
            issues,
            "A3144",
            "Motor RPM",
            "<180 RPM",
            rpm,
            "RPM",
            "WARNING",
            "Motor RPM is below the project threshold.",
        )

    # --------------------------------------------------------
    # Overall status
    # --------------------------------------------------------

    severities = [
        str(
            item["severity"]
        ).upper()
        for item in issues
    ]

    if "CRITICAL" in severities:

        status = "CRITICAL"

    elif "WARNING" in severities:

        status = "WARNING"

    else:

        status = "NORMAL"

    score = 100

    for severity in severities:

        if severity == "CRITICAL":

            score -= 25

        elif severity == "WARNING":

            score -= 10

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    return {
        "status": status,
        "score": score,
        "issues": issues,
        "data_quality": build_data_quality(
            telemetry
        ),
        "thresholds": {
            "temperature_warning": 35,
            "temperature_critical": 45,
            "humidity_warning": 70,
            "humidity_critical": 85,
            "distance_warning_min": 10,
            "distance_warning_max": 20,
            "distance_critical": 10,
            "rpm_warning": 180,
            "pir_warning_seconds": 10,
            "pir_critical_seconds": 30,
            "sound_warning_seconds": 2,
            "sound_critical_seconds": 5,
        },
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    return render_template(
        "index.html"
    )


# ============================================================
# LATEST
# ============================================================

@app.route(
    "/api/latest"
)
def api_latest():

    latest = (
        get_latest_telemetry()
    )

    if latest is None:

        return jsonify(
            {
                "available": False,
                "message": (
                    "No telemetry data available yet."
                ),
            }
        )

    health = calculate_health(
        latest
    )

    return jsonify(
        {
            "available": True,
            "telemetry": latest,
            "health": health,
            "health_status": health[
                "status"
            ],
            "health_score": health[
                "score"
            ],
            "health_issues": health[
                "issues"
            ],
            **latest,
        }
    )


# ============================================================
# HISTORY
# ============================================================

@app.route(
    "/api/history"
)
def api_history():

    limit = request.args.get(
        "limit",
        default=100,
        type=int,
    )

    return jsonify(
        get_recent_telemetry(
            limit
        )
    )


@app.route(
    "/api/recent"
)
def api_recent():

    return jsonify(
        get_recent_telemetry(
            100
        )
    )


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/api/health"
)
def api_health():

    latest = (
        get_latest_telemetry()
    )

    if latest is None:

        return jsonify(
            {
                "status": "UNKNOWN",
                "score": 0,
                "issues": [],
            }
        )

    return jsonify(
        calculate_health(
            latest
        )
    )


# ============================================================
# STATUS
# ============================================================

@app.route(
    "/api/status"
)
def api_status():

    latest = (
        get_latest_telemetry()
    )

    return jsonify(
        {
            "server": "online",
            "database_exists": DATABASE_PATH.exists(),
            "database": str(
                DATABASE_PATH
            ),
            "telemetry_available": (
                latest is not None
            ),
            "device_id": (
                latest.get(
                    "device_id"
                )
                if latest
                else None
            ),
            "last_update": (
                latest.get(
                    "timestamp"
                )
                if latest
                else None
            ),
        }
    )


# ============================================================
# KNOWLEDGE BASE
# ============================================================

@app.route(
    "/api/knowledge"
)
def api_knowledge():

    if not KNOWLEDGE_BASE_PATH.exists():

        return jsonify([])

    try:

        data = json.loads(
            KNOWLEDGE_BASE_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception as error:

        print(
            "[KNOWLEDGE] Error:",
            error,
        )

        return jsonify([])

    if isinstance(
        data,
        list,
    ):

        return jsonify(data)

    if isinstance(
        data,
        dict,
    ):

        if isinstance(
            data.get(
                "knowledge"
            ),
            list,
        ):

            return jsonify(
                data["knowledge"]
            )

        if isinstance(
            data.get(
                "entries"
            ),
            list,
        ):

            return jsonify(
                data["entries"]
            )

        return jsonify(
            [data]
        )

    return jsonify([])


# ============================================================
# RAW TELEMETRY
# ============================================================

@app.route(
    "/api/raw"
)
def api_raw():

    latest = (
        get_latest_telemetry()
    )

    if latest is None:

        return jsonify(
            {
                "available": False
            }
        )

    return jsonify(
        {
            "available": True,
            "payload": latest,
        }
    )


# ============================================================
# AI DIAGNOSIS
# ============================================================

@app.route(
    "/api/ai-diagnosis",
    methods=["POST"],
)
def api_ai_diagnosis():

    latest = (
        get_latest_telemetry()
    )

    if latest is None:

        return jsonify(
            {
                "success": False,
                "error": (
                    "No telemetry data is available."
                ),
            }
        ), 400

    health = calculate_health(
        latest
    )

    try:

        from rag.diagnostic_assistant import (
            generate_diagnosis
        )

    except Exception as error:

        print(
            "[AI] Import error:",
            error,
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Could not load "
                    "rag.diagnostic_assistant: "
                    f"{error}"
                ),
            }
        ), 500

    try:

        result = generate_diagnosis(
            latest,
            health,
        )

    except Exception as error:

        print(
            "[AI] Diagnosis error:",
            error,
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    f"AI diagnosis failed: {error}"
                ),
            }
        ), 500

    if isinstance(
        result,
        dict,
    ):

        answer = (
            result.get(
                "answer"
            )
            or result.get(
                "diagnosis"
            )
            or result.get(
                "response"
            )
            or result.get(
                "result"
            )
            or "No diagnosis generated."
        )

        response = dict(
            result
        )

        response[
            "success"
        ] = True

        response[
            "answer"
        ] = answer

        response[
            "diagnosis"
        ] = answer

        response[
            "health"
        ] = health

        response[
            "telemetry"
        ] = latest

        return jsonify(
            response
        )

    answer = str(
        result
    )

    return jsonify(
        {
            "success": True,
            "answer": answer,
            "diagnosis": answer,
            "health": health,
            "telemetry": latest,
        }
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print(
        "Knowledge-Driven IoT Fault Diagnosis Assistant"
    )
    print("=" * 70)
    print(
        "Dashboard : http://127.0.0.1:5000"
    )
    print(
        "Latest API: http://127.0.0.1:5000/api/latest"
    )
    print(
        f"Database  : {DATABASE_PATH}"
    )
    print("=" * 70)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )