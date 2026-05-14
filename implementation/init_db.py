import sqlite3
import os

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    cohort  TEXT    NOT NULL,
    score   REAL    NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT    NOT NULL,
    credits INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS enrollments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id  INTEGER NOT NULL REFERENCES courses(id),
    grade      TEXT
);
"""

SEED_SQL = """
INSERT OR IGNORE INTO students (id, name, cohort, score) VALUES
    (1, 'Alice',  'A1', 92.5),
    (2, 'Bob',    'A1', 78.0),
    (3, 'Carol',  'A2', 88.5),
    (4, 'David',  'A2', 65.0),
    (5, 'Eve',    'A1', 95.0);
INSERT OR IGNORE INTO courses (id, title, credits) VALUES
    (1, 'Python Basics',    3),
    (2, 'Data Structures',  4),
    (3, 'Machine Learning', 4);
INSERT OR IGNORE INTO enrollments (id, student_id, course_id, grade) VALUES
    (1, 1, 1, 'A'),
    (2, 1, 2, 'B+'),
    (3, 2, 1, 'B'),
    (4, 3, 3, 'A-'),
    (5, 4, 2, 'C+'),
    (6, 5, 3, 'A');
"""


def create_database(path: str = "lab.db") -> str:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SEED_SQL)
    conn.commit()
    conn.close()
    return path


if __name__ == "__main__":
    db_path = create_database(
        os.path.join(os.path.dirname(__file__), "lab.db")
    )
    print(f"Database created: {db_path}")
