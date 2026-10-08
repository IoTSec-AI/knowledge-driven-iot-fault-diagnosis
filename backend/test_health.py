from health_monitor import analyze_telemetry


normal_data = {
    "motor_temperature": 36.5,
    "vibration": 0.18,
    "current": 0.45,
    "rpm": 201,
    "voltage": 11.9
}


fault_data = {
    "motor_temperature": 63.5,
    "vibration": 0.82,
    "current": 1.15,
    "rpm": 155,
    "voltage": 10.6
}


print("NORMAL TEST:")
print(analyze_telemetry(normal_data))

print("\nFAULT TEST:")
print(analyze_telemetry(fault_data))