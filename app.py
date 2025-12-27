from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
import calendar
from datetime import date, datetime
from psycopg2.extras import RealDictCursor

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
        sslmode="require",
        connect_timeout=5
    )

# --------------------
# 初期テーブル作成
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
        UNIQUE (user_id, date),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

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
        return redirect("/calendar")

    return render_template("login.html")

# --------------------
# 記録画面（新規・編集共通）
# --------------------
@app.route("/record", methods=["GET", "POST"])
def record():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        record_date = request.form.get("record_date")
        weekday = datetime.strptime(record_date, "%Y-%m-%d").strftime("%A")

        conn = get_db_connection()
        cur = conn.cursor()

        # 既存チェック
        cur.execute("""
            SELECT id FROM records
            WHERE user_id=%s AND date=%s
        """, (session["user_id"], record_date))
        existing = cur.fetchone()

        if existing:
            # 更新
            cur.execute("""
                UPDATE records
                SET weather=%s,
                    score=%s,
                    good1=%s,
                    good2=%s,
                    good3=%s
                WHERE user_id=%s AND date=%s
            """, (
                request.form.get("weather"),
                request.form.get("score"),
                request.form.get("good1"),
                request.form.get("good2"),
                request.form.get("good3"),
                session["user_id"],
                record_date
            ))
        else:
            # 新規
            cur.execute("""
                INSERT INTO records
                (user_id, date, weekday, weather, score, good1, good2, good3)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session["user_id"],
                record_date,
                weekday,
                request.form.get("weather"),
                request.form.get("score"),
                request.form.get("good1"),
                request.form.get("good2"),
                request.form.get("good3")
            ))

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/calendar")

    # -------- GET --------
    record_date = request.args.get("date") or date.today().strftime("%Y-%m-%d")
    weekday = datetime.strptime(record_date, "%Y-%m-%d").strftime("%A")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM records
        WHERE user_id=%s AND date=%s
    """, (session["user_id"], record_date))
    record = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "record.html",
        record=record,
        date=record_date,
        weekday=weekday,
        edit=record is not None
    )

# --------------------
# カレンダー
# --------------------
@app.route("/calendar")
def calendar_view():
    if "user_id" not in session:
        return redirect("/login")

    today = date.today()
    year = today.year
    month = today.month

    cal = calendar.Calendar(firstweekday=6)
    month_days = list(cal.itermonthdates(year, month))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT date, score FROM records WHERE user_id=%s",
        (session["user_id"],)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    score_map = {}
    for r in rows:
        binary = 1 if r["score"] is not None and r["score"] >= 5 else 0
        score_map[r["date"]] = binary

    days = []
    for d in month_days:
        days.append({
            "day": d.day,
            "date": d.strftime("%Y-%m-%d"),  # ← これを追加
            "in_month": d.month == month,
            "score": score_map.get(d)
        })

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        days=days
    )

# --------------------
# ログアウト
# --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
