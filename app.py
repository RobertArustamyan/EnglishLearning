from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import random
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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


def parse_word_file(filepath):
    """Parse uploaded text file and return list of word pairs"""
    words = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '-' in line:
                parts = line.split('-', 1)
                if len(parts) == 2:
                    english = parts[0].strip()
                    armenian = parts[1].strip()
                    words.append((english, armenian))
    return words


# HTML Templates
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Vocabulary Study</title>
    <meta charset="UTF-8">
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
    <meta charset="UTF-8">
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
        input[type="file"] {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
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
        .info-box {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin: 15px 0;
            font-size: 14px;
            color: #1976d2;
        }
        .info-box code {
            background: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Back to Home</a>
        <h1>Manage Pages</h1>

        <h2>Upload Word File</h2>
        <div class="info-box">
            <strong>File Format:</strong> Upload .txt files (UTF-8 encoded) with format:<br>
            <code>english_word-armenian_word</code><br>
            For synonyms: <code>word1,word2-translation</code><br>
            File name becomes page name (e.g., <code>1.txt</code> → "Page 1")
        </div>
        <form method="POST" action="/upload_file" enctype="multipart/form-data">
            <div class="form-group">
                <input type="file" name="files" accept=".txt" multiple required>
                <button type="submit" class="btn-primary">Upload & Create Page</button>
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
                    <button class="btn-secondary" onclick="location.href='/view_page/{{ page.id }}'">View Words</button>
                    <form method="POST" action="/reupload_page/{{ page.id }}" enctype="multipart/form-data" style="display:inline;">
                        <input type="file" name="file" accept=".txt" id="file_{{ page.id }}" style="display:none;" onchange="this.form.submit()">
                        <button type="button" class="btn-secondary" onclick="document.getElementById('file_{{ page.id }}').click()">Re-upload</button>
                    </form>
                    <button class="btn-danger" onclick="if(confirm('Delete this page?')) location.href='/delete_page/{{ page.id }}'">Delete</button>
                </div>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p>No pages yet. Upload your first file above.</p>
        {% endif %}
    </div>
</body>
</html>
'''

VIEW_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>View Page: {{ page.name }}</title>
    <meta charset="UTF-8">
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
        <h1>{{ page.name }}</h1>

        <h2>Words in this Page ({{ words|length }})</h2>
        {% if words %}
        <table>
            <thead>
                <tr>
                    <th>English</th>
                    <th>Armenian</th>
                    <th>Statistics</th>
                </tr>
            </thead>
            <tbody>
                {% for word in words %}
                <tr>
                    <td>{{ word.english }}</td>
                    <td>{{ word.armenian }}</td>
                    <td>✓{{ word.correct }} / ✗{{ word.incorrect }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No words in this page.</p>
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
    <meta charset="UTF-8">
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
                        <p class="error">No pages available. Please upload files first.</p>
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
    <meta charset="UTF-8">
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
        .revealed-answer {
            font-size: 36px;
            color: #4CAF50;
            margin: 20px 0;
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
        .btn-reveal { background: #FF9800; }
        .btn-reveal:hover { background: #F57C00; }
        .btn-next { background: #4CAF50; }
        .btn-next:hover { background: #45a049; }
        .btn-end { background: #f44336; }
        .btn-end:hover { background: #da190b; }
        .btn-skip { background: #9E9E9E; }
        .btn-skip:hover { background: #757575; }
        .btn-wrong { background: #f44336; }
        .btn-wrong:hover { background: #da190b; }
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
        .synonym-inputs {
            margin: 30px 0;
        }
        .synonym-field {
            margin: 20px 0;
        }
        .input-row {
            display: flex;
            gap: 10px;
            justify-content: center;
            align-items: center;
        }
        .synonym-input {
            padding: 12px;
            font-size: 20px;
            border: 2px solid #ddd;
            border-radius: 6px;
            width: 300px;
            text-align: center;
        }
        .answer-placeholder {
        min-height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 30px 0;
        }
        .synonym-input:disabled {
            background: #f5f5f5;
        }
        .btn-hint {
            background: #9C27B0;
            padding: 12px 20px;
            font-size: 16px;
        }
        .btn-hint:hover {
            background: #7B1FA2;
        }
        .btn-check-field {
            background: #2196F3;
            padding: 12px 30px;
            font-size: 16px;
        }
        .btn-check-field:hover {
            background: #0b7dda;
        }
        .btn-check-field:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .field-feedback {
            margin-top: 10px;
            text-align: center;
            font-size: 18px;
        }
        .correct-mark {
            color: #2E7D32;
            font-weight: bold;
        }
        .incorrect-mark {
            color: #C62828;
            font-weight: bold;
        }
        .user-answer {
            color: #666;
            font-size: 16px;
            margin-top: 5px;
        }
        .correct-answer {
            font-size: 16px;
            color: #4CAF50;
            margin-top: 5px;
            font-weight: bold;
        }
        .wrong-words-section {
            margin-top: 30px;
            padding: 20px;
            background: #ffebee;
            border-radius: 6px;
        }
        .wrong-words-section h3 {
            color: #c62828;
            margin-bottom: 15px;
        }
        .wrong-word-item {
            background: white;
            padding: 10px;
            margin: 8px 0;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .wrong-word-item .word {
            font-weight: bold;
        }
        .wrong-word-item .translation {
            color: #666;
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
                <p><strong>Correct:</strong> {{ session_stats.correct }}</p>
                <p><strong>Incorrect:</strong> {{ session_stats.incorrect }}</p>
                <p><strong>Accuracy:</strong> {{ session_stats.accuracy }}%</p>
            </div>

            {% if wrong_words %}
            <div class="wrong-words-section">
                <h3>Words You Got Wrong ({{ wrong_words|length }})</h3>
                {% for word in wrong_words %}
                <div class="wrong-word-item">
                    <span class="word">{{ word.prompt }}</span>
                    <span class="translation">→ {{ word.answer }}</span>
                </div>
                {% endfor %}
            </div>
            {% endif %}

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
                {% if not all_revealed %}
                    <div class="synonym-inputs">
                        {% for i in range(current_word.answer_count) %}
                        <div class="synonym-field" id="field_{{ i }}">
                            <div class="input-row">
                                <input type="text" 
                                       class="synonym-input" 
                                       id="input_{{ i }}" 
                                       placeholder="Synonym {{ i + 1 }}" 
                                       autocomplete="off"
                                       {% if session.get('field_' ~ i ~ '_checked') %}disabled{% endif %}>
                                <button type="button" class="btn-hint" onclick="showHint({{ i }})">Hint</button>
                                <button type="button" 
                                        class="btn-check-field" 
                                        onclick="checkField({{ i }})"
                                        {% if session.get('field_' ~ i ~ '_checked') %}disabled{% endif %}>Check</button>
                            </div>
                            <div class="field-feedback" id="feedback_{{ i }}">
                                {% if session.get('field_' ~ i ~ '_checked') %}
                                    {% if session.get('field_' ~ i ~ '_correct') %}
                                        <span class="correct-mark">✓ Correct!</span>
                                    {% else %}
                                        <span class="incorrect-mark">✗ Wrong</span>
                                        <div class="user-answer">Your answer: {{ session.get('field_' ~ i ~ '_user_answer') }}</div>
                                    {% endif %}
                                {% endif %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>

                    <div class="btn-group">
                        <button type="button" class="btn-reveal" onclick="revealAnswers()">Reveal All Answers</button>
                        <button type="button" class="btn-skip" onclick="document.getElementById('skipForm').submit()">Skip</button>
                    </div>
                    <form id="skipForm" method="POST" action="/study_action" style="display:none;">
                        <input type="hidden" name="action" value="skip">
                    </form>
                {% else %}
                    <div class="revealed-answer">
                        {{ current_word.display_answer }}
                    </div>
                    <form method="POST" action="/study_action">
                        <input type="hidden" name="action" value="next">
                        <div class="btn-group">
                            <button type="submit" class="btn-next">Next Word</button>
                        </div>
                    </form>
                {% endif %}

                <script>
                    const correctAnswers = {{ current_word.answer_list | tojson }};
                    const wordId = {{ current_word.id }};
                    const usedAnswers = new Set();

                    function showHint(fieldIndex) {
                        const input = document.getElementById('input_' + fieldIndex);

                        // Find an unused answer for the hint
                        let hintAnswer = null;
                        for (let answer of correctAnswers) {
                            if (!usedAnswers.has(answer.toLowerCase())) {
                                hintAnswer = answer;
                                usedAnswers.add(answer.toLowerCase());
                                break;
                            }
                        }

                        if (hintAnswer) {
                            const firstLetter = hintAnswer.charAt(0);
                            input.value = firstLetter;
                            input.focus();
                        } else {
                            alert('All hints have been used!');
                        }
                    }

                    function checkField(fieldIndex) {
                        const input = document.getElementById('input_' + fieldIndex);
                        const userAnswer = input.value.trim();

                        if (!userAnswer) {
                            alert('Please enter an answer first');
                            return;
                        }

                        // Check if answer matches ANY correct answer (case-insensitive)
                        let isCorrect = false;
                        let matchedAnswer = '';
                        for (let answer of correctAnswers) {
                            if (answer.toLowerCase() === userAnswer.toLowerCase()) {
                                isCorrect = true;
                                matchedAnswer = answer;
                                usedAnswers.add(answer.toLowerCase());
                                break;
                            }
                        }

                        // Disable input and button immediately
                        input.disabled = true;
                        document.querySelector('#field_' + fieldIndex + ' .btn-check-field').disabled = true;
                        document.querySelector('#field_' + fieldIndex + ' .btn-hint').disabled = true;

                        // Show feedback immediately
                        const feedbackDiv = document.getElementById('feedback_' + fieldIndex);
                        if (isCorrect) {
                            feedbackDiv.innerHTML = '<span class="correct-mark">✓ Correct! (' + matchedAnswer + ')</span>';
                        } else {
                            feedbackDiv.innerHTML = '<span class="incorrect-mark">✗ Wrong</span><div class="user-answer">Your answer: ' + userAnswer + '</div><div class="correct-answer">Any of: ' + correctAnswers.join(', ') + '</div>';
                        }

                        // Send to server (no reload)
                        fetch('/check_field', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/x-www-form-urlencoded',
                            },
                            body: 'field_index=' + fieldIndex + '&user_answer=' + encodeURIComponent(userAnswer) + '&is_correct=' + isCorrect + '&word_id=' + wordId
                        });
                    }

                    function revealAnswers() {
                        // Show all answers in their respective fields
                        correctAnswers.forEach((answer, index) => {
                            const input = document.getElementById('input_' + index);
                            const feedbackDiv = document.getElementById('feedback_' + index);

                            if (input && feedbackDiv) {
                                input.disabled = true;
                                input.value = answer;
                                const checkBtn = document.querySelector('#field_' + index + ' .btn-check-field');
                                const hintBtn = document.querySelector('#field_' + index + ' .btn-hint');
                                if (checkBtn) checkBtn.disabled = true;
                                if (hintBtn) hintBtn.disabled = true;
                                feedbackDiv.innerHTML = '<span class="correct-mark">Answer: ' + answer + '</span>';
                            }
                        });

                        // Send to server and skip to next word
                        fetch('/reveal_all', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/x-www-form-urlencoded',
                            },
                            body: 'word_id=' + wordId
                        }).then(() => {
                            setTimeout(() => {
                                document.getElementById('skipForm').submit();
                            }, 1500);
                        });
                    }
                </script>
            {% else %}
                <form method="POST" action="/study_action" id="mainForm">
                    <div class="answer-placeholder">
                        {% if revealed %}
                        <div class="revealed-answer">
                            {{ current_word.display_answer }}
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if not revealed %}
                        <input type="hidden" name="action" value="reveal">
                        <input type="hidden" name="word_id" value="{{ current_word.id }}">
                        <div class="btn-group">
                            <button type="submit" class="btn-reveal">Reveal Answer</button>
                            <button type="button" class="btn-skip" onclick="document.getElementById('skipForm').submit()">Skip</button>
                        </div>
                    {% else %}
                        <div class="btn-group">
                            <button type="submit" name="action" value="next" class="btn-next">✓ Correct (Next)</button>
                            <button type="submit" name="action" value="mark_wrong" class="btn-wrong">✗ Wrong</button>
                        </div>
                    {% endif %}
                </form>
                <form id="skipForm" method="POST" action="/study_action" style="display:none;">
                    <input type="hidden" name="action" value="skip">
                </form>
            {% endif %}

        </div>

        {% if progress %}
        <div class="progress">
            Progress: {{ progress.current }} / {{ progress.total }}
        </div>
        {% endif %}

        <div class="btn-group">
            <button class="btn-end" onclick="if(confirm('End session?')) location.href='/end_session'">End Session</button>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''


def parse_synonyms(text):
    """Parse comma-separated synonyms and return list"""
    return [s.strip() for s in text.split(',')]


# Routes
@app.route('/')
def index():
    return render_template_string(HOME_TEMPLATE)


@app.route('/end_session')
def end_session():
    """End the current session and show statistics"""
    if 'words' not in session:
        return redirect(url_for('study'))

    direction = session.get('direction')
    method = session.get('method')
    mode = session.get('mode')

    session_stats = session.get('stats', {'correct': 0, 'incorrect': 0, 'total': 0})
    if session_stats['total'] > 0:
        session_stats['accuracy'] = round((session_stats['correct'] / session_stats['total']) * 100, 1)
    else:
        session_stats['accuracy'] = 0

    wrong_words = session.get('wrong_words', [])

    direction_text = "English → Armenian" if direction == 'en_to_am' else "Armenian → English"
    method_text = "Write" if method == 'write' else "Say"
    mode_text = {"smart": "Smart Mode", "random": "Random Mode", "session": "Session Mode"}.get(mode, "Unknown")

    return render_template_string(
        STUDY_SESSION_TEMPLATE,
        completed=True,
        session_stats=session_stats,
        wrong_words=wrong_words,
        direction=direction,
        method=method,
        mode=mode,
        direction_text=direction_text,
        method_text=method_text,
        mode_text=mode_text
    )
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


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return redirect(url_for('manage'))

    files = request.files.getlist('files')

    for file in files:
        if file.filename == '' or not file.filename.endswith('.txt'):
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract page name from filename
        page_name = filename.replace('.txt', '')
        if page_name.isdigit():
            page_name = f"Page {page_name}"
        else:
            page_name = page_name.replace('_', ' ').title()

        # Parse file and add to database
        words = parse_word_file(filepath)

        with get_db() as conn:
            cursor = conn.execute('INSERT INTO pages (name) VALUES (?)', (page_name,))
            page_id = cursor.lastrowid

            for english, armenian in words:
                cursor = conn.execute(
                    'INSERT INTO words (page_id, english, armenian) VALUES (?, ?, ?)',
                    (page_id, english, armenian)
                )
                word_id = cursor.lastrowid
                conn.execute('INSERT INTO statistics (word_id) VALUES (?)', (word_id,))
            conn.commit()

        os.remove(filepath)

    return redirect(url_for('manage'))


@app.route('/reupload_page/<int:page_id>', methods=['POST'])
def reupload_page(page_id):
    if 'file' not in request.files:
        return redirect(url_for('manage'))

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.txt'):
        return redirect(url_for('manage'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    words = parse_word_file(filepath)

    with get_db() as conn:
        conn.execute('DELETE FROM words WHERE page_id = ?', (page_id,))

        for english, armenian in words:
            cursor = conn.execute(
                'INSERT INTO words (page_id, english, armenian) VALUES (?, ?, ?)',
                (page_id, english, armenian)
            )
            word_id = cursor.lastrowid
            conn.execute('INSERT INTO statistics (word_id) VALUES (?)', (word_id,))
        conn.commit()

    os.remove(filepath)
    return redirect(url_for('manage'))


@app.route('/view_page/<int:page_id>')
def view_page(page_id):
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
    return render_template_string(VIEW_PAGE_TEMPLATE, page=page, words=words)


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

    if mode == 'smart':
        words_list.sort(key=lambda w: w['incorrect'] / (w['correct'] + w['incorrect'] + 1), reverse=True)
        word_order = [w['id'] for w in words_list]
    elif mode == 'session':
        word_order = [w['id'] for w in words_list]
        random.shuffle(word_order)
    else:
        word_order = [w['id'] for w in words_list]

    session['direction'] = direction
    session['method'] = method
    session['mode'] = mode
    session['words'] = words_list
    session['word_order'] = word_order
    session['current_index'] = 0
    session['stats'] = {'correct': 0, 'incorrect': 0, 'total': 0}
    session['wrong_words'] = []
    session['checked'] = False
    session['revealed'] = False
    session['all_revealed'] = False
    session['is_correct'] = False
    session['current_word_id'] = None

    return redirect(url_for('study_word'))


@app.route('/check_field', methods=['POST'])
def check_field():
    field_index = int(request.form.get('field_index'))
    user_answer = request.form.get('user_answer')
    is_correct = request.form.get('is_correct') == 'true'
    word_id = int(request.form.get('word_id'))

    session[f'field_{field_index}_checked'] = True
    session[f'field_{field_index}_correct'] = is_correct
    session[f'field_{field_index}_user_answer'] = user_answer
    session.modified = True

    if not session.get('word_stats_updated'):
        words_list = session['words']
        current_word_dict = next(w for w in words_list if w['id'] == word_id)

        direction = session['direction']
        if direction == 'en_to_am':
            answer_list = parse_synonyms(current_word_dict['armenian'])
        else:
            answer_list = parse_synonyms(current_word_dict['english'])

        all_checked = all(session.get(f'field_{i}_checked') for i in range(len(answer_list)))

        if all_checked:
            all_correct = all(session.get(f'field_{i}_correct') for i in range(len(answer_list)))

            with get_db() as conn:
                if all_correct:
                    conn.execute('UPDATE statistics SET correct = correct + 1, last_studied = ? WHERE word_id = ?',
                                 (datetime.now(), word_id))
                    session['stats']['correct'] += 1
                else:
                    conn.execute('UPDATE statistics SET incorrect = incorrect + 1, last_studied = ? WHERE word_id = ?',
                                 (datetime.now(), word_id))
                    session['stats']['incorrect'] += 1

                    # Track wrong word
                    prompt = current_word_dict['english'] if direction == 'en_to_am' else current_word_dict['armenian']
                    answer = current_word_dict['armenian'] if direction == 'en_to_am' else current_word_dict['english']
                    session['wrong_words'].append({'prompt': prompt, 'answer': answer})

                conn.commit()

            session['stats']['total'] += 1
            session['word_stats_updated'] = True
            session.modified = True

    return '', 204


@app.route('/reveal_all', methods=['POST'])
def reveal_all():
    word_id = int(request.form.get('word_id'))

    session['all_revealed'] = True

    if not session.get('word_stats_updated'):
        with get_db() as conn:
            conn.execute('UPDATE statistics SET incorrect = incorrect + 1, last_studied = ? WHERE word_id = ?',
                         (datetime.now(), word_id))
            conn.commit()

        session['stats']['incorrect'] += 1
        session['stats']['total'] += 1
        session['word_stats_updated'] = True

        # Track wrong word
        words_list = session['words']
        current_word_dict = next(w for w in words_list if w['id'] == word_id)
        direction = session['direction']
        prompt = current_word_dict['english'] if direction == 'en_to_am' else current_word_dict['armenian']
        answer = current_word_dict['armenian'] if direction == 'en_to_am' else current_word_dict['english']
        session['wrong_words'].append({'prompt': prompt, 'answer': answer})

    session.modified = True
    return '', 204


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

    if mode == 'session' and current_index >= len(word_order):
        session_stats = session['stats']
        if session_stats['total'] > 0:
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
            wrong_words=session.get('wrong_words', []),
            direction=direction,
            method=method,
            mode=mode,
            direction_text=direction_text,
            method_text=method_text,
            mode_text=mode_text
        )

    if session.get('current_word_id'):
        current_word_id = session['current_word_id']
        current_word_dict = next(w for w in words_list if w['id'] == current_word_id)
    elif mode == 'random':
        current_word_dict = random.choice(words_list)
    else:
        current_word_id = word_order[current_index]
        current_word_dict = next(w for w in words_list if w['id'] == current_word_id)

    if direction == 'en_to_am':
        prompt = current_word_dict['english']
        answer_list = parse_synonyms(current_word_dict['armenian'])
        display_answer = current_word_dict['armenian']
        direction_text = "English → Armenian"
    else:
        prompt = current_word_dict['armenian']
        answer_list = parse_synonyms(current_word_dict['english'])
        display_answer = current_word_dict['english']
        direction_text = "Armenian → English"

    current_word = {
        'id': current_word_dict['id'],
        'prompt': prompt,
        'correct_answers': '|||'.join(answer_list),
        'display_answer': display_answer,
        'answer_count': len(answer_list),
        'answer_list': answer_list
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
        all_revealed=session.get('all_revealed', False),
        progress=progress,
        user_answer=session.get('user_answer', '')
    )


@app.route('/study_action', methods=['POST'])
def study_action():
    if 'words' not in session:
        return redirect(url_for('study'))

    action = request.form.get('action')

    if action == 'reveal':
        word_id = request.form.get('word_id')
        if word_id:
            session['current_word_id'] = int(word_id)
        session['revealed'] = True
        session.modified = True
        return redirect(url_for('study_word'))

    elif action == 'mark_wrong':
        # Mark as wrong for "say" method
        if session.get('current_word_id') and not session.get('word_stats_updated'):
            word_id = session['current_word_id']
            with get_db() as conn:
                conn.execute('UPDATE statistics SET incorrect = incorrect + 1, last_studied = ? WHERE word_id = ?',
                             (datetime.now(), word_id))
                conn.commit()

            session['stats']['incorrect'] += 1
            session['stats']['total'] += 1

            # Track wrong word
            words_list = session['words']
            current_word_dict = next(w for w in words_list if w['id'] == word_id)
            direction = session['direction']
            prompt = current_word_dict['english'] if direction == 'en_to_am' else current_word_dict['armenian']
            answer = current_word_dict['armenian'] if direction == 'en_to_am' else current_word_dict['english']
            session['wrong_words'].append({'prompt': prompt, 'answer': answer})

            session['word_stats_updated'] = True

        # Move to next word
        session['current_word_id'] = None
        if session['mode'] != 'random':
            session['current_index'] += 1
        session['checked'] = False
        session['revealed'] = False
        session['is_correct'] = False
        session.pop('word_stats_updated', None)
        session.modified = True
        return redirect(url_for('study_word'))

    elif action == 'skip':
        session['current_word_id'] = None

        for key in list(session.keys()):
            if key.startswith('field_'):
                session.pop(key)
        session.pop('word_stats_updated', None)
        session.pop('all_revealed', None)

        if session['mode'] != 'random':
            session['current_index'] += 1

        session['checked'] = False
        session['revealed'] = False
        session['is_correct'] = False
        session.modified = True
        return redirect(url_for('study_word'))

    elif action == 'next':
        # For "say" method - mark as correct if not already updated
        if session.get('current_word_id') and not session.get('word_stats_updated'):
            word_id = session['current_word_id']
            with get_db() as conn:
                conn.execute('UPDATE statistics SET correct = correct + 1, last_studied = ? WHERE word_id = ?',
                             (datetime.now(), word_id))
                conn.commit()

            session['stats']['correct'] += 1
            session['stats']['total'] += 1
            session['word_stats_updated'] = True

        session['current_word_id'] = None

        for key in list(session.keys()):
            if key.startswith('field_'):
                session.pop(key)
        session.pop('word_stats_updated', None)
        session.pop('all_revealed', None)

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