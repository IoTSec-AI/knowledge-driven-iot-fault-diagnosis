\# MQTT Protocol



\## Overview



MQTT is the communication layer between the IoT sensing platform and the backend system.



The IoT controller publishes telemetry to a Mosquitto MQTT broker. The Python backend subscribes to the telemetry topic, processes the received JSON payload, and stores the data in SQLite.



\## Communication Flow



```text

┌──────────────────────┐

│   IoT Controller     │

│                      │

│ Sensors + Motor      │

└──────────┬───────────┘

&#x20;          │

&#x20;          │ MQTT Publish

&#x20;          ▼

┌──────────────────────┐

│  Mosquitto Broker    │

│                      │

│ Topic:               │

│ sic/iot/telemetry    │

└──────────┬───────────┘

&#x20;          │

&#x20;          │ MQTT Subscribe

&#x20;          ▼

┌──────────────────────┐

│ Python Telemetry     │

│ Receiver             │

└──────────┬───────────┘

&#x20;          │

&#x20;          ▼

&#x20;     SQLite Database

