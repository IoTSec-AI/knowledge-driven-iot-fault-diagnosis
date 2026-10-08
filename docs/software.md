\# Software Architecture



\## Overview



The software stack connects the IoT sensing platform to MQTT communication, telemetry storage, rule-based diagnosis, web visualization, knowledge retrieval, and local Generative AI.



\## Software Stack



| Layer | Technology | Purpose |

|---|---|---|

| Firmware | Arduino IDE | Develop and upload the IoT firmware |

| Communication | MQTT | Lightweight telemetry messaging |

| Broker | Mosquitto | MQTT message broker |

| MQTT Client | Paho MQTT | Python MQTT publishing/subscribing |

| Backend | Python | Telemetry processing and diagnosis |

| Web Framework | Flask | Dashboard and REST API |

| Database | SQLite | Telemetry storage |

| Data Processing | NumPy, Pandas | Data processing and analysis |

| Frontend | HTML, CSS, JavaScript | Dashboard interface |

| RAG | ChromaDB | Knowledge retrieval |

| Embeddings | Sentence Transformers | Knowledge-base vector representation |

| Local AI | LM Studio | Local LLM inference |

| LLM | Qwen3-VL 4B | Diagnostic explanation |



\## Software Layers



\### 1. Firmware Layer



The IoT firmware reads the connected sensors and controls the motor.



The firmware is responsible for:



\- Reading DHT22 temperature and humidity

\- Reading PIR motion

\- Measuring HC-SR04 distance

\- Monitoring the LM393 sound-event output

\- Detecting A3144 Hall pulses

\- Calculating motor RPM

\- Reading INA219 auxiliary electrical values

\- Controlling the L293D motor driver

\- Performing sensor fault checks

\- Building telemetry JSON

\- Publishing telemetry through MQTT



The firmware is the source of the real-time sensor data used by the rest of the system.



\---



\## 2. MQTT Communication Layer



MQTT provides communication between the IoT controller and the backend.



The telemetry flow is:



```text

IoT Controller

&#x20;     │

&#x20;     │ MQTT Publish

&#x20;     ▼

Mosquitto Broker

&#x20;     │

&#x20;     │ MQTT Subscribe

&#x20;     ▼

Python Telemetry Receiver

