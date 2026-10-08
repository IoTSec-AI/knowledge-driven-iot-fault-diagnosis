\# Fault Detection



\## Overview



The fault-detection layer identifies abnormal sensor conditions and sensor-health problems using deterministic rules.



The purpose of this layer is to establish the factual system condition before the RAG and local LLM components provide contextual explanation.



\## Detection Architecture



```text

Live Telemetry

&#x20;     │

&#x20;     ▼

Sensor Status / Fault Fields

&#x20;     │

&#x20;     ▼

Rule-Based Evaluation

&#x20;     │

&#x20;     ├───────────────┐

&#x20;     │               │

&#x20;     ▼               ▼

Normal           Abnormal

&#x20;                     │

&#x20;                     ▼

&#x20;              Fault / Warning

&#x20;                     │

&#x20;                     ▼

&#x20;              RAG + Local LLM

