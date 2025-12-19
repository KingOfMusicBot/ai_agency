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
    return render_template('index.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check agar user pehle se hai
        if db.users.find_one({"email": email}):
            return "Email already registered! <a href='/login'>Login</a>"

        # Password ko secure (hash) karna
        hashed_password = generate_password_hash(password)

        user_data = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": "user",  # Default role
            "created_at": datetime.datetime.now()
        }
        db.users.insert_one(user_data)
        
        # Auto login after signup
        session['user'] = {"name": name, "email": email, "role": "user"}
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.users.find_one({"email": email})

        # Password check karna
        if user and check_password_hash(user['password'], password):
            session['user'] = {
                "name": user['name'], 
                "email": user['email'],
                "role": user.get('role', 'user')
            }
            return redirect(url_for('dashboard'))
        else:
            return "❌ Wrong Email or Password! <a href='/login'>Try Again</a>"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/submit-query', methods=['POST'])
def submit_query():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    data = request.form
    query_doc = {
        "user_email": session['user']['email'],
        "user_name": session['user']['name'],
        "service_type": data.get('service'),
        "message": data.get('message'),
        "status": "Pending",
        "date": datetime.datetime.now()
    }
    db.queries.insert_one(query_doc)
    return redirect(url_for('dashboard'))

# --- ADMIN PANEL ---
@app.route('/admin')
def admin_panel():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Yahan apni Email ID dalein jo Admin banegi
    admin_email = "aapki_email@gmail.com"
    
    if session['user']['email'] != admin_email:
        return "<h1>🚫 Access Denied!</h1>"

    all_queries = list(db.queries.find().sort("date", -1))
    return render_template('admin.html', queries=all_queries, user=session['user'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
