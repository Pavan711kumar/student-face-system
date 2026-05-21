"""HTTP and import smoke tests for the attendance API."""

from __future__ import annotations

import uuid

import pytest

import face_utils


def test_teacher_students_requires_auth(client):
    r = client.get("/api/teacher/students")
    assert r.status_code == 401


def test_bad_login(client):
    r = client.post("/api/login", json={"username": "x", "password": "y"})
    assert r.status_code == 400


def test_register_teacher_and_login(client):
    username = f"teacher_{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/register",
        json={
            "username": username,
            "password": "secret99",
            "role": "teacher",
            "assigned_class": "MATH-201",
        },
    )
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    r = client.post("/api/login", json={"username": username, "password": "secret99"})
    assert r.status_code == 200
    assert r.get_json()["role"] == "teacher"
    assert r.get_json()["assigned_class"] == "MATH-201"


def test_register_dean(client):
    username = f"dean_{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/register",
        json={"username": username, "password": "secret99", "role": "dean"},
    )
    assert r.status_code == 200
    r = client.post("/api/login", json={"username": username, "password": "secret99"})
    assert r.get_json()["role"] == "dean"


def test_register_duplicate_username(client):
    client.post(
        "/api/register",
        json={"username": "dupuser", "password": "secret99", "role": "dean"},
    )
    r = client.post(
        "/api/register",
        json={"username": "dupuser", "password": "other99", "role": "dean"},
    )
    assert r.status_code == 400


def test_teacher_login_and_me(client):
    r = client.post("/api/login", json={"username": "teacher", "password": "teacher123"})
    assert r.status_code == 200
    assert r.get_json()["role"] == "teacher"
    r = client.get("/api/me")
    j = r.get_json()
    assert j["ok"] and j["user"]["role"] == "teacher"


def test_teacher_list_students(client):
    client.post("/api/login", json={"username": "teacher", "password": "teacher123"})
    r = client.get("/api/teacher/students")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_train_without_dataset_returns_ok_false(client, monkeypatch):
    monkeypatch.setattr(face_utils, "collect_training_samples", lambda: ([], []))
    client.post("/api/login", json={"username": "teacher", "password": "teacher123"})
    r = client.post("/api/teacher/train")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is False
    assert "message" in j


def test_dean_summary_and_timeseries(client):
    client.post("/api/login", json={"username": "dean", "password": "dean123"})
    r = client.get("/api/dean/summary")
    assert r.status_code == 200
    assert "summary" in r.get_json()
    r = client.get("/api/dean/timeseries?start=2026-01-01&end=2026-12-31")
    assert r.status_code == 200
    assert "points" in r.get_json()


def test_teacher_cannot_access_dean_routes(client):
    client.post("/api/login", json={"username": "teacher", "password": "teacher123"})
    r = client.get("/api/dean/summary")
    assert r.status_code == 401


def test_index_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Face Recognition" in r.data


def test_face_utils_invalid_base64_returns_none():
    assert face_utils.decode_base64_image("not-valid-base64!!!") is None


def test_opencv_lbph_available():
    import cv2

    r = cv2.face.LBPHFaceRecognizer_create()
    assert r is not None


def test_train_with_single_face_image(tmp_path, monkeypatch):
    import cv2
    import numpy as np

    import face_utils

    monkeypatch.setattr(face_utils, "DATASET_DIR", tmp_path)
    monkeypatch.setattr(face_utils, "MODEL_PATH", tmp_path / "lbph_model.yml")
    monkeypatch.setattr(face_utils, "LABEL_MAP_PATH", tmp_path / "label_map.json")

    folder = tmp_path / "42"
    folder.mkdir()
    img = np.full((120, 120), 140, dtype=np.uint8)
    cv2.imwrite(str(folder / "1.png"), img)

    ok, msg = face_utils.train_and_save_model()
    assert ok is True
    assert "1 image" in msg
    assert (tmp_path / "lbph_model.yml").exists()
