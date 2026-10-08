from backend.health_monitor import analyze_telemetry


def diagnose_telemetry(
    telemetry,
    history=None
):

    health = analyze_telemetry(
        telemetry,
        history
    )

    findings = []

    for issue in health["issues"]:

        findings.append(
            {
                "fault": issue["message"],
                "sensor": issue["sensor"],
                "parameter": issue["parameter"],
                "condition": issue["condition"],
                "value": issue["value"],
                "unit": issue["unit"],
                "severity": issue["severity"]
            }
        )

    return {
        "severity": health["status"],
        "finding_count": len(findings),
        "findings": findings,
        "thresholds": health["thresholds"],
        "derived": health["derived"]
    }