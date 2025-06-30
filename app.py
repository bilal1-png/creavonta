import os
import csv
import json
import re
import smtplib
import markdown
import yaml
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from dotenv import load_dotenv

load_dotenv()  # Load email credentials from .env

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ---------- EMAIL CONFIG ----------
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
RECEIVER_EMAIL = EMAIL_USER  # or set another email
# ----------------------------------

# ---------- TESTIMONIALS ----------
TESTIMONIALS_PATH = Path(__file__).with_name("testimonials.json")
with open(TESTIMONIALS_PATH, encoding="utf-8") as f:
    testimonials = json.load(f)
# ----------------------------------

# ---------- BLOG CONFIG ----------
BLOG_DIR = Path(__file__).with_name("blog_posts")
JSON_PATH = Path(__file__).with_name("blog.json")
MD_EXTS = ["fenced_code", "tables", "toc", "codehilite"]
# ----------------------------------

# ----------- ROUTES --------------

@app.route("/")
def home():
    return render_template("index.html", testimonials=testimonials)

@app.route("/contact", methods=["POST"])
def contact():
    data = {
        "first_name": request.form.get("firstName"),
        "last_name": request.form.get("lastName"),
        "email": request.form.get("email"),
        "project_type": request.form.get("projectType"),
        "message": request.form.get("message")
    }

    # Save to CSV
    file_exists = os.path.isfile("submissions.csv")
    with open("submissions.csv", mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

    # Send Email
    try:
        msg = EmailMessage()
        msg["Subject"] = "🚀 New Contact Form Submission"
        msg["From"] = EMAIL_USER
        msg["To"] = RECEIVER_EMAIL
        msg.set_content(f"""
Name: {data['first_name']} {data['last_name']}
Email: {data['email']}
Project Type: {data['project_type']}
Message: {data['message']}
        """)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print("Failed to send email:", e)

    return redirect(url_for("thank_you"))

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")

@app.route("/blog")
def blog_list():
    posts = get_all_posts()
    return render_template("blog_list.html", posts=posts)

@app.route("/blog/<slug>")
def blog_post(slug):
    posts = {p["slug"]: p for p in get_all_posts()}
    post = posts.get(slug)
    if not post:
        abort(404)
    return render_template("blog_post.html", post=post)

# ----------- BLOG UTILITIES ------------

def _parse_md(fp: Path):
    raw = fp.read_text(encoding="utf-8")
    fm, body = re.match(r"^---(.*?)---(.*)$", raw, re.S).groups()
    meta = yaml.safe_load(fm)
    html = markdown.markdown(body.strip(), extensions=MD_EXTS)
    return {
        "slug": fp.stem,
        "html": html,
        **meta,
        "date": datetime.fromisoformat(meta["date"])
    }

def _parse_json():
    if not JSON_PATH.exists():
        return []
    with open(JSON_PATH, encoding="utf-8") as f:
        items = json.load(f)
    for itm in items:
        itm["html"] = markdown.markdown(itm["content"], extensions=MD_EXTS)
        itm["date"] = datetime.fromisoformat(itm["date"])
    return items

def get_all_posts():
    md_posts = [_parse_md(p) for p in BLOG_DIR.glob("*.md")]
    json_posts = _parse_json()
    return sorted(md_posts + json_posts, key=lambda p: p["date"], reverse=True)

# ------------ RUN ------------
if __name__ == "__main__":
    app.run(debug=True)
