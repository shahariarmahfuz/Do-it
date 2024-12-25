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

app = Flask(__name__)
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

# ইমেল পাঠানোর ফাংশন
def send_email(subject, body):
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

# Helper function: মাস শুরু করার জন্য
def initialize_month(year, month):
    if year not in data:
        data[year] = {}
    if month not in data[year]:
        days_in_month = calendar.monthrange(int(year), list(calendar.month_name).index(month))[1]
        data[year][month] = [{"date": f"{day}-{month}-{year}",
                              "হস্তমৈথুন": "",
                              "নামাজ (ওয়াক্ত)": "",
                              "গেম (ঘণ্টা)": "",
                              "ঘুম থেকে উঠা": "",
                              "ঘুমানো": ""} for day in range(1, days_in_month + 1)]
        save_data(data)
        send_email(f"New month added: {month} {year}", f"A new month ({month} {year}) has been added to the database.")

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
            del session['generated_password']  # Remove the password after successful login
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Incorrect password")
    else:
        # Check if session is expired or not even logged in.
        if not is_session_expired():
           return redirect(url_for("admin_dashboard"))

        # Generate and send a new password only if there isn't one already
        if 'generated_password' not in session:
            new_password = generate_password()
            send_email("Your Admin Panel Password", f"Your new password is: {new_password}")
            session['generated_password'] = new_password
            print(f"Generated Password: {new_password}") # For debugging
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

# Edit data for a specific month (Admin Only)
@app.route('/admin/<year>/<month>/edit', methods=['GET', 'POST'])
def edit_month(year, month):
    if not session.get('admin') or is_session_expired():
        session.pop('admin', None)
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        updated_data = request.form.to_dict(flat=False)
        changes = ""

        for i, day in enumerate(data[year][month]):
            original_day = day.copy()

            if "হস্তমৈথুন" in updated_data:
                day["হস্তমৈথুন"] = updated_data["হস্তমৈথুন"][i]
            if "নামাজ (ওয়াক্ত)" in updated_data:
                day["নামাজ (ওয়াক্ত)"] = updated_data["নামাজ (ওয়াক্ত)"][i]
            if "গেম (ঘণ্টা)" in updated_data:
                day["গেম (ঘণ্টা)"] = updated_data["গেম (ঘণ্টা)"][i]
            if "ঘুম থেকে উঠা" in updated_data:
                day["ঘুম থেকে উঠা"] = updated_data["ঘুম থেকে উঠা"][i]
            if "ঘুমানো" in updated_data:
                day["ঘুমানো"] = updated_data["ঘুমানো"][i]

            # Compare original and updated data to build the changes string
            for key in day:
                if original_day[key] != day[key]:
                    changes += f"\n{day['date']}: {key} changed from '{original_day[key]}' to '{day[key]}'"

        save_data(data)
        if changes:
            send_email(f"Changes made to {month} {year}", f"Changes were made to {month} {year}:\n{changes}")
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
        send_email(f"Month deleted: {month} {year}", f"The month {month} {year} has been deleted from the database.")
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

# Logout Admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
