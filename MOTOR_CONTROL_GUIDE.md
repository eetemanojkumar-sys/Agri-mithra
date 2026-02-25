# AgriSmart - External Motor Control via ThingSpeak

## Overview
Control real irrigation motors/pumps through AgriSmart using ThingSpeak IoT platform and ESP32/NodeMCU.

## Hardware Requirements
- ESP32 / NodeMCU (ESP8266)
- Relay Module (5V, 1-channel or 2-channel)
- 12V DC Motor / Water Pump
- 12V Power Supply
- Jumper Wires
- Breadboard (optional)

## Software Requirements
- Arduino IDE
- ESP32/ESP8266 Board Library
- WiFiManager Library
- ThingSpeak Account (free)

---

## Part 1: ThingSpeak Setup

### Step 1: Create ThingSpeak Channel
1. Go to https://thingspeak.com/
2. Sign up / Login
3. Click "Channels" → "New Channel"
4. Configure channel:
   - **Name**: AgriSmart Monitoring
   - **Field 1**: Soil Moisture (%)
   - **Field 2**: Temperature (°C)
   - **Field 3**: Humidity (%)
   - **Field 4**: Rain Sensor (%)
   - **Field 5**: Motor Control (1=ON, 0=OFF) ← **Important**
5. Save Channel

### Step 2: Get API Keys
1. Go to "API Keys" tab
2. Copy **Channel ID**
3. Copy **Read API Key** (for sensor data)
4. Copy **Write API Key** (for motor control)

---

## Part 2: Hardware Wiring

### Connections
```
ESP32/NodeMCU → Relay Module:
- GPIO 16 (D0) → Relay IN
- 3.3V → Relay VCC
- GND → Relay GND

Relay Module → Motor:
- COM → Motor +ve
- NO (Normally Open) → 12V Power Supply +ve
- Motor -ve → 12V Power Supply -ve
```

### Sensor Connections (Optional - for full monitoring)
```
Soil Moisture Sensor → ESP32 GPIO 34
DHT22 Temperature → ESP32 GPIO 4
Rain Sensor → ESP32 GPIO 5
```

---

## Part 3: Arduino Code

### ESP32 Motor Control Code
```cpp
#include <WiFi.h>
#include <HTTPClient.h>

// WiFi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// ThingSpeak Configuration
String thingSpeakReadKey = "YOUR_READ_API_KEY";
String thingSpeakChannelID = "YOUR_CHANNEL_ID";
const int motorControlField = 5; // Field 5 for motor control

// Hardware Pins
const int MOTOR_PIN = 16; // GPIO 16 (D0)
const int LED_PIN = 2;    // Built-in LED

// Timing
unsigned long lastCheck = 0;
const unsigned long checkInterval = 15000; // Check every 15 seconds

void setup() {
  Serial.begin(115200);
  
  // Configure pins
  pinMode(MOTOR_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\\nWiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // Blink LED to indicate ready
  for(int i=0; i<3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
}

void loop() {
  // Check motor command every 15 seconds
  if (millis() - lastCheck >= checkInterval) {
    lastCheck = millis();
    checkMotorCommand();
  }
}

void checkMotorCommand() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    // Read Field 5 (motor control) from ThingSpeak
    String url = "https://api.thingspeak.com/channels/" + thingSpeakChannelID + 
                 "/fields/" + String(motorControlField) + 
                 "/last.txt?api_key=" + thingSpeakReadKey;
    
    http.begin(url);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
      String motorState = http.getString();
      motorState.trim();
      
      Serial.print("Motor Command: ");
      Serial.println(motorState);
      
      if (motorState == "1") {
        // Turn motor ON
        digitalWrite(MOTOR_PIN, HIGH);
        digitalWrite(LED_PIN, HIGH);
        Serial.println("✓ Motor ON");
      } 
      else if (motorState == "0") {
        // Turn motor OFF
        digitalWrite(MOTOR_PIN, LOW);
        digitalWrite(LED_PIN, LOW);
        Serial.println("✓ Motor OFF");
      }
    } else {
      Serial.print("HTTP Error: ");
      Serial.println(httpCode);
    }
    
    http.end();
  } else {
    Serial.println("WiFi Disconnected! Reconnecting...");
    WiFi.reconnect();
  }
}
```

---

## Part 4: AgriSmart Configuration

### Step 1: Open AgriSmart Dashboard
1. Navigate to AgriSmart app
2. Scroll to "IoT Sensor Integration" section

### Step 2: Connect ThingSpeak
1. Enter **Channel ID**
2. Enter **Read API Key**
3. Enter **Write API Key** (for motor control)
4. Click "Connect IoT Sensors"

### Step 3: Verify Hardware Control
1. Motor Control panel should show "Hardware Control Active"
2. Toggle motor switch
3. Check ESP32 serial monitor for confirmation
4. Motor should turn ON/OFF within 15 seconds

---

## Testing & Troubleshooting

### Test Motor Control
```bash
# From AgriSmart:
1. Click motor toggle switch
2. Check "Hardware Control Active" badge
3. Wait 15 seconds
4. Motor should respond

# From Arduino Serial Monitor:
- Watch for "Motor Command: 1" or "Motor Command: 0"
- LED should blink when command received
```

### Common Issues

**Motor not responding:**
- Check WiFi connection on ESP32
- Verify Write API Key is correct
- Check relay wiring
- Reduce checkInterval to 10000ms (10 seconds)

**Relay clicking but motor not running:**
- Check 12V power supply
- Verify motor connections
- Test relay with multimeter

**WiFi disconnections:**
- Move ESP32 closer to router
- Add WiFi reconnect logic (already included)
- Use WiFiManager for easier configuration

**ThingSpeak rate limiting:**
- Free accounts: Update every 15 seconds minimum
- Paid accounts: Faster updates available

---

## Safety Considerations

⚠️ **IMPORTANT SAFETY WARNINGS:**

1. **Electrical Safety**
   - Do NOT work with mains AC voltage (110V/220V)
   - Use only 12V DC motors
   - Isolate high voltage circuits properly
   - Use proper fuses

2. **Water Safety**
   - Keep electronics away from water
   - Use waterproof enclosures for outdoor installation
   - Ground all metal components

3. **Motor Protection**
   - Add flyback diode across relay contacts
   - Use proper gauge wires
   - Don't exceed motor current rating

4. **System Protection**
   - Add timeout logic (auto-off after 30 minutes)
   - Implement emergency stop button
   - Monitor motor current

---

## Advanced Features

### Auto-Off Timer (Safety)
```cpp
// Add to global variables
unsigned long motorOnTime = 0;
const unsigned long maxRunTime = 1800000; // 30 minutes

// In loop():
if (digitalRead(MOTOR_PIN) == HIGH) {
  if (millis() - motorOnTime > maxRunTime) {
    digitalWrite(MOTOR_PIN, LOW);
    Serial.println("⚠ Auto-off: Max runtime reached");
  }
}
```

### Push Notifications (Optional)
- Use IFTTT with ThingSpeak
- Send SMS when motor turns ON/OFF
- Email alerts for failures

### Multiple Motors
- Use Field 6, Field 7 for additional motors
- Add more relay channels
- Implement zone-based irrigation

---

## API Reference

### Motor Control Response
```json
{
  "success": true,
  "motorState": "ON",
  "hardwareControl": true,
  "hardwareMessage": "Command sent to external motor via ThingSpeak",
  "thingspeakEntry": 12345
}
```

### Configure ThingSpeak Write
```bash
POST /api/motor/configure-thingspeak
{
  "channel_id": "your_channel_id",
  "write_api_key": "your_write_key",
  "motor_field": 5
}
```

---

## Support

For issues or questions:
1. Check serial monitor output
2. Verify ThingSpeak channel updates
3. Test with ThingSpeak's built-in API tester
4. Review AgriSmart console logs

**Hardware control is now fully operational! 🚀**
