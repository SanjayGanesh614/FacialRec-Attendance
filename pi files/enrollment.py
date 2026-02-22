# ─────────────────────────────────────────────
# enrollment.py  —  Register new employees
#
# Enrollment flow:
#   1. Capture N photos of the person (varied angles/lighting)
#   2. For each photo: detect → align → embed
#   3. Store all embeddings linked to their employee ID
#   4. Call recogniser.reload_db() so the index updates immediately
#
# Can be run standalone:
#   python enrollment.py --id EMP042 --name "Priya Rajan"
#
# Or imported and called programmatically from your ERP integration.
# ─────────────────────────────────────────────

import cv2
import pickle
import argparse
import numpy as np
from pathlib import Path
from typing import Optional
from loguru import logger

import config
from detector   import FaceDetector
from aligner    import FaceAligner
from recogniser import FaceRecogniser


class EnrollmentManager:
    """
    Handles adding, updating, and removing people from the face database.
    """

    def __init__(self, recogniser: Optional[FaceRecogniser] = None):
        self._detector  = FaceDetector()
        self._aligner   = FaceAligner()
        # Accept an existing recogniser so we can call reload_db() after enrollment
        self._recogniser = recogniser
        self._db_path = Path(config.EMBEDDINGS_DB)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Database helpers ───────────────────────────────────────────────────────

    def _load_db(self) -> dict:
        if self._db_path.exists():
            with open(self._db_path, "rb") as f:
                return pickle.load(f)
        return {"records": []}

    def _save_db(self, db: dict):
        with open(self._db_path, "wb") as f:
            pickle.dump(db, f)
        logger.info(f"Database saved → {self._db_path}")

    def _find_record(self, db: dict, employee_id: str) -> Optional[dict]:
        for rec in db["records"]:
            if rec["employee_id"] == employee_id:
                return rec
        return None

    # ── Enrollment from camera ─────────────────────────────────────────────────

    def enroll_from_camera(
        self,
        employee_id: str,
        name: str,
        num_samples: int = config.MAX_EMBEDDINGS_PER_PERSON,
        camera_index: int = config.CAMERA_INDEX,
    ) -> bool:
        """
        Interactive enrollment: open camera, guide user to capture N face samples.

        Instructions are printed to terminal.
        Press SPACE to capture a sample, Q to quit early.

        Returns True if at least 3 samples were captured successfully.
        """
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not cap.isOpened():
            logger.error(f"Cannot open camera {camera_index}")
            return False

        # Use a throwaway recogniser just to get embeddings
        from recogniser import FaceRecogniser
        rec = FaceRecogniser()

        embeddings_collected = []
        print(f"\n{'─'*50}")
        print(f"Enrolling: {name} ({employee_id})")
        print(f"Press SPACE to capture | Q to quit")
        print(f"Target: {num_samples} samples")
        print(f"{'─'*50}\n")

        try:
            while len(embeddings_collected) < num_samples:
                ret, frame = cap.read()
                if not ret:
                    continue

                faces = self._detector.detect(frame)
                display = self._detector.draw_debug(frame, faces)

                # Overlay instructions
                cv2.putText(
                    display,
                    f"Samples: {len(embeddings_collected)}/{num_samples}  |  SPACE=capture  Q=done",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                )
                cv2.imshow("Enrollment", display)

                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

                if key == ord(" "):
                    if not faces:
                        print("  No face detected — please look directly at the camera")
                        continue

                    if len(faces) > 1:
                        print("  Multiple faces detected — please ensure only one person is in frame")
                        continue

                    face    = faces[0]
                    aligned = self._aligner.align(face)
                    if aligned is None:
                        print("  Alignment failed — try again")
                        continue

                    embedding = rec.get_embedding(aligned)
                    if embedding is None:
                        print("  Embedding extraction failed — try again")
                        continue

                    embeddings_collected.append(embedding)
                    print(f"  ✓ Sample {len(embeddings_collected)}/{num_samples} captured")

        finally:
            cap.release()
            cv2.destroyAllWindows()

        if len(embeddings_collected) < 3:
            print(f"\n✗ Not enough samples ({len(embeddings_collected)}). Enrollment cancelled.")
            return False

        success = self._save_embeddings(employee_id, name, embeddings_collected)
        if success:
            print(f"\n✓ {name} enrolled successfully with {len(embeddings_collected)} samples")
            if self._recogniser:
                self._recogniser.reload_db()
        return success

    # ── Enrollment from image files ────────────────────────────────────────────

    def enroll_from_images(
        self,
        employee_id: str,
        name: str,
        image_paths: list[str],
    ) -> bool:
        """
        Enroll from a list of existing image file paths.
        Useful when you already have employee photos on file.
        """
        from recogniser import FaceRecogniser
        rec = FaceRecogniser()

        embeddings_collected = []
        for path in image_paths:
            img = cv2.imread(path)
            if img is None:
                logger.warning(f"Cannot read image: {path}")
                continue

            faces = self._detector.detect(img)
            if not faces:
                logger.warning(f"No face found in: {path}")
                continue

            # Use the largest face if multiple are found
            face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
            aligned = self._aligner.align(face)
            if aligned is None:
                continue

            embedding = rec.get_embedding(aligned)
            if embedding is not None:
                embeddings_collected.append(embedding)
                logger.info(f"  Embedded: {path}")

        if len(embeddings_collected) < 1:
            logger.error("No valid embeddings extracted from provided images")
            return False

        success = self._save_embeddings(employee_id, name, embeddings_collected)
        if success and self._recogniser:
            self._recogniser.reload_db()
        return success

    # ── Save / delete ──────────────────────────────────────────────────────────

    def _save_embeddings(self, employee_id: str, name: str, embeddings: list) -> bool:
        try:
            db = self._load_db()
            existing = self._find_record(db, employee_id)

            if existing:
                # Update: replace embeddings (re-enrollment)
                existing["embeddings"] = embeddings
                existing["name"] = name
                logger.info(f"Updated enrollment for {name} ({employee_id})")
            else:
                db["records"].append({
                    "employee_id": employee_id,
                    "name": name,
                    "embeddings": embeddings,
                })
                logger.info(f"New enrollment: {name} ({employee_id})")

            self._save_db(db)
            return True

        except Exception as exc:
            logger.error(f"Failed to save embeddings: {exc}")
            return False

    def delete_person(self, employee_id: str) -> bool:
        """Remove a person from the database (e.g. when they leave the company)."""
        db = self._load_db()
        original_count = len(db["records"])
        db["records"] = [r for r in db["records"] if r["employee_id"] != employee_id]

        if len(db["records"]) == original_count:
            logger.warning(f"Employee ID {employee_id} not found in database")
            return False

        self._save_db(db)
        if self._recogniser:
            self._recogniser.reload_db()
        logger.info(f"Deleted employee {employee_id}")
        return True

    def list_enrolled(self):
        """Print all enrolled people."""
        db = self._load_db()
        records = db.get("records", [])
        if not records:
            print("No one enrolled yet.")
            return
        print(f"\n{'─'*40}")
        print(f"{'ID':<12} {'Name':<25} {'Samples'}")
        print(f"{'─'*40}")
        for rec in records:
            print(f"{rec['employee_id']:<12} {rec['name']:<25} {len(rec['embeddings'])}")
        print(f"{'─'*40}\n")


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enroll a new employee")
    parser.add_argument("--id",      required=True, help="Employee ID (e.g. EMP042)")
    parser.add_argument("--name",    required=True, help="Full name (e.g. 'Priya Rajan')")
    parser.add_argument("--images",  nargs="*",     help="Optional: paths to existing photos")
    parser.add_argument("--delete",  action="store_true", help="Delete this employee from DB")
    parser.add_argument("--list",    action="store_true", help="List all enrolled people")
    args = parser.parse_args()

    mgr = EnrollmentManager()

    if args.list:
        mgr.list_enrolled()
    elif args.delete:
        mgr.delete_person(args.id)
    elif args.images:
        mgr.enroll_from_images(args.id, args.name, args.images)
    else:
        mgr.enroll_from_camera(args.id, args.name)
