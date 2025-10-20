from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import sqlite3, os, hashlib, csv, datetime
from functools import wraps
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")

app = Flask(__name__)
app.secret_key = "replace_this_with_a_random_secret_in_production"

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {'png','jpg','jpeg','gif'}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'employee'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        title TEXT,
        comments TEXT,
        rating INTEGER,
        created_at TEXT
    )''')
    conn.commit()
    cur = c.execute("SELECT COUNT(*) as cnt FROM users WHERE role='admin'")
    row = cur.fetchone()
    if row is None or row['cnt'] == 0:
        pwd = hash_password('admin123')
        c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                  ('Admin','admin@example.com',pwd,'admin'))
        conn.commit()
    conn.close()

def hash_password(password):
    salt = 'static_salt_for_demo'
    return hashlib.sha256((password + salt).encode()).hexdigest()

def check_password(stored_hash, password):
    return stored_hash == hash_password(password)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def avatar_filename_for(user_id, filename):
    ext = filename.rsplit('.',1)[1].lower() if '.' in filename else 'png'
    return f"user_{user_id}.{ext}"

def initials_from_name(name):
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()

def color_for_name(name):
    h = hashlib.sha256(name.encode()).hexdigest()
    r = int(h[0:2],16)
    g = int(h[2:4],16)
    b = int(h[4:6],16)
    r = (r + 255)//2
    g = (g + 255)//2
    b = (b + 255)//2
    return f'rgb({r},{g},{b})'

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn = get_db()
        cur = conn.execute('SELECT role FROM users WHERE id=?', (session['user_id'],))
        row = cur.fetchone()
        conn.close()
        if not row or row['role'] != 'admin':
            flash('Admin access required','danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

@app.context_processor
def inject_helpers():
    return dict(initials_from_name=initials_from_name, color_for_name=color_for_name)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = request.form.get('role','employee')
        avatar = request.files.get('avatar')
        if not name or not email or not password:
            flash('Please fill all fields','warning')
            return redirect(url_for('register'))
        conn = get_db()
        try:
            cur = conn.execute('INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)',
                         (name,email,hash_password(password),role))
            conn.commit()
            user_id = cur.lastrowid
            if avatar and avatar.filename and allowed_file(avatar.filename):
                fname = secure_filename(avatar.filename)
                outname = avatar_filename_for(user_id, fname)
                path = os.path.join(UPLOAD_FOLDER, outname)
                avatar.save(path)
            flash('Registration successful. Please log in.','success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered','danger')
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/add_user', methods=['GET','POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password'] or 'changeme'
        role = request.form.get('role','employee')
        avatar = request.files.get('avatar')
        if not name or not email:
            flash('Please fill name and email','warning')
            return redirect(url_for('add_user'))
        conn = get_db()
        try:
            cur = conn.execute('INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)',
                        (name,email,hash_password(password),role))
            conn.commit()
            user_id = cur.lastrowid
            if avatar and avatar.filename and allowed_file(avatar.filename):
                fname = secure_filename(avatar.filename)
                outname = avatar_filename_for(user_id, fname)
                path = os.path.join(UPLOAD_FOLDER, outname)
                avatar.save(path)
            flash('User added','success')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('Email already registered','danger')
            return redirect(url_for('add_user'))
        finally:
            conn.close()
    return render_template('add_user.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db()
        cur = conn.execute('SELECT * FROM users WHERE email=?', (email,))
        user = cur.fetchone()
        conn.close()
        if user and check_password(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            flash('Logged in successfully','success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials','danger')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out','info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    users = conn.execute('SELECT id, name, email, role FROM users').fetchall()
    if session.get('role') == 'admin':
        recents = conn.execute('''SELECT f.*, u_from.name as from_name, u_to.name as to_name
                                  FROM feedback f
                                  LEFT JOIN users u_from ON f.from_user=u_from.id
                                  LEFT JOIN users u_to ON f.to_user=u_to.id
                                  ORDER BY f.created_at DESC LIMIT 10''').fetchall()
    else:
        recents = conn.execute('''SELECT f.*, u_from.name as from_name, u_to.name as to_name
                                  FROM feedback f
                                  LEFT JOIN users u_from ON f.from_user=u_from.id
                                  LEFT JOIN users u_to ON f.to_user=u_to.id
                                  WHERE f.to_user=?
                                  ORDER BY f.created_at DESC LIMIT 10''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('dashboard.html', users=users, recents=recents)

@app.route('/submit_feedback', methods=['GET','POST'])
@login_required
def submit_feedback():
    conn = get_db()
    users = conn.execute('SELECT id, name FROM users WHERE id != ?', (session['user_id'],)).fetchall()
    if request.method == 'POST':
        try:
            to_user = int(request.form.get('to_user'))
        except (TypeError, ValueError):
            flash('Please select a valid recipient','warning')
            conn.close()
            return redirect(url_for('submit_feedback'))

        title = (request.form.get('title') or '').strip()
        comments = (request.form.get('comments') or '').strip()
        try:
            rating = int(request.form.get('rating') or 0)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash('Please provide a rating between 1 and 5','warning')
            conn.close()
            return redirect(url_for('submit_feedback'))

        created_at = datetime.datetime.utcnow().isoformat()
        conn.execute(
            'INSERT INTO feedback (from_user, to_user, title, comments, rating, created_at) VALUES (?,?,?,?,?,?)',
            (session['user_id'], to_user, title, comments, rating, created_at)
        )
        conn.commit()
        conn.close()
        flash('Feedback submitted','success')
        return redirect(url_for('dashboard') + '?submitted=1')
    conn.close()
    return render_template('submit_feedback.html', users=users)

@app.route('/user/<int:user_id>/feedbacks')
@login_required
def user_feedbacks(user_id):
    conn = get_db()
    if session.get('role') != 'admin' and session.get('user_id') != user_id:
        flash('Access denied','danger')
        return redirect(url_for('dashboard'))
    user = conn.execute('SELECT id,name FROM users WHERE id=?', (user_id,)).fetchone()
    feedbacks = conn.execute('SELECT f.*, u_from.name as from_name FROM feedback f LEFT JOIN users u_from ON f.from_user=u_from.id WHERE f.to_user=? ORDER BY f.created_at DESC', (user_id,)).fetchall()
    avg_row = conn.execute('SELECT AVG(rating) as avg_rating, COUNT(*) as cnt FROM feedback WHERE to_user=?', (user_id,)).fetchone()
    conn.close()
    return render_template('user_feedbacks.html', user=user, feedbacks=feedbacks, avg=avg_row)

@app.route('/all_feedbacks')
@admin_required
def all_feedbacks():
    conn = get_db()
    feedbacks = conn.execute('SELECT f.*, u_from.name as from_name, u_to.name as to_name FROM feedback f LEFT JOIN users u_from ON f.from_user=u_from.id LEFT JOIN users u_to ON f.to_user=u_to.id ORDER BY f.created_at DESC').fetchall()
    conn.close()
    return render_template('all_feedbacks.html', feedbacks=feedbacks)

@app.route('/export_feedbacks')
@admin_required
def export_feedbacks():
    conn = get_db()
    feedbacks = conn.execute('SELECT f.id, u_from.name as from_name, u_to.name as to_name, f.title, f.comments, f.rating, f.created_at FROM feedback f LEFT JOIN users u_from ON f.from_user=u_from.id LEFT JOIN users u_to ON f.to_user=u_to.id ORDER BY f.created_at DESC').fetchall()
    conn.close()
    csv_path = os.path.join(BASE_DIR, 'feedbacks_export.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID','From','To','Title','Comments','Rating','Created At'])
        for r in feedbacks:
            writer.writerow([r['id'], r['from_name'], r['to_name'], r['title'], r['comments'], r['rating'], r['created_at']])
    return send_file(csv_path, as_attachment=True)

@app.route('/analytics_data')
@login_required
def analytics_data():
    conn = get_db()
    rows = conn.execute('''
        SELECT u.id, u.name, AVG(f.rating) as avg_rating, COUNT(f.id) as cnt
        FROM users u
        LEFT JOIN feedback f ON u.id=f.to_user
        GROUP BY u.id
        ORDER BY avg_rating DESC
    ''').fetchall()

    avg_list = [
        {'id': r['id'], 'name': r['name'], 'avg': round(r['avg_rating'] or 0,2), 'count': r['cnt']}
        for r in rows
    ]

    today = datetime.date.today()
    months = []
    for i in range(5, -1, -1):
        month_date = (today.replace(day=1) - datetime.timedelta(days=30*i)).replace(day=1)
        months.append(month_date.strftime('%Y-%m'))

    trend = []
    for m in months:
        cur = conn.execute("SELECT COUNT(*) as cnt FROM feedback WHERE substr(created_at,1,7)=?", (m,)).fetchone()
        trend.append({'month': m, 'count': cur['cnt']})

    conn.close()
    return jsonify({'avg_per_user': avg_list, 'monthly_trend': trend})

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
    else:
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)