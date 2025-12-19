from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key")

# --- Database Connection ---
try:
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client.ai_agency
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ Database Error: {e}")

# --- Routes ---

@app.route('/')
def home():
    user = session.get('user')
    # Database se latest 6 Reviews nikaalein
    reviews = list(db.reviews.find().sort("date", -1).limit(6))
    return render_template('index.html', user=user, reviews=reviews)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if db.users.find_one({"email": email}):
            flash("Email already registered! Please Login.")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        user_data = {
            "name": name, "email": email, "password": hashed_password,
            "role": "user", "created_at": datetime.datetime.now()
        }
        db.users.insert_one(user_data)
        session['user'] = {"name": name, "email": email, "role": "user"}
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.users.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            session['user'] = {"name": user['name'], "email": user['email'], "role": user.get('role', 'user')}
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Ghalat Email ya Password!")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

# --- QUERY SYSTEM ---
@app.route('/submit-query', methods=['POST'])
def submit_query():
    if 'user' not in session:
        flash("Please login to send a query.")
        return redirect(url_for('login'))
        
    data = request.form
    db.queries.insert_one({
        "user_email": session['user']['email'],
        "user_name": session['user']['name'],
        "service_type": data.get('service'),
        "message": data.get('message'),
        "status": "Pending",
        "date": datetime.datetime.now()
    })
    flash("✅ Query Submitted! Hum jaldi contact karenge.")
    return redirect(url_for('dashboard'))

# --- FEEDBACK SYSTEM (NEW) ---
@app.route('/submit-review', methods=['POST'])
def submit_review():
    if 'user' not in session:
        flash("Review dene ke liye Login karein.")
        return redirect(url_for('login'))
    
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    db.reviews.insert_one({
        "user_name": session['user']['name'],
        "rating": int(rating),
        "comment": comment,
        "date": datetime.datetime.now()
    })
    flash("⭐ Thanks for your feedback!")
    return redirect(url_for('home'))

# --- ADMIN PANEL ---
@app.route('/admin')
def admin_panel():
    if 'user' not in session: return redirect(url_for('login'))
    
    # YAHAN APNI EMAIL DALEIN
    admin_email = "rajkoushal862@gmail.com"
    
    if session['user']['email'] != admin_email:
        return "<h1>🚫 Access Denied!</h1>"

    queries = list(db.queries.find().sort("date", -1))
    return render_template('admin.html', queries=queries, user=session['user'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
