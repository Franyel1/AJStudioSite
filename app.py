#!/usr/bin/env python3

import os
import flask_login
import pymongo
from bson.objectid import ObjectId
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv, dotenv_values
from flask_login import login_required, current_user
import smtplib
from email.message import EmailMessage
import datetime;

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
config = dotenv_values()
app.config.from_mapping(config)

# Initialize MongoDB
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DBNAME")]

# # Flask-Login setup
# login_manager = flask_login.LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = "login"


# class User(flask_login.UserMixin):
#     def __init__(self, user_data):
#         self.id = str(user_data["_id"])
#         self.email = user_data["email"]
#         self.username = user_data["username"]
#         self.password = user_data["password"]
#         self.role = user_data.get("role", "user")

#     @property
#     def is_admin(self):
#         return self.role == "admin"

#     @staticmethod
#     def find_by_email(email):
#         user_data = db.loginInfo.find_one({"email": email})
#         return User(user_data) if user_data else None

#     @staticmethod
#     def find_by_id(user_id):
#         user_data = db.loginInfo.find_one({"_id": ObjectId(user_id)})
#         return User(user_data) if user_data else None

#     @staticmethod
#     def create_user(email, username, password):
#         if db.loginInfo.find_one({"email": email}):
#             return False
#         hashed_password = generate_password_hash(password)
#         db.loginInfo.insert_one({
#             "email": email,
#             "username": username,
#             "password": hashed_password,
#             "role": "user"
#         })
#         return True

# @login_manager.user_loader
# def load_user(user_id):
#     return User.find_by_id(user_id)


@app.route("/")
def home():
    return render_template("home.html")

# @app.route('/book')
# def book():
#     return render_template('book.html')

@app.route('/services')
def services():
    return render_template('services.html')

# @app.route('/shop')
# def shop():
#     return render_template('shop.html')

@app.route('/studio')
def studio():
    return render_template('studio.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', 'No Name Provided')
        email = request.form.get('email', 'No Email Provided')
        subject = request.form.get('subject', 'No Subject Provided')
        message = request.form.get('message', '')

        full_msg = "\n".join([
            "✨ New message from the Antonio Jefferson Studio contact form ✨",
            "",
            f"👤 Name: {name}",
            f"📧 Email: {email}",
            f"📌 Subject: {subject}",
            "",
            "💬 Message:",
            message,
            "",
            "-" * 60,
            "This message was sent via the contact form on your website."
        ])

        msg = EmailMessage()
        msg.set_content(full_msg)
        msg['Subject'] = f'Contact Form: {subject}'
        msg['From'] = os.environ['EMAIL_USER']
        msg['To'] = os.environ['EMAIL_RECEIVER']
        msg['Reply-To'] = email  # So you can reply to the sender

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(os.environ['EMAIL_USER'], os.environ['EMAIL_PASS'])
                smtp.send_message(msg)
            flash("Message sent successfully!", "success")
        except Exception as e:
            print(f"Email sending failed: {e}")
            flash("Something went wrong. Please try again later.", "danger")

        return redirect('/contact')

    return render_template('contact.html')


if __name__ == "__main__":
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=FLASK_PORT)
