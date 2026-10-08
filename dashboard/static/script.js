"use strict";


// ============================================================
// CONFIGURATION
// ============================================================

const REFRESH_INTERVAL = 2000;


// ============================================================
// HELPERS
// ============================================================

function getElement(id) {
    return document.getElementById(id);
}


function toNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return null;
    }


    const number = Number(
        value
    );


    return Number.isFinite(
        number
    )
        ? number
        : null;
}


function formatNumber(
    value,
    decimals = 2
) {

    const number =
        toNumber(value);


    if (number === null) {
        return "--";
    }


    return number.toFixed(
        decimals
    );
}


function setText(
    id,
    value
) {

    const element =
        getElement(id);


    if (!element) {
        return;
    }


    element.textContent =
        value === null ||
        value === undefined
            ? "--"
            : value;
}


// ============================================================
// NORMALIZE API DATA
// ============================================================

function normalizeTelemetry(
    response
) {

    if (
        !response ||
        typeof response !== "object"
    ) {
        return null;
    }


    const data =
        response.telemetry &&
        typeof response.telemetry === "object"

            ? response.telemetry

            : response;


    return {

        timestamp:
            data.timestamp ?? null,

        device_id:
            data.device_id ??
            "bharatpi_01",


        // DHT22

        temperature:
            toNumber(
                data.temperature
            ),

        temperature_status:
            data.temperature_status ??
            "FAULT",


        humidity:
            toNumber(
                data.humidity
            ),

        humidity_status:
            data.humidity_status ??
            "FAULT",


        // PIR

        motion:
            toNumber(
                data.motion
            ),

        pir_duration:
            toNumber(
                data.pir_duration
            ),

        pir_status:
            data.pir_status ??
            "NORMAL",


        // HC-SR04

        distance:
            toNumber(
                data.distance
            ),

        distance_status:
            data.distance_status ??
            "UNAVAILABLE",


        // LM393

        sound:
            toNumber(
                data.sound
            ),

        sound_duration:
            toNumber(
                data.sound_duration
            ),

        sound_status:
            data.sound_status ??
            "NORMAL",


        // A3144

        hall_magnet:
            toNumber(
                data.hall_magnet
            ),

        rpm:
            toNumber(
                data.rpm
            ),

        rpm_status:
            data.rpm_status ??
            "NORMAL",


        // Motor

        motor_running:
            toNumber(
                data.motor_running
            ),


        // INA219

        voltage:
            toNumber(
                data.voltage
            ),

        current:
            toNumber(
                data.current
            ),

        power:
            toNumber(
                data.power
            ),

        ina219_status:
            data.ina219_status ??
            "INFO",


        // Faults

        fault_detected:
            data.fault_detected === true ||
            toNumber(
                data.fault_detected
            ) === 1,

        fault_count:
            toNumber(
                data.fault_count
            ) ?? 0,

        dht22_fault:
            data.dht22_fault === true ||
            toNumber(
                data.dht22_fault
            ) === 1,

        hc_sr04_fault:
            data.hc_sr04_fault === true ||
            toNumber(
                data.hc_sr04_fault
            ) === 1,

        pir_fault:
            data.pir_fault === true ||
            toNumber(
                data.pir_fault
            ) === 1,

        lm393_fault:
            data.lm393_fault === true ||
            toNumber(
                data.lm393_fault
            ) === 1,

        a3144_fault:
            data.a3144_fault === true ||
            toNumber(
                data.a3144_fault
            ) === 1,

        ina219_fault:
            data.ina219_fault === true ||
            toNumber(
                data.ina219_fault
            ) === 1,

        fault_summary:
            data.fault_summary ??
            "NONE"
    };
}


// ============================================================
// LIVE TELEMETRY PANEL
// ============================================================

function createLivePanel() {

    let panel =
        getElement(
            "live-telemetry-panel"
        );


    if (panel) {
        return panel;
    }


    panel =
        document.createElement(
            "section"
        );


    panel.id =
        "live-telemetry-panel";


    panel.innerHTML = `

        <div class="live-panel-header">

            <div>

                <div class="live-panel-label">
                    LIVE IOT TELEMETRY
                </div>

                <h2>
                    Bharat Pi Sensor Data
                </h2>

            </div>


            <div
                id="live-connection-status"
                class="live-connection-status"
            >
                WAITING FOR DATA
            </div>

        </div>


        <div
            id="live-telemetry-grid"
            class="live-telemetry-grid"
        >
        </div>


        <div class="live-panel-footer">

            <span>
                Device:
                <strong id="live-device">
                    --
                </strong>
            </span>


            <span>
                Last update:
                <strong id="live-time">
                    --
                </strong>
            </span>


            <span>
                Faults:
                <strong id="live-fault-count">
                    0
                </strong>
            </span>

        </div>

    `;


    const main =
        document.querySelector(
            ".main-content"
        ) ||
        document.querySelector(
            "main"
        ) ||
        document.body;


    main.prepend(
        panel
    );


    createLivePanelStyle();


    return panel;
}


// ============================================================
// LIVE PANEL STYLE
// ============================================================

function createLivePanelStyle() {

    if (
        getElement(
            "live-telemetry-style"
        )
    ) {
        return;
    }


    const style =
        document.createElement(
            "style"
        );


    style.id =
        "live-telemetry-style";


    style.textContent = `

        #live-telemetry-panel {

            margin: 20px;

            padding: 20px;

            border-radius: 16px;

            background:
                #111827;

            color:
                #f9fafb;

            box-shadow:
                0 8px 30px
                rgba(0,0,0,0.22);

            font-family:
                Arial,
                sans-serif;

        }


        .live-panel-header {

            display: flex;

            justify-content:
                space-between;

            align-items:
                center;

            gap: 20px;

            flex-wrap: wrap;

            margin-bottom: 18px;

        }


        .live-panel-label {

            font-size:
                11px;

            letter-spacing:
                1.2px;

            opacity:
                0.65;

        }


        .live-panel-header h2 {

            margin:
                5px 0 0;

            font-size:
                22px;

        }


        .live-connection-status {

            padding:
                8px 14px;

            border-radius:
                20px;

            background:
                #92400e;

            font-size:
                12px;

        }


        .live-telemetry-grid {

            display:
                grid;

            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(
                        145px,
                        1fr
                    )
                );

            gap:
                12px;

        }


        .live-card {

            padding:
                15px;

            border:
                1px solid
                #374151;

            border-radius:
                12px;

            background:
                #1f2937;

        }


        .live-card-title {

            font-size:
                12px;

            opacity:
                0.65;

            margin-bottom:
                7px;

        }


        .live-card-value {

            font-size:
                23px;

            font-weight:
                700;

        }


        .live-card-unit {

            font-size:
                11px;

            opacity:
                0.65;

            margin-left:
                4px;

        }


        .live-card-status {

            margin-top:
                7px;

            font-size:
                10px;

            letter-spacing:
                0.7px;

            opacity:
                0.65;

        }


        .live-panel-footer {

            display:
                flex;

            gap:
                24px;

            flex-wrap:
                wrap;

            margin-top:
                18px;

            padding-top:
                14px;

            border-top:
                1px solid
                #374151;

            font-size:
                12px;

            opacity:
                0.8;

        }

    `;


    document.head.appendChild(
        style
    );
}


// ============================================================
// CREATE CARD
// ============================================================

function createCard(
    title,
    value,
    unit,
    status
) {

    return `

        <div class="live-card">

            <div class="live-card-title">
                ${title}
            </div>


            <div class="live-card-value">

                ${value}

                <span
                    class="live-card-unit"
                >
                    ${unit}
                </span>

            </div>


            <div
                class="live-card-status"
            >
                ${status}
            </div>

        </div>

    `;
}


// ============================================================
// UPDATE LIVE PANEL
// ============================================================

function updateLivePanel(
    telemetry
) {

    createLivePanel();


    const grid =
        getElement(
            "live-telemetry-grid"
        );


    if (!grid) {
        return;
    }


    grid.innerHTML = [

        createCard(
            "Temperature",
            formatNumber(
                telemetry.temperature,
                1
            ),
            "°C",
            telemetry.temperature_status
        ),


        createCard(
            "Humidity",
            formatNumber(
                telemetry.humidity,
                1
            ),
            "% RH",
            telemetry.humidity_status
        ),


        createCard(
            "PIR Motion",
            telemetry.motion === 1
                ? "DETECTED"
                : "NONE",
            "",
            telemetry.pir_status
        ),


        createCard(
            "Distance",
            formatNumber(
                telemetry.distance,
                1
            ),
            "cm",
            telemetry.distance_status
        ),


        createCard(
            "Sound",
            telemetry.sound === 1
                ? "ACTIVE"
                : "NORMAL",
            "",
            telemetry.sound_status
        ),


        createCard(
            "Motor RPM",
            formatNumber(
                telemetry.rpm,
                0
            ),
            "RPM",
            telemetry.rpm_status
        ),


        createCard(
            "INA219 Voltage",
            formatNumber(
                telemetry.voltage,
                3
            ),
            "V",
            telemetry.ina219_status
        ),


        createCard(
            "INA219 Current",
            formatNumber(
                telemetry.current,
                3
            ),
            "mA",
            telemetry.ina219_status
        ),


        createCard(
            "INA219 Power",
            formatNumber(
                telemetry.power,
                3
            ),
            "mW",
            telemetry.ina219_status
        ),


        createCard(
            "Motor",
            telemetry.motor_running === 1
                ? "RUNNING"
                : "STOPPED",
            "",
            telemetry.motor_running === 1
                ? "NORMAL"
                : "INFO"
        )

    ].join("");


    const connection =
        getElement(
            "live-connection-status"
        );


    if (connection) {

        connection.textContent =
            "LIVE • MQTT → SQLite → API";

        connection.style.background =
            "#065f46";
    }


    setText(
        "live-device",
        telemetry.device_id
    );


    setText(
        "live-time",
        telemetry.timestamp
    );


    setText(
        "live-fault-count",
        telemetry.fault_count
    );
}


// ============================================================
// UPDATE EXISTING DASHBOARD IDs
// ============================================================

function updateExistingDashboard(
    telemetry
) {

    // --------------------------------------------------------
    // Existing parameter cards
    // --------------------------------------------------------

    setText(
        "motor-temperature",
        formatNumber(
            telemetry.temperature,
            1
        )
    );


    setText(
        "vibration",
        formatNumber(
            telemetry.humidity,
            1
        )
    );


    setText(
        "current",
        formatNumber(
            telemetry.distance,
            1
        )
    );


    setText(
        "rpm",
        formatNumber(
            telemetry.rpm,
            0
        )
    );


    setText(
        "voltage",
        telemetry.sound === 1
            ? "ACTIVE"
            : "NORMAL"
    );


    // --------------------------------------------------------
    // Environment
    // --------------------------------------------------------

    setText(
        "temperature",
        `${formatNumber(
            telemetry.temperature,
            1
        )} °C`
    );


    setText(
        "humidity",
        `${formatNumber(
            telemetry.humidity,
            1
        )} % RH`
    );


    setText(
        "motion",
        telemetry.motion === 1
            ? "DETECTED"
            : "NONE"
    );


    setText(
        "distance",
        `${formatNumber(
            telemetry.distance,
            1
        )} cm`
    );


    setText(
        "sound",
        telemetry.sound === 1
            ? "ACTIVE"
            : "NORMAL"
    );


    // --------------------------------------------------------
    // Status fields
    // --------------------------------------------------------

    setText(
        "motor-temp-state",
        telemetry.temperature_status
    );


    setText(
        "vibration-state",
        telemetry.humidity_status
    );


    setText(
        "current-state",
        telemetry.distance_status
    );


    setText(
        "rpm-state",
        telemetry.rpm_status
    );


    setText(
        "voltage-state",
        telemetry.sound_status
    );


    // --------------------------------------------------------
    // Device information
    // --------------------------------------------------------

    setText(
        "device-id",
        telemetry.device_id
    );


    setText(
        "last-update",
        telemetry.timestamp
    );


    setText(
        "active-fault-count",
        telemetry.fault_count
    );


    setText(
        "fault-summary",
        telemetry.fault_summary
    );


    // --------------------------------------------------------
    // Large dashboard values
    // --------------------------------------------------------

    setText(
        "large-motor-temperature",
        formatNumber(
            telemetry.temperature,
            1
        )
    );


    setText(
        "large-vibration",
        formatNumber(
            telemetry.humidity,
            1
        )
    );


    setText(
        "large-current",
        formatNumber(
            telemetry.distance,
            1
        )
    );


    setText(
        "large-rpm",
        formatNumber(
            telemetry.rpm,
            0
        )
    );


    setText(
        "large-voltage",
        telemetry.sound === 1
            ? "ACTIVE"
            : "NORMAL"
    );
}


// ============================================================
// HEALTH
// ============================================================

function updateHealth(
    health
) {

    if (!health) {
        return;
    }


    setText(
        "health-status",
        health.status
    );


    setText(
        "health-score",
        Math.round(
            toNumber(
                health.score
            ) ?? 0
        )
    );


    if (
        Array.isArray(
            health.issues
        )
    ) {

        setText(
            "active-fault-count",
            health.issues.length
        );
    }
}


// ============================================================
// LOAD LATEST TELEMETRY
// ============================================================

async function loadLatestTelemetry() {

    try {

        const response =
            await fetch(
                "/api/latest",
                {
                    cache:
                        "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        if (
            !data.available
        ) {

            createLivePanel();


            const connection =
                getElement(
                    "live-connection-status"
                );


            if (connection) {

                connection.textContent =
                    "WAITING FOR MQTT TELEMETRY";

                connection.style.background =
                    "#92400e";
            }


            return;
        }


        const telemetry =
            normalizeTelemetry(
                data
            );


        if (!telemetry) {

            throw new Error(
                "Invalid telemetry data."
            );
        }


        updateLivePanel(
            telemetry
        );


        updateExistingDashboard(
            telemetry
        );


        updateHealth(
            data.health
        );


    } catch (error) {

        console.error(
            "Dashboard telemetry error:",
            error
        );


        createLivePanel();


        const connection =
            getElement(
                "live-connection-status"
            );


        if (connection) {

            connection.textContent =
                "API CONNECTION ERROR";

            connection.style.background =
                "#991b1b";
        }
    }
}


// ============================================================
// START DASHBOARD
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        createLivePanel();


        loadLatestTelemetry();


        setInterval(
            loadLatestTelemetry,
            REFRESH_INTERVAL
        );

    }
);