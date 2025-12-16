from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# --------------------
# DB接続
# --------------------
def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor,
        sslmode="require"
    )

# --------------------
# 初期テーブル作成（最初の1回だけ呼ばれる）
# --------------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        nickname TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    """)

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
# 初回アクセス時にDB初期化
# --------------------
@app.before_request
def before_request():
    if not getattr(app, "_db_initialized", False):
        init_db()
        app._db_initialized = True

# --------------------
# ルーティング
# --------------------
@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nickname = request.form.get("nickname")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE nickname=%s", (nickname,))
        user = cur.fetchone()

        if not user:
            cur.execute(
                "INSERT INTO users (nickname, password) VALUES (%s, %s)",
                (nickname, password)
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE nickname=%s", (nickname,))
            user = cur.fetchone()

        session["user_id"] = user["id"]

        cur.close()
        conn.close()
        return redirect("/record")

    return render_template("login.html")

@app.route("/record", methods=["GET", "POST"])
def record():
    if "user_id" not in session:
        return redirect("/login")

    today = datetime.now()
    date = today.strftime("%Y-%m-%d")
    weekday = today.strftime("%A")

    if request.method == "POST":
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO records
            (user_id, date, weekday, weather, score, good1, good2, good3)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session["user_id"],
            date,
            weekday,
            request.form.get("weather"),
            request.form.get("score"),
            request.form.get("good1"),
            request.form.get("good2"),
            request.form.get("good3"),
        ))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/record")

    return render_template("record.html", date=date, weekday=weekday)

@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM records WHERE user_id=%s ORDER BY date DESC",
        (session["user_id"],)
    )
    records = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("history.html", records=records)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
