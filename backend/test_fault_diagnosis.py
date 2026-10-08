from fault_diagnosis import diagnose_telemetry


# ---------------------------------------------------------
# WARNING TEST
# ---------------------------------------------------------

warning_data = {
    "motor_temperature": 55,
    "vibration": 0.20,
    "current": 0.50,
    "rpm": 200,
    "voltage": 12.0
}

warning_result = diagnose_telemetry(warning_data)

print("\n========== WARNING TEST ==========")
print("Severity:", warning_result["severity"])
print("Fault count:", warning_result["fault_count"])

for item in warning_result["findings"]:
    print("-", item["fault"])

print("\nPossible causes:")
for cause in warning_result["possible_causes"]:
    print("-", cause)

print("\nRecommended checks:")
for check in warning_result["recommended_checks"]:
    print("-", check)


# ---------------------------------------------------------
# CRITICAL TEST
# ---------------------------------------------------------

critical_data = {
    "motor_temperature": 55,
    "vibration": 0.60,
    "current": 1.00,
    "rpm": 160,
    "voltage": 10.5
}

critical_result = diagnose_telemetry(critical_data)

print("\n========== CRITICAL TEST ==========")
print("Severity:", critical_result["severity"])
print("Fault count:", critical_result["fault_count"])

for item in critical_result["findings"]:
    print("-", item["fault"])

print("\nRelationship analysis:")
for item in critical_result["relationship_findings"]:
    print("-", item)

print("\nPossible causes:")
for cause in critical_result["possible_causes"]:
    print("-", cause)

print("\nRecommended checks:")
for check in critical_result["recommended_checks"]:
    print("-", check)