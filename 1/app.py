"""
AI-Трепач — Flask Backend
==========================
Запуск: python app.py
Требования: pip install flask

Этот файл содержит полный бэкенд для приложения AI-Трепач.
Использует SQLite для хранения пользователей и werkzeug для хэширования паролей.
"""

import os
import sqlite3
from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-trepach-secret-key-change-in-production')

# Database setup
DB_PATH = 'users.db'

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with users table."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()


# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve the main page."""
    return app.send_static_file('index.html')


@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user.
    POST /api/register
    Body: { "username": "string", "password": "string" }
    Returns: { "success": true/false, "error": "string" }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Неверный формат данных'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # Validation
    if not username or not password:
        return jsonify({'success': False, 'error': 'Заполните все поля'}), 400
    
    if len(username) < 3:
        return jsonify({'success': False, 'error': 'Имя пользователя должно быть не менее 3 символов'}), 400
    
    if len(password) < 4:
        return jsonify({'success': False, 'error': 'Пароль должен быть не менее 4 символов'}), 400
    
    # Check if user exists
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM users WHERE LOWER(username) = LOWER(?)', (username,)
    ).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'success': False, 'error': 'Пользователь с таким именем уже существует'}), 409
    
    # Create user with hashed password
    hashed_password = generate_password_hash(password)
    conn.execute(
        'INSERT INTO users (username, password) VALUES (?, ?)',
        (username, hashed_password)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Регистрация успешна!'}), 201


@app.route('/api/login', methods=['POST'])
def login():
    """
    Login user.
    POST /api/login
    Body: { "username": "string", "password": "string" }
    Returns: { "success": true/false, "error": "string" }
    Sets session cookie on success.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Неверный формат данных'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Заполните все поля'}), 400
    
    # Find user
    conn = get_db()
    user = conn.execute(
        'SELECT id, username, password FROM users WHERE LOWER(username) = LOWER(?)',
        (username,)
    ).fetchone()
    conn.close()
    
    if not user:
        return jsonify({'success': False, 'error': 'Пользователь не найден'}), 401
    
    # Verify password
    if not check_password_hash(user['password'], password):
        return jsonify({'success': False, 'error': 'Неверный пароль'}), 401
    
    # Set session
    session['user_id'] = user['id']
    session['username'] = user['username']
    
    return jsonify({
        'success': True,
        'message': 'Вход выполнен успешно!',
        'username': user['username']
    }), 200


@app.route('/api/logout', methods=['POST'])
def logout():
    """
    Logout user.
    POST /api/logout
    Clears session.
    """
    session.clear()
    return jsonify({'success': True, 'message': 'Вы вышли из аккаунта'}), 200


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat endpoint.
    POST /api/chat
    Body: { "message": "string" }
    Returns: { "success": true, "response": "string" }
    
    Note: Currently returns echo response. Will be replaced with AI integration.
    """
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
    
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({'success': False, 'error': 'Сообщение не найдено'}), 400
    
    user_message = data['message'].strip()
    
    if not user_message:
        return jsonify({'success': False, 'error': 'Пустое сообщение'}), 400
    
    # TODO: Replace with actual AI integration (OpenAI, etc.)
    # For now, return echo response
    bot_response = f"Я тебя услышал: \"{user_message}\""
    
    return jsonify({
        'success': True,
        'response': bot_response,
        'user': session['username']
    }), 200


@app.route('/api/me', methods=['GET'])
def me():
    """
    Get current user info.
    GET /api/me
    Returns: { "logged_in": true/false, "username": "string" }
    """
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'username': session['username']
        }), 200
    else:
        return jsonify({'logged_in': False}), 200


if __name__ == '__main__':
    print("=" * 50)
    print("  AI-Трепач — Сервер запущен!")
    print("  Откройте: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
