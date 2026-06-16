# ═══════════════════════════════════════════════════════════════
# PC Temperature Monitor — Serial Reader + MQTT Publisher
# Requirements: pip install pyserial paho-mqtt
# ═══════════════════════════════════════════════════════════════

import serial
import paho.mqtt.client as mqtt
import json
import time
import datetime
import threading
import sys
import os

# ══════════════════════════════════════════════════════════════
# CONFIGURATION — Edit these to match your setup
# ══════════════════════════════════════════════════════════════
SERIAL_PORT   = "COM6"    # Windows: "COM3", Linux: "/dev/ttyUSB0"
BAUD_RATE     = 9600
BROKER_IP     = "157.173.101.159"
BROKER_PORT   = 1883
MQTT_TOPIC    = "sensor/temperature"
CANDIDATE     = "KAYINAMURA KARIMBA GEOFREY"

# ══════════════════════════════════════════════════════════════
# GLOBAL STATE
# ══════════════════════════════════════════════════════════════
temperature_log  = []             # Store all readings
mqtt_connected   = False
publish_count    = 0

# ══════════════════════════════════════════════════════════════
# DISPLAY HELPERS
# ══════════════════════════════════════════════════════════════
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("╔══════════════════════════════════════════════════════╗")
    print("║         TEMPERATURE MONITOR & MQTT PUBLISHER         ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Candidate : {CANDIDATE:<39}║")
    print(f"║  Broker    : {BROKER_IP}:{BROKER_PORT:<27}║")
    print(f"║  Topic     : {MQTT_TOPIC:<39}║")
    print(f"║  Serial    : {SERIAL_PORT:<39}║")
    print("╠══════════════════════════════════════════════════════╣")

def print_status(temp, published, connected, timestamp):
    status = "CONNECTED ✓" if connected else "DISCONNECTED ✗"
    print(f"║  MQTT      : {status:<39}║")
    print(f"║  Published : {str(published) + ' messages':<39}║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Latest Reading                                      ║")
    print(f"║  ─────────────────────────────────────────────────  ║")
    print(f"║  Temperature : {str(temp) + ' °C':<37}║")
    print(f"║  Time        : {str(timestamp):<37}║")
    print("╠══════════════════════════════════════════════════════╣")

def print_log(log):
    print("║  Recent Readings (last 5):                           ║")
    last5 = log[-5:] if len(log) >= 5 else log
    for entry in reversed(last5):
        line = f"  {entry['time']}  →  {entry['temp']} °C"
        print(f"║  {line:<52}║")
    # Fill empty rows if fewer than 5
    for _ in range(5 - len(last5)):
        print(f"║  {'---':<52}║")
    print("╚══════════════════════════════════════════════════════╝")
    print("\n  Press Ctrl+C to stop\n")

# ══════════════════════════════════════════════════════════════
# MQTT CALLBACKS
# ══════════════════════════════════════════════════════════════
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print_to_log("MQTT broker connected successfully")
    else:
        mqtt_connected = False
        error_codes = {
            1: "Incorrect protocol version",
            2: "Invalid client ID",
            3: "Broker unavailable",
            4: "Bad username/password",
            5: "Not authorized"
        }
        print_to_log(f"MQTT connection failed: {error_codes.get(rc, 'Unknown error')}")

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    if rc != 0:
        print_to_log("Unexpected MQTT disconnect — will auto-reconnect")

def on_publish(client, userdata, mid):
    pass   # Handled in main loop display

def print_to_log(msg):
    # Simple log to file for background events
    with open("monitor_log.txt", "a") as f:
        f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")

# ══════════════════════════════════════════════════════════════
# MQTT SETUP
# ══════════════════════════════════════════════════════════════
def setup_mqtt():
    client = mqtt.Client(client_id=f"TempMonitor_{int(time.time())}")
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish    = on_publish

    print(f"Connecting to MQTT broker {BROKER_IP}:{BROKER_PORT} ...")
    try:
        client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
        client.loop_start()        # Run MQTT in background thread
        time.sleep(1.5)            # Give time to connect
    except Exception as e:
        print(f"MQTT connection error: {e}")
        sys.exit(1)

    return client

# ══════════════════════════════════════════════════════════════
# SERIAL SETUP
# ══════════════════════════════════════════════════════════════
def setup_serial():
    print(f"Opening serial port {SERIAL_PORT} at {BAUD_RATE} baud ...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2)              # Wait for Arduino to reset after serial open
        print("Serial port opened successfully")
        return ser
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        print(f"Check that Arduino is connected and port is correct")
        sys.exit(1)

# ══════════════════════════════════════════════════════════════
# PARSE TEMPERATURE FROM SERIAL LINE
# Arduino sends: "TEMP:24.5"
# ══════════════════════════════════════════════════════════════
def parse_temperature(line):
    line = line.strip()
    if line.startswith("TEMP:"):
        try:
            value = float(line.split(":")[1])
            return value
        except (ValueError, IndexError):
            return None
    return None

# ══════════════════════════════════════════════════════════════
# MAIN PROGRAM
# ══════════════════════════════════════════════════════════════
def main():
    global publish_count, temperature_log

    print("\n" + "="*55)
    print("  TEMPERATURE MONITOR & MQTT PUBLISHER")
    print("="*55 + "\n")

    # Setup connections
    mqtt_client = setup_mqtt()
    ser         = setup_serial()

    print("\nMonitoring started. Reading temperature data...\n")
    time.sleep(1)

    current_temp = "--"
    current_time = "--"

    try:
        while True:
            # ── Read from Serial ─────────────────────────────────
            try:
                raw_line = ser.readline().decode('utf-8').strip()
            except UnicodeDecodeError:
                continue           # Skip garbled bytes

            if not raw_line:
                continue           # Skip empty lines

            # ── Parse Temperature ────────────────────────────────
            temp = parse_temperature(raw_line)

            if temp is not None:
                now_str      = datetime.datetime.now().strftime("%H:%M:%S")
                current_temp = f"{temp:.1f}"
                current_time = now_str

                # ── Build MQTT Payload ───────────────────────────
                payload = json.dumps({
                    "candidate":   CANDIDATE,
                    "temperature": temp,
                    "unit":        "Celsius",
                    "timestamp":   datetime.datetime.now().isoformat()
                })

                # ── Publish to MQTT Broker ───────────────────────
                if mqtt_connected:
                    result = mqtt_client.publish(MQTT_TOPIC, payload, qos=1)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        publish_count += 1

                # ── Log the reading ──────────────────────────────
                temperature_log.append({
                    "time": now_str,
                    "temp": f"{temp:.1f}"
                })
                # Keep log manageable
                if len(temperature_log) > 100:
                    temperature_log.pop(0)

                # ── Update Real-Time Display ─────────────────────
                clear_screen()
                print_header()
                print_status(
                    temp        = f"{temp:.1f}",
                    published   = publish_count,
                    connected   = mqtt_connected,
                    timestamp   = current_time
                )
                print_log(temperature_log)

            else:
                # Print non-temperature lines (startup messages etc.)
                if raw_line and not raw_line.startswith("TEMP:"):
                    print(f"  [Arduino]: {raw_line}")

    except KeyboardInterrupt:
        print("\n\n  Stopping monitor...")

    finally:
        # ── Clean Shutdown ───────────────────────────────────────
        ser.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

        # ── Final Summary ────────────────────────────────────────
        print("\n╔══════════════════════════════════════╗")
        print("║           SESSION SUMMARY            ║")
        print("╠══════════════════════════════════════╣")
        print(f"║  Total readings : {len(temperature_log):<19}║")
        print(f"║  MQTT published : {publish_count:<19}║")
        if temperature_log:
            temps = [float(e['temp']) for e in temperature_log]
            print(f"║  Min temp       : {min(temps):.1f} °C{'':<13}║")
            print(f"║  Max temp       : {max(temps):.1f} °C{'':<13}║")
            print(f"║  Average temp   : {sum(temps)/len(temps):.1f} °C{'':<13}║")
        print("╚══════════════════════════════════════╝\n")

# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()