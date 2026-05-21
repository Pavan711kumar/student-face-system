"""End-to-end tests for train → predict recognition pipeline."""

from __future__ import annotations

import uuid

import cv2
import numpy as np
import pytest

import face_utils


def _synthetic_face(seed: int) -> np.ndarray:
    """Distinct grayscale pattern per student (LBPH can separate labels)."""
    g = np.full((160, 160), 70 + seed * 25, dtype=np.uint8)
    cv2.circle(g, (80, 80), 35, 120 + seed * 10, -1)
    cv2.rectangle(g, (40, 50), (120, 130), 90 + seed * 8, 2)
    cv2.line(g, (50, 100), (110, 60), 200 - seed * 5, 2)
    return face_utils._normalize_face(g)


def _gray_to_bgr(gray: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def face_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(face_utils, "DATASET_DIR", tmp_path)
    monkeypatch.setattr(face_utils, "MODEL_PATH", tmp_path / "lbph_model.yml")
    monkeypatch.setattr(face_utils, "LABEL_MAP_PATH", tmp_path / "label_map.json")
    return tmp_path


def test_train_predict_single_student(face_paths):
    sid = 7
    folder = face_paths / str(sid)
    folder.mkdir()
    for i in range(3):
        cv2.imwrite(str(folder / f"{i + 1}.png"), _synthetic_face(sid))

    ok, msg = face_utils.train_and_save_model()
    assert ok is True
    assert face_utils.is_model_ready()

    probe = _synthetic_face(sid)
    pred = face_utils.predict_from_gray(probe)
    assert pred is not None
    label, confidence = pred
    assert label == sid
    assert confidence < face_utils.LBPH_CONFIDENCE_THRESHOLD


def test_train_predict_two_students(face_paths):
    for sid in (1, 2):
        folder = face_paths / str(sid)
        folder.mkdir()
        for i in range(2):
            cv2.imwrite(str(folder / f"{i + 1}.png"), _synthetic_face(sid))

    ok, _ = face_utils.train_and_save_model()
    assert ok

    p1 = face_utils.predict_from_gray(_synthetic_face(1))
    p2 = face_utils.predict_from_gray(_synthetic_face(2))
    assert p1 and p1[0] == 1
    assert p2 and p2[0] == 2


def test_predict_without_model(face_paths):
    assert face_utils.is_model_ready() is False
    assert face_utils.predict_from_gray(_synthetic_face(1)) is None


def test_http_recognition_pipeline(client, face_paths, monkeypatch):
    """Register student, inject dataset, train, recognize via API."""
    monkeypatch.setattr(face_utils, "DATASET_DIR", face_paths)
    monkeypatch.setattr(face_utils, "MODEL_PATH", face_paths / "lbph_model.yml")
    monkeypatch.setattr(face_utils, "LABEL_MAP_PATH", face_paths / "label_map.json")

    username = f"t_{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/register",
        json={
            "username": username,
            "password": "secret99",
            "role": "teacher",
            "assigned_class": "TEST-99",
        },
    )
    client.post("/api/login", json={"username": username, "password": "secret99"})

    # Add student directly in DB + dataset (bypass webcam Haar for CI)
    import db

    roll = f"R{uuid.uuid4().hex[:6]}"
    sid = db.add_student("Test User", roll, "TEST-99")
    folder = face_paths / str(sid)
    folder.mkdir()
    face_img = _synthetic_face(sid)
    cv2.imwrite(str(folder / "1.png"), face_img)

    r = client.post("/api/teacher/train")
    assert r.get_json()["ok"] is True

    r = client.get("/api/teacher/model-status")
    assert r.get_json()["model_ready"] is True

    gray = _synthetic_face(sid)
    bgr = _gray_to_bgr(gray)
    _, buf = cv2.imencode(".jpg", bgr)
    import base64

    b64 = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

    monkeypatch.setattr(
        face_utils,
        "largest_face_roi_gray",
        lambda _img: face_utils._normalize_face(gray),
    )

    r = client.post("/api/teacher/recognize", json={"image_base64": b64, "date": "2026-05-20"})
    j = r.get_json()
    assert j["recognized"] is True
    assert j["student"]["roll_no"] == roll
