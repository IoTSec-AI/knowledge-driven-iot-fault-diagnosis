import sqlite3
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "telemetry.db"


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_id TEXT NOT NULL,

            temperature REAL,
            humidity REAL,
            motion INTEGER,

            distance REAL,
            sound INTEGER,

            voltage REAL,
            current REAL,
            power REAL,

            rpm REAL,
            hall_magnet INTEGER,

            motor_running INTEGER
        )
        """
    )

    connection.commit()

    # ---------------------------------------------------------
    # Migration for older database versions
    # ---------------------------------------------------------

    cursor.execute("PRAGMA table_info(telemetry)")
    existing_columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    required_columns = {
        "power": "REAL",
        "hall_magnet": "INTEGER",
        "motor_running": "INTEGER"
    }

    for column_name, column_type in required_columns.items():

        if column_name not in existing_columns:

            cursor.execute(
                f"""
                ALTER TABLE telemetry
                ADD COLUMN {column_name} {column_type}
                """
            )

    connection.commit()
    connection.close()


def insert_telemetry(data):
    connection = get_connection()

    cursor = connection.cursor()

    timestamp = datetime.now().isoformat(timespec="seconds")

    cursor.execute(
        """
        INSERT INTO telemetry (
            timestamp,
            device_id,
            temperature,
            humidity,
            motion,
            distance,
            sound,
            voltage,
            current,
            power,
            rpm,
            hall_magnet,
            motor_running
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            data.get("device_id", "unknown"),
            data.get("temperature"),
            data.get("humidity"),
            data.get("motion"),
            data.get("distance"),
            data.get("sound"),
            data.get("voltage"),
            data.get("current"),
            data.get("power"),
            data.get("rpm"),
            data.get("hall_magnet"),
            data.get("motor_running", 1),
        )
    )

    connection.commit()

    inserted_id = cursor.lastrowid

    connection.close()

    return inserted_id


def get_latest(limit=1):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM telemetry
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return rows


def get_history(limit=100):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM telemetry
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = [dict(row) for row in cursor.fetchall()]

    connection.close()

    rows.reverse()

    return rows


def get_recent_events(limit=100):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM telemetry
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return rows


initialize_database()