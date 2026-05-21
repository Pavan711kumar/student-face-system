import base64
import json
from typing import Optional

import cv2
import numpy as np

from config import DATASET_DIR, LABEL_MAP_PATH, LBPH_CONFIDENCE_THRESHOLD, MODEL_PATH

FACE_SIZE = (200, 200)
IMAGE_EXTENSIONS = ("*.png", "*.jpg", "*.jpeg")


_CASCADE = None


def _cascade():
    global _CASCADE
    if _CASCADE is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _CASCADE = cv2.CascadeClassifier(path)
    return _CASCADE


def is_model_ready() -> bool:
    return MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 0


def decode_base64_image(b64: str) -> Optional[np.ndarray]:
    if not b64:
        return None
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return None
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def largest_face_roi_gray(bgr: np.ndarray) -> Optional[np.ndarray]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = _cascade().detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(40, 40))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    roi = gray[y : y + h, x : x + w]
    return _normalize_face(roi)


def _normalize_face(gray_roi: np.ndarray) -> np.ndarray:
    return cv2.resize(gray_roi, FACE_SIZE, interpolation=cv2.INTER_AREA)


def _list_face_files(student_dir) -> list:
    paths = []
    for pattern in IMAGE_EXTENSIONS:
        paths.extend(student_dir.glob(pattern))
    return sorted(paths, key=lambda p: p.name.lower())


def save_student_face_image(student_id: int, bgr: np.ndarray) -> bool:
    roi = largest_face_roi_gray(bgr)
    if roi is None:
        return False
    folder = DATASET_DIR / str(student_id)
    folder.mkdir(parents=True, exist_ok=True)
    n = len(_list_face_files(folder))
    out = folder / f"{n + 1}.png"
    ok = cv2.imwrite(str(out), roi)
    return bool(ok)


def collect_training_samples():
    """Returns (faces list of gray mats, labels list of student ids)."""
    faces = []
    labels = []
    if not DATASET_DIR.exists():
        return faces, labels
    for sub in sorted(DATASET_DIR.iterdir()):
        if not sub.is_dir():
            continue
        try:
            sid = int(sub.name)
        except ValueError:
            continue
        for img_path in _list_face_files(sub):
            g = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if g is None or g.size == 0:
                continue
            faces.append(_normalize_face(g))
            labels.append(sid)
    return faces, labels


def dataset_stats() -> dict:
    """Counts saved face samples per student folder."""
    per_student: dict[int, int] = {}
    total = 0
    if DATASET_DIR.exists():
        for sub in DATASET_DIR.iterdir():
            if not sub.is_dir():
                continue
            try:
                sid = int(sub.name)
            except ValueError:
                continue
            n = len(_list_face_files(sub))
            if n:
                per_student[sid] = n
                total += n
    return {
        "total_images": total,
        "students_with_images": len(per_student),
        "per_student": per_student,
    }


def train_and_save_model() -> tuple[bool, str]:
    faces, labels = collect_training_samples()
    n_faces = len(faces)
    n_students = len(set(labels))

    if n_faces == 0:
        return (
            False,
            "No face images in dataset/. Register a student with a webcam capture, "
            "or add extra samples below, then train again.",
        )
    if n_students < 1:
        return False, "No valid student folders in dataset/."

    recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
    recognizer.train(faces, np.array(labels, dtype=np.int32))
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    recognizer.write(str(MODEL_PATH))
    label_map = {str(int(l)): int(l) for l in sorted(set(labels))}
    LABEL_MAP_PATH.write_text(json.dumps(label_map), encoding="utf-8")

    msg = f"Trained on {n_faces} image(s) from {n_students} student(s)."
    if n_faces < 3:
        msg += " Tip: add 3–5 captures per student for better recognition."
    return True, msg


def load_recognizer():
    if not MODEL_PATH.exists():
        return None
    r = cv2.face.LBPHFaceRecognizer_create()
    r.read(str(MODEL_PATH))
    return r


def predict_from_gray(gray_roi: np.ndarray) -> Optional[tuple[int, float]]:
    """Recognize from a normalized grayscale face (used after detection or in tests)."""
    recognizer = load_recognizer()
    if recognizer is None:
        return None
    face = _normalize_face(gray_roi)
    label, confidence = recognizer.predict(face)
    if confidence > LBPH_CONFIDENCE_THRESHOLD:
        return None
    return int(label), float(confidence)


def detect_face_boxes(bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = _cascade().detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(40, 40))
    return [tuple(int(v) for v in f) for f in faces]


def predict_student_id(bgr: np.ndarray) -> Optional[tuple[int, float]]:
    roi = largest_face_roi_gray(bgr)
    if roi is None:
        return None
    return predict_from_gray(roi)
