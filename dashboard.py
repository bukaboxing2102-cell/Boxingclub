from flask import Flask, render_template
import sqlite3
import os

app = Flask(__name__)
DB = "club.db"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

@app.route("/")
def home():
    conn = db()

    total = conn.execute(
        "SELECT COUNT(*) c FROM users"
    ).fetchone()["c"]

    paid = conn.execute(
        "SELECT COUNT(*) c FROM users WHERE payment=1"
    ).fetchone()["c"]

    rows = conn.execute("""
    SELECT name, phone, payment, attendance, missed
    FROM users
    """).fetchall()

    names = [r["name"] for r in rows]
    attendance = [r["attendance"] for r in rows]

    conn.close()

    return render_template(
        "dashboard.html",
        total=total,
        paid=paid,
        unpaid=total-paid,
        rows=rows,
        names=names,
        attendance=attendance
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)