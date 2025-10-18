from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import random
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database setup
DATABASE = 'vocabulary.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
                     CREATE TABLE IF NOT EXISTS pages
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY
                         AUTOINCREMENT,
                         name
                         TEXT
                         NOT
                         NULL,
                         created_at
                         TIMESTAMP
                         DEFAULT
                         CURRENT_TIMESTAMP
                     )
                     ''')
        conn.execute('''
                     CREATE TABLE IF NOT EXISTS words
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY
                         AUTOINCREMENT,
                         page_id
                         INTEGER
                         NOT
                         NULL,
                         english
                         TEXT
                         NOT
                         NULL,
                         armenian
                         TEXT
                         NOT
                         NULL,
                         FOREIGN
                         KEY
                     (
                         page_id
                     ) REFERENCES pages
                     (
                         id
                     ) ON DELETE CASCADE
                         )
                     ''')
        conn.execute('''
                     CREATE TABLE IF NOT EXISTS statistics
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY
                         AUTOINCREMENT,
                         word_id
                         INTEGER
                         NOT
                         NULL,
                         correct
                         INTEGER
                         DEFAULT
                         0,
                         incorrect
                         INTEGER
                         DEFAULT
                         0,
                         last_studied
                         TIMESTAMP,
                         FOREIGN
                         KEY
                     (
                         word_id
                     ) REFERENCES words
                     (
                         id
                     ) ON DELETE CASCADE
                         )
                     ''')
        conn.commit()


# HTML Templates
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Vocabulary Study</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 50px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { 
            text-align: center; 
            margin-bottom: 40px; 
            color: #333;
        }
        .btn-group {
            display: flex;
            gap: 20px;
            justify-content: center;
        }
        button {
            padding: 20px 40px;
            font-size: 18px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            background: #4CAF50;
            color: white;
            transition: background 0.3s;
        }
        button:hover { background: #45a049; }
        .secondary { background: #2196F3; }
        .secondary:hover { background: #0b7dda; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Vocabulary Study App</h1>
        <div class="btn-group">
            <button onclick="location.href='/study'">Study</button>
            <button class="secondary" onclick="location.href='/manage'">Manage Pages</button>
        </div>
    </div>
</body>
</html>
'''

MANAGE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Manage Pages</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1000px; 
            margin: 20px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { margin-bottom: 30px; color: #333; }
        h2 { margin: 30px 0 15px 0; color: #555; }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-primary:hover { background: #45a049; }
        .btn-secondary { background: #2196F3; color: white; }
        .btn-secondary:hover { background: #0b7dda; }
        .btn-danger { background: #f44336; color: white; }
        .btn-danger:hover { background: #da190b; }
        .page-list {
            list-style: none;
            margin: 20px 0;
        }
        .page-item {
            padding: 15px;
            margin: 10px 0;
            background: #f9f9f9;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .page-info { flex: 1; }
        .page-name { font-weight: bold; font-size: 16px; }
        .page-stats { color: #666; font-size: 14px; margin-top: 5px; }
        .btn-group { display: flex; gap: 10px; }
        input[type="text"] {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            width: 300px;
        }
        .form-group { margin: 20px 0; }
        .back-link { 
            display: inline-block;
            margin-bottom: 20px;
            color: #2196F3;
            text-decoration: none;
        }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Back to Home</a>
        <h1>Manage Pages</h1>

        <h2>Create New Page</h2>
        <form method="POST" action="/create_page">
            <div class="form-group">
                <input type="text" name="page_name" placeholder="Page name (e.g., Page 1, Chapter 3)" required>
                <button type="submit" class="btn-primary">Create Page</button>
            </div>
        </form>

        <h2>Existing Pages</h2>
        {% if pages %}
        <ul class="page-list">
            {% for page in pages %}
            <li class="page-item">
                <div class="page-info">
                    <div class="page-name">{{ page.name }}</div>
                    <div class="page-stats">
                        {{ page.word_count }} words | 
                        Correct: {{ page.correct }} | 
                        Incorrect: {{ page.incorrect }}
                    </div>
                </div>
                <div class="btn-group">
                    <button class="btn-secondary" onclick="location.href='/edit_page/{{ page.id }}'">Edit Words</button>
                    <button class="btn-danger" onclick="if(confirm('Delete this page?')) location.href='/delete_page/{{ page.id }}'">Delete</button>
                </div>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p>No pages yet. Create your first page above.</p>
        {% endif %}
    </div>
</body>
</html>
'''

EDIT_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Edit Page: {{ page.name }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1000px; 
            margin: 20px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { margin-bottom: 30px; color: #333; }
        h2 { margin: 30px 0 15px 0; color: #555; }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-primary:hover { background: #45a049; }
        .btn-danger { background: #f44336; color: white; }
        .btn-danger:hover { background: #da190b; }
        input[type="text"] {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            width: 200px;
        }
        .form-group { 
            margin: 20px 0;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .back-link { 
            display: inline-block;
            margin-bottom: 20px;
            color: #2196F3;
            text-decoration: none;
        }
        .back-link:hover { text-decoration: underline; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f5f5f5;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/manage" class="back-link">← Back to Manage Pages</a>
        <h1>Edit Page: {{ page.name }}</h1>

        <h2>Add New Word</h2>
        <form method="POST" action="/add_word/{{ page.id }}">
            <div class="form-group">
                <input type="text" name="english" placeholder="English word" required>
                <input type="text" name="armenian" placeholder="Armenian word" required>
                <button type="submit" class="btn-primary">Add Word</button>
            </div>
        </form>

        <h2>Words in this Page ({{ words|length }})</h2>
        {% if words %}
        <table>
            <thead>
                <tr>
                    <th>English</th>
                    <th>Armenian</th>
                    <th>Statistics</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for word in words %}
                <tr>
                    <td>{{ word.english }}</td>
                    <td>{{ word.armenian }}</td>
                    <td>✓{{ word.correct }} / ✗{{ word.incorrect }}</td>
                    <td>
                        <button class="btn-danger" onclick="if(confirm('Delete this word?')) location.href='/delete_word/{{ word.id }}'">Delete</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No words yet. Add words using the form above.</p>
        {% endif %}
    </div>
</body>
</html>
'''

STUDY_SETUP_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Study Setup</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 50px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { 
            text-align: center; 
            margin-bottom: 40px; 
            color: #333;
        }
        h2 { 
            margin: 30px 0 15px 0; 
            color: #555;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 6px;
        }
        .btn-group {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin: 15px 0;
        }
        button {
            padding: 15px 30px;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            background: #4CAF50;
            color: white;
            transition: background 0.3s;
            flex: 1;
            min-width: 150px;
        }
        button:hover { background: #45a049; }
        button.selected { 
            background: #2196F3;
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.3);
        }
        .page-selection {
            margin: 20px 0;
        }
        .page-checkbox {
            display: block;
            padding: 10px;
            margin: 5px 0;
            background: white;
            border: 2px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
        }
        .page-checkbox:hover { background: #f5f5f5; }
        .page-checkbox input[type="checkbox"] {
            margin-right: 10px;
            transform: scale(1.2);
        }
        .start-btn {
            background: #FF9800;
            font-size: 18px;
            padding: 20px 40px;
            width: 100%;
            margin-top: 20px;
        }
        .start-btn:hover { background: #F57C00; }
        .start-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .back-link { 
            display: inline-block;
            margin-bottom: 20px;
            color: #2196F3;
            text-decoration: none;
        }
        .back-link:hover { text-decoration: underline; }
        .error { 
            color: #f44336; 
            margin-top: 10px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Back to Home</a>
        <h1>Study Setup</h1>

        <form id="studyForm" method="POST" action="/study_session">
            <div class="section">
                <h2>1. Select Direction</h2>
                <div class="btn-group">
                    <button type="button" onclick="selectDirection('en_to_am')" id="btn_en_to_am">English → Armenian</button>
                    <button type="button" onclick="selectDirection('am_to_en')" id="btn_am_to_en">Armenian → English</button>
                </div>
                <input type="hidden" name="direction" id="direction" required>
            </div>

            <div class="section">
                <h2>2. Select Input Method</h2>
                <div class="btn-group">
                    <button type="button" onclick="selectMethod('write')" id="btn_write">Write</button>
                    <button type="button" onclick="selectMethod('say')" id="btn_say">Say</button>
                </div>
                <input type="hidden" name="method" id="method" required>
            </div>

            <div class="section">
                <h2>3. Select Study Mode</h2>
                <div class="btn-group">
                    <button type="button" onclick="selectMode('smart')" id="btn_smart">Smart (Mistake-based)</button>
                    <button type="button" onclick="selectMode('random')" id="btn_random">Random</button>
                    <button type="button" onclick="selectMode('session')" id="btn_session">Session (Each Once)</button>
                </div>
                <input type="hidden" name="mode" id="mode" required>
            </div>

            <div class="section">
                <h2>4. Select Pages</h2>
                <div class="page-selection">
                    {% if pages %}
                        {% for page in pages %}
                        <label class="page-checkbox">
                            <input type="checkbox" name="pages" value="{{ page.id }}">
                            {{ page.name }} ({{ page.word_count }} words)
                        </label>
                        {% endfor %}
                    {% else %}
                        <p class="error">No pages available. Please create pages first.</p>
                    {% endif %}
                </div>
            </div>

            <button type="submit" class="start-btn" id="startBtn" {% if not pages %}disabled{% endif %}>Start Study Session</button>
            <div id="error" class="error"></div>
        </form>
    </div>

    <script>
        function selectDirection(dir) {
            document.getElementById('direction').value = dir;
            document.querySelectorAll('[id^="btn_en_"], [id^="btn_am_"]').forEach(b => b.classList.remove('selected'));
            document.getElementById('btn_' + dir).classList.add('selected');
            validateForm();
        }

        function selectMethod(method) {
            document.getElementById('method').value = method;
            document.querySelectorAll('[id^="btn_write"], [id^="btn_say"]').forEach(b => b.classList.remove('selected'));
            document.getElementById('btn_' + method).classList.add('selected');
            validateForm();
        }

        function selectMode(mode) {
            document.getElementById('mode').value = mode;
            document.querySelectorAll('[id^="btn_smart"], [id^="btn_random"], [id^="btn_session"]').forEach(b => b.classList.remove('selected'));
            document.getElementById('btn_' + mode).classList.add('selected');
            validateForm();
        }

        function validateForm() {
            const direction = document.getElementById('direction').value;
            const method = document.getElementById('method').value;
            const mode = document.getElementById('mode').value;
            const pages = document.querySelectorAll('input[name="pages"]:checked').length;

            const isValid = direction && method && mode && pages > 0;
            document.getElementById('startBtn').disabled = !isValid;

            if (!isValid && direction && method && mode) {
                document.getElementById('error').textContent = 'Please select at least one page';
            } else {
                document.getElementById('error').textContent = '';
            }
        }

        document.querySelectorAll('input[name="pages"]').forEach(cb => {
            cb.addEventListener('change', validateForm);
        });
    </script>
</body>
</html>
'''

STUDY_SESSION_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Study Session</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 50px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 400px;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .mode-info {
            color: #666;
            font-size: 14px;
        }
        .word-display {
            text-align: center;
            margin: 50px 0;
        }
        .prompt-word {
            font-size: 48px;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 20px;
        }
        .answer-area {
            text-align: center;
            margin: 30px 0;
        }
        input[type="text"] {
            padding: 15px;
            font-size: 24px;
            border: 2px solid #ddd;
            border-radius: 6px;
            width: 400px;
            text-align: center;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #2196F3;
        }
        .revealed-answer {
            font-size: 36px;
            color: #4CAF50;
            margin: 20px 0;
        }
        .feedback {
            font-size: 24px;
            margin: 20px 0;
            padding: 20px;
            border-radius: 6px;
        }
        .correct {
            background: #C8E6C9;
            color: #2E7D32;
        }
        .incorrect {
            background: #FFCDD2;
            color: #C62828;
        }
        .correct-answer {
            font-size: 20px;
            color: #4CAF50;
            margin-top: 10px;
        }
        .btn-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
        }
        button {
            padding: 15px 40px;
            font-size: 18px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            color: white;
            transition: all 0.3s;
        }
        .btn-check { background: #2196F3; }
        .btn-check:hover { background: #0b7dda; }
        .btn-reveal { background: #FF9800; }
        .btn-reveal:hover { background: #F57C00; }
        .btn-next { background: #4CAF50; }
        .btn-next:hover { background: #45a049; }
        .btn-end { background: #f44336; }
        .btn-end:hover { background: #da190b; }
        .progress {
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 14px;
        }
        .complete-message {
            text-align: center;
            margin: 50px 0;
        }
        .complete-message h2 {
            color: #4CAF50;
            margin-bottom: 20px;
        }
        .stats {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .stats p {
            margin: 10px 0;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Study Session</h1>
            <div class="mode-info">
                {{ direction_text }} | {{ method_text }} | {{ mode_text }}
            </div>
        </div>

        {% if completed %}
        <div class="complete-message">
            <h2>Session Complete! 🎉</h2>
            <div class="stats">
                <p><strong>Words studied:</strong> {{ session_stats.total }}</p>
                {% if method == 'write' %}
                <p><strong>Correct:</strong> {{ session_stats.correct }}</p>
                <p><strong>Incorrect:</strong> {{ session_stats.incorrect }}</p>
                <p><strong>Accuracy:</strong> {{ session_stats.accuracy }}%</p>
                {% endif %}
            </div>
            <div class="btn-group">
                <button class="btn-next" onclick="location.href='/study'">New Session</button>
                <button class="btn-end" onclick="location.href='/'">Home</button>
            </div>
        </div>
        {% else %}
        <div class="word-display">
            <div class="prompt-word">{{ current_word.prompt }}</div>
        </div>

        <div class="answer-area">
            {% if method == 'write' %}
                {% if not checked %}
                <form method="POST" action="/study_action">
                    <input type="text" name="answer" id="answerInput" placeholder="Type your answer" autofocus>
                    <input type="hidden" name="action" value="check">
                    <input type="hidden" name="word_id" value="{{ current_word.id }}">
                    <input type="hidden" name="correct_answer" value="{{ current_word.answer }}">
                    <div class="btn-group">
                        <button type="submit" class="btn-check">Check</button>
                        <button type="button" class="btn-next" onclick="document.getElementById('skipForm').submit()">Next (Skip)</button>
                    </div>
                </form>
                <form id="skipForm" method="POST" action="/study_action" style="display:none;">
                    <input type="hidden" name="action" value="next">
                </form>
                {% else %}
                <div class="feedback {{ 'correct' if is_correct else 'incorrect' }}">
                    {{ 'Correct! ✓' if is_correct else 'Incorrect ✗' }}
                </div>
                {% if not is_correct %}
                <div class="correct-answer">
                    Correct answer: {{ current_word.answer }}
                </div>
                {% endif %}
                <form method="POST" action="/study_action">
                    <input type="hidden" name="action" value="next">
                    <div class="btn-group">
                        <button type="submit" class="btn-next">Next Word</button>
                    </div>
                </form>
                {% endif %}
            {% else %}
                {% if not revealed %}
                <form method="POST" action="/study_action">
                    <input type="hidden" name="action" value="reveal">
                    <div class="btn-group">
                        <button type="submit" class="btn-reveal">Reveal Answer</button>
                        <button type="button" class="btn-next" onclick="document.getElementById('skipForm').submit()">Next (Skip)</button>
                    </div>
                </form>
                <form id="skipForm" method="POST" action="/study_action" style="display:none;">
                    <input type="hidden" name="action" value="next">
                </form>
                {% else %}
                <div class="revealed-answer">
                    {{ current_word.answer }}
                </div>
                <form method="POST" action="/study_action">
                    <input type="hidden" name="action" value="next">
                    <div class="btn-group">
                        <button type="submit" class="btn-next">Next Word</button>
                    </div>
                </form>
                {% endif %}
            {% endif %}
        </div>

        {% if progress %}
        <div class="progress">
            Progress: {{ progress.current }} / {{ progress.total }}
        </div>
        {% endif %}

        <div class="btn-group">
            <button class="btn-end" onclick="if(confirm('End session?')) location.href='/study'">End Session</button>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''


# Routes
@app.route('/')
def index():
    return render_template_string(HOME_TEMPLATE)


@app.route('/manage')
def manage():
    with get_db() as conn:
        pages = conn.execute('''
                             SELECT p.*,
                                    COUNT(DISTINCT w.id)          as word_count,
                                    COALESCE(SUM(s.correct), 0)   as correct,
                                    COALESCE(SUM(s.incorrect), 0) as incorrect
                             FROM pages p
                                      LEFT JOIN words w ON p.id = w.page_id
                                      LEFT JOIN statistics s ON w.id = s.word_id
                             GROUP BY p.id
                             ORDER BY p.created_at DESC
                             ''').fetchall()
    return render_template_string(MANAGE_TEMPLATE, pages=pages)


@app.route('/create_page', methods=['POST'])
def create_page():
    page_name = request.form.get('page_name')
    with get_db() as conn:
        conn.execute('INSERT INTO pages (name) VALUES (?)', (page_name,))
        conn.commit()
    return redirect(url_for('manage'))


@app.route('/edit_page/<int:page_id>')
def edit_page(page_id):
    with get_db() as conn:
        page = conn.execute('SELECT * FROM pages WHERE id = ?', (page_id,)).fetchone()
        words = conn.execute('''
                             SELECT w.*,
                                    COALESCE(s.correct, 0)   as correct,
                                    COALESCE(s.incorrect, 0) as incorrect
                             FROM words w
                                      LEFT JOIN statistics s ON w.id = s.word_id
                             WHERE w.page_id = ?
                             ORDER BY w.id
                             ''', (page_id,)).fetchall()
    return render_template_string(EDIT_PAGE_TEMPLATE, page=page, words=words)


@app.route('/add_word/<int:page_id>', methods=['POST'])
def add_word(page_id):
    english = request.form.get('english')
    armenian = request.form.get('armenian')
    with get_db() as conn:
        cursor = conn.execute(
            'INSERT INTO words (page_id, english, armenian) VALUES (?, ?, ?)',
            (page_id, english, armenian)
        )
        word_id = cursor.lastrowid
        conn.execute('INSERT INTO statistics (word_id) VALUES (?)', (word_id,))
        conn.commit()
    return redirect(url_for('edit_page', page_id=page_id))


@app.route('/delete_word/<int:word_id>')
def delete_word(word_id):
    with get_db() as conn:
        page_id = conn.execute('SELECT page_id FROM words WHERE id = ?', (word_id,)).fetchone()['page_id']
        conn.execute('DELETE FROM words WHERE id = ?', (word_id,))
        conn.commit()
    return redirect(url_for('edit_page', page_id=page_id))


@app.route('/delete_page/<int:page_id>')
def delete_page(page_id):
    with get_db() as conn:
        conn.execute('DELETE FROM pages WHERE id = ?', (page_id,))
        conn.commit()
    return redirect(url_for('manage'))


@app.route('/study')
def study():
    session.clear()
    with get_db() as conn:
        pages = conn.execute('''
                             SELECT p.*, COUNT(w.id) as word_count
                             FROM pages p
                                      LEFT JOIN words w ON p.id = w.page_id
                             GROUP BY p.id
                             HAVING word_count > 0
                             ORDER BY p.name
                             ''').fetchall()
    return render_template_string(STUDY_SETUP_TEMPLATE, pages=pages)


@app.route('/study_session', methods=['POST'])
def study_session():
    direction = request.form.get('direction')
    method = request.form.get('method')
    mode = request.form.get('mode')
    page_ids = request.form.getlist('pages')

    with get_db() as conn:
        words = conn.execute('''
            SELECT w.*, 
                   COALESCE(s.correct, 0) as correct,
                   COALESCE(s.incorrect, 0) as incorrect
            FROM words w
            LEFT JOIN statistics s ON w.id = s.word_id
            WHERE w.page_id IN ({})
        '''.format(','.join('?' * len(page_ids))), page_ids).fetchall()

    words_list = [dict(w) for w in words]

    # Prepare word order based on mode
    if mode == 'smart':
        # Sort by mistake rate
        words_list.sort(key=lambda w: w['incorrect'] / (w['correct'] + w['incorrect'] + 1), reverse=True)
        word_order = [w['id'] for w in words_list]
    elif mode == 'session':
        word_order = [w['id'] for w in words_list]
        random.shuffle(word_order)
    else:  # random mode
        word_order = [w['id'] for w in words_list]

    # Store in session
    session['direction'] = direction
    session['method'] = method
    session['mode'] = mode
    session['words'] = words_list
    session['word_order'] = word_order
    session['current_index'] = 0
    session['stats'] = {'correct': 0, 'incorrect': 0, 'total': 0}
    session['checked'] = False
    session['revealed'] = False
    session['is_correct'] = False

    return redirect(url_for('study_word'))


@app.route('/study_word')
def study_word():
    if 'words' not in session:
        return redirect(url_for('study'))

    direction = session['direction']
    method = session['method']
    mode = session['mode']
    words_list = session['words']
    word_order = session['word_order']
    current_index = session['current_index']

    # Check if session complete
    if mode == 'session' and current_index >= len(word_order):
        session_stats = session['stats']
        if method == 'write' and session_stats['total'] > 0:
            session_stats['accuracy'] = round((session_stats['correct'] / session_stats['total']) * 100, 1)
        else:
            session_stats['accuracy'] = 0

        direction_text = "English → Armenian" if direction == 'en_to_am' else "Armenian → English"
        method_text = "Write" if method == 'write' else "Say"
        mode_text = {"smart": "Smart Mode", "random": "Random Mode", "session": "Session Mode"}[mode]

        return render_template_string(
            STUDY_SESSION_TEMPLATE,
            completed=True,
            session_stats=session_stats,
            direction=direction,
            method=method,
            mode=mode,
            direction_text=direction_text,
            method_text=method_text,
            mode_text=mode_text
        )

    # Get current word
    if mode == 'random':
        current_word_dict = random.choice(words_list)
    else:
        current_word_id = word_order[current_index]
        current_word_dict = next(w for w in words_list if w['id'] == current_word_id)

    # Prepare word display
    if direction == 'en_to_am':
        prompt = current_word_dict['english']
        answer = current_word_dict['armenian']
        direction_text = "English → Armenian"
    else:
        prompt = current_word_dict['armenian']
        answer = current_word_dict['english']
        direction_text = "Armenian → English"

    current_word = {
        'id': current_word_dict['id'],
        'prompt': prompt,
        'answer': answer
    }

    method_text = "Write" if method == 'write' else "Say"
    mode_text = {"smart": "Smart Mode", "random": "Random Mode", "session": "Session Mode"}[mode]

    progress = None
    if mode == 'session':
        progress = {'current': current_index + 1, 'total': len(word_order)}

    return render_template_string(
        STUDY_SESSION_TEMPLATE,
        completed=False,
        current_word=current_word,
        direction=direction,
        method=method,
        mode=mode,
        direction_text=direction_text,
        method_text=method_text,
        mode_text=mode_text,
        checked=session.get('checked', False),
        is_correct=session.get('is_correct', False),
        revealed=session.get('revealed', False),
        progress=progress
    )


@app.route('/study_action', methods=['POST'])
def study_action():
    if 'words' not in session:
        return redirect(url_for('study'))

    action = request.form.get('action')

    if action == 'check':
        answer = request.form.get('answer', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip()
        word_id = int(request.form.get('word_id'))

        is_correct = answer == correct_answer

        # Update statistics
        with get_db() as conn:
            if is_correct:
                conn.execute('UPDATE statistics SET correct = correct + 1, last_studied = ? WHERE word_id = ?',
                             (datetime.now(), word_id))
            else:
                conn.execute('UPDATE statistics SET incorrect = incorrect + 1, last_studied = ? WHERE word_id = ?',
                             (datetime.now(), word_id))
            conn.commit()

        session['stats']['total'] += 1
        if is_correct:
            session['stats']['correct'] += 1
        else:
            session['stats']['incorrect'] += 1

        session['checked'] = True
        session['is_correct'] = is_correct
        session.modified = True

        return redirect(url_for('study_word'))

    elif action == 'reveal':
        session['revealed'] = True
        session.modified = True
        return redirect(url_for('study_word'))

    elif action == 'next':
        # Move to next word
        if session['mode'] != 'random':
            session['current_index'] += 1

        session['checked'] = False
        session['revealed'] = False
        session['is_correct'] = False
        session.modified = True

        return redirect(url_for('study_word'))

    return redirect(url_for('study'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)