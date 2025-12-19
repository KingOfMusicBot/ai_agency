from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import datetime
from bson.objectid import ObjectId
from groq import Groq

# Environment Variables Load
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key")

# --- CONFIGURATION ---
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
MONGO_URI = os.getenv("MONGO_URI")

# --- 1. Database Connection ---
try:
    client = MongoClient(MONGO_URI)
    db = client.ai_agency
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ Database Error: {e}")

# --- 2. Groq AI Setup ---
try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    print("✅ Groq AI Connected!")
except Exception as e:
    print(f"❌ Groq Connection Error: {e}")

# --- ROUTES ---

@app.route('/')
def home():
    user = session.get('user')
    # Fetch Reviews & Projects for Home Page
    reviews = list(db.reviews.find().sort("date", -1).limit(6))
    projects = list(db.projects.find().sort("date", -1))
    return render_template('index.html', user=user, reviews=reviews, projects=projects)

@app.route('/tools')
def tools_page():
    user = session.get('user')
    return render_template('tools.html', user=user)

# --- GROQ AI TOOLS (Updated Model: llama-3.3-70b-versatile) ---

@app.route('/api/youtube-gen', methods=['POST'])
def youtube_gen():
    topic = request.form.get('topic')
    prompt = f"""
    Act as a YouTube Expert. I am making a video about '{topic}'.
    1. Generate 5 Viral Clickbait Titles (Catchy & SEO friendly).
    2. Generate 15 Comma-separated High Ranking Tags.
    Format output strictly:
    Titles:
    - Title 1...
    Tags:
    tag1, tag2...
    """
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        ai_text = completion.choices[0].message.content
        parts = ai_text.split("Tags:")
        titles = [t.strip("- ").strip() for t in parts[0].replace("Titles:", "").strip().split("\n") if t.strip()]
        tags = parts[1].strip() if len(parts) > 1 else "No tags"
        return render_template('tool_result.html', result_type="youtube", titles=titles, tags=tags)
    except Exception as e:
        return f"<h3 style='color:red'>Groq Error: {e}</h3>"

@app.route('/api/insta-gen', methods=['POST'])
def insta_gen():
    desc = request.form.get('desc')
    prompt = f"""
    Act as Social Media Manager. Photo description: '{desc}'.
    1. Write 5 Engaging Captions.
    2. Generate 20 Trending Hashtags.
    Format output strictly:
    Captions:
    - Caption 1...
    Hashtags:
    #tag1 #tag2...
    """
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        ai_text = completion.choices[0].message.content
        parts = ai_text.split("Hashtags:")
        captions = [c.strip("- ").strip() for c in parts[0].replace("Captions:", "").strip().split("\n") if c.strip()]
        hashtags = parts[1].strip() if len(parts) > 1 else "#NoTags"
        return render_template('tool_result.html', result_type="instagram", captions=captions, hashtags=hashtags)
    except Exception as e:
        return f"<h3 style='color:red'>Groq Error: {e}</h3>"

# --- AUTH SYSTEM ---

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
        db.users.insert_one({"name": name, "email": email, "password": hashed_password, "role": "user", "created_at": datetime.datetime.now()})
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
    is_admin = (session['user']['email'] == ADMIN_EMAIL)
    return render_template('dashboard.html', user=session['user'], is_admin=is_admin)

# --- USER ACTIONS ---

@app.route('/submit-query', methods=['POST'])
def submit_query():
    if 'user' not in session: return redirect(url_for('login'))
    data = request.form
    db.queries.insert_one({
        "user_email": session['user']['email'], "user_name": session['user']['name'],
        "service_type": data.get('service'), "message": data.get('message'),
        "status": "Pending", "date": datetime.datetime.now()
    })
    flash("✅ Query Sent Successfully!")
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

# --- ADMIN PANEL & MANAGEMENT ---

@app.route('/admin')
def admin_panel():
    if 'user' not in session: return redirect(url_for('login'))
    if session['user']['email'] != ADMIN_EMAIL: return f"🚫 Access Denied!"
    
    queries = list(db.queries.find().sort("date", -1))
    projects = list(db.projects.find().sort("date", -1))
    reviews = list(db.reviews.find().sort("date", -1))
    return render_template('admin.html', queries=queries, projects=projects, reviews=reviews, user=session['user'])

@app.route('/add-project', methods=['POST'])
def add_project():
    if 'user' not in session or session['user']['email'] != ADMIN_EMAIL: return "🚫 Access Denied!"
    db.projects.insert_one({
        "title": request.form.get('title'), "category": request.form.get('category'),
        "image_url": request.form.get('image_url'), "description": request.form.get('description'),
        "date": datetime.datetime.now()
    })
    flash("✅ Project Added!")
    return redirect(url_for('admin_panel'))

@app.route('/delete-project/<id>')
def delete_project(id):
    if 'user' not in session or session['user']['email'] != ADMIN_EMAIL: return "🚫 Access Denied!"
    db.projects.delete_one({"_id": ObjectId(id)})
    flash("🗑️ Project Deleted!")
    return redirect(url_for('admin_panel'))

@app.route('/delete-review/<id>')
def delete_review(id):
    if 'user' not in session or session['user']['email'] != ADMIN_EMAIL: return "🚫 Access Denied!"
    db.reviews.delete_one({"_id": ObjectId(id)})
    flash("🗑️ Review Deleted!")
    return redirect(url_for('admin_panel'))

@app.route('/update-query/<id>')
def update_query(id):
    if 'user' not in session or session['user']['email'] != ADMIN_EMAIL: return "🚫 Access Denied!"
    query = db.queries.find_one({"_id": ObjectId(id)})
    new_status = "Completed" if query.get('status') == "Pending" else "Pending"
    db.queries.update_one({"_id": ObjectId(id)}, {"$set": {"status": new_status}})
    flash(f"✅ Status updated to {new_status}")
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    # Running on Port 5001
    app.run(host='0.0.0.0', port=5001, debug=True)
