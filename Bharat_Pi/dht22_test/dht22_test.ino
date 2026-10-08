#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// =====================================================
// DHT22 CONFIGURATION
// =====================================================

#define DHT_PIN 13
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);


// =====================================================
// WIFI CONFIGURATION
// =====================================================

const char* WIFI_SSID = "NP";
const char* WIFI_PASSWORD = "12345687";


// =====================================================
// MQTT CONFIGURATION
// =====================================================

// IMPORTANT:
// Replace this with your Windows laptop's IPv4 address.
// Example: 192.168.1.10

const char* MQTT_SERVER = "172.29.85.142";

const int MQTT_PORT = 1883;

const char* MQTT_TOPIC = "sic/iot/telemetry";


// =====================================================
// DEVICE CONFIGURATION
// =====================================================

const char* DEVICE_ID = "bharatpi_01";


// =====================================================
// OBJECTS
// =====================================================

WiFiClient espClient;
PubSubClient mqttClient(espClient);


// =====================================================
// TIMING
// =====================================================

unsigned long lastPublish = 0;

const unsigned long PUBLISH_INTERVAL = 2000;


// =====================================================
// WIFI CONNECTION
// =====================================================

void connectWiFi()
{
    Serial.println();
    Serial.println("Connecting to Wi-Fi...");

    WiFi.begin(
        WIFI_SSID,
        WIFI_PASSWORD
    );

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);

        Serial.print(".");
    }

    Serial.println();
    Serial.println("Wi-Fi connected.");

    Serial.print("Bharat Pi IP address: ");
    Serial.println(WiFi.localIP());
}


// =====================================================
// MQTT CONNECTION
// =====================================================

void connectMQTT()
{
    while (!mqttClient.connected())
    {
        Serial.print("Connecting to MQTT broker...");

        String clientId = DEVICE_ID;

        clientId += "_";

        clientId += String(
            random(0xffff),
            HEX
        );

        if (
            mqttClient.connect(
                clientId.c_str()
            )
        )
        {
            Serial.println("connected.");

            Serial.print("MQTT topic: ");
            Serial.println(MQTT_TOPIC);
        }
        else
        {
            Serial.print("failed, rc=");
            Serial.print(
                mqttClient.state()
            );

            Serial.println(
                " - retrying in 2 seconds"
            );

            delay(2000);
        }
    }
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
    Serial.begin(115200);

    delay(1000);

    Serial.println();
    Serial.println("====================================");
    Serial.println("SIC IoT CAPSTONE");
    Serial.println("DHT22 HARDWARE INTEGRATION");
    Serial.println("====================================");

    // Start DHT22
    dht.begin();

    Serial.println();
    Serial.println("DHT22 initialized.");

    // Connect Wi-Fi
    connectWiFi();

    // Configure MQTT
    mqttClient.setServer(
        MQTT_SERVER,
        MQTT_PORT
    );

    // Connect MQTT
    connectMQTT();

    Serial.println();
    Serial.println("System ready.");
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
    // -------------------------------------------------
    // Maintain Wi-Fi
    // -------------------------------------------------

    if (WiFi.status() != WL_CONNECTED)
    {
        connectWiFi();
    }


    // -------------------------------------------------
    // Maintain MQTT
    // -------------------------------------------------

    if (!mqttClient.connected())
    {
        connectMQTT();
    }

    mqttClient.loop();


    // -------------------------------------------------
    // Publish every 2 seconds
    // -------------------------------------------------

    unsigned long currentMillis =
        millis();

    if (
        currentMillis - lastPublish
        >= PUBLISH_INTERVAL
    )
    {
        lastPublish =
            currentMillis;


        // ---------------------------------------------
        // Read DHT22
        // ---------------------------------------------

        float temperature =
            dht.readTemperature();

        float humidity =
            dht.readHumidity();


        // ---------------------------------------------
        // Check sensor reading
        // ---------------------------------------------

        if (
            isnan(temperature) ||
            isnan(humidity)
        )
        {
            Serial.println(
                "ERROR: Failed to read DHT22."
            );

            return;
        }


        // ---------------------------------------------
        // Display sensor values
        // ---------------------------------------------

        Serial.println();
        Serial.println("------------------------------");

        Serial.print(
            "Temperature: "
        );

        Serial.print(
            temperature
        );

        Serial.println(
            " °C"
        );


        Serial.print(
            "Humidity: "
        );

        Serial.print(
            humidity
        );

        Serial.println(
            " %"
        );


        // ---------------------------------------------
        // Create MQTT JSON payload
        // ---------------------------------------------

        String payload = "{";

        payload += "\"timestamp\":\"";

        payload += String(
            millis()
        );

        payload += "\",";


        payload += "\"device_id\":\"";

        payload += DEVICE_ID;

        payload += "\",";


        // Real DHT22 values
        payload += "\"temperature\":";

        payload += String(
            temperature,
            2
        );

        payload += ",";


        payload += "\"humidity\":";

        payload += String(
            humidity,
            2
        );

        payload += ",";


        // Placeholder values
        // These will be replaced when
        // the remaining sensors are integrated.

        payload += "\"motion\":0,";

        payload += "\"distance\":0,";

        payload += "\"sound\":0,";

        payload += "\"motor_temperature\":0,";

        payload += "\"vibration\":0,";

        payload += "\"voltage\":0,";

        payload += "\"current\":0,";

        payload += "\"rpm\":0";


        payload += "}";


        // ---------------------------------------------
        // Publish MQTT
        // ---------------------------------------------

        Serial.println();

        Serial.println(
            "Publishing MQTT:"
        );

        Serial.println(
            payload
        );


        bool published =
            mqttClient.publish(
                MQTT_TOPIC,
                payload.c_str()
            );


        if (published)
        {
            Serial.println(
                "MQTT publish: SUCCESS"
            );
        }
        else
        {
            Serial.println(
                "MQTT publish: FAILED"
            );
        }
    }
}