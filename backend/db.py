import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from werkzeug.security import generate_password_hash, check_password_hash

from config import DB_PATH


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


@contextmanager
def get_db():
    conn = _conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('teacher','dean')),
                assigned_class TEXT
            );

            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT NOT NULL,
                class_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(roll_no, class_name)
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                att_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'present',
                marked_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id),
                UNIQUE(student_id, att_date)
            );

            CREATE INDEX IF NOT EXISTS idx_att_date ON attendance(att_date);
            CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_name);
            """
        )
        cur = conn.execute("SELECT COUNT(*) AS n FROM users")
        if cur.fetchone()["n"] == 0:
            _seed_users(conn)


def _seed_users(conn):
    conn.execute(
        """
        INSERT INTO users (username, password_hash, role, assigned_class)
        VALUES (?, ?, 'teacher', ?)
        """,
        (
            "teacher",
            generate_password_hash("teacher123"),
            "CS-101",
        ),
    )
    conn.execute(
        """
        INSERT INTO users (username, password_hash, role, assigned_class)
        VALUES (?, ?, 'dean', NULL)
        """,
        ("dean", generate_password_hash("dean123")),
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def get_user_by_username(username: str) -> Optional[dict]:
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return row_to_dict(row) if row else None


def verify_user(username: str, password: str) -> Optional[dict]:
    u = get_user_by_username(username)
    if not u or not check_password_hash(u["password_hash"], password):
        return None
    return u


def create_user(
    username: str,
    password: str,
    role: str,
    assigned_class: Optional[str] = None,
) -> int:
    """Create a teacher or dean account. Raises ValueError or sqlite3.IntegrityError."""
    if role not in ("teacher", "dean"):
        raise ValueError("Invalid role.")
    if role == "teacher" and not (assigned_class or "").strip():
        raise ValueError("Teachers must specify an assigned class.")
    cls = (assigned_class or "").strip() or None
    if role == "dean":
        cls = None
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (username, password_hash, role, assigned_class)
            VALUES (?, ?, ?, ?)
            """,
            (username, generate_password_hash(password), role, cls),
        )
        return int(cur.lastrowid)


def add_student(name: str, roll_no: str, class_name: str) -> int:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO students (name, roll_no, class_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, roll_no, class_name, now),
        )
        return int(cur.lastrowid)


def list_students(class_name: Optional[str] = None) -> list[dict]:
    with get_db() as conn:
        if class_name:
            cur = conn.execute(
                "SELECT * FROM students WHERE class_name = ? ORDER BY roll_no",
                (class_name,),
            )
        else:
            cur = conn.execute("SELECT * FROM students ORDER BY class_name, roll_no")
        return [row_to_dict(r) for r in cur.fetchall()]


def get_student(student_id: int) -> Optional[dict]:
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cur.fetchone()
        return row_to_dict(row) if row else None


def mark_attendance(student_id: int, att_date: str) -> bool:
    """Insert present for student on date. Returns True if inserted."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with get_db() as conn:
        try:
            conn.execute(
                """
                INSERT INTO attendance (student_id, att_date, status, marked_at)
                VALUES (?, ?, 'present', ?)
                """,
                (student_id, att_date, now),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def attendance_for_date(att_date: str, class_name: Optional[str] = None) -> list[dict]:
    with get_db() as conn:
        if class_name:
            cur = conn.execute(
                """
                SELECT a.*, s.name, s.roll_no, s.class_name
                FROM attendance a
                JOIN students s ON s.id = a.student_id
                WHERE a.att_date = ? AND s.class_name = ?
                ORDER BY s.roll_no
                """,
                (att_date, class_name),
            )
        else:
            cur = conn.execute(
                """
                SELECT a.*, s.name, s.roll_no, s.class_name
                FROM attendance a
                JOIN students s ON s.id = a.student_id
                WHERE a.att_date = ?
                ORDER BY s.class_name, s.roll_no
                """,
                (att_date,),
            )
        return [row_to_dict(r) for r in cur.fetchall()]


def dean_summary_for_date(att_date: str) -> dict:
    with get_db() as conn:
        present = conn.execute(
            "SELECT COUNT(DISTINCT student_id) AS c FROM attendance WHERE att_date = ?",
            (att_date,),
        ).fetchone()["c"]
        total_students = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
        by_class = conn.execute(
            """
            SELECT c.class_name AS class_name,
                   COALESCE(p.present_count, 0) AS present_count,
                   c.enrolled AS enrolled
            FROM (
                SELECT class_name, COUNT(*) AS enrolled
                FROM students
                GROUP BY class_name
            ) AS c
            LEFT JOIN (
                SELECT s.class_name AS class_name,
                       COUNT(DISTINCT a.student_id) AS present_count
                FROM attendance a
                JOIN students s ON s.id = a.student_id
                WHERE a.att_date = ?
                GROUP BY s.class_name
            ) AS p ON p.class_name = c.class_name
            ORDER BY c.class_name
            """,
            (att_date,),
        ).fetchall()
        rows = [row_to_dict(r) for r in by_class]
    absent = max(0, total_students - present)
    return {
        "date": att_date,
        "total_students": total_students,
        "present": present,
        "absent": absent,
        "by_classroom": rows,
    }


def attendance_counts_by_day(start: str, end: str) -> list[dict]:
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT att_date AS d, COUNT(DISTINCT student_id) AS present_count
            FROM attendance
            WHERE att_date >= ? AND att_date <= ?
            GROUP BY att_date
            ORDER BY att_date
            """,
            (start, end),
        )
        return [row_to_dict(r) for r in cur.fetchall()]


def attendance_percentage_for_class(class_name: str, att_date: str) -> dict:
    with get_db() as conn:
        enrolled = conn.execute(
            "SELECT COUNT(*) AS c FROM students WHERE class_name = ?",
            (class_name,),
        ).fetchone()["c"]
        present = conn.execute(
            """
            SELECT COUNT(DISTINCT a.student_id) AS c
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE a.att_date = ? AND s.class_name = ?
            """,
            (att_date, class_name),
        ).fetchone()["c"]
    pct = round(100.0 * present / enrolled, 1) if enrolled else 0.0
    return {"class_name": class_name, "date": att_date, "enrolled": enrolled, "present": present, "percentage": pct}
