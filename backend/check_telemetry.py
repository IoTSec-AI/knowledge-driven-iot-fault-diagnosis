from database import get_connection

connection = get_connection()

rows = connection.execute(
    """
    SELECT
        id,
        timestamp,
        device_id,
        temperature,
        motor_temperature,
        vibration,
        current,
        rpm
    FROM telemetry
    ORDER BY id DESC
    LIMIT 10
    """
).fetchall()

print(f"Records found: {len(rows)}")

for row in rows:
    print(dict(row))

connection.close()