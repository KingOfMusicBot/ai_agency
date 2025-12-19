from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import datetime
from bson.objectid import ObjectId

# Environment Variables Load karein
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key")

# --- ADMIN CONFIGURATION ---
# Ab ye email seedha .env file se aayega
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

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
    reviews = list(db.reviews.find().sort("date", -1).limit(6))
    projects = list(db.projects.find().sort("date", -1))
    return render_template('index.html', user=user, reviews=reviews, projects=projects)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if db.users.find_one({"email": email}):
            flash("Email already registered!")
            return redirect(url_for('login'))
            
        hashed_password = generate_password_hash(password)
        db.users.insert_one({
            "name": name, "email": email, "password": hashed_password,
            "role": "user", "created_at": datetime.datetime.now()
        })
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
            flash("❌ Wrong Email or Password")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    # Dashboard par Admin Link dikhane ke liye admin status pass karein
    is_admin = (session['user']['email'] == ADMIN_EMAIL)
    return render_template('dashboard.html', user=session['user'], is_admin=is_admin)

@app.route('/submit-query', methods=['POST'])
def submit_query():
    if 'user' not in session: return redirect(url_for('login'))
    data = request.form
    db.queries.insert_one({
        "user_email": session['user']['email'], "user_name": session['user']['name'],
        "service_type": data.get('service'), "message": data.get('message'),
        "status": "Pending", "date": datetime.datetime.now()
    })
    flash("✅ Query Sent!")
    return redirect(url_for('dashboard'))

@app.route('/submit-review', methods=['POST'])
def submit_review():
    if 'user' not in session: return redirect(url_for('login'))
    db.reviews.insert_one({
        "user_name": session['user']['name'], "rating": int(request.form.get('rating')),
        "comment": request.form.get('comment'), "date": datetime.datetime.now()
    })
    flash("⭐ Review Added!")
    return redirect(url_for('home'))

# --- ADMIN FEATURES (Controlled by .env) ---

@app.route('/add-project', methods=['POST'])
def add_project():
    # Check: Kya user ki email wahi hai jo .env mein hai?
    if 'user' not in session or session['user']['email'] != ADMIN_EMAIL:
        return "🚫 Access Denied! Sirf Admin allowed hai."
    
    db.projects.insert_one({
        "title": request.form.get('title'),
        "category": request.form.get('category'),
        "image_url": request.form.get('image_url'),
        "description": request.form.get('description'),
        "date": datetime.datetime.now()
    })
    flash("✅ New Project Added!")
    return redirect(url_for('admin_panel'))

@app.route('/delete-project/<id>')
def delete_project(id):
    # Check: Admin verification
    if 'user' not in session or session['user']['email'] != ADMIN_EMAIL:
        return "🚫 Access Denied!"
    
    db.projects.delete_one({"_id": ObjectId(id)})
    flash("🗑️ Project Deleted!")
    return redirect(url_for('admin_panel'))

@app.route('/admin')
def admin_panel():
    if 'user' not in session: return redirect(url_for('login'))
    
    # Check: Admin verification
    if session['user']['email'] != ADMIN_EMAIL:
        return f"🚫 Access Denied! Your email ({session['user']['email']}) is not authorized."

    queries = list(db.queries.find().sort("date", -1))
    projects = list(db.projects.find().sort("date", -1))
    
    return render_template('admin.html', queries=queries, projects=projects, user=session['user'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
