import json
import paho.mqtt.publish as publish

BROKER = "localhost"
PORT = 1883
TOPIC = "sic/iot/telemetry"

payload = {
    "timestamp": "2026-10-01T11:00:00",
    "device_id": "critical_test",
    "temperature": 32,
    "humidity": 55,
    "motion": 0,
    "distance": 40,
    "sound": 0,
    "motor_temperature": 55,
    "vibration": 0.60,
    "voltage": 10.5,
    "current": 1.00,
    "rpm": 160
}

print("=" * 50)
print("FAULT INJECTION TEST")
print("=" * 50)

print("\nTopic:")
print(TOPIC)

print("\nPayload:")
print(json.dumps(payload, indent=4))

print("\nPublishing...")

publish.single(
    TOPIC,
    payload=json.dumps(payload),
    hostname=BROKER,
    port=PORT
)

print("\nSUCCESS: Fault telemetry published.")