# Face Recognition Attendance System
### Raspberry Pi 4 + MediaPipe + ArcFace + FAISS + Liveness Detection

---

## Project Structure

```
facerec/
├── main.py                  ← Run this — main attendance loop
├── enrollment.py            ← Register new employees
├── detector.py              ← MediaPipe face detection
├── aligner.py               ← ArcFace landmark alignment
├── liveness.py              ← Anti-spoofing (MiniFASNetV2)
├── recogniser.py            ← ArcFace embeddings + FAISS search
├── erp_client.py            ← HTTP to your ERP portal
├── arduino_controller.py    ← Serial to Arduino (LED/buzzer/door)
├── config.py                ← All settings (reads from .env)
├── requirements.txt
├── .env.example             ← Copy to .env and fill in
├── attendance.service       ← systemd auto-start
├── models/
│   └── liveness/            ← Put ONNX model here
└── data/
    ├── embeddings/          ← face_db.pkl lives here
    └── frames/              ← Unknown face captures saved here
```

---

## Setup (Do Once)

### 1. Install dependencies
```bash
pip install -r requirements.txt --break-system-packages
```

### 2. Download the liveness model
```bash
mkdir -p models/liveness
# Download MiniFASNetV2 from:
# https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/tree/master/resources/anti_spoof_models
# Rename to: 2.7_80x80_MiniFASNetV2.onnx
# Place at:  models/liveness/2.7_80x80_MiniFASNetV2.onnx
```

### 3. Configure
```bash
cp .env.example .env
nano .env          # fill in your ERP URL, API key, device ID
```

### 4. Upload Arduino sketch
- Open arduino_controller.py, scroll to the bottom
- Copy the sketch (it's in a comment block)
- Flash to your Arduino Uno/Nano via Arduino IDE
- Note which port it appears on (usually /dev/ttyUSB0 on Pi)
- Set ARDUINO_PORT in your .env

### 5. Enroll employees
```bash
# Interactive camera enrollment (recommended)
python enrollment.py --id EMP001 --name "Alice Smith"

# From existing photos
python enrollment.py --id EMP002 --name "Bob Jones" --images photo1.jpg photo2.jpg

# List everyone enrolled
python enrollment.py --list

# Remove someone
python enrollment.py --id EMP003 --delete
```

---

## Running

### Manual start (with display)
```bash
python main.py
```

### Headless (no monitor)
```bash
python main.py --headless
```

### Auto-start on boot (systemd)
```bash
sudo cp attendance.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable attendance
sudo systemctl start attendance
```

---

## ERP Integration

Your ERP needs ONE endpoint:

```
POST /api/attendance/punch
Headers: X-Api-Key: <your ERP_API_KEY>

Request body:
{
  "employee_id": "EMP001",
  "device_id":   "pi-door-01",
  "timestamp":   "2025-03-15T09:04:22+00:00"
}

Response:
{
  "success": true,
  "action":  "punch_in",   // or "punch_out"
  "employee_name": "Alice Smith"
}
```

The server decides punch_in vs punch_out based on whether the employee
already has an open shift today (no punch_out yet).

---

## Tuning Tips

| Problem | Fix |
|---|---|
| Real employees rejected | Lower RECOGNITION_THRESHOLD (try 0.45) |
| Wrong person accepted | Raise RECOGNITION_THRESHOLD (try 0.55) |
| Real faces flagged as spoof | Lower LIVENESS_THRESHOLD (try 0.5) |
| Printed photos passing | Raise LIVENESS_THRESHOLD (try 0.7) |
| System too slow on Pi | Lower CAPTURE_FPS in config.py |
| Double punches happening | Raise COOLDOWN_SECONDS in config.py |

---

## Hardware Wiring

```
Raspberry Pi 4
    USB → Arduino Uno
    USB → Webcam

Arduino Uno
    Pin 8  → Green LED → 220Ω → GND
    Pin 9  → Red LED   → 220Ω → GND
    Pin 10 → Buzzer (+)
    Pin 11 → Relay IN (for door lock — optional)
    GND    → Common ground
```
