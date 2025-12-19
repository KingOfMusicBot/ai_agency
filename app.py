from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import datetime

# Load environment variables (.env file se)
load_dotenv()

app = Flask(__name__)
# Security Key (Zaroori hai session ke liye)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key_agar_env_khali_ho")

# --- 1. Database Connection (MongoDB) ---
try:
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("⚠️ Warning: MONGO_URI .env file mein nahi mila!")
    
    client = MongoClient(mongo_uri)
    db = client.ai_agency  # Database Name
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ Database Connection Failed: {e}")

# --- 2. Google Login Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# --- 3. Routes (Pages) ---

@app.route('/')
def home():
    # Session check karein: User logged in hai ya nahi?
    user = session.get('user')
    # index.html render karein aur user ka data bhejein
    return render_template('index.html', user=user)

@app.route('/login')
def login():
    # Google Login Page par redirect karein
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    # Session clear karein (Logout)
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/authorize')
def authorize():
    try:
        # Google se wapas aane par token lein
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()
        
        # User ka data database mein save karein
        users_col = db.users
        user_data = {
            "google_id": user_info['id'],
            "name": user_info['name'],
            "email": user_info['email'],
            "picture": user_info['picture'],
            "last_login": datetime.datetime.now()
        }
        
        # Upsert: Agar user naya hai to create karein, purana hai to update karein
        users_col.update_one({"google_id": user_info['id']}, {"$set": user_data}, upsert=True)
        
        # Session mein user save karein
        session['user'] = user_data
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Login Error: {e}"

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    # Abhi ke liye simple dashboard (Baad mein iska HTML banayenge)
    user = session['user']
    return f"""
    <div style='text-align:center; padding:50px; font-family:sans-serif;'>
        <h1>Welcome, {user['name']}! 🚀</h1>
        <img src='{user['picture']}' style='border-radius:50%; width:100px;'><br><br>
        <p>Email: {user['email']}</p>
        <p>Status: Active</p>
        <br>
        <a href='/' style='background:blue; color:white; padding:10px 20px; text-decoration:none;'>Go Home</a>
        <a href='/logout' style='background:red; color:white; padding:10px 20px; text-decoration:none;'>Logout</a>
    </div>
    """

@app.route('/submit-query', methods=['POST'])
def submit_query():
    # Login check
    if 'user' not in session:
        return "<h1>❌ Please Login First</h1><a href='/login'>Login Here</a>", 401
        
    data = request.form
    
    # Query database ke liye document banayein
    query_doc = {
        "user_email": session['user']['email'],
        "user_name": session['user']['name'],
        "service_type": data.get('service'),
        "message": data.get('message'),
        "status": "Pending",
        "date": datetime.datetime.now()
    }
    
    try:
        db.queries.insert_one(query_doc)
        return """
        <div style='text-align:center; padding:50px; font-family:sans-serif;'>
            <h1 style='color:green;'>✅ Query Submitted!</h1>
            <p>Humari team jald hi aapse contact karegi.</p>
            <a href='/'>Go Back</a>
        </div>
        """
    except Exception as e:
        return f"Error saving query: {e}"

# --- Server Start ---
if __name__ == '__main__':
    # 0.0.0.0 = Public Access
    app.run(host='0.0.0.0', port=5000, debug=True)
