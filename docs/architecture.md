\# System Architecture



\## Overview



The Knowledge-Driven IoT Fault Diagnosis Assistant uses a layered architecture that connects the physical IoT sensing platform to real-time monitoring, deterministic fault detection, knowledge retrieval, and local Generative AI.



\## Architecture Flow



```text

┌─────────────────────────────────────────────────────────────┐

│                    IoT SENSING PLATFORM                    │

│                                                             │

│  DHT22 ─────── Temperature / Humidity                       │

│  PIR ───────── Motion                                       │

│  HC-SR04 ───── Distance                                     │

│  LM393 ─────── Sound Event                                  │

│  A3144 ─────── Motor RPM                                    │

│  INA219 ────── Auxiliary Electrical Load                   │

│  DC Motor ──── Actuator                                     │

│                                                             │

│                     Bharat Pi / Controller                  │

└──────────────────────────┬──────────────────────────────────┘

&#x20;                          │

&#x20;                          │ MQTT

&#x20;                          ▼

&#x20;                 ┌─────────────────┐

&#x20;                 │ MQTT Broker     │

&#x20;                 │   Mosquitto     │

&#x20;                 └────────┬────────┘

&#x20;                          │

&#x20;                          ▼

&#x20;               ┌──────────────────────┐

&#x20;               │ Telemetry Receiver   │

&#x20;               │ Python + Paho MQTT   │

&#x20;               └──────────┬───────────┘

&#x20;                          │

&#x20;                          ▼

&#x20;                   ┌─────────────┐

&#x20;                   │   SQLite    │

&#x20;                   │  Telemetry  │

&#x20;                   └──────┬──────┘

&#x20;                          │

&#x20;            ┌─────────────┴──────────────┐

&#x20;            │                            │

&#x20;            ▼                            ▼

&#x20;  ┌──────────────────┐        ┌─────────────────────┐

&#x20;  │ Rule-Based       │        │ Web Dashboard       │

&#x20;  │ Fault Detection  │        │ Flask + JavaScript  │

&#x20;  └────────┬─────────┘        └─────────────────────┘

&#x20;           │

&#x20;           ▼

&#x20;  ┌──────────────────────────────┐

&#x20;  │ RAG Knowledge Retrieval      │

&#x20;  │ ChromaDB + Knowledge Base    │

&#x20;  └──────────────┬───────────────┘

&#x20;                 │

&#x20;                 ▼

&#x20;  ┌──────────────────────────────┐

&#x20;  │ Local Generative AI          │

&#x20;  │ LM Studio + Qwen3-VL 4B      │

&#x20;  └──────────────┬───────────────┘

&#x20;                 │

&#x20;                 ▼

&#x20;       Knowledge-Driven

&#x20;       Diagnostic Explanation

