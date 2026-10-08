\# Knowledge-Driven IoT Fault Diagnosis Assistant



A knowledge-driven IoT fault diagnosis system that combines real-time sensor telemetry, MQTT communication, rule-based fault monitoring, Retrieval-Augmented Generation (RAG), and a local Generative AI model to support IoT device diagnosis.



The system collects live telemetry from a Bharat Pi-based sensing platform, detects abnormal conditions using deterministic rules, retrieves relevant engineering knowledge, and uses a locally hosted LLM to generate a human-readable diagnostic explanation.



\---



\## Overview



IoT devices can produce large amounts of sensor data, but raw telemetry alone does not explain why an abnormal condition is occurring.



This project combines:



\- Real-time IoT telemetry

\- MQTT communication

\- Sensor health monitoring

\- Rule-based fault detection

\- SQLite telemetry storage

\- Web-based monitoring dashboard

\- Retrieval-Augmented Generation (RAG)

\- Local Generative AI

\- Knowledge-driven diagnostic explanations



The core design principle is:



> \*\*Deterministic rules establish what is happening; RAG provides relevant engineering knowledge; the local LLM explains the condition and recommends checks.\*\*



\---



\## System Architecture



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

