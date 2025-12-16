from flask import Flask, render_template, request, redirect, session
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev-secret-key"

# --------------------
# DB接続
# --------------------
def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    return psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor
    )

# --------------------
# 初期テーブル作成
# --------------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # users テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        nickname TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    """)

    # records テーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        date DATE NOT NULL,
        weekday TEXT NOT NULL,
        weather TEXT,
        score INTEGER,
        good1 TEXT,
        good2 TEXT,
        good3 TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

# --------------------
# ログイン
# --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nickname = request.form.get("nickname")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE nickname = %s",
            (nickname,)
        )
        user = cur.fetchone()

        if user is None:
            cur.execute(
                "INSERT INTO users (nickname, password) VALUES (%s, %s)",
                (nickname, password)
            )
            conn.commit()
            cur.execute(
                "SELECT * FROM users WHERE nickname = %s",
                (nickname,)
            )
            user = cur.fetchone()

        cur.close()
        conn.close()

        session["user_id"] = user["id"]
        return redirect("/record")

    return render_template("login.html")

@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/record")
    return redirect("/login")

# --------------------
# 記録入力
# --------------------
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
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO records
            (user_id, date, weekday, weather, score, good1, good2, good3)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
        cur.close()
        conn.close()

        return redirect("/record")

    return render_template("record.html", date=date, weekday=weekday)

# --------------------
# 履歴一覧
# --------------------
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM records
        WHERE user_id = %s
        ORDER BY date DESC
    """, (session["user_id"],))

    records = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("history.html", records=records)

# --------------------
# 編集
# --------------------
@app.route("/edit/<int:record_id>", methods=["GET", "POST"])
def edit(record_id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM records
        WHERE id = %s AND user_id = %s
    """, (record_id, session["user_id"]))

    record = cur.fetchone()

    if record is None:
        cur.close()
        conn.close()
        return redirect("/history")

    if request.method == "POST":
        weather = request.form.get("weather")
        score = request.form.get("score")
        good1 = request.form.get("good1")
        good2 = request.form.get("good2")
        good3 = request.form.get("good3")

        cur.execute("""
            UPDATE records
            SET weather=%s, score=%s, good1=%s, good2=%s, good3=%s
            WHERE id=%s AND user_id=%s
        """, (
            weather, score, good1, good2, good3,
            record_id, session["user_id"]
        ))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/history")

    cur.close()
    conn.close()
    return render_template("record.html", record=record, edit=True)

# --------------------
# 削除
# --------------------
@app.route("/delete/<int:record_id>", methods=["POST"])
def delete(record_id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM records
        WHERE id = %s AND user_id = %s
    """, (record_id, session["user_id"]))

    conn.commit()
    cur.close()
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
# 起動
# --------------------
if __name__ == "__main__":
    init_db()
    app.run()