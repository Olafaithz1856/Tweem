from flask import Flask, flash, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
import os
from flask import jsonify
import time
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

import smtplib
from email.mime.text import MIMEText

def send_email(subject, body, to_email):
    sender_email = "oladipupoaustin1856@gmail.com"
    app_password = "ojcgljcifbkjwivz"   # no spaces

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print("✅ Email sent successfully!")

    except Exception as e:
        print("❌ Email error:", e)

# Load environment variables
load_dotenv()

# Initialize app
app = Flask(__name__)
app.secret_key = "tweem_secret_key"

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
app.secret_key = "tweem_secret_key"

def init_db():
    conn = sqlite3.connect("database.db", timeout=10)
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    """)

    # FEEDBACK TABLE --------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS testimonies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

#-------- Prayer request table-----------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prayer_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        request TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # CHAT TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # SAVED SCRIPTURES TABLE (if you still want it)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_scriptures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse TEXT
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_verses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        verse TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db()



# ---------- LOGIN PAGE ----------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:

            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["role"] = user[4]
            session["is_verified"] = 0
            
            flash("Login successful! Welcome back 🙌")

            if user[4] == "admin":
                return redirect(url_for("admin_dashboard"))

            elif user[4] == "user":
                return redirect(url_for("dashboard"))

            else:
                return "Invalid login details"

    return render_template("index.html")

#------ Send user to all templates-------
@app.context_processor
def inject_user():
    if "user_id" in session:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
        user = cursor.fetchone()

        conn.close()

        return dict(user=user)

    return dict(user=None)

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO users (name, email, password, profile_pic)
            VALUES (?, ?, ?, ?)
            """, (name, email, password, "default-avatar.png"))

            conn.commit()

        except sqlite3.IntegrityError:
            return "Email already exists"

        finally:
            conn.close()   

        conn.close()
        return redirect(url_for("home"))

    return render_template("register.html")
import uuid
from werkzeug.security import generate_password_hash

# ---------- FORGOT PASSWORD ----------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()

        if user:
            # Generate unique reset token
            reset_token = str(uuid.uuid4())
            cursor.execute("UPDATE users SET reset_token=? WHERE email=?", (reset_token, email))
            conn.commit()
            
            # Here you would send an email to the user with a reset link
            # e.g., link: http://yourdomain.com/reset_password/<reset_token>
            print(f"Reset link: http://localhost:5000/reset_password/{reset_token}")
            flash("Password reset link has been sent to your email (Check console for demo).")
        else:
            flash("Email not found.")

        conn.close()
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")

#----------Dashboard----------
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    import requests
    from datetime import date

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    user_id = session["user_id"]
    username = session["user_name"]
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    # Counselor replies (FIXED: use username correctly)
    cursor.execute("""
    SELECT message, created_at
    FROM counselor_chats
    WHERE username=? AND sender='admin'
    ORDER BY created_at DESC
    LIMIT 5
    """, (username,))
    chats = cursor.fetchall()

    cursor.execute("""
    SELECT message, created_at 
    FROM notifications 
    WHERE user_id=? 
    ORDER BY created_at DESC 
    LIMIT 5
    """, (user_id,))
    notifications = cursor.fetchall()

    # Testimonies
    cursor.execute("""
    SELECT title, message, created_at
    FROM testimonies
    WHERE user_id=?
    ORDER BY created_at DESC
    LIMIT 5
    """, (user_id,))
    testimonies = cursor.fetchall()

    # Notifications
    notifications = []
    for chat in chats:
        notifications.append("Counselor replied to your message")

    # ✅ Verse of the Day (FIXED INDENTATION)
    today = str(date.today())

    cursor.execute(
        "SELECT verse_text, verse_ref FROM daily_verse WHERE date=?",
        (today,)
    )
    saved_verse = cursor.fetchone()

    if saved_verse:
        verse_text = saved_verse["verse_text"]
        verse_ref = saved_verse["verse_ref"]

    else:
        try:
            response = requests.get("https://bible-api.com/?random=verse")
            data = response.json()

            verse_text = data["text"].strip()
            verse_ref = data["reference"]

            cursor.execute("""
            INSERT INTO daily_verse (verse_text, verse_ref, date)
            VALUES (?, ?, ?)
            """, (verse_text, verse_ref, today))

            conn.commit()

        except:
            verse_text = "The Lord is my shepherd; I shall not want."
            verse_ref = "Psalm 23:1"

    conn.close()

    # ✅ RETURN MUST BE OUTSIDE
    return render_template(
        "dashboard.html",
        chats=chats,
        testimonies=testimonies,
        verse_text=verse_text,
        verse_ref=verse_ref,
        user=user,
        notifications=notifications
    )


# ---------- TESTIMONY / FEEDBACK ----------
@app.route("/testimony", methods=["GET", "POST"])
def testimony():

    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    message = ""

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["message"]

        if not title or not content:
            message = "Please fill in all fields."
        else:
            cursor.execute("""
            INSERT INTO testimonies (user_id, title, message)
            VALUES (?, ?, ?)
            """, (session["user_id"], title, content))

            conn.commit()
            message = "Thank you for sharing your testimony!"

    cursor.execute("""
        SELECT testimonies.title, testimonies.message, users.name
        FROM testimonies
        JOIN users ON testimonies.user_id = users.id
        ORDER BY testimonies.id DESC
    """)

    testimonies = cursor.fetchall()
    conn.close()

    return render_template(
        "testimony.html",
        testimonies=testimonies,
        message=message
    )

# ---------- PRAYER REQUEST ----------
@app.route("/prayer", methods=["GET", "POST"])
def prayer():

    if "user_id" not in session:
        return redirect(url_for("home"))

    message = ""

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # USER SUBMITS PRAYER
    if request.method == "POST":

        prayer_text = request.form.get("prayer")

        if prayer_text:
            cursor.execute("""
            INSERT INTO prayer_requests (username, request)
            VALUES (?, ?)
            """, (session["user_name"], prayer_text))

            conn.commit()
            message = "Your prayer request has been submitted."

    # FETCH USER PRAYERS + RESPONSES
    cursor.execute("""
    SELECT * FROM prayer_requests
    WHERE username = ?
    ORDER BY id DESC
    """, (session["user_name"],))

    prayers = cursor.fetchall()

    conn.close()

    return render_template(
        "prayer.html",
        message=message,
        prayers=prayers
    )

# ---------- CHAT ----------
import time
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        user_message = request.form["message"].strip()

        # Save user message
        cursor.execute(
            "INSERT INTO chat_messages (user_id, role, message) VALUES (?, ?, ?)",
            (session["user_id"], "user", user_message)
        )
        conn.commit()

        # Temporary AI typing message
        ai_reply = "AI is thinking..."
        cursor.execute(
            "INSERT INTO chat_messages (user_id, role, message) VALUES (?, ?, ?)",
            (session["user_id"], "assistant", ai_reply)
        )
        conn.commit()

        # Build the system prompt for structured counseling
        system_prompt = """
        You are a compassionate Christian spiritual counselor. Always structure your reply in this style:
        1. Greet the user warmly.
        2. Comfort & encourage them based on their message.
        3. Share a relevant Bible verse.
        4. Give spiritual advice in plain, human-friendly language.
        5. Suggest a simple practical step they can take.
        6. Keep it readable, human, and empathetic. 
        7. Split naturally into paragraphs, no markdown symbols, no headers.
        """

        try:
            # Call Gemini API
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{system_prompt}\n\nUser: {user_message}"
            )

            ai_reply = response.text.strip()

        except Exception as e:
            print("Gemini AI Error:", e)
            ai_reply = "AI service temporarily unavailable. Please try again later."

        # Update AI response in the database (replace the temporary "thinking..." message)
        cursor.execute(
            "SELECT id FROM chat_messages WHERE user_id = ? AND role = ? ORDER BY id DESC LIMIT 1",
            (session["user_id"], "assistant")
        )
        last_ai = cursor.fetchone()
        if last_ai:
            cursor.execute(
                "UPDATE chat_messages SET message = ? WHERE id = ?",
                (ai_reply, last_ai["id"])
            )
            conn.commit()

    # Fetch all messages to display
    cursor.execute(
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id ASC",
        (session["user_id"],)
    )
    messages = cursor.fetchall()
    conn.close()

    return render_template("chat.html", messages=messages)

#--------- BIBBLE -------- 
#--------- BIBLE -------- 

import os
# Initialize Gemini client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.route("/bible", methods=["GET", "POST"])
def bible():
    verse = ""
    devotional = ""
    search_results = []

    # 🔹 DAILY DEVOTIONAL (USING GEMINI)
    try:
        # Use lighter model to avoid free-tier quota exhaustion
        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content(
            "Write a short Christian devotional with a Bible verse, message, and prayer. "
            "Make it simple, human-like, warm, and friendly. Do not use symbols like ** or ---."
        )

        # Safe extraction of text
        devotional = getattr(response, "text", "").strip()

        if not devotional:
            devotional = "Today's devotion is not available right now."

    except Exception as e:
        print("Devotional Error:", e)
        # ✅ FALLBACK DEVOTION
        devotional = """Today's Devotion

Bible Verse:
"The Lord is my shepherd; I shall not want." — Psalm 23:1

Message:
Even when life feels uncertain, God is guiding you every step of the way. 
You may not see the full path, but He sees the end from the beginning.

Prayer:
Lord, help me trust You even when I don't understand. Lead me and give me peace. Amen.
"""

    # 🔹 SCRIPTURE SEARCH
    if request.method == "POST":
        reference = request.form.get("reference")
        try:
            response = requests.get(f"https://bible-api.com/{reference}")
            data = response.json()
            search_results.append({
                "reference": data.get("reference"),
                "text": data.get("text")
            })
        except Exception as e:
            print("Search Error:", e)

    return render_template(
        "bible.html",
        verse=verse,
        devotional=devotional,
        search_results=search_results
    )
#------- Admin dashboad --------
@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Total Users
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    # Total Chats
    cursor.execute("SELECT COUNT(*) FROM counselor_chats")
    chats = cursor.fetchone()[0]

    # Prayer Requests
    cursor.execute("SELECT COUNT(*) FROM prayer_requests")
    prayers = cursor.fetchone()[0]

    # Testimonies
    cursor.execute("SELECT COUNT(*) FROM testimonies")
    testimonies = cursor.fetchone()[0]

    # Recent counselling chats
    cursor.execute("""
        SELECT username, message
        FROM counselor_chats
        ORDER BY id DESC
        LIMIT 5
    """)

    recent_chats = cursor.fetchall()
    cursor.execute("""
        SELECT username, request
        FROM prayer_requests
        ORDER BY id DESC
        LIMIT 5
        """)

    recent_prayers = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        users=users,
        chats=chats,
        prayers=prayers,
        testimonies=testimonies,
        recent_chats=recent_chats,
        recent_prayers=recent_prayers
    )
# ---------- ADMIN VIEW PRAYER ----------
@app.route("/admin/prayers", methods=["GET", "POST"])
def admin_prayers():

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":

        prayer_id = request.form["prayer_id"]
        response = request.form["response"]

        cursor.execute("""
        UPDATE prayer_requests
        SET response=?, status='answered'
        WHERE id=?
        """, (response, prayer_id))

        conn.commit()

    cursor.execute("SELECT * FROM prayer_requests ORDER BY id DESC")
    prayers = cursor.fetchall()

    conn.close()

    return render_template("admin_prayers.html", prayers=prayers)

@app.route("/admin/delete_prayer/<int:id>")
def delete_prayer(id):

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM prayer_requests WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/admin/prayers")

# ---------- User CHAT ----------
@app.route("/counselor_chat", methods=["GET", "POST"])
def counselor_chat():

    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":

        message = request.form["message"]

        cursor.execute("""
        INSERT INTO counselor_chats (username, sender, message)
        VALUES (?, ?, ?)
        """, (session["user_name"], "user", message))

        conn.commit()

    cursor.execute("""
    SELECT * FROM counselor_chats
    WHERE username=?
    ORDER BY id ASC
    """, (session["user_name"],))

    chats = cursor.fetchall()

    conn.close()

    return render_template("counselor_chat.html", chats=chats)

# ---------Typing indicator rout --------
@app.route("/typing", methods=["POST"])
def typing():

    username = request.form["username"]

    return {"status": "typing"}

#-------- Notification Badg root -------
@app.route("/new_messages/<username>")
def new_messages(username):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*) FROM counselor_chats
    WHERE username=? AND sender='user'
    """, (username,))

    count = cursor.fetchone()[0]

    conn.close()

    return {"count":count}

# ---------- ADMIN CHAT USERS ----------
@app.route("/admin/chats")
def admin_chats():

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT DISTINCT username
    FROM counselor_chats
    ORDER BY id DESC
    """)

    users = cursor.fetchall()

    conn.close()

    return render_template("admin_chats.html", users=users)

# ---------- ADMIN CHAT PANEL ----------
@app.route("/admin/chat/<username>", methods=["GET", "POST"])
def admin_chat(username):

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":

        message = request.form["message"]

        cursor.execute("""
        INSERT INTO counselor_chats (username, sender, message)
        VALUES (?, ?, ?)
        """, (username, "counsellor", message))

        conn.commit()

    cursor.execute("""
    SELECT * FROM counselor_chats
    WHERE username = ?
    ORDER BY id ASC
    """, (username,))

    chats = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_chat.html",
        chats=chats,
        username=username
    )
#------ Message reload root -------
@app.route("/get_messages/<username>")
def get_messages(username):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM counselor_chats
    WHERE username = ?
    ORDER BY id ASC
    """, (username,))

    chats = cursor.fetchall()

    conn.close()

    messages = []

    for chat in chats:
        messages.append({
            "sender": chat["sender"],
            "message": chat["message"]
        })

    return {"messages": messages}
#-------- Manage user-------
@app.route("/admin/users")
def admin_users():

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    users = cursor.fetchall()

    conn.close()

    return render_template("admin_users.html", users=users)

#-----Admin Delete user account----- 
@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/users")

#------- admin_testimonies--------
@app.route("/admin/testimonies")
def admin_testimonies():

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT testimonies.id, users.name, testimonies.message
        FROM testimonies
        JOIN users ON testimonies.user_id = users.id
        ORDER BY testimonies.id DESC
        """)

    testimonies = cursor.fetchall()

    conn.close()

    return render_template("admin_testimonies.html", testimonies=testimonies)

#------- Admin delete test----------
@app.route("/admin/delete_testimony/<int:testimony_id>")
def delete_testimony(testimony_id):

    if session.get("role") != "admin":
        return "Access denied"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM testimonies WHERE id=?", (testimony_id,))

    conn.commit()
    conn.close()

    return redirect("/admin/testimonies")

#--------- User Profile root---------
@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, email, profile_pic
    FROM users
    WHERE id=?
    """, (session["user_id"],))

    user = cursor.fetchone()
    conn.close()

    return render_template("profile.html", user=user)

@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
    user = cursor.fetchone()

    conn.close()

    return render_template("account.html", user=user)

#-------Edit profile roots------
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form["name"]
    user_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET name=? WHERE id=?", (name, user_id))
    conn.commit()
    conn.close()

    session["user_name"] = name  # update session

    return redirect(url_for("profile"))

#--------Edit profile picture --------
import os
from werkzeug.utils import secure_filename

@app.route("/upload_pic", methods=["POST"])
def upload_pic():
    if "user_id" not in session:
        return redirect(url_for("login"))

    file = request.files["profile_pic"]
    filename = secure_filename(file.filename)

    filepath = os.path.join("static/uploads", filename)
    file.save(filepath)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET profile_pic=? WHERE id=?", (filename, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect(url_for("profile"))

#------- Edit email root ----------
@app.route("/update_email", methods=["POST"])
def update_email():
    if "user_id" not in session:
        return redirect(url_for("login"))

    email = request.form["email"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE users SET email=? WHERE id=?", (email, session["user_id"]))
        conn.commit()
    except:
        return "Email already exists"

    conn.close()
    return redirect(url_for("account"))

#-------- change password-------
@app.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))

    current = request.form["current_password"]
    new = request.form["new_password"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM users WHERE id=?", (session["user_id"],))
    user = cursor.fetchone()

    if user[0] != current:
        return "Incorrect current password"

    cursor.execute("UPDATE users SET password=? WHERE id=?", (new, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect(url_for("account"))

#-------- Delete account-------
@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    password = request.form["password"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM users WHERE id=?", (session["user_id"],))
    user = cursor.fetchone()

    if user[0] != password:
        return "Incorrect password. Cannot delete account."

    cursor.execute("DELETE FROM users WHERE id=?", (session["user_id"],))
    conn.commit()
    conn.close()

    session.clear()
    return redirect(url_for("home"))

#------Verify Email-------
@app.route("/verify_email")
def verify_email():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET is_verified=1 WHERE id=?", (session["user_id"],))
    conn.commit()
    conn.close()

    session["is_verified"] = 1

    return redirect(url_for("dashboard"))

#-------- Admin ban user--------
@app.route("/admin/ban_user/<int:user_id>")
def ban_user(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET status='banned' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_users"))

#------Admin Urban----------
@app.route("/admin/unban_user/<int:user_id>")
def unban_user(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_users"))

#-------- Admin warn user-----
@app.route("/admin/warn_user/<int:user_id>")
def warn_user(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET warning='Please follow community rules' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_users"))

#-------admin send notice---------
@app.route("/admin/send_notice", methods=["POST"])
def send_notice():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    message = request.form["message"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Send to ALL users
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()

    for user in users:
        cursor.execute(
            "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
            (user[0], message)
        )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

#-------About ------
@app.route("/about")
def about():
    return render_template("about.html")

#------ contact -------
@app.route("/contact", methods=["GET", "POST"])
def contact():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        cursor.execute("""
        INSERT INTO contact_messages (name, email, message, user_id)
        VALUES (?, ?, ?, ?)
        """, (name, email, message, user_id))

        conn.commit()
        flash("Message sent successfully!")

        # ✅ EMAIL MUST BE INSIDE THIS BLOCK
        try:
            send_email(
                subject="New Contact Message - TWEEM",
                body=f"""
New message received:

Name: {name}
Email: {email}

Message:
{message}
""",
                to_email="oladipupoaustin1856@gmail.com"
            )

            print("✅ Email sent!")

        except Exception as e:
            print("❌ Email error:", e)

    # FETCH USER MESSAGES
    cursor.execute("""
    SELECT * FROM contact_messages
    WHERE user_id=?
    ORDER BY created_at DESC
    """, (user_id,))

    messages = cursor.fetchall()

    conn.close()

    return render_template("contact.html", messages=messages)

#--------Admin contact dbard-------
@app.route("/admin/contacts")
def admin_contacts():

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM contact_messages
    ORDER BY created_at DESC
    """)
    messages = cursor.fetchall()

    conn.close()

    return render_template("admin_contacts.html", messages=messages)

#---------Admin reply_contact----------
@app.route("/admin/reply_contact/<int:id>", methods=["POST"])
def reply_contact(id):

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    reply = request.form["reply"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 📩 GET USER EMAIL
    cursor.execute("SELECT email FROM contact_messages WHERE id=?", (id,))
    user = cursor.fetchone()

    if user:
        user_email = user[0]

        # ✅ SEND EMAIL USING smtplib FUNCTION
        try:
            send_email(
                subject="Reply from TWEEM Support",
                body=f"""
Hello,

You have received a reply from TWEEM Support:

{reply}

Thank you for reaching out to us.
""",
                to_email=user_email
            )

            print("✅ Reply email sent!")

        except Exception as e:
            print("❌ Email error:", e)

    # ✅ SAVE REPLY IN DATABASE
    cursor.execute("""
    UPDATE contact_messages
    SET reply = ?
    WHERE id = ?
    """, (reply, id))

    conn.commit()
    conn.close()

    flash("Reply sent successfully!")

    return redirect(url_for("admin_contacts"))

#------- Admin delete contact message-------
@app.route("/admin/delete_contact/<int:id>")
def delete_contact(id):

    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM contact_messages WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Message deleted successfully!")

    return redirect(url_for("admin_contacts"))
# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    conn.commit()
    print("Role column added successfully")
except:
    print("Role column already exists")

conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("UPDATE users SET role='admin' WHERE email='oladipupoaustin1856@gmail.com'")
conn.commit()
conn.close()
conn.close()

if __name__ == "__main__":
    app.run(debug=True)

