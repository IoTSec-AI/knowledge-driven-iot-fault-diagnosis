\# RAG Pipeline



\## Overview



The Knowledge-Driven IoT Fault Diagnosis Assistant uses Retrieval-Augmented Generation (RAG) to connect live IoT telemetry with project-specific engineering knowledge.



The RAG layer provides contextual information to the local Generative AI model instead of relying only on the model's general knowledge.



\## RAG Architecture



```text

┌──────────────────────┐

│   Live Telemetry     │

└──────────┬───────────┘

&#x20;          │

&#x20;          ▼

┌──────────────────────┐

│ Rule-Based Diagnosis │

└──────────┬───────────┘

&#x20;          │

&#x20;          ▼

┌──────────────────────┐

│ Detected Condition   │

└──────────┬───────────┘

&#x20;          │

&#x20;          ▼

┌──────────────────────┐

│ Knowledge Retrieval  │

│                      │

│ ChromaDB + Embedding │

└──────────┬───────────┘

&#x20;          │

&#x20;          ▼

┌──────────────────────┐

│ Retrieved Engineering│

│ Knowledge            │

└──────────┬───────────┘

&#x20;          │

&#x20;          ▼

┌──────────────────────┐

│ Local LLM            │

│ Qwen3-VL 4B          │

└──────────┬───────────┘

&#x20;          │

&#x20;          ▼

┌──────────────────────┐

│ Diagnostic Response  │

└──────────────────────┘

