# ─────────────────────────────────────────────
# main.py  —  Main attendance loop
#
# Orchestrates the full pipeline:
#   Camera → Detect → Liveness → Align → Recognise → Punch ERP → Arduino
#
# Run with:
#   python main.py
#
# Environment variables (set in .env):
#   ERP_BASE_URL, ERP_API_KEY, DEVICE_ID
#   CAMERA_INDEX, ARDUINO_PORT, ARDUINO_ENABLED
#   RECOGNITION_THRESHOLD, LIVENESS_THRESHOLD
# ─────────────────────────────────────────────

import cv2
import sys
import time
import signal
import datetime
import numpy as np
from pathlib import Path
from loguru import logger

import config
from detector           import FaceDetector
from aligner            import FaceAligner
from liveness           import LivenessDetector
from recogniser         import FaceRecogniser
from erp_client         import ERPClient
from arduino_controller import ArduinoController


# ── Logging setup ──────────────────────────────────────────────────────────────
logger.remove()
logger.add(sys.stdout, level=config.LOG_LEVEL, colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add(config.LOG_FILE, level="DEBUG", rotation="10 MB", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


class AttendanceSystem:

    def __init__(self):
        logger.info("Initialising attendance system...")

        self.detector   = FaceDetector()
        self.aligner    = FaceAligner()
        self.liveness   = LivenessDetector()
        self.recogniser = FaceRecogniser()
        self.erp        = ERPClient()
        self.arduino    = ArduinoController()

        self._running   = False
        self._cap       = None

        # Overlay display state
        self._overlay_text  = "Ready"
        self._overlay_color = (0, 255, 0)
        self._overlay_until = 0.0

        logger.success("All modules loaded — system ready")

    # ── Camera ─────────────────────────────────────────────────────────────────

    def _open_camera(self) -> bool:
        self._cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, config.CAPTURE_FPS)

        if not self._cap.isOpened():
            logger.error(f"Cannot open camera index {config.CAMERA_INDEX}")
            return False

        logger.info(f"Camera opened ({config.FRAME_WIDTH}×{config.FRAME_HEIGHT} @ {config.CAPTURE_FPS}fps)")
        return True

    # ── Main processing pipeline ───────────────────────────────────────────────

    def _process_frame(self, frame: np.ndarray):
        """
        Full pipeline for one video frame.
        Returns the annotated frame for display.
        """
        # ── Step 1: Detect all faces ──────────────────────────────────────────
        faces = self.detector.detect(frame)
        display = self.detector.draw_debug(frame, faces)

        for face in faces:
            # ── Step 2: Align face ────────────────────────────────────────────
            aligned = self.aligner.align(face)
            if aligned is None:
                continue

            # ── Step 3: Liveness check ────────────────────────────────────────
            is_real, liveness_score = self.liveness.check(aligned)

            if not is_real:
                logger.warning(f"Spoof attempt detected (score: {liveness_score:.3f})")
                self.arduino.signal_liveness_fail()
                self._set_overlay("SPOOF DETECTED", (0, 0, 255), duration=2)
                # Save the frame for audit
                self._save_unknown_frame(frame, label="spoof")
                continue

            # ── Step 4: Recognise ─────────────────────────────────────────────
            result = self.recogniser.recognise(aligned)

            if not result.matched:
                # Unknown face
                self.arduino.signal_failure()
                self._set_overlay("UNKNOWN FACE", (0, 0, 255), duration=2)
                if config.SAVE_UNKNOWN_FRAMES:
                    self._save_unknown_frame(frame, label="unknown")

                x1, y1, x2, y2 = face.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(display, "Unknown", (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                continue

            # ── Step 5: Punch ERP ─────────────────────────────────────────────
            punch = self.erp.punch(result.employee_id, result.name)

            x1, y1, x2, y2 = face.bbox

            if punch.action == "cooldown":
                # Still in cooldown — show name but don't re-punch
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 165, 0), 2)
                cv2.putText(display, f"{result.name} (wait)", (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
                continue

            if punch.success:
                action_label = "IN ✓" if punch.action == "punch_in" else "OUT ✓"
                color = (0, 200, 0) if punch.action == "punch_in" else (0, 165, 255)
                self.arduino.signal_success()
                self._set_overlay(f"{result.name} — {action_label}", color, duration=3)
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display, f"{result.name} {action_label}", (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            else:
                self.arduino.signal_failure()
                self._set_overlay(f"Error: {punch.message}", (0, 0, 255), duration=3)

        # ── Render overlay text ───────────────────────────────────────────────
        if time.time() < self._overlay_until:
            cv2.putText(display, self._overlay_text, (10, config.FRAME_HEIGHT - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, self._overlay_color, 2)

        return display

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _set_overlay(self, text: str, color: tuple, duration: float = 2.0):
        self._overlay_text  = text
        self._overlay_color = color
        self._overlay_until = time.time() + duration

    def _save_unknown_frame(self, frame: np.ndarray, label: str = "unknown"):
        """Save frame to disk for manual review / later enrollment."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = Path(config.UNKNOWN_FRAMES) / f"{label}_{ts}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), frame)

    # ── Run loop ───────────────────────────────────────────────────────────────

    def run(self, show_window: bool = True):
        """
        Start the main loop.

        show_window=True opens a preview window (needs display / VNC).
        Set show_window=False for headless Pi deployments.
        """
        if not self._open_camera():
            return

        self._running = True
        logger.info("Attendance system running — press Ctrl+C to stop")

        # ── Frame rate tracking ───────────────────────────────────────────────
        frame_count = 0
        fps_timer   = time.time()

        try:
            while self._running:
                ret, frame = self._cap.read()
                if not ret:
                    logger.warning("Camera read failed — retrying")
                    time.sleep(0.1)
                    continue

                display = self._process_frame(frame)

                frame_count += 1
                elapsed = time.time() - fps_timer
                if elapsed >= 5.0:
                    fps = frame_count / elapsed
                    logger.debug(f"FPS: {fps:.1f}")
                    frame_count = 0
                    fps_timer   = time.time()

                if show_window:
                    cv2.imshow("Attendance System", display)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.shutdown()

    def shutdown(self):
        self._running = False
        if self._cap:
            self._cap.release()
        cv2.destroyAllWindows()
        self.detector.close()
        self.arduino.close()
        logger.info("System shut down cleanly")


# ── Signal handling (for running as a systemd service) ────────────────────────

_system = None

def _handle_signal(sig, frame):
    global _system
    if _system:
        _system.shutdown()
    sys.exit(0)

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT,  _handle_signal)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true",
                        help="Run without display window (for Pi with no monitor)")
    args = parser.parse_args()

    _system = AttendanceSystem()
    _system.run(show_window=not args.headless)
