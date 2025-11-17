from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import os
from datetime import datetime, timedelta
from functools import wraps
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.permanent_session_lifetime = timedelta(hours=24)


# JSON file to store users and notes
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = '/tmp' if os.path.isdir('/tmp') and os.access('/tmp', os.W_OK) else BASE_DIR
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')

def load_json_file(filename):
    """Load JSON data from file, create empty structure if file doesn't exist"""
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_json_file(filename, data):
    """Save data to JSON file"""
    dirpath = os.path.dirname(filename)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_data_files():
    """Initialize data files if they don't exist"""
    if not os.path.exists(USERS_FILE):
        # Create default users
        users = {
            "admin": {
                "password": "admin123",
                "email": "admin@example.com",
                "created_at": datetime.now().isoformat()
            },
            "demo": {
                "password": "demo123", 
                "email": "demo@example.com",
                "created_at": datetime.now().isoformat()
            }
        }
        save_json_file(USERS_FILE, users)
    
    if not os.path.exists(NOTES_FILE):
        # Create sample notes
        notes = {
            "admin": [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Meeting Notes",
                    "content": "Discussed project timeline and deliverables. Key points:\n- Complete design mockups by Friday\n- Review user feedback\n- Plan next sprint",
                    "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                    "updated_at": (datetime.now() - timedelta(days=2)).isoformat(),
                    "category": "Work"
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "HTML Basics",
                    "content": "Learn about the basic structure of HTML documents, including elements like <html>, <head>, and <body>.\n\nKey concepts:\n- Semantic HTML\n- Document structure\n- Meta tags",
                    "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
                    "updated_at": (datetime.now() - timedelta(days=5)).isoformat(),
                    "category": "HTML"
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "CSS Styling", 
                    "content": "Explore CSS selectors, properties, and values to style HTML elements.\n\n- Selectors: class, id, element\n- Box model\n- Flexbox and Grid",
                    "created_at": (datetime.now() - timedelta(weeks=1)).isoformat(),
                    "updated_at": (datetime.now() - timedelta(weeks=1)).isoformat(),
                    "category": "CSS"
                }
            ],
            "demo": [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Grocery List",
                    "content": "Shopping list for this week:\n- Milk\n- Bread\n- Eggs\n- Apples\n- Chicken breast",
                    "created_at": (datetime.now() - timedelta(weeks=1)).isoformat(),
                    "updated_at": (datetime.now() - timedelta(weeks=1)).isoformat(),
                    "category": "Personal"
                }
            ]
        }
        save_json_file(NOTES_FILE, notes)

# Initialize data files at import time (needed for serverless environments)
init_data_files()

@app.route('/')
def index():
    """Redirect to dashboard if logged in, otherwise to login"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = load_json_file(USERS_FILE)
        
        # Check if user exists and password is correct
        if username in users and users[username]['password'] == password:
            session.permanent = True
            session['user_id'] = username
            session['user_email'] = users[username]['email']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard showing user's notes"""
    # Get and print the sample_api_key from environment variable
    sample_api_key = os.getenv('sample_api_key', 'Not configured')
    print(f"Sample API Key: {sample_api_key}")
    
    notes_data = load_json_file(NOTES_FILE)
    user_notes = notes_data.get(session['user_id'], [])
    
    # Sort notes by updated_at (most recent first)
    user_notes.sort(key=lambda x: x['updated_at'], reverse=True)
    
    # Add formatted dates
    for note in user_notes:
        note_date = datetime.fromisoformat(note['updated_at'])
        days_ago = (datetime.now() - note_date).days
        
        if days_ago == 0:
            note['formatted_date'] = 'Today'
        elif days_ago == 1:
            note['formatted_date'] = '1 day ago'
        elif days_ago < 7:
            note['formatted_date'] = f'{days_ago} days ago'
        elif days_ago < 30:
            weeks = days_ago // 7
            note['formatted_date'] = f'{weeks} week{"s" if weeks > 1 else ""} ago'
        else:
            months = days_ago // 30
            note['formatted_date'] = f'{months} month{"s" if months > 1 else ""} ago'
    
    
    return render_template('dashboard.html', notes=user_notes, username=session['user_id'], sample_api_key=sample_api_key)

@app.route('/new-note', methods=['GET', 'POST'])
@login_required
def new_note():
    """Create new note"""
    if request.method == 'POST':
        title = request.form.get('title', 'Untitled Note').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'General').strip()
        
        if not title:
            title = 'Untitled Note'
        
        # Create new note
        new_note = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": content,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Load existing notes
        notes_data = load_json_file(NOTES_FILE)
        user_id = session['user_id']
        
        if user_id not in notes_data:
            notes_data[user_id] = []
        
        notes_data[user_id].append(new_note)
        save_json_file(NOTES_FILE, notes_data)
        
        flash(f'Note "{title}" created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('new_note.html', username=session['user_id'])

@app.route('/edit-note/<note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    """Edit existing note"""
    notes_data = load_json_file(NOTES_FILE)
    user_notes = notes_data.get(session['user_id'], [])
    
    # Find the note
    note = next((n for n in user_notes if n['id'] == note_id), None)
    if not note:
        flash('Note not found', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        note['title'] = request.form.get('title', note['title']).strip()
        note['content'] = request.form.get('content', note['content']).strip()
        note['category'] = request.form.get('category', note['category']).strip()
        note['updated_at'] = datetime.now().isoformat()
        
        save_json_file(NOTES_FILE, notes_data)
        flash(f'Note "{note["title"]}" updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_note.html', note=note, username=session['user_id'])

@app.route('/delete-note/<note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    """Delete a note"""
    notes_data = load_json_file(NOTES_FILE)
    user_notes = notes_data.get(session['user_id'], [])
    
    # Find and remove the note
    original_count = len(user_notes)
    notes_data[session['user_id']] = [n for n in user_notes if n['id'] != note_id]
    
    if len(notes_data[session['user_id']]) < original_count:
        save_json_file(NOTES_FILE, notes_data)
        flash('Note deleted successfully!', 'success')
    else:
        flash('Note not found', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/api/notes')
@login_required
def api_notes():
    """API endpoint to get user's notes as JSON"""
    notes_data = load_json_file(NOTES_FILE)
    user_notes = notes_data.get(session['user_id'], [])
    return jsonify(user_notes)

@app.route('/search')
@login_required
def search_notes():
    """Search notes"""
    query = request.args.get('q', '').strip().lower()
    notes_data = load_json_file(NOTES_FILE)
    user_notes = notes_data.get(session['user_id'], [])
    
    if query:
        # Filter notes that match the search query
        filtered_notes = []
        for note in user_notes:
            if (query in note['title'].lower() or 
                query in note['content'].lower() or 
                query in note['category'].lower()):
                filtered_notes.append(note)
        user_notes = filtered_notes
    
    # Sort notes by updated_at (most recent first)
    user_notes.sort(key=lambda x: x['updated_at'], reverse=True)
    
    # Add formatted dates
    for note in user_notes:
        note_date = datetime.fromisoformat(note['updated_at'])
        days_ago = (datetime.now() - note_date).days
        
        if days_ago == 0:
            note['formatted_date'] = 'Today'
        elif days_ago == 1:
            note['formatted_date'] = '1 day ago'
        elif days_ago < 7:
            note['formatted_date'] = f'{days_ago} days ago'
        elif days_ago < 30:
            weeks = days_ago // 7
            note['formatted_date'] = f'{weeks} week{"s" if weeks > 1 else ""} ago'
        else:
            months = days_ago // 30
            note['formatted_date'] = f'{months} month{"s" if months > 1 else ""} ago'
    
    return render_template('dashboard.html', notes=user_notes, username=session['user_id'], search_query=query)

if __name__ == '__main__':
    # Initialize data files
    init_data_files()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)