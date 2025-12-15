from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev-secret-key"

# --------------------
# DB接続用関数
# --------------------
def get_db_connection():
    conn = sqlite3.connect("mood.db")
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db_connection()

    # users テーブル
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # records テーブル
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            weekday TEXT NOT NULL,
            weather TEXT,
            score INTEGER,
            good1 TEXT,
            good2 TEXT,
            good3 TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()

# --------------------
# トップ（ログイン画面）
# --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nickname = request.form.get("nickname")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE nickname = ?",
            (nickname,)
        ).fetchone()

        if user is None:
            conn.execute(
                "INSERT INTO users (nickname, password) VALUES (?, ?)",
                (nickname, password)
            )
            conn.commit()
            user = conn.execute(
                "SELECT * FROM users WHERE nickname = ?",
                (nickname,)
            ).fetchone()

        conn.close()
        session["user_id"] = user["id"]
        return redirect("/record")

    return render_template("login.html")

@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/record")
    return redirect("/login")


@app.route("/record", methods=["GET", "POST"])
def record():
    if "user_id" not in session:
        return redirect("/")

    today = datetime.now()
    date = today.strftime("%Y-%m-%d")
    weekday = today.strftime("%A")

    if request.method == "POST":
        weather = request.form.get("weather")
        score = request.form.get("score")
        good1 = request.form.get("good1")
        good2 = request.form.get("good2")
        good3 = request.form.get("good3")

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO records
            (user_id, date, weekday, weather, score, good1, good2, good3)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            date,
            weekday,
            weather,
            score,
            good1,
            good2,
            good3
        ))
        conn.commit()
        conn.close()

        return redirect("/record")

    return render_template("record.html", date=date, weekday=weekday)



# --------------------
# 記録画面（仮）
# --------------------
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    records = conn.execute("""
    SELECT
        id,
        date,
        weekday,
        weather,
        score,
        good1,
        good2,
        good3
    FROM records
    WHERE user_id = ?
    ORDER BY date DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("history.html", records=records)
@app.route("/edit/<int:record_id>", methods=["GET", "POST"])
def edit(record_id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()

    record = conn.execute("""
        SELECT *
        FROM records
        WHERE id = ? AND user_id = ?
    """, (record_id, session["user_id"])).fetchone()

    if record is None:
        conn.close()
        return redirect("/history")

    if request.method == "POST":
        weather = request.form.get("weather")
        score = request.form.get("score")
        good1 = request.form.get("good1")
        good2 = request.form.get("good2")
        good3 = request.form.get("good3")

        conn.execute("""
            UPDATE records
            SET weather = ?, score = ?, good1 = ?, good2 = ?, good3 = ?
            WHERE id = ? AND user_id = ?
        """, (
            weather, score, good1, good2, good3,
            record_id, session["user_id"]
        ))
        conn.commit()
        conn.close()

        return redirect("/history")

    conn.close()
    return render_template("record.html", record=record, edit=True)
@app.route("/delete/<int:record_id>", methods=["POST"])
def delete(record_id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    conn.execute("""
        DELETE FROM records
        WHERE id = ? AND user_id = ?
    """, (record_id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/history")

# --------------------
# ログアウト
# --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# --------------------
# アプリ起動
# --------------------
if __name__ == "__main__":
    init_db()
    app.run()
