from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.config['DATABASE'] = 'news.db'
app.secret_key = 'secretkey'


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    with connect_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author TEXT NOT NULL,
                created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()


@app.before_first_request
def init_db_tables():
    init_db()


@app.route('/')
def index():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, content, author, created_on FROM news ORDER BY created_on DESC')
        news = cursor.fetchall()
        return render_template('index.html', news=news)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username=?', (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error=True)
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username=?', (username,))
            user = cursor.fetchone()
            if user:
                return render_template('register.html', error=True)
            elif password != confirm_password:
                return render_template('register.html', error=True)
            else:
                hashed_password = generate_password_hash(password)
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
                conn.commit()
                return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, user_id, title, content, author, created_on FROM news ORDER BY created_on DESC')
        news = cursor.fetchall()
    return render_template('dashboard.html', news=news, user_id=user_id)


@app.route('/add-news', methods=['GET', 'POST'])
def add_news():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        with connect_db() as conn:
            conn.execute('INSERT INTO news (title, content, author, user_id) VALUES (?, ?, ?, ?)',
                         (title, content, author, user_id))
            conn.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_news.html')


@app.route('/delete-news/<int:id>')
def delete_news(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news WHERE id=? AND user_id=?', (id, user_id))
        news_item = cursor.fetchone()
        if not news_item:
            return redirect(url_for('dashboard'))
        conn.execute('DELETE FROM news WHERE id=? AND user_id=?', (id, user_id))
        conn.commit()
    return redirect(url_for('dashboard'))


@app.route('/edit-news/<int:id>', methods=['GET', 'POST'])
def edit_news(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news WHERE id=?', (id,))
        news_item = cursor.fetchone()
        if not news_item:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            author = request.form['author']
            conn.execute('UPDATE news SET title=?, content=?, author=? WHERE id=?', (title, content, author, id))
            conn.commit()
            return redirect(url_for('dashboard'))
        return render_template('edit_news.html', news_item=news_item)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
