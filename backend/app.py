import csv
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session

import db
from config import RECORDS_DIR, SECRET_KEY
import face_utils

FRONTEND_DIR = (Path(__file__).resolve().parent.parent / "frontend").resolve()

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.secret_key = SECRET_KEY

db.init_db()


def require_role(*roles):
    def deco(f):
        @wraps(f)
        def w(*args, **kwargs):
            if "user_id" not in session or session.get("role") not in roles:
                return jsonify({"ok": False, "error": "Unauthorized"}), 401
            return f(*args, **kwargs)

        return w

    return deco


@app.route("/")
def root():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/teacher.html")
def teacher_page():
    return send_from_directory(app.static_folder, "teacher.html")


@app.route("/dean.html")
def dean_page():
    return send_from_directory(app.static_folder, "dean.html")


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().lower()
    assigned_class = (data.get("assigned_class") or "").strip()

    if len(username) < 3:
        return jsonify({"ok": False, "error": "Username must be at least 3 characters."}), 400
    if len(password) < 6:
        return jsonify({"ok": False, "error": "Password must be at least 6 characters."}), 400
    if role not in ("teacher", "dean"):
        return jsonify({"ok": False, "error": "Role must be teacher or dean."}), 400
    if role == "teacher" and not assigned_class:
        return jsonify({"ok": False, "error": "Assigned class is required for teachers."}), 400
    if db.get_user_by_username(username):
        return jsonify({"ok": False, "error": "Username already taken."}), 400

    try:
        db.create_user(username, password, role, assigned_class or None)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "Could not create account."}), 400

    return jsonify(
        {
            "ok": True,
            "message": "Account created. You can sign in now.",
            "role": role,
            "username": username,
        }
    )


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = db.verify_user(username, password)
    if not user:
        return jsonify({"ok": False, "error": "Invalid username or password"}), 400
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["assigned_class"] = user.get("assigned_class")
    return jsonify(
        {
            "ok": True,
            "role": user["role"],
            "username": user["username"],
            "assigned_class": user.get("assigned_class"),
        }
    )


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"ok": False, "user": None})
    return jsonify(
        {
            "ok": True,
            "user": {
                "username": session.get("username"),
                "role": session.get("role"),
                "assigned_class": session.get("assigned_class"),
            },
        }
    )


@app.post("/api/teacher/students")
@require_role("teacher")
def teacher_add_student():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    roll_no = (data.get("roll_no") or "").strip()
    class_name = (data.get("class_name") or "").strip() or (session.get("assigned_class") or "")
    image = data.get("image_base64")
    if not name or not roll_no or not class_name:
        return jsonify({"ok": False, "error": "Name, roll number, and class are required."}), 400
    assigned = session.get("assigned_class")
    if assigned and class_name != assigned:
        return jsonify(
            {
                "ok": False,
                "error": f"Students must be registered for your assigned class ({assigned}).",
            }
        ), 400
    img = face_utils.decode_base64_image(image) if image else None
    if img is None:
        return jsonify({"ok": False, "error": "A webcam capture (image) is required."}), 400
    try:
        sid = db.add_student(name, roll_no, class_name)
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return jsonify({"ok": False, "error": "Roll number already exists in this class."}), 400
        raise
    if not face_utils.save_student_face_image(sid, img):
        # rollback student row if no face — keep DB simple: delete student
        with db.get_db() as conn:
            conn.execute("DELETE FROM students WHERE id = ?", (sid,))
        return jsonify({"ok": False, "error": "No face detected. Try better lighting and face the camera."}), 400
    return jsonify({"ok": True, "student_id": sid})


@app.get("/api/teacher/students")
@require_role("teacher")
def teacher_list_students():
    cls = session.get("assigned_class")
    rows = db.list_students(cls)
    return jsonify({"ok": True, "students": rows})


@app.post("/api/teacher/capture")
@require_role("teacher")
def teacher_extra_capture():
    """Add another training image for an existing student."""
    data = request.get_json(silent=True) or {}
    sid = int(data.get("student_id") or 0)
    image = data.get("image_base64")
    st = db.get_student(sid)
    if not st:
        return jsonify({"ok": False, "error": "Student not found."}), 404
    assigned = session.get("assigned_class")
    if assigned and st["class_name"] != assigned:
        return jsonify({"ok": False, "error": "Not allowed for this student."}), 403
    img = face_utils.decode_base64_image(image) if image else None
    if img is None:
        return jsonify({"ok": False, "error": "Invalid image."}), 400
    if not face_utils.save_student_face_image(sid, img):
        return jsonify({"ok": False, "error": "No face detected."}), 400
    return jsonify({"ok": True})


@app.get("/api/teacher/training-stats")
@require_role("teacher")
def teacher_training_stats():
    stats = face_utils.dataset_stats()
    cls = session.get("assigned_class")
    students = db.list_students(cls)
    rows = []
    for s in students:
        sid = s["id"]
        rows.append(
            {
                "student_id": sid,
                "name": s["name"],
                "roll_no": s["roll_no"],
                "samples": stats["per_student"].get(sid, 0),
            }
        )
    return jsonify(
        {
            "ok": True,
            "total_images": stats["total_images"],
            "students_with_images": stats["students_with_images"],
            "model_ready": face_utils.is_model_ready(),
            "students": rows,
        }
    )


@app.get("/api/teacher/model-status")
@require_role("teacher")
def teacher_model_status():
    stats = face_utils.dataset_stats()
    return jsonify(
        {
            "ok": True,
            "model_ready": face_utils.is_model_ready(),
            "total_images": stats["total_images"],
            "students_with_images": stats["students_with_images"],
        }
    )


@app.post("/api/teacher/train")
@require_role("teacher")
def teacher_train():
    ok, msg = face_utils.train_and_save_model()
    return jsonify({"ok": ok, "message": msg})


@app.post("/api/teacher/recognize")
@require_role("teacher")
def teacher_recognize():
    data = request.get_json(silent=True) or {}
    image = data.get("image_base64")
    att_date = (data.get("date") or date.today().isoformat()).strip()
    img = face_utils.decode_base64_image(image) if image else None
    if img is None:
        return jsonify({"ok": False, "error": "Invalid image."}), 400
    if not face_utils.is_model_ready():
        return jsonify(
            {
                "ok": True,
                "recognized": False,
                "model_ready": False,
                "face_detected": False,
                "message": "Model not trained. Open Train model and click Train now.",
            }
        )
    boxes = face_utils.detect_face_boxes(img)
    pred = face_utils.predict_student_id(img)
    if pred is None:
        msg = "No face detected. Face the camera in good light." if not boxes else "No confident match."
        return jsonify(
            {
                "ok": True,
                "recognized": False,
                "model_ready": True,
                "face_detected": bool(boxes),
                "message": msg,
            }
        )
    student_id, confidence = pred
    st = db.get_student(student_id)
    if not st:
        return jsonify({"ok": True, "recognized": False, "message": "Unknown label."})
    assigned = session.get("assigned_class")
    if assigned and st["class_name"] != assigned:
        return jsonify({"ok": True, "recognized": False, "message": "Student not in your class."})
    inserted = db.mark_attendance(student_id, att_date)
    return jsonify(
        {
            "ok": True,
            "recognized": True,
            "model_ready": True,
            "face_detected": True,
            "already_marked": not inserted,
            "confidence": confidence,
            "student": {"id": st["id"], "name": st["name"], "roll_no": st["roll_no"], "class_name": st["class_name"]},
        }
    )


@app.get("/api/teacher/attendance")
@require_role("teacher")
def teacher_attendance():
    att_date = request.args.get("date") or date.today().isoformat()
    cls = session.get("assigned_class")
    rows = db.attendance_for_date(att_date, cls)
    return jsonify({"ok": True, "date": att_date, "records": rows})


@app.get("/api/teacher/roster")
@require_role("teacher")
def teacher_roster():
    """Students in class with present/absent for a date."""
    att_date = request.args.get("date") or date.today().isoformat()
    cls = session.get("assigned_class")
    if not cls:
        return jsonify({"ok": False, "error": "No class assigned to this teacher account."}), 400
    students = db.list_students(cls)
    present_rows = db.attendance_for_date(att_date, cls)
    present_ids = {r["student_id"] for r in present_rows}
    roster = []
    for s in students:
        roster.append(
            {
                **s,
                "status": "present" if s["id"] in present_ids else "absent",
            }
        )
    pct = db.attendance_percentage_for_class(cls, att_date)
    return jsonify({"ok": True, "date": att_date, "roster": roster, "percentage": pct})


@app.get("/api/dean/summary")
@require_role("dean")
def dean_summary():
    att_date = request.args.get("date") or date.today().isoformat()
    s = db.dean_summary_for_date(att_date)
    for row in s["by_classroom"]:
        en = row.get("enrolled") or 0
        pr = row.get("present_count") or 0
        row["percentage"] = round(100.0 * pr / en, 1) if en else 0.0
    return jsonify({"ok": True, "summary": s})


@app.get("/api/dean/timeseries")
@require_role("dean")
def dean_timeseries():
    end = request.args.get("end") or date.today().isoformat()
    start = request.args.get("start") or (date.today() - timedelta(days=30)).isoformat()
    rows = db.attendance_counts_by_day(start, end)
    return jsonify({"ok": True, "start": start, "end": end, "points": rows})


@app.get("/api/dean/export")
@require_role("dean")
def dean_export():
    att_date = request.args.get("date") or date.today().isoformat()
    rows = db.attendance_for_date(att_date, None)
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    path = RECORDS_DIR / f"attendance_{att_date}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "student_id", "roll_no", "name", "class", "status", "marked_at"])
        for r in rows:
            w.writerow(
                [
                    r["att_date"],
                    r["student_id"],
                    r["roll_no"],
                    r["name"],
                    r["class_name"],
                    r["status"],
                    r["marked_at"],
                ]
            )
    return send_from_directory(str(RECORDS_DIR), path.name, as_attachment=True)


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
