# ─────────────────────────────────────────────
# config.py  —  All system settings in one place
# Copy .env.example to .env and fill in your values
# ─────────────────────────────────────────────

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).parent
EMBEDDINGS_DB    = BASE_DIR / "data" / "embeddings" / "face_db.pkl"
UNKNOWN_FRAMES   = BASE_DIR / "data" / "frames"
LIVENESS_MODEL   = BASE_DIR / "models" / "liveness" / "2.7_80x80_MiniFASNetV2.onnx"
LOG_FILE         = BASE_DIR / "logs" / "attendance.log"

# ── Camera ─────────────────────────────────────────────────────────────────────
CAMERA_INDEX     = int(os.getenv("CAMERA_INDEX", 0))
FRAME_WIDTH      = 640
FRAME_HEIGHT     = 480
CAPTURE_FPS      = 15        # keep low on Pi to reduce CPU pressure

# ── Detection (MediaPipe) ──────────────────────────────────────────────────────
MP_MIN_DETECTION_CONFIDENCE = 0.7
MP_MIN_TRACKING_CONFIDENCE  = 0.6
# Minimum face size (pixels) to bother recognising — filters tiny background faces
MIN_FACE_SIZE_PX = 80

# ── Recognition (ArcFace via InsightFace) ──────────────────────────────────────
# Cosine similarity threshold — tune this with your own hardware + lighting
# Start at 0.50, raise if you get false positives, lower if legitimate users fail
RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", 0.50))
# How many embeddings to keep per person during enrollment
MAX_EMBEDDINGS_PER_PERSON = 8
# InsightFace model — buffalo_sc is the lightest, good for Pi CPU
INSIGHTFACE_MODEL_PACK = "buffalo_sc"

# ── Liveness ───────────────────────────────────────────────────────────────────
LIVENESS_THRESHOLD = float(os.getenv("LIVENESS_THRESHOLD", 0.6))
# Input size expected by the MiniFASNet liveness model
LIVENESS_INPUT_SIZE = (80, 80)

# ── Attendance Logic ────────────────────────────────────────────────────────────
# After a successful punch, ignore the same face for this many seconds
#   prevents double-punching if someone stands in front of camera
COOLDOWN_SECONDS = 30
# Minimum seconds between a punch-in and punch-out for the same person
MIN_SHIFT_SECONDS = 300   # 5 minutes

# ── ERP API ────────────────────────────────────────────────────────────────────
ERP_BASE_URL     = os.getenv("ERP_BASE_URL", "http://your-erp-server.com")
ERP_PUNCH_ENDPOINT   = f"{ERP_BASE_URL}/api/attendance/punch"
ERP_API_KEY      = os.getenv("ERP_API_KEY", "")          # shared secret header
DEVICE_ID        = os.getenv("DEVICE_ID", "pi-door-01")  # identifies which terminal
ERP_TIMEOUT_SEC  = 5

# ── Arduino Serial ─────────────────────────────────────────────────────────────
ARDUINO_PORT     = os.getenv("ARDUINO_PORT", "/dev/ttyUSB0")
ARDUINO_BAUD     = 9600
ARDUINO_ENABLED  = os.getenv("ARDUINO_ENABLED", "true").lower() == "true"

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL        = os.getenv("LOG_LEVEL", "INFO")
# Save frames of unknown faces for later review / enrollment
SAVE_UNKNOWN_FRAMES = True
