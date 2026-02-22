# ─────────────────────────────────────────────
# arduino_controller.py  —  Hardware feedback
#
# Sends one-character commands over USB serial to Arduino.
# Arduino listens and controls:
#   • Green LED  — successful punch
#   • Red LED    — unknown face or spoof
#   • Buzzer     — short beep for success, long buzz for failure
#   • Door relay — optional, unlock on success
#
# Command protocol (single byte):
#   'S' → SUCCESS (green LED + short beep + unlock door)
#   'F' → FAIL    (red LED + long buzz)
#   'L' → LIVENESS FAIL (red LED + double buzz — specific to spoof attempt)
#
# If Arduino is not connected or ARDUINO_ENABLED=false in .env,
# all methods silently no-op so the rest of the system still works.
# ─────────────────────────────────────────────

import time
import serial
from loguru import logger

import config


class ArduinoController:

    def __init__(self):
        self._serial: serial.Serial | None = None
        self._connected = False

        if config.ARDUINO_ENABLED:
            self._connect()

    def _connect(self):
        try:
            self._serial = serial.Serial(
                port=config.ARDUINO_PORT,
                baudrate=config.ARDUINO_BAUD,
                timeout=1,
            )
            # Arduino resets on serial open — wait for it to boot
            time.sleep(2)
            self._connected = True
            logger.info(f"Arduino connected on {config.ARDUINO_PORT}")
        except serial.SerialException as exc:
            logger.warning(f"Arduino not found on {config.ARDUINO_PORT}: {exc}")
            logger.warning("Hardware feedback disabled — system will still log attendance")

    def signal_success(self):
        """Green LED + beep + door unlock."""
        self._send(b"S")

    def signal_failure(self):
        """Red LED + buzz — unknown face."""
        self._send(b"F")

    def signal_liveness_fail(self):
        """Red LED + double buzz — spoof attempt detected."""
        self._send(b"L")

    def _send(self, command: bytes):
        if not self._connected or self._serial is None:
            return
        try:
            self._serial.write(command)
        except serial.SerialException as exc:
            logger.warning(f"Arduino send failed: {exc}")
            self._connected = False   # mark as disconnected, don't crash

    def close(self):
        if self._serial and self._serial.is_open:
            self._serial.close()


# ─────────────────────────────────────────────
# ARDUINO SKETCH  (copy this to your Arduino IDE)
# ─────────────────────────────────────────────
#
# const int GREEN_LED  = 8;
# const int RED_LED    = 9;
# const int BUZZER     = 10;
# const int DOOR_RELAY = 11;   // optional — HIGH = unlock
#
# void setup() {
#   Serial.begin(9600);
#   pinMode(GREEN_LED,  OUTPUT);
#   pinMode(RED_LED,    OUTPUT);
#   pinMode(BUZZER,     OUTPUT);
#   pinMode(DOOR_RELAY, OUTPUT);
#   digitalWrite(DOOR_RELAY, LOW);  // keep locked on boot
# }
#
# void loop() {
#   if (Serial.available() > 0) {
#     char cmd = Serial.read();
#
#     if (cmd == 'S') {          // SUCCESS
#       digitalWrite(GREEN_LED, HIGH);
#       tone(BUZZER, 1000, 200); // short beep
#       digitalWrite(DOOR_RELAY, HIGH);
#       delay(3000);
#       digitalWrite(GREEN_LED, LOW);
#       digitalWrite(DOOR_RELAY, LOW);
#     }
#     else if (cmd == 'F') {     // FAIL - unknown face
#       digitalWrite(RED_LED, HIGH);
#       tone(BUZZER, 400, 800);  // long low buzz
#       delay(1000);
#       digitalWrite(RED_LED, LOW);
#     }
#     else if (cmd == 'L') {     // LIVENESS FAIL - spoof
#       for (int i=0; i<2; i++) {
#         digitalWrite(RED_LED, HIGH);
#         tone(BUZZER, 400, 300);
#         delay(400);
#         digitalWrite(RED_LED, LOW);
#         delay(200);
#       }
#     }
#   }
# }
#
# ─────────────────────────────────────────────
