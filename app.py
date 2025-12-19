from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# --- 1. Database Connection (MongoDB) ---
try:
    client = MongoClient(os.getenv("MONGO_URI"))
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
)

# --- 3. Routes (Pages) ---

@app.route('/')
def home():
    # Newsletter & Feedback features yahan integrate honge
    return "<h1>AI Marketing Agency - Coming Soon</h1>"

@app.route('/login')
def login():
    # Google Login Redirect
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    # Google se wapas aane par data save karna
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    
    # User ko DB mein save/update karna
    users_col = db.users
    user_data = {
        "google_id": user_info['id'],
        "name": user_info['name'],
        "email": user_info['email'],
        "picture": user_info['picture'],
        "last_login": datetime.datetime.now()
    }
    
    # Agar user pehle se hai to update, nahi to insert (Upsert)
    users_col.update_one({"google_id": user_info['id']}, {"$set": user_data}, upsert=True)
    
    session['user'] = user_data
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    return f"Welcome {session['user']['name']}! <br> <img src='{session['user']['picture']}' width='50'>"

@app.route('/submit-query', methods=['POST'])
def submit_query():
    # User queries DB mein save hongi
    if 'user' not in session:
        return "Please Login first", 401
        
    data = request.form
    query_doc = {
        "user_email": session['user']['email'],
        "service_type": data.get('service'),
        "message": data.get('message'),
        "status": "Pending",
        "date": datetime.datetime.now()
    }
    db.queries.insert_one(query_doc)
    return "Query Submitted!"

# --- Server Start ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
