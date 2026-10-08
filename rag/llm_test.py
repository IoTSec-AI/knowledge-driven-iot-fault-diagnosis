from openai import OpenAI

BASE_URL = "http://localhost:1234/v1"
MODEL = "qwen/qwen3-vl-4b"

client = OpenAI(
    base_url=BASE_URL,
    api_key="lm-studio"
)

prompt = """
You are an IoT fault diagnosis assistant.

Analyze only these available parameters:
- Motor RPM from A3144 Hall sensor
- INA219 voltage
- INA219 current
- INA219 power
- DHT22 temperature/humidity
- PIR motion
- HC-SR04 distance
- LM393 sound state

Do not mention or infer MPU6050 vibration.
Do not mention or infer DS18B20 motor temperature.

Explain:
1. Current condition
2. Abnormalities
3. Possible interpretation
4. Recommended checks

Do not claim that a physical component has definitely failed.
"""

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": "You are an evidence-based IoT diagnostics assistant."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.2,
    max_tokens=500
)

print(response.choices[0].message.content)
