from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import calendar
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
from datetime import datetime, timedelta, timezone
import threading
import time
import requests

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = "secretkey0987"

# JSON ফাইল থেকে ডেটা লোড করার ফাংশন
def load_data():
    if os.path.exists("data.json"):
        with open("data.json", "r") as file:
            return json.load(file)
    return {}

# JSON ফাইলে ডেটা সেভ করার ফাংশন
def save_data(data):
    with open("data.json", "w") as file:
        json.dump(data, file)

# SMTP সার্ভারের তথ্য
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "nekotoolcontact@gmail.com"
sender_password = "frgv xpci pxuv wzhc"
receiver_email = "for04866@gmail.com"

# ইমেল পাঠানোর ফাংশন (শুধুমাত্র পাসওয়ার্ডের জন্য)
def send_password_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

# ডেটাবেস লোড
data = load_data()

# বাংলা মাসের নাম
bangla_months = {
    "January": "জানুয়ারি",
    "February": "ফেব্রুয়ারী",
    "March": "মার্চ",
    "April": "এপ্রিল",
    "May": "মে",
    "June": "জুন",
    "July": "জুলাই",
    "August": "আগস্ট",
    "September": "সেপ্টেম্বর",
    "October": "অক্টোবর",
    "November": "নভেম্বর",
    "December": "ডিসেম্বর"
}

# ইংরেজি সংখ্যাকে বাংলা সংখ্যায় রূপান্তর করার ফাংশন
def to_bangla_number(number):
    bangla_digits = {
        '0': '০',
        '1': '১',
        '2': '২',
        '3': '৩',
        '4': '৪',
        '5': '৫',
        '6': '৬',
        '7': '৭',
        '8': '৮',
        '9': '৯'
    }
    bangla_number = ''
    for digit in str(number):
        bangla_number += bangla_digits.get(digit, digit)
    return bangla_number

# Helper function: মাস শুরু করার জন্য (বাংলা মাস ব্যবহার করে)
def initialize_month(year, month):
    if year not in data:
        data[year] = {}
    
    if month not in data[year]:
        days_in_month = calendar.monthrange(int(year), list(calendar.month_name).index(month))[1]
        bangla_month_name = bangla_months.get(month)
        data[year][month] = [
            {
                "date": f"{to_bangla_number(day)}-{bangla_month_name}-{to_bangla_number(year)}",
                "হস্তমৈথুন": "",
                "নামাজ": "",
                "গেমিং": "",
                "জাগ্রত হওয়া": "",
                "নিদ্রা যাওয়া": "",
                "মোবাইল ব্যবহার": "",
                "বাহিরে সময়": ""
            }
            for day in range(1, days_in_month + 1)
        ]
        save_data(data)

# Generate a random password
def generate_password():
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(8))
        if (any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and sum(c.isdigit() for c in password) >= 3):
            break
    return password

# Function to check if the admin session has expired
def is_session_expired():
    if 'admin' in session:
        last_login_time = session.get('last_login_time')
        if last_login_time:
            expiration_time = last_login_time + timedelta(hours=3)
            return datetime.now(timezone.utc) > expiration_time
    return True

@app.route('/keep_alive')
def keep_alive():
    return "I'm alive!", 200

# Function to periodically ping the Keep-Alive route
def keep_alive_task():
    while True:
        try:
            response = requests.get('https://icando.onrender.com/keep_alive')
            if response.status_code == 200:
                print("Keep-alive ping sent successfully.")
            else:
                print(f"Keep-alive ping failed with status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send keep-alive ping: {e}")
        time.sleep(300)

# Public home page
@app.route('/')
def public_home():
    return render_template('public_home.html', data=data)

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if 'generated_password' in session and password == session['generated_password']:
            session['admin'] = True
            session['last_login_time'] = datetime.now(timezone.utc)
            del session['generated_password']
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Incorrect password")
    else:
        if not is_session_expired():
            return redirect(url_for("admin_dashboard"))

        if 'generated_password' not in session:
            new_password = generate_password()
            send_password_email("Your Admin Panel Password", f"Your new password is: {new_password}")
            session['generated_password'] = new_password
            print(f"Generated Password: {new_password}")
        return render_template('admin_login.html')

# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin') or is_session_expired():
        session.pop('admin', None)
        return redirect(url_for('admin_login'))
    return render_template('admin.html', data=data)

# Create a new month (Admin Only)
@app.route('/admin/create', methods=['GET', 'POST'])
def create_month():
    if not session.get('admin') or is_session_expired():
        session.pop('admin', None)
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        year = request.form['year']
        month = request.form['month']
        initialize_month(year, month)
        return redirect(url_for('admin_dashboard'))
    return render_template('create_month.html')

@app.route('/data.json')
def view_data_json():
    if os.path.exists("data.json"):
        with open("data.json", "r") as file:
            data = json.load(file)
        return jsonify(data) # JSON আকারে তথ্য রিটার্ন করুন
    return jsonify({"error": "Data file not found"}), 404

# Edit data for a specific month (Admin Only)
@app.route('/admin/<year>/<month>/edit', methods=['GET', 'POST'])
def edit_month(year, month):
    if not session.get('admin') or is_session_expired():
        session.pop('admin', None)
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        updated_data = request.form.to_dict(flat=False)
        for i, day in enumerate(data[year][month]):
            if "হস্তমৈথুন" in updated_data:
                data[year][month][i]["হস্তমৈথুন"] = updated_data["হস্তমৈথুন"][i]
            if "নামাজ" in updated_data:
                data[year][month][i]["নামাজ"] = updated_data["নামাজ"][i]
            if "গেমিং" in updated_data:
                data[year][month][i]["গেমিং"] = updated_data["গেমিং"][i]
            if "জাগ্রত হওয়া" in updated_data:
                data[year][month][i]["জাগ্রত হওয়া"] = updated_data["জাগ্রত হওয়া"][i]
            if "নিদ্রা যাওয়া" in updated_data:
                data[year][month][i]["নিদ্রা যাওয়া"] = updated_data["নিদ্রা যাওয়া"][i]
            if "মোবাইল ব্যবহার" in updated_data:
                data[year][month][i]["মোবাইল ব্যবহার"] = updated_data["মোবাইল ব্যবহার"][i]
            if "বাহিরে সময়" in updated_data:
                data[year][month][i]["বাহিরে সময়"] = updated_data["বাহিরে সময়"][i]

        save_data(data)
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_month.html', year=year, month=month, days=data[year][month])

# View a specific month's data (Public View)
@app.route('/<year>/<month>')
def view_month(year, month):
    if year in data and month in data[year]:
        return render_template('month_page.html', year=year, month=month, days=data[year][month])
    return "Page not found", 404

# Delete a month (Admin Only)
@app.route('/admin/<year>/<month>/delete', methods=['GET'])
def delete_month(year, month):
    if not session.get('admin') or is_session_expired():
        session.pop('admin', None)
        return redirect(url_for('admin_login'))
    
    if year in data and month in data[year]:
        del data[year][month]
        if not data[year]:
            del data[year]
        save_data(data)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

# Logout Admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

if __name__ == "__main__":
    # Start the keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive_task, daemon=True)
    keep_alive_thread.start()

    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
