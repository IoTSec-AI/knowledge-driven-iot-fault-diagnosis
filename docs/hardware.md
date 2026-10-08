\# Hardware Architecture



\## Overview



The physical prototype uses a Bharat Pi-based IoT sensing and actuator platform. The system collects environmental, motion, distance, sound, rotational, and auxiliary electrical telemetry while controlling a 12V DC geared motor.



\## Hardware Components



| Component | Quantity | Purpose |

|---|---:|---|

| Bharat Pi | 1 | Main IoT controller |

| DHT22 | 1 | Temperature and humidity sensing |

| PIR Motion Sensor | 1 | Motion detection |

| HC-SR04 | 1 | Distance measurement |

| LM393 Sound Detection Module | 1 | Digital sound-event detection |

| A3144 Hall-Effect Sensor | 1 | Motor rotation / RPM detection |

| 12V DC Geared Motor | 1 | Actuator |

| L293D Motor Driver | 1 | Motor control |

| INA219 | 1 | Auxiliary electrical measurement |

| 12V 1A DC Adapter | 1 | Power supply |

| Breadboard | 1 | Prototyping |

| Jumper Wires | — | Electrical connections |



\## Sensor Roles



\### DHT22



Measures:



\- Temperature

\- Relative humidity



These values are used for environmental monitoring and threshold-based diagnosis.



\### PIR Motion Sensor



Detects whether motion is present in the monitored area.



The system also evaluates motion persistence because a short motion event and prolonged continuous motion have different diagnostic significance.



\### HC-SR04



Measures the distance between the sensor and an object.



The configured software measurement range is:



```text

2 cm – 400 cm

