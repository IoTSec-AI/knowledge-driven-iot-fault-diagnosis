#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <Adafruit_INA219.h>

// ============================================================
// KNOWLEDGE-DRIVEN IoT FAULT DIAGNOSIS ASSISTANT
// ============================================================


// ============================================================
// WIFI / MQTT
// ============================================================

const char* WIFI_SSID = "------";
const char* WIFI_PASSWORD = "------";

const char* MQTT_BROKER = "-------";
const int MQTT_PORT = 1883;

const char* MQTT_TOPIC = "sic/iot/telemetry";

const char* DEVICE_ID = "bharatpi_01";


// ============================================================
// PIN CONFIGURATION
// ============================================================

#define PIR_PIN 27

#define TRIG_PIN 25
#define ECHO_PIN 26

#define SOUND_PIN 14

#define HALL_PIN 33

#define DHT_PIN 13
#define DHT_TYPE DHT22

#define SDA_PIN 21
#define SCL_PIN 22

#define MOTOR_IN3 23
#define MOTOR_IN4 19


// ============================================================
// TIMING
// ============================================================

const unsigned long TELEMETRY_INTERVAL = 2000;

const unsigned long DHT_FAILURE_LIMIT = 3;

const unsigned long HC_SR04_FAILURE_LIMIT = 3;

const unsigned long HALL_NO_PULSE_TIMEOUT = 5000;

const unsigned long HALL_STARTUP_GRACE = 10000;


// ============================================================
// PROJECT THRESHOLDS
// FROM knowledge_base.json
// ============================================================

// DHT22 temperature
const float TEMP_WARNING = 35.0;
const float TEMP_CRITICAL = 45.0;

// DHT22 humidity
const float HUMIDITY_WARNING = 70.0;
const float HUMIDITY_CRITICAL = 85.0;

// PIR continuous motion
const unsigned long PIR_WARNING_MS = 10000;
const unsigned long PIR_CRITICAL_MS = 30000;

// HC-SR04
const float DISTANCE_WARNING_MIN = 10.0;
const float DISTANCE_WARNING_MAX = 20.0;
const float DISTANCE_CRITICAL = 10.0;

// HC-SR04 practical measurement range
const float HC_SR04_MIN_DISTANCE = 2.0;
const float HC_SR04_MAX_DISTANCE = 400.0;

// LM393 continuous sound event
const unsigned long SOUND_WARNING_MS = 2000;
const unsigned long SOUND_CRITICAL_MS = 5000;

// A3144 RPM
const float RPM_WARNING = 180.0;

// One magnet = one revolution
const int MAGNETS_PER_REVOLUTION = 1;


// ============================================================
// INA219
// ============================================================

const byte INA219_I2C_ADDR = 0x40;


// ============================================================
// OBJECTS
// ============================================================

WiFiClient espClient;

PubSubClient mqttClient(espClient);

DHT dht(
    DHT_PIN,
    DHT_TYPE
);

Adafruit_INA219 ina219;


// ============================================================
// HALL VARIABLES
// ============================================================

volatile unsigned long hallPulses = 0;

volatile unsigned long lastHallPulseMillis = 0;

float rpm = 0.0;

bool hallEverValid = false;


// ============================================================
// GENERAL VARIABLES
// ============================================================

unsigned long bootMillis = 0;

unsigned long lastTelemetryMillis = 0;

unsigned long lastMQTTAttempt = 0;


// ============================================================
// DHT FAULT
// ============================================================

int dhtFailureCount = 0;

bool dhtFault = false;


// ============================================================
// HC-SR04 FAULT
// ============================================================

int hcSr04FailureCount = 0;

bool hcSr04EverValid = false;

bool hcSr04Fault = false;


// ============================================================
// INA219
// ============================================================

bool ina219Available = false;

bool ina219Fault = false;


// ============================================================
// HALL FAULT
// ============================================================

bool hallFault = false;


// ============================================================
// PIR DURATION
// ============================================================

bool pirActive = false;

unsigned long pirStartMillis = 0;

unsigned long pirDurationMillis = 0;


// ============================================================
// SOUND DURATION
// ============================================================

bool soundActive = false;

unsigned long soundStartMillis = 0;

unsigned long soundDurationMillis = 0;


// ============================================================
// HALL INTERRUPT
// ============================================================

void IRAM_ATTR hallISR()
{
    hallPulses++;

    lastHallPulseMillis = millis();
}


// ============================================================
// WIFI
// ============================================================

void connectWiFi()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        return;
    }

    Serial.println();

    Serial.print(
        "Connecting to Wi-Fi: "
    );

    Serial.println(
        WIFI_SSID
    );

    WiFi.mode(WIFI_STA);

    WiFi.begin(
        WIFI_SSID,
        WIFI_PASSWORD
    );

    int attempts = 0;

    while (
        WiFi.status() != WL_CONNECTED &&
        attempts < 30
    )
    {
        delay(500);

        Serial.print(".");

        attempts++;
    }

    Serial.println();

    if (
        WiFi.status() ==
        WL_CONNECTED
    )
    {
        Serial.println(
            "Wi-Fi connected."
        );

        Serial.print(
            "IP Address: "
        );

        Serial.println(
            WiFi.localIP()
        );
    }
    else
    {
        Serial.println(
            "Wi-Fi connection failed."
        );
    }
}


// ============================================================
// MQTT
// ============================================================

void connectMQTT()
{
    if (
        mqttClient.connected()
    )
    {
        return;
    }

    unsigned long now =
        millis();

    if (
        now - lastMQTTAttempt <
        3000
    )
    {
        return;
    }

    lastMQTTAttempt = now;

    Serial.print(
        "Connecting to MQTT broker... "
    );

    String clientId =
        String(DEVICE_ID) +
        "_" +
        String(
            (uint32_t)ESP.getEfuseMac(),
            HEX
        );

    if (
        mqttClient.connect(
            clientId.c_str()
        )
    )
    {
        Serial.println(
            "connected."
        );
    }
    else
    {
        Serial.print(
            "failed. MQTT state = "
        );

        Serial.println(
            mqttClient.state()
        );
    }
}


// ============================================================
// HC-SR04 SINGLE READING
// ============================================================

float readSingleDistance()
{
    digitalWrite(
        TRIG_PIN,
        LOW
    );

    delayMicroseconds(3);

    digitalWrite(
        TRIG_PIN,
        HIGH
    );

    delayMicroseconds(10);

    digitalWrite(
        TRIG_PIN,
        LOW
    );

    unsigned long duration =
        pulseIn(
            ECHO_PIN,
            HIGH,
            30000UL
        );

    if (
        duration == 0
    )
    {
        return -1.0;
    }

    float distance =
        duration *
        0.0343 /
        2.0;

    if (
        distance <
        HC_SR04_MIN_DISTANCE
    )
    {
        return -1.0;
    }

    if (
        distance >
        HC_SR04_MAX_DISTANCE
    )
    {
        return -1.0;
    }

    return distance;
}


// ============================================================
// HC-SR04 STABLE READING
// ============================================================

float readDistanceCM()
{
    float readings[3];

    int validCount = 0;

    for (
        int i = 0;
        i < 3;
        i++
    )
    {
        float value =
            readSingleDistance();

        if (
            value >=
            HC_SR04_MIN_DISTANCE &&
            value <=
            HC_SR04_MAX_DISTANCE
        )
        {
            readings[validCount] =
                value;

            validCount++;
        }

        delay(25);
    }

    if (
        validCount == 0
    )
    {
        return -1.0;
    }

    if (
        validCount == 1
    )
    {
        return readings[0];
    }

    // Sort
    for (
        int i = 0;
        i < validCount - 1;
        i++
    )
    {
        for (
            int j = i + 1;
            j < validCount;
            j++
        )
        {
            if (
                readings[j] <
                readings[i]
            )
            {
                float temp =
                    readings[i];

                readings[i] =
                    readings[j];

                readings[j] =
                    temp;
            }
        }
    }

    // Median
    if (
        validCount == 2
    )
    {
        return (
            readings[0] +
            readings[1]
        ) / 2.0;
    }

    return readings[1];
}


// ============================================================
// RPM
// ============================================================

void calculateRPM()
{
    static unsigned long
        lastRPMMillis = 0;

    unsigned long now =
        millis();

    if (
        lastRPMMillis == 0
    )
    {
        lastRPMMillis =
            now;

        noInterrupts();

        hallPulses = 0;

        interrupts();

        rpm = 0.0;

        return;
    }

    unsigned long elapsed =
        now -
        lastRPMMillis;

    if (
        elapsed >= 1000
    )
    {
        noInterrupts();

        unsigned long pulses =
            hallPulses;

        hallPulses = 0;

        interrupts();

        float revolutions =
            (float)pulses /
            MAGNETS_PER_REVOLUTION;

        rpm =
            revolutions *
            (60000.0 / elapsed);

        lastRPMMillis =
            now;

        if (
            rpm >= RPM_WARNING
        )
        {
            hallEverValid = true;
        }
    }
}


// ============================================================
// MOTOR
// ============================================================

void runMotor()
{
    digitalWrite(
        MOTOR_IN3,
        HIGH
    );

    digitalWrite(
        MOTOR_IN4,
        LOW
    );
}


// ============================================================
// I2C CHECK
// ============================================================

bool isI2CDevicePresent(
    byte address
)
{
    Wire.beginTransmission(
        address
    );

    byte error =
        Wire.endTransmission();

    return (
        error == 0
    );
}


// ============================================================
// PIR STATUS
// ============================================================

String getPIRStatus()
{
    if (
        pirDurationMillis >=
        PIR_CRITICAL_MS
    )
    {
        return "CRITICAL";
    }

    if (
        pirDurationMillis >=
        PIR_WARNING_MS
    )
    {
        return "WARNING";
    }

    return "NORMAL";
}


// ============================================================
// SOUND STATUS
// ============================================================

String getSoundStatus()
{
    if (
        soundDurationMillis >=
        SOUND_CRITICAL_MS
    )
    {
        return "CRITICAL";
    }

    if (
        soundDurationMillis >=
        SOUND_WARNING_MS
    )
    {
        return "WARNING";
    }

    return "NORMAL";
}


// ============================================================
// TEMPERATURE STATUS
// ============================================================

String getTemperatureStatus(
    float temperature
)
{
    if (
        isnan(temperature)
    )
    {
        return "FAULT";
    }

    if (
        temperature >
        TEMP_CRITICAL
    )
    {
        return "CRITICAL";
    }

    if (
        temperature >
        TEMP_WARNING
    )
    {
        return "WARNING";
    }

    return "NORMAL";
}


// ============================================================
// HUMIDITY STATUS
// ============================================================

String getHumidityStatus(
    float humidity
)
{
    if (
        isnan(humidity)
    )
    {
        return "FAULT";
    }

    if (
        humidity >
        HUMIDITY_CRITICAL
    )
    {
        return "CRITICAL";
    }

    if (
        humidity >
        HUMIDITY_WARNING
    )
    {
        return "WARNING";
    }

    return "NORMAL";
}


// ============================================================
// DISTANCE STATUS
// ============================================================

String getDistanceStatus(
    float distance
)
{
    if (
        distance < 0
    )
    {
        return "UNAVAILABLE";
    }

    if (
        distance <=
        DISTANCE_CRITICAL
    )
    {
        return "CRITICAL";
    }

    if (
        distance <=
        DISTANCE_WARNING_MAX
    )
    {
        return "WARNING";
    }

    return "NORMAL";
}


// ============================================================
// RPM STATUS
// ============================================================

String getRPMStatus(
    float value
)
{
    if (
        value <
        RPM_WARNING
    )
    {
        return "WARNING";
    }

    return "NORMAL";
}


// ============================================================
// UPDATE PIR
// ============================================================

void updatePIR(
    int motion
)
{
    unsigned long now =
        millis();

    if (
        motion == HIGH
    )
    {
        if (!pirActive)
        {
            pirActive = true;

            pirStartMillis =
                now;
        }

        pirDurationMillis =
            now -
            pirStartMillis;
    }
    else
    {
        pirActive = false;

        pirStartMillis = 0;

        pirDurationMillis = 0;
    }
}


// ============================================================
// UPDATE SOUND
// ============================================================

void updateSound(
    int sound
)
{
    unsigned long now =
        millis();

    // LM393 module used in current wiring:
    // LOW = threshold exceeded

    bool active =
        (
            sound == LOW
        );

    if (active)
    {
        if (!soundActive)
        {
            soundActive = true;

            soundStartMillis =
                now;
        }

        soundDurationMillis =
            now -
            soundStartMillis;
    }
    else
    {
        soundActive = false;

        soundStartMillis = 0;

        soundDurationMillis = 0;
    }
}


// ============================================================
// UPDATE FAULTS
// ============================================================

void updateFaults(
    float temperature,
    float humidity,
    float distance
)
{
    // ========================================================
    // DHT22 DISCONNECTION
    // ========================================================

    if (
        isnan(temperature) ||
        isnan(humidity)
    )
    {
        dhtFailureCount++;

        if (
            dhtFailureCount >=
            DHT_FAILURE_LIMIT
        )
        {
            dhtFault = true;
        }
    }
    else
    {
        dhtFailureCount = 0;

        dhtFault = false;
    }


    // ========================================================
    // HC-SR04
    // ========================================================

    if (
        distance < 0
    )
    {
        if (hcSr04EverValid)
        {
            hcSr04FailureCount++;

            /*
              IMPORTANT:

              A no-echo condition cannot electrically prove
              that the HC-SR04 is disconnected.

              Therefore this flag means that the sensor has
              stopped producing valid echoes after previously
              working.

              Do not interpret a distant object beyond the
              sensor's practical range as a guaranteed physical
              disconnection.
            */

            if (
                hcSr04FailureCount >=
                HC_SR04_FAILURE_LIMIT
            )
            {
                hcSr04Fault = true;
            }
        }
    }
    else
    {
        hcSr04EverValid = true;

        hcSr04FailureCount = 0;

        hcSr04Fault = false;
    }


    // ========================================================
    // INA219 DISCONNECTION
    // ========================================================

    ina219Available =
        isI2CDevicePresent(
            INA219_I2C_ADDR
        );

    ina219Fault =
        !ina219Available;


    // ========================================================
    // HALL SENSOR
    // ========================================================

    unsigned long now =
        millis();

    if (
        now - bootMillis <
        HALL_STARTUP_GRACE
    )
    {
        hallFault = false;
    }
    else
    {
        if (hallEverValid)
        {
            if (
                now -
                lastHallPulseMillis >
                HALL_NO_PULSE_TIMEOUT
            )
            {
                hallFault = true;
            }
            else
            {
                hallFault = false;
            }
        }
        else
        {
            hallFault = true;
        }
    }
}


// ============================================================
// BUILD FAULT SUMMARY
// ============================================================

String buildFaultSummary()
{
    String summary = "";

    if (dhtFault)
    {
        summary +=
            "DHT22 disconnected/unresponsive; ";
    }

    if (hcSr04Fault)
    {
        summary +=
            "HC-SR04 echo unavailable after previous valid operation; ";
    }

    if (hallFault)
    {
        summary +=
            "A3144 Hall signal lost; ";
    }

    if (ina219Fault)
    {
        summary +=
            "INA219 disconnected from I2C; ";
    }

    if (
        summary.length() == 0
    )
    {
        return "NONE";
    }

    return summary;
}


// ============================================================
// PUBLISH
// ============================================================

void publishTelemetry()
{
    float temperature =
        dht.readTemperature();

    float humidity =
        dht.readHumidity();


    int motion =
        digitalRead(
            PIR_PIN
        );

    int sound =
        digitalRead(
            SOUND_PIN
        );

    float distance =
        readDistanceCM();


    int hallMagnet =
        digitalRead(
            HALL_PIN
        );


    updatePIR(
        motion
    );

    updateSound(
        sound
    );

    calculateRPM();


    float busVoltage = 0.0;

    float current_mA = 0.0;

    float power_mW = 0.0;


    if (
        ina219Available
    )
    {
        busVoltage =
            ina219.getBusVoltage_V();

        current_mA =
            ina219.getCurrent_mA();

        power_mW =
            ina219.getPower_mW();
    }


    updateFaults(
        temperature,
        humidity,
        distance
    );


    String temperatureStatus =
        getTemperatureStatus(
            temperature
        );

    String humidityStatus =
        getHumidityStatus(
            humidity
        );

    String pirStatus =
        getPIRStatus();

    String distanceStatus =
        getDistanceStatus(
            distance
        );

    String soundStatus =
        getSoundStatus();

    String rpmStatus =
        getRPMStatus(
            rpm
        );

    String faultSummary =
        buildFaultSummary();


    int faultCount = 0;

    if (dhtFault)
        faultCount++;

    if (hcSr04Fault)
        faultCount++;

    if (hallFault)
        faultCount++;

    if (ina219Fault)
        faultCount++;


    // ========================================================
    // JSON
    // ========================================================

    String payload = "{";


    payload +=
        "\"device_id\":\"";

    payload +=
        DEVICE_ID;

    payload += "\",";


    // Temperature

    payload +=
        "\"temperature\":";

    if (isnan(temperature))
    {
        payload += "null";
    }
    else
    {
        payload +=
            String(
                temperature,
                2
            );
    }

    payload += ",";


    payload +=
        "\"temperature_status\":\"";

    payload +=
        temperatureStatus;

    payload += "\",";


    // Humidity

    payload +=
        "\"humidity\":";

    if (isnan(humidity))
    {
        payload += "null";
    }
    else
    {
        payload +=
            String(
                humidity,
                2
            );
    }

    payload += ",";


    payload +=
        "\"humidity_status\":\"";

    payload +=
        humidityStatus;

    payload += "\",";


    // PIR

    payload +=
        "\"motion\":";

    payload +=
        String(
            motion
        );

    payload += ",";


    payload +=
        "\"pir_duration\":";

    payload +=
        String(
            pirDurationMillis / 1000.0,
            1
        );

    payload += ",";


    payload +=
        "\"pir_status\":\"";

    payload +=
        pirStatus;

    payload += "\",";


    // Distance

    payload +=
        "\"distance\":";

    if (
        distance < 0
    )
    {
        payload += "null";
    }
    else
    {
        payload +=
            String(
                distance,
                2
            );
    }

    payload += ",";


    payload +=
        "\"distance_status\":\"";

    payload +=
        distanceStatus;

    payload += "\",";


    // Sound

    bool soundDetected =
        (
            sound == LOW
        );

    payload +=
        "\"sound\":";

    payload +=
        String(
            soundDetected ? 1 : 0
        );

    payload += ",";


    payload +=
        "\"sound_duration\":";

    payload +=
        String(
            soundDurationMillis / 1000.0,
            1
        );

    payload += ",";


    payload +=
        "\"sound_status\":\"";

    payload +=
        soundStatus;

    payload += "\",";


    // Hall

    payload +=
        "\"hall_magnet\":";

    payload +=
        String(
            hallMagnet
        );

    payload += ",";


    // RPM

    payload +=
        "\"rpm\":";

    payload +=
        String(
            rpm,
            2
        );

    payload += ",";


    payload +=
        "\"rpm_status\":\"";

    payload +=
        rpmStatus;

    payload += "\",";


    // Motor

    payload +=
        "\"motor_running\":1,";


    // INA219

    payload +=
        "\"voltage\":";

    if (ina219Fault)
    {
        payload += "null";
    }
    else
    {
        payload +=
            String(
                busVoltage,
                4
            );
    }

    payload += ",";


    payload +=
        "\"current\":";

    if (ina219Fault)
    {
        payload += "null";
    }
    else
    {
        payload +=
            String(
                current_mA,
                4
            );
    }

    payload += ",";


    payload +=
        "\"power\":";

    if (ina219Fault)
    {
        payload += "null";
    }
    else
    {
        payload +=
            String(
                power_mW,
                4
            );
    }

    payload += ",";


    payload +=
        "\"ina219_status\":\"INFO\",";


    // Faults

    payload +=
        "\"fault_detected\":";

    payload +=
        (
            faultCount > 0
            ? "true"
            : "false"
        );

    payload += ",";


    payload +=
        "\"fault_count\":";

    payload +=
        String(
            faultCount
        );

    payload += ",";


    payload +=
        "\"dht22_fault\":";

    payload +=
        (
            dhtFault
            ? "true"
            : "false"
        );

    payload += ",";


    payload +=
        "\"hc_sr04_fault\":";

    payload +=
        (
            hcSr04Fault
            ? "true"
            : "false"
        );

    payload += ",";


    payload +=
        "\"pir_fault\":false,";


    payload +=
        "\"lm393_fault\":false,";


    payload +=
        "\"a3144_fault\":";

    payload +=
        (
            hallFault
            ? "true"
            : "false"
        );

    payload += ",";


    payload +=
        "\"ina219_fault\":";

    payload +=
        (
            ina219Fault
            ? "true"
            : "false"
        );

    payload += ",";


    payload +=
        "\"fault_summary\":\"";

    payload +=
        faultSummary;

    payload += "\"";


    payload += "}";


    // ========================================================
    // MQTT
    // ========================================================

    bool published = false;

    if (
        mqttClient.connected()
    )
    {
        published =
            mqttClient.publish(
                MQTT_TOPIC,
                payload.c_str()
            );
    }


    // ========================================================
    // SERIAL
    // ========================================================

    Serial.println();

    Serial.println(
        "========== TELEMETRY =========="
    );


    // Temperature

    Serial.print(
        "Temperature : "
    );

    if (isnan(temperature))
    {
        Serial.println(
            "FAULT / INVALID"
        );
    }
    else
    {
        Serial.print(
            temperature,
            2
        );

        Serial.print(
            " °C ["
        );

        Serial.print(
            temperatureStatus
        );

        Serial.println(
            "]"
        );
    }


    // Humidity

    Serial.print(
        "Humidity    : "
    );

    if (isnan(humidity))
    {
        Serial.println(
            "FAULT / INVALID"
        );
    }
    else
    {
        Serial.print(
            humidity,
            2
        );

        Serial.print(
            " % RH ["
        );

        Serial.print(
            humidityStatus
        );

        Serial.println(
            "]"
        );
    }


    // PIR

    Serial.print(
        "PIR Motion  : "
    );

    Serial.print(
        motion
        ? "DETECTED"
        : "NONE"
    );

    Serial.print(
        " | "
    );

    Serial.print(
        pirDurationMillis / 1000.0,
        1
    );

    Serial.print(
        " s ["
    );

    Serial.print(
        pirStatus
    );

    Serial.println(
        "]"
    );


    // Distance

    Serial.print(
        "Distance    : "
    );

    if (
        distance >=
        HC_SR04_MIN_DISTANCE &&
        distance <=
        HC_SR04_MAX_DISTANCE
    )
    {
        Serial.print(
            distance,
            2
        );

        Serial.print(
            " cm ["
        );

        Serial.print(
            distanceStatus
        );

        Serial.println(
            "]"
        );
    }
    else
    {
        Serial.println(
            "MEASUREMENT UNAVAILABLE"
        );
    }


    // Sound

    Serial.print(
        "Sound       : "
    );

    Serial.print(
        soundDetected
        ? "THRESHOLD EXCEEDED"
        : "NORMAL"
    );

    Serial.print(
        " | "
    );

    Serial.print(
        soundDurationMillis / 1000.0,
        1
    );

    Serial.print(
        " s ["
    );

    Serial.print(
        soundStatus
    );

    Serial.println(
        "]"
    );


    // Hall

    Serial.print(
        "Hall        : "
    );

    Serial.println(
        hallMagnet
    );


    // RPM

    Serial.print(
        "RPM         : "
    );

    Serial.print(
        rpm,
        2
    );

    Serial.print(
        " ["
    );

    Serial.print(
        rpmStatus
    );

    Serial.println(
        "]"
    );


    // INA219

    if (ina219Fault)
    {
        Serial.println(
            "INA219      : FAULT / DISCONNECTED"
        );
    }
    else
    {
        Serial.print(
            "INA219 V    : "
        );

        Serial.print(
            busVoltage,
            4
        );

        Serial.println(
            " V [INFO]"
        );

        Serial.print(
            "INA219 I    : "
        );

        Serial.print(
            current_mA,
            4
        );

        Serial.println(
            " mA [INFO]"
        );

        Serial.print(
            "INA219 P    : "
        );

        Serial.print(
            power_mW,
            4
        );

        Serial.println(
            " mW [INFO]"
        );
    }


    Serial.println(
        "--------------------------------"
    );


    if (
        faultCount > 0
    )
    {
        Serial.println(
            "!!! FAULT DETECTED !!!"
        );

        Serial.print(
            "Fault Count : "
        );

        Serial.println(
            faultCount
        );

        Serial.print(
            "Fault       : "
        );

        Serial.println(
            faultSummary
        );
    }
    else
    {
        Serial.println(
            "SYSTEM CONNECTION STATUS: OK"
        );
    }


    Serial.print(
        "MQTT Publish: "
    );

    Serial.println(
        published
        ? "SUCCESS"
        : "FAILED"
    );


    Serial.print(
        "Payload Size: "
    );

    Serial.print(
        payload.length()
    );

    Serial.println(
        " bytes"
    );


    Serial.println(
        "==============================="
    );
}


// ============================================================
// SETUP
// ============================================================

void setup()
{
    Serial.begin(
        115200
    );

    delay(1000);

    bootMillis =
        millis();


    // GPIO

    pinMode(
        PIR_PIN,
        INPUT
    );

    pinMode(
        TRIG_PIN,
        OUTPUT
    );

    pinMode(
        ECHO_PIN,
        INPUT
    );

    pinMode(
        SOUND_PIN,
        INPUT
    );

    pinMode(
        HALL_PIN,
        INPUT_PULLUP
    );

    pinMode(
        MOTOR_IN3,
        OUTPUT
    );

    pinMode(
        MOTOR_IN4,
        OUTPUT
    );


    digitalWrite(
        TRIG_PIN,
        LOW
    );


    // I2C

    Wire.begin(
        SDA_PIN,
        SCL_PIN
    );


    // DHT

    dht.begin();


    // INA219

    if (
        ina219.begin()
    )
    {
        ina219Available =
            true;

        ina219.setCalibration_32V_2A();

        Serial.println(
            "INA219 detected."
        );
    }
    else
    {
        ina219Available =
            false;

        Serial.println(
            "INA219 NOT detected."
        );
    }


    // Hall interrupt

    attachInterrupt(
        digitalPinToInterrupt(
            HALL_PIN
        ),
        hallISR,
        FALLING
    );


    // Motor

    runMotor();


    // MQTT

    mqttClient.setServer(
        MQTT_BROKER,
        MQTT_PORT
    );

    mqttClient.setBufferSize(
        1024
    );

    mqttClient.setKeepAlive(
        30
    );

    mqttClient.setSocketTimeout(
        5
    );


    // Wi-Fi

    connectWiFi();


    // MQTT

    connectMQTT();


    Serial.println();

    Serial.println(
        "======================================"
    );

    Serial.println(
        "Knowledge-Driven IoT Fault Diagnosis"
    );

    Serial.println(
        "Bharat Pi IoT Telemetry System"
    );

    Serial.println(
        "======================================"
    );

    Serial.println(
        "Threshold-based monitoring enabled."
    );

    Serial.println(
        "Fault detection enabled."
    );

    Serial.println(
        "======================================"
    );
}


// ============================================================
// LOOP
// ============================================================

void loop()
{
    connectWiFi();

    if (
        !mqttClient.connected()
    )
    {
        connectMQTT();
    }

    mqttClient.loop();

    runMotor();

    unsigned long now =
        millis();

    if (
        now -
        lastTelemetryMillis >=
        TELEMETRY_INTERVAL
    )
    {
        lastTelemetryMillis =
            now;

        publishTelemetry();
    }

    delay(10);
}