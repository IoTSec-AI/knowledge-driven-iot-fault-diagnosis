import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "sic/iot/test"


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker. Result code: {reason_code}")
    client.subscribe(TOPIC)
    print(f"Subscribed to: {TOPIC}")


def on_message(client, userdata, msg):
    print(f"Received: {msg.payload.decode()}")


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="sic-python-test"
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to Mosquitto...")

client.connect(BROKER, PORT, 60)

client.loop_forever()