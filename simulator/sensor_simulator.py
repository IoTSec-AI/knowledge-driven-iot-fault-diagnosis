import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


BROKER = "localhost"
PORT = 1883
TOPIC = "sic/iot/telemetry"

DEVICE_ID = "simulator_01"


def generate_telemetry():
    """Generate realistic normal operating values."""

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": DEVICE_ID,

        # DHT22
        "temperature": round(random.uniform(28.0, 34.0), 2),
        "humidity": round(random.uniform(45.0, 65.0), 2),

        # PIR
        "motion": random.choice([0, 0, 0, 1]),

        # HC-SR04
        "distance": round(random.uniform(15.0, 80.0), 2),

        # LM393
        "sound": random.choice([0, 0, 0, 1]),

        # DS18B20 - motor temperature
        "motor_temperature": round(random.uniform(30.0, 42.0), 2),

        # MPU6050 - simplified vibration value
        "vibration": round(random.uniform(0.05, 0.30), 3),

        # INA219
        "voltage": round(random.uniform(11.7, 12.2), 2),
        "current": round(random.uniform(0.25, 0.65), 3),

        # A3144
        "rpm": round(random.uniform(190, 210), 1)
    }


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker: {reason_code}")


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="sic-sensor-simulator"
)

client.on_connect = on_connect

print("Connecting to Mosquitto...")

client.connect(BROKER, PORT, 60)

client.loop_start()

try:
    while True:
        telemetry = generate_telemetry()

        payload = json.dumps(telemetry)

        client.publish(TOPIC, payload)

        print(f"Published: {payload}")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nSimulator stopped.")

finally:
    client.loop_stop()
    client.disconnect()