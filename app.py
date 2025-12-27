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
# 初期テーブル作成（手動実行推奨）
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
        return redirect("/record")

    return render_template("login.html")

# --------------------
# 記録画面
# --------------------
@app.route("/record", methods=["GET", "POST"])
def record():
    if "user_id" not in session:
        return redirect("/login")

    # POST（保存・更新）
    if request.method == "POST":
        record_date = request.form.get("record_date")
        weekday = datetime.strptime(record_date, "%Y-%m-%d").strftime("%A")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM records WHERE user_id=%s AND date=%s
        """, (session["user_id"], record_date))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE records
                SET weather=%s, score=%s, good1=%s, good2=%s, good3=%s
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
            cur.execute("""
                INSERT INTO records
                (user_id, date, weekday, weather, score, good1, good2, good3)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
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
        return redirect(f"/record?date={record_date}")

    # GET（表示）
    record_date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.strptime(record_date, "%Y-%m-%d").strftime("%A")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM records WHERE user_id=%s AND date=%s
    """, (session["user_id"], record_date))
    record = cur.fetchone()
    cur.close()
    conn.close()

    edit = record is not None

    return render_template(
        "record.html",
        record=record,
        date=record_date,
        weekday=weekday,
        edit=edit
    )

# --------------------
# 編集画面（historyカードから）
# --------------------
@app.route("/edit/<int:record_id>", methods=["GET", "POST"])
def edit(record_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM records WHERE id=%s AND user_id=%s", (record_id, session["user_id"]))
    record = cur.fetchone()

    if not record:
        cur.close()
        conn.close()
        return "Not Found", 404

    if request.method == "POST":
        record_date = request.form.get("record_date")
        cur.execute("""
            UPDATE records
            SET weather=%s, score=%s, good1=%s, good2=%s, good3=%s
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
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/history")

    cur.close()
    conn.close()
    return render_template("record.html", edit=True, record=record)

# --------------------
# 履歴
# --------------------
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM records WHERE user_id=%s ORDER BY date DESC", (session["user_id"],))
    records = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("history.html", records=records)

# --------------------
# カレンダー
# --------------------
@app.route("/calendar")
def calendar_view():
    if "user_id" not in session:
        return redirect("/login")

    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    cal = calendar.Calendar(firstweekday=6)
    month_days = list(cal.itermonthdates(year, month))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT date, score FROM records WHERE user_id=%s", (session["user_id"],))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    score_map = {r["date"]: 1 if r["score"] and r["score"] >= 5 else 0 for r in rows}

    days = []
    for d in month_days:
        days.append({
            "day": d.day,
            "date":d.strftime("%Y-%m-%d")
            "in_month": d.month == month,
            "score": score_map.get(d)
        })

    prev_month = month - 1 or 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        days=days,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month
    )

# --------------------
# ログアウト
# --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    # デバッグ起動用のみ
    app.run(debug=True)
