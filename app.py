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

    # Verse of the Day (FIXED INDENTATION)
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
from google import genai
import os
import time

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------- RULE-BASED ----------
def rule_based_response(user_message, history=""):
    msg = user_message.lower()

    # 🔹 greetings
    if any(word in msg for word in ["hi", "hello", "hey"]):
        return """Hello 🤍

I'm really glad you reached out today.
How are you feeling right now?"""

    if any(greet in msg for greet in ["good morning", "good afternoon", "good evening"]):
        return """Hello 🤍

I'm really glad you came here.

You can talk to me about anything at all—how are you feeling today?"""

    # 🔹 happy
    if any(word in msg for word in ["happy", "joy", "excited", "grateful"]):
        return """That’s beautiful to hear 🤍

“This is the day the Lord has made; let us rejoice and be glad in it.” — Psalm 118:24

What’s been bringing you joy lately?"""

    # 🔹 sadness
    if any(word in msg for word in ["sad", "down", "unhappy"]):
        return """I’m really sorry you're feeling this way 🤍

“The Lord is close to the brokenhearted.” — Psalm 34:18

Do you want to share what’s been weighing on your heart?"""

    # 🔹 deep emotional
    if any(word in msg for word in ["depressed", "hopeless", "tired"]):
        return """I'm really sorry you're going through this 🤍

“Cast all your anxiety on Him because He cares for you.” — 1 Peter 5:7

You don’t have to carry this alone. I'm here with you."""

    # 🔹 prayer
    if "pray" in msg:
        return """Let’s pray together 🤍

Heavenly Father, please bring peace, strength, and comfort right now.
Remind them they are not alone. Amen."""

    # 🔹 memory awareness
    if "job" in msg and "sad" in history.lower():
        return """Losing something important like a job can really affect your heart 🤍

But please remember, your worth is not defined by your situation.

God still has a plan for you."""

    return None
    
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

        # Insert temporary message
        cursor.execute(
            "INSERT INTO chat_messages (user_id, role, message) VALUES (?, ?, ?)",
            (session["user_id"], "assistant", "Typing...")
        )
        conn.commit()

        # ---------- STEP 1: RULE-BASED ----------
        ai_reply = rule_based_response(user_message)

        # ---------- STEP 2: GEMINI (ONLY IF NEEDED) ----------
        if not ai_reply:
            try:
                time.sleep(1)  # avoid rate limit

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"""
You are a compassionate Christian spiritual counselor.
User: {user_message} 
Your role is to: 
- Comfort users emotionally
- Provide spiritual guidance based on biblical principles 
- Respond naturally to ANY user input Rules: 
1. Be warm and kind 
2. Understand user deeply 
3. Comfort emotional users first 
4. Include a Bible verse when appropriate 
5. Give simple spiritual advice 
6. Ask gentle follow-up questions 
7. Never judge 
8. Suggest a human counselor if needed 
Style: 
- Natural conversation 
- Short paragraphs 
- Friendly tone
"""
                )

                if response and response.text:
                    ai_reply = response.text.strip()
                else:
                    ai_reply = "I'm here with you 🤍 Tell me more."

            except Exception as e:
                print("Gemini Error:", e)

                # ---------- STEP 3: FALLBACK ----------
                ai_reply = """I'm here with you 🤍

I'm having a small delay connecting right now, but I still care about what you're going through.

Tell me more — I'm listening."""

        # ---------- UPDATE MESSAGE ----------
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

    # Fetch messages
    cursor.execute(
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id ASC",
        (session["user_id"],)
    )
    messages = cursor.fetchall()
    conn.close()

    return render_template("chat.html", messages=messages)

#--------- BIBLE -------- 

import datetime
from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ================= DEVOTIONAL LIST =================
DEVOTIONALS = [
{"title":"Trusting God","verse":"Proverbs 3:5-6","text":"Trust in the Lord with all your heart.","message":"Even when life feels confusing, God knows the way.","prayer":"Lord, help me trust You more each day. Amen."},

{"title":"God’s Strength","verse":"Isaiah 40:31","text":"Those who hope in the Lord will renew their strength.","message":"God gives strength when you feel weak.","prayer":"Father, renew my strength today. Amen."},

{"title":"Peace in Christ","verse":"John 14:27","text":"Peace I leave with you; my peace I give you.","message":"God’s peace is greater than any worry.","prayer":"Lord, fill me with Your peace. Amen."},

{"title":"You Are Loved","verse":"Jeremiah 31:3","text":"I have loved you with an everlasting love.","message":"God loves you deeply, always.","prayer":"Thank You Lord for loving me. Amen."},

{"title":"Do Not Fear","verse":"Isaiah 41:10","text":"Do not fear, for I am with you.","message":"God is always with you, even in fear.","prayer":"Lord, remove my fear and give me courage. Amen."},

{"title":"God Provides","verse":"Philippians 4:19","text":"God will meet all your needs.","message":"God knows what you need and will provide.","prayer":"Father, I trust Your provision. Amen."},

{"title":"New Beginning","verse":"2 Corinthians 5:17","text":"Anyone in Christ is a new creation.","message":"Every day is a fresh start with God.","prayer":"Lord, help me walk in newness today. Amen."},

{"title":"Stay Strong","verse":"Joshua 1:9","text":"Be strong and courageous.","message":"God is with you wherever you go.","prayer":"Give me strength, Lord. Amen."},

{"title":"God Cares","verse":"1 Peter 5:7","text":"Cast all your anxiety on Him.","message":"You don’t have to carry your burdens alone.","prayer":"Lord, I give You my worries. Amen."},

{"title":"Joy in the Lord","verse":"Psalm 118:24","text":"This is the day the Lord has made.","message":"Choose joy today.","prayer":"Help me rejoice today, Lord. Amen."},

{"title":"God is Near","verse":"Psalm 34:18","text":"The Lord is close to the brokenhearted.","message":"God is closest when you feel broken.","prayer":"Stay near me Lord. Amen."},

{"title":"Faith Over Fear","verse":"2 Timothy 1:7","text":"God gave us a spirit not of fear.","message":"Walk in faith, not fear.","prayer":"Strengthen my faith, Lord. Amen."},

{"title":"God is Light","verse":"1 John 1:5","text":"God is light; in Him is no darkness.","message":"God brings clarity into confusion.","prayer":"Shine Your light in my life, Lord. Amen."},

{"title":"Be Patient","verse":"Romans 12:12","text":"Be patient in affliction.","message":"God is working even when you wait.","prayer":"Teach me patience, Lord. Amen."},

{"title":"God is Faithful","verse":"Lamentations 3:23","text":"His mercies are new every morning.","message":"God is faithful every single day.","prayer":"Thank You for Your faithfulness. Amen."},

{"title":"Walk in Love","verse":"Ephesians 5:2","text":"Walk in the way of love.","message":"Let love guide your actions today.","prayer":"Help me show love, Lord. Amen."},

{"title":"God is My Refuge","verse":"Psalm 46:1","text":"God is our refuge and strength.","message":"Run to God when life feels heavy.","prayer":"Be my refuge, Lord. Amen."},

{"title":"Hope in God","verse":"Romans 15:13","text":"May God fill you with hope.","message":"Hope is found in God alone.","prayer":"Fill me with hope today. Amen."},

{"title":"Stay Humble","verse":"James 4:10","text":"Humble yourselves before the Lord.","message":"God lifts those who stay humble.","prayer":"Keep me humble, Lord. Amen."},

{"title":"God Guides","verse":"Psalm 32:8","text":"I will instruct you and teach you.","message":"God will guide your steps.","prayer":"Lead me, Lord. Amen."},

{"title":"Be Thankful","verse":"1 Thessalonians 5:18","text":"Give thanks in all circumstances.","message":"Gratitude changes everything.","prayer":"Help me stay thankful. Amen."},

{"title":"God is Good","verse":"Psalm 100:5","text":"The Lord is good.","message":"God’s goodness never fails.","prayer":"Thank You for Your goodness. Amen."},

{"title":"Seek God First","verse":"Matthew 6:33","text":"Seek first His kingdom.","message":"Put God first in everything.","prayer":"Help me seek You first. Amen."},

{"title":"God Gives Wisdom","verse":"James 1:5","text":"Ask God for wisdom.","message":"God gives wisdom freely.","prayer":"Give me wisdom, Lord. Amen."},

{"title":"Rest in God","verse":"Matthew 11:28","text":"Come to me, all who are weary.","message":"Find rest in God’s presence.","prayer":"Give me rest, Lord. Amen."}
]
def get_daily_devotional():
    today = datetime.date.today()
    index = today.toordinal() % len(DEVOTIONALS)
    return DEVOTIONALS[index]

@app.route("/bible", methods=["GET", "POST"])
def bible():
    verse = ""
    search_results = []

    # 🔥 LOCAL DEVOTIONAL (ALWAYS WORKS)
    daily = get_daily_devotional()

    devotional = f"""
Today's Devotion

Title: {daily['title']}

Bible Verse:
"{daily['text']}" — {daily['verse']}

Message:
{daily['message']}

Prayer:
{daily['prayer']}
"""

    # 🔹 OPTIONAL GEMINI (UPGRADE ONLY)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Write a short Christian devotional with verse, message, and prayer."
        )

        if response and response.text:
            devotional = response.text.strip()

    except Exception as e:
        print("Gemini Devotional Error:", e)
       
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

@app.route("/save_verse", methods=["POST"])
def save_verse():
    verse = request.form.get("verse")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO saved_scriptures (verse) VALUES (?)", (verse,))
    conn.commit()
    conn.close()

    return redirect(url_for("saved_scriptures"))

@app.route("/saved_scriptures")
def saved_scriptures():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT verse FROM saved_scriptures")
    verses = cursor.fetchall()

    conn.close()

    return render_template("saved_scriptures.html", verses=verses)

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

#---------- help routes ---------
@app.route("/help")
def help():
    return render_template("help.html")

# ----- invite friends --------- 
@app.route("/invite")
def invite():
    return render_template("invite.html")

#--------- pricacy routes--------
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

# ---------- ADMI VIEW PRAYER ----------
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

        #  EMAIL MUST BE INSIDE THIS BLOCK
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

    #  GET USER EMAIL
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
