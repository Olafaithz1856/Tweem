from flask import Flask, flash, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message

app = Flask(__name__)

# Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'oladipupoaustin1856@gmail.com'
app.config['MAIL_PASSWORD'] = 'ojcg ljci fbkj wivz'

mail = Mail(app)

@app.route("/test-email")
def test_email():
    msg = Message(
        "Test Email",
        sender=app.config['Admin'],
        recipients=["oladipupoaustin1856@gmail.com"]
    )
    msg.body = "Email is working!"
    mail.send(msg)

    return "Email sent!"