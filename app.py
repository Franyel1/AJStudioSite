#!/usr/bin/env python3

import os
import flask_login
import pymongo
import requests
from bson.objectid import ObjectId
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv, dotenv_values
from flask_login import login_required, current_user
import smtplib
from email.message import EmailMessage
import datetime;
import stripe
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import base64


load_dotenv()

# def write_google_credentials():
#     encoded = os.getenv("GOOGLE_CREDENTIALS_B64")
#     if not encoded:
#         raise RuntimeError("GOOGLE_CREDENTIALS_B64 not set")
    
#     decoded = base64.b64decode(encoded)
#     with open("google_credentials.json", "wb") as f:
#         f.write(decoded)
#     return "google_credentials.json"

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DOMAIN = os.getenv("DOMAIN")

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'google_credentials.json' #write_google_credentials()
CALENDAR_ID = 'primary'

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
config = dotenv_values()
app.config.from_mapping(config)

# Initialize MongoDB
# client = pymongo.MongoClient(os.getenv("MONGO_URI"))
# db = client[os.getenv("MONGO_DBNAME")]

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


# @app.route('/services')
# def services():
#     return render_template('services.html')

# @app.route('/shop')
# def shop():
#     return render_template('shop.html')

@app.route('/studio')
def studio():
    return render_template('studio.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Verify reCAPTCHA
        recaptcha_response = request.form.get('g-recaptcha-response')
        payload = {
            'secret': os.getenv('RECAPTCHA_SECRET_KEY'),
            'response': recaptcha_response
        }
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
        result = r.json()

        if not result.get('success'):
            flash("reCAPTCHA verification failed. Please try again.")
            return redirect('/contact')
        

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not email or not subject or not message:
            flash("All fields are required.")
            return redirect('/contact')
        
        if request.form.get('website'):
            # bot filled the hidden field
            return redirect('/contact')
        
        
        


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

    return render_template("contact.html", recaptcha_site_key=os.getenv("RECAPTCHA_SITE_KEY"))

@app.route('/book')
def book():
    return render_template('book.html')

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.form
    NY_TZ = ZoneInfo("America/New_York")

    # Extract form data
    date = data['date']
    tables = int(data.get('tables', 0))
    chairs = int(data.get('chairs', 0))
    name = data['name']
    email = data['email']
    phone = data['phone']

    start_time = data['start_time']
    end_time = data['end_time']

    start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=NY_TZ)
    end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=NY_TZ)

    duration = (end_dt - start_dt).total_seconds() / 3600
    if duration <= 0:
        flash("End time must be after start time.")
        return redirect('/book')

    # Compute start and end datetime
    start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=NY_TZ)
    end_dt = start_dt + timedelta(hours=duration)

    # Closing time check (8 AM – midnight)
    closing_dt = datetime.strptime(f"{date} 23:59", "%Y-%m-%d %H:%M").replace(tzinfo=NY_TZ) + timedelta(minutes=1)
    if end_dt > closing_dt:
        flash("Booking exceeds studio closing time (midnight). Please choose a shorter duration or earlier start.")
        return redirect('/book')

    # **Check availability via Free/Busy API**
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('calendar', 'v3', credentials=creds)

    freebusy_request = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "timeZone": "America/New_York",
        "items": [{"id": os.getenv("CALENDAR_ID")}]
    }
    response = service.freebusy().query(body=freebusy_request).execute()
    busy_slots = response["calendars"][os.getenv("CALENDAR_ID")]["busy"]

    NY_TZ = ZoneInfo("America/New_York")
    conflict_found = False

    for b in busy_slots:
        b_start = datetime.fromisoformat(b['start']).astimezone(NY_TZ)
        b_end = datetime.fromisoformat(b['end']).astimezone(NY_TZ)

        # Check for overlap but allow end-to-start bookings
        if start_dt < b_end and end_dt > b_start and not (end_dt == b_start or start_dt == b_end):
            conflict_found = True
            break

    if conflict_found:
        flash("This time is already booked. Please select another slot.")
        return redirect('/book')


    # Calculate price
    total_price = (39 * duration) + (tables * 5) + (chairs * 2)
    total_amount = int(total_price * 100)

    # Store booking details in session
    session['latest_booking'] = {
        'date': date,
        'start_time': start_time,
        'duration': duration,
        'name': name,
        'email': email,
        'phone': phone,
        'tables': tables,
        'chairs': chairs,
        'total': total_price
    }

    # Create Stripe session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'Studio Booking'},
                'unit_amount': total_amount,
            },
            'quantity': 1,
        }],
        mode='payment',
        customer_creation='always',
        payment_intent_data={
            'setup_future_usage': 'off_session'  # Save card for future
        },
        allow_promotion_codes=True,
        success_url=f"{DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{DOMAIN}/book",
        customer_email=email,
    )
    return redirect(checkout_session.url, code=303)




def get_freebusy_slots(date_str, duration):
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    NY_TZ = ZoneInfo("America/New_York")
    day_start = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=8, minute=0, tzinfo=NY_TZ)
    day_end = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=23, minute=59, tzinfo=NY_TZ)

    freebusy_request = {
        "timeMin": day_start.isoformat(),
        "timeMax": day_end.isoformat(),
        "timeZone": "America/New_York",
        "items": [{"id": os.getenv("CALENDAR_ID")}]
    }

    response = service.freebusy().query(body=freebusy_request).execute()
    busy_slots = response["calendars"][os.getenv("CALENDAR_ID")]["busy"]

    return busy_slots


@app.route('/available-times')
def available_times():
    date = request.args.get('date')
    if not date:
        return jsonify([])

    NY_TZ = ZoneInfo("America/New_York")
    opening_dt = datetime.strptime(f"{date} 08:00", "%Y-%m-%d %H:%M").replace(tzinfo=NY_TZ)
    closing_dt = datetime.strptime(f"{date} 23:59", "%Y-%m-%d %H:%M").replace(tzinfo=NY_TZ)

    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    freebusy_request = {
        "timeMin": opening_dt.isoformat(),
        "timeMax": (closing_dt + timedelta(minutes=1)).isoformat(),
        "timeZone": "America/New_York",
        "items": [{"id": os.getenv("CALENDAR_ID")}]
    }
    response = service.freebusy().query(body=freebusy_request).execute()
    busy_slots = response["calendars"][os.getenv("CALENDAR_ID")]["busy"]

    current = opening_dt
    free_slots = []

    while current <= closing_dt:
        conflict = False
        for b in busy_slots:
            b_start = datetime.fromisoformat(b['start']).astimezone(NY_TZ)
            b_end = datetime.fromisoformat(b['end']).astimezone(NY_TZ)

            # This slot is considered busy if it overlaps any busy event
            slot_end = current + timedelta(minutes=30)
            if current < b_end and slot_end > b_start:
                conflict = True
                break

        if not conflict:
            free_slots.append(current.strftime("%H:%M"))

        current += timedelta(minutes=30)

    return jsonify(free_slots)




@app.route('/success')
def success():
    booking = session.pop('latest_booking', None)
    if not booking:
        flash("Booking not found. Please try again.")
        return redirect('/book')

    # Ensure correct ISO format for date + time
    date_str = booking['date']  # e.g., "2025-07-26"
    time_str = booking['start_time']  # e.g., "12:30"

    try:
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError as e:
        print(f"Date parsing error: {e}, date={date_str}, time={time_str}")
        flash("Invalid date or time selected.")
        return redirect('/book')

    end_dt = start_dt + timedelta(hours=int(booking['duration']))

    # Add formatted times for display
    booking['pretty_date'] = start_dt.strftime("%B %d, %Y")   # e.g., "July 26, 2025"
    booking['start_time_display'] = start_dt.strftime("%I:%M %p")  # e.g., "12:30 PM"
    booking['end_time_display'] = end_dt.strftime("%I:%M %p")      # e.g., "02:30 PM"

    # Google Calendar
    create_event(start_dt.isoformat(), end_dt.isoformat(), booking['name'], booking['email'])

    # Email Confirmation
    send_confirmation_email(booking, start_dt.isoformat(), end_dt.isoformat())

    return render_template('success.html', booking=booking)



def send_confirmation_email(booking, start_time, end_time):
    email_user = os.getenv('EMAIL_USER')
    email_owner = os.getenv('EMAIL_RECEIVER')

    msg = EmailMessage()
    msg['Subject'] = "Your Studio Booking Confirmation"
    msg['From'] = email_user
    msg['To'] = booking['email']
    msg['Cc'] = email_owner  # Send a copy to studio owner

    # Build itemized bill
    tables_cost = booking['tables'] * 5
    chairs_cost = booking['chairs'] * 2
    base_cost = 39 * booking['duration']

    total_cost = base_cost + tables_cost + chairs_cost

    # Pretty HTML email
    msg.add_alternative(f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Hi {booking['name']},</h2>
        <p>Your studio booking with Antonio Jefferson Studio is confirmed! Here are the details:</p>
        
        <h3>Booking Summary</h3>
        <ul>
          <li><strong>Date:</strong> {booking['date']}</li>
          <li><strong>Time:</strong> {booking['start_time']} - {end_time[11:16]}</li>
          <li><strong>Duration:</strong> {booking['duration']} hour(s)</li>
        </ul>

        <h3>Itemized Bill</h3>
        <table style="border-collapse: collapse; width: 100%; max-width: 400px;">
          <tr>
            <td style="border-bottom: 1px solid #ddd; padding: 8px;">Studio ({booking['duration']}h x $39)</td>
            <td style="border-bottom: 1px solid #ddd; padding: 8px; text-align: right;">${base_cost}</td>
          </tr>
          {"<tr><td style='border-bottom: 1px solid #ddd; padding: 8px;'>Folding Tables (" + str(booking['tables']) + " x $5)</td><td style='border-bottom: 1px solid #ddd; padding: 8px; text-align: right;'>$" + str(tables_cost) + "</td></tr>" if booking['tables'] > 0 else ""}
          {"<tr><td style='border-bottom: 1px solid #ddd; padding: 8px;'>Folding Chairs (" + str(booking['chairs']) + " x $2)</td><td style='border-bottom: 1px solid #ddd; padding: 8px; text-align: right;'>$" + str(chairs_cost) + "</td></tr>" if booking['chairs'] > 0 else ""}
          <tr>
            <td style="border-top: 2px solid #000; padding: 8px;"><strong>Total</strong></td>
            <td style="border-top: 2px solid #000; padding: 8px; text-align: right;"><strong>${total_cost}</strong></td>
          </tr>
        </table>

        <p>For more details regarding our studio, visit our <a href="https://www.antoniojeffersonstudio.com/contact#faq" style="color: #3f51b5;">FAQ & Contact Page</a>.</p>

        <p style="margin-top:20px;">Thank you for booking with <strong>Antonio Jefferson Studio</strong>!<br>
        We look forward to seeing you.</p>
      </body>
    </html>
    """, subtype='html')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, os.getenv('EMAIL_PASS'))
        smtp.send_message(msg)



def create_event(start_time, end_time, name, email):
    """Create a booking event on Google Calendar."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': f'Studio Booking - {name}',
        'location': 'Antonio Jefferson Studio',
        'description': f'Booking confirmed for {name} ({email})',
        'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},
        'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                {'method': 'popup', 'minutes': 30}       # 30 minutes before
            ]
        },
    }
    created_event = service.events().insert(
        calendarId = os.getenv("CALENDAR_ID"),
        body=event
    ).execute()
    print("Created Event:", created_event)
    return created_event


if __name__ == "__main__":
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=FLASK_PORT)
