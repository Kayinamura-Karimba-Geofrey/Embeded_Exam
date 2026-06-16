// ═══════════════════════════════════════════════════════════════
// Temperature Display & Serial Transmission
// Hardware: Arduino UNO + LM35 on A0 + 16x2 LCD via I2C
// ═══════════════════════════════════════════════════════════════

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ── LCD Setup ─────────────────────────────────────────────────
// I2C address is usually 0x27 or 0x3F — check your module
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ── Configuration ─────────────────────────────────────────────
const int    TEMP_PIN       = A0;       // LM35 analog input
const int    BAUD_RATE      = 9600;     // Serial baud rate
const int    READ_INTERVAL  = 1000;     // Read temp every 1 second
const int    SCROLL_SPEED   = 350;      // Scroll delay in ms

// ── Candidate Name ─────────────────────────────────────────────
// Change this to your actual name
String candidateName = "MUGISHA Emmanuel Pierre";

// ── Scroll Variables ───────────────────────────────────────────
int  scrollPos          = 0;            // Current scroll position
bool needsScrolling     = false;        // Flag if name > 16 chars
String scrollBuffer     = "";           // Padded scroll string

// ── Timing Variables ───────────────────────────────────────────
unsigned long lastTempRead   = 0;
unsigned long lastScroll     = 0;

// ══════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(BAUD_RATE);

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();

  // Determine if name needs scrolling
  if (candidateName.length() > 16) {
    needsScrolling = true;
    // Pad with spaces so text scrolls cleanly off screen
    // Format: "NAME                NAME" (16 trailing spaces)
    scrollBuffer = candidateName + "                ";
  }

  // Startup message
  lcd.setCursor(0, 0);
  lcd.print("  System Ready  ");
  lcd.setCursor(0, 1);
  lcd.print("Temp Monitor v1 ");
  delay(2000);
  lcd.clear();

  Serial.println("=== Temperature Monitor Started ===");
  Serial.println("Format: TEMP:<value>");
}

// ══════════════════════════════════════════════════════════════
void loop() {
  unsigned long now = millis();

  // ── Read & Display Temperature every READ_INTERVAL ──────────
  if (now - lastTempRead >= READ_INTERVAL) {
    lastTempRead = now;

    float temperature = readTemperature();

    // Display temperature on LCD row 2
    displayTemperature(temperature);

    // Send temperature to PC via Serial
    Serial.print("TEMP:");
    Serial.println(temperature, 1);    // 1 decimal place
  }

  // ── Handle Name Display / Scrolling ─────────────────────────
  if (needsScrolling) {
    // Scroll name if longer than 16 characters
    if (now - lastScroll >= SCROLL_SPEED) {
      lastScroll = now;
      scrollName();
    }
  } else {
    // Static display — name fits in 16 chars
    lcd.setCursor(0, 0);
    lcd.print(candidateName);
    // Pad remaining spaces to clear old characters
    for (int i = candidateName.length(); i < 16; i++) {
      lcd.print(" ");
    }
  }
}

// ══════════════════════════════════════════════════════════════
// Read LM35 temperature from analog pin
// LM35: 10mV per °C → Vout = Temp(°C) × 10mV
// ══════════════════════════════════════════════════════════════
float readTemperature() {
  // Take 5 samples and average for stability
  long sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(TEMP_PIN);
    delay(5);
  }
  int raw = sum / 5;

  // Convert ADC reading to voltage (5V reference, 10-bit ADC)
  float voltage = raw * (5.0 / 1023.0);

  // Convert voltage to Celsius (LM35: 10mV per degree)
  float tempC = voltage * 100.0;

  return tempC;
}

// ══════════════════════════════════════════════════════════════
// Display temperature on LCD row 2 (index 1)
// ══════════════════════════════════════════════════════════════
void displayTemperature(float temp) {
  lcd.setCursor(0, 1);
  lcd.print("Temp: ");
  lcd.print(temp, 1);             // 1 decimal place
  lcd.print((char)223);           // ° degree symbol
  lcd.print("C   ");              // Trailing spaces clear old digits
}

// ══════════════════════════════════════════════════════════════
// Horizontal scroll for names longer than 16 characters
// Shows a 16-character window that slides through the name
// ══════════════════════════════════════════════════════════════
void scrollName() {
  // Extract 16-char window from scroll buffer
  String visible = "";
  int bufLen = scrollBuffer.length();

  for (int i = 0; i < 16; i++) {
    int idx = (scrollPos + i) % bufLen;
    visible += scrollBuffer[idx];
  }

  // Write to LCD row 1 (index 0)
  lcd.setCursor(0, 0);
  lcd.print(visible);

  // Advance scroll position
  scrollPos++;
  if (scrollPos >= bufLen) {
    scrollPos = 0;               // Loop back to start
  }
}