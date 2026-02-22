# ─────────────────────────────────────────────
# recogniser.py  —  Stage 3: Who is this person?
#
# Uses InsightFace's ArcFace model (buffalo_sc pack)
# to generate a 512-dim embedding vector for each face,
# then searches the enrolled embedding database using
# cosine similarity via FAISS.
#
# The embedding database is stored as a .pkl file and
# loaded into a FAISS index at startup.  It is also
# re-loaded whenever you call reload_db() after enrollment.
# ─────────────────────────────────────────────

import pickle
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger

import faiss
import insightface
from insightface.app import FaceAnalysis

import config


@dataclass
class RecognitionResult:
    matched: bool
    employee_id: Optional[str]   # your ERP employee ID
    name: Optional[str]
    similarity: float            # cosine similarity score 0–1
    embedding: Optional[np.ndarray] = field(default=None, repr=False)


class FaceRecogniser:
    """
    Generates ArcFace embeddings and matches them against
    the enrolled faces database.

    Usage:
        rec = FaceRecogniser()
        result = rec.recognise(aligned_face_bgr)
    """

    def __init__(self):
        self._model = None
        self._index = None           # FAISS index
        self._index_to_meta = []     # maps FAISS vector index → {employee_id, name}
        self._db_path = config.EMBEDDINGS_DB

        self._load_model()
        self.reload_db()

    # ── Model loading ──────────────────────────────────────────────────────────

    def _load_model(self):
        """Load InsightFace buffalo_sc (lightest pack, good for Pi CPU)."""
        try:
            # ctx_id=-1 forces CPU; 0 would use GPU if available
            app = FaceAnalysis(
                name=config.INSIGHTFACE_MODEL_PACK,
                providers=["CPUExecutionProvider"],
            )
            # det_size affects detection inside InsightFace — we handle detection
            # ourselves with MediaPipe, but InsightFace still needs this set
            app.prepare(ctx_id=-1, det_size=(320, 320))
            # We only need the recognition model, not the detector
            self._model = app.models.get("recognition")
            if self._model is None:
                # Fallback: grab the first model that has an 'get_feat' method
                for name, m in app.models.items():
                    if hasattr(m, "get_feat"):
                        self._model = m
                        break
            logger.info(f"FaceRecogniser loaded InsightFace ({config.INSIGHTFACE_MODEL_PACK})")
        except Exception as exc:
            logger.error(f"Failed to load InsightFace model: {exc}")
            raise

    # ── Database management ────────────────────────────────────────────────────

    def reload_db(self):
        """
        Load (or re-load) the embeddings database from disk into a FAISS index.
        Call this after enrolling a new person so recognitions pick up the update.

        DB format (pickle):
        {
            "records": [
                {
                    "employee_id": "EMP001",
                    "name": "Alice Smith",
                    "embeddings": [np.ndarray shape (512,), ...]  # up to MAX_EMBEDDINGS_PER_PERSON
                },
                ...
            ]
        }
        """
        db_path = Path(self._db_path)
        if not db_path.exists():
            logger.info("No embedding database found — starting empty. Enroll people first.")
            self._index = faiss.IndexFlatIP(512)   # Inner Product = cosine on unit vectors
            self._index_to_meta = []
            return

        try:
            with open(db_path, "rb") as f:
                db = pickle.load(f)

            records = db.get("records", [])
            all_embeddings = []
            meta = []

            for record in records:
                for emb in record["embeddings"]:
                    all_embeddings.append(emb.astype(np.float32))
                    meta.append({
                        "employee_id": record["employee_id"],
                        "name": record["name"],
                    })

            if not all_embeddings:
                self._index = faiss.IndexFlatIP(512)
                self._index_to_meta = []
                logger.info("Embedding database is empty.")
                return

            # Stack into matrix and L2-normalise so inner product = cosine similarity
            matrix = np.stack(all_embeddings, axis=0)
            faiss.normalize_L2(matrix)

            index = faiss.IndexFlatIP(512)
            index.add(matrix)

            self._index = index
            self._index_to_meta = meta
            logger.info(f"Loaded {len(all_embeddings)} embeddings for {len(records)} people")

        except Exception as exc:
            logger.error(f"Failed to load embedding DB: {exc}")

    # ── Embedding extraction ───────────────────────────────────────────────────

    def get_embedding(self, aligned_face_bgr: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract a 512-dim ArcFace embedding from an aligned 112×112 BGR face image.
        Returns None if extraction fails.
        """
        if self._model is None or aligned_face_bgr is None:
            return None

        try:
            # InsightFace recognition model expects BGR, shape (112, 112, 3)
            feat = self._model.get_feat(aligned_face_bgr)
            if feat is None:
                return None
            embedding = feat.flatten().astype(np.float32)
            # L2 normalise so we can use inner product as cosine similarity
            norm = np.linalg.norm(embedding)
            if norm < 1e-6:
                return None
            return embedding / norm

        except Exception as exc:
            logger.error(f"Embedding extraction failed: {exc}")
            return None

    # ── Recognition ────────────────────────────────────────────────────────────

    def recognise(self, aligned_face_bgr: np.ndarray) -> RecognitionResult:
        """
        Identify who this face belongs to.

        Returns RecognitionResult with matched=True and employee details
        if a match is found above threshold, otherwise matched=False.
        """
        embedding = self.get_embedding(aligned_face_bgr)

        if embedding is None:
            return RecognitionResult(matched=False, employee_id=None, name=None, similarity=0.0)

        if self._index is None or self._index.ntotal == 0:
            logger.warning("Recogniser: database is empty — no one enrolled yet")
            return RecognitionResult(
                matched=False, employee_id=None, name="[DB Empty]",
                similarity=0.0, embedding=embedding
            )

        try:
            query = embedding[np.newaxis, :].copy()
            faiss.normalize_L2(query)

            # Search for 1 nearest neighbour
            distances, indices = self._index.search(query, k=1)
            similarity = float(distances[0][0])
            idx = int(indices[0][0])

            if idx < 0 or idx >= len(self._index_to_meta):
                return RecognitionResult(matched=False, employee_id=None, name=None,
                                         similarity=similarity, embedding=embedding)

            meta = self._index_to_meta[idx]

            if similarity >= config.RECOGNITION_THRESHOLD:
                logger.info(
                    f"Recognised: {meta['name']} ({meta['employee_id']}) "
                    f"similarity={similarity:.3f}"
                )
                return RecognitionResult(
                    matched=True,
                    employee_id=meta["employee_id"],
                    name=meta["name"],
                    similarity=similarity,
                    embedding=embedding,
                )
            else:
                logger.info(f"Unknown face — best match: {meta['name']} sim={similarity:.3f} (below threshold {config.RECOGNITION_THRESHOLD})")
                return RecognitionResult(
                    matched=False,
                    employee_id=None,
                    name=None,
                    similarity=similarity,
                    embedding=embedding,
                )

        except Exception as exc:
            logger.error(f"Recognition search failed: {exc}")
            return RecognitionResult(matched=False, employee_id=None, name=None, similarity=0.0)
