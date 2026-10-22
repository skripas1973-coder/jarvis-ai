import os
import sqlite3
from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from gigachat import GigaChat

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_family_chat'

giga = GigaChat(
    credentials=os.environ.get("GIGACHAT_CREDENTIALS", ""),
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2-Pro",
    verify_ssl_certs=False
)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Все поля обязательны'}), 400
    hashed_pw = generate_password_hash(password)
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({'success': 'Регистрация успешна'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Пользователь уже существует'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user[0], password):
        session['username'] = username
        return jsonify({'success': 'Вход выполнен'})
    else:
        return jsonify({'error': 'Неверное имя или пароль'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'success': 'Выход выполнен'})

@app.route('/api/history', methods=['GET'])
def history():
    if 'username' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE username = ? ORDER BY id ASC", (session['username'],))
    rows = c.fetchall()
    conn.close()
    
    history_list = [{'role': row[0], 'content': row[1]} for row in rows]
    return jsonify(history_list)

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
        
    data = request.json
    user_message = data.get('message', '')
    username = session['username']
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Сохраняем сообщение пользователя
    c.execute("INSERT INTO messages (username, role, content) VALUES (?, ?, ?)", (username, 'user', user_message))
    conn.commit()
    
    # Достаем последние 10 сообщений для контекста
    c.execute("SELECT role, content FROM messages WHERE username = ? ORDER BY id DESC LIMIT 10", (username,))
    recent = c.fetchall()
    conn.close()
    
    # Переворачиваем, чтобы было от старых к новым
    recent.reverse()
    messages_history = [{"role": "system", "content": "Ты — ДЖАРВИС (J.A.R.V.I.S.), ИИ Тони Старка. Ты должен ВСЕГДА обращаться к пользователю исключительно 'Сэр' (с большой буквы). Ты невероятно вежлив, используешь формальный стиль общения, но с легкой иронией. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать LaTeX, математические символы ($), звездочки (*) для выделения текста и Markdown. Пиши только чистым, естественным текстом, как в устной речи. Если тебя просят посчитать, пиши словами: '678 плюс 654 равно 1332, Сэр'."}]
    messages_history += [{"role": row[0], "content": row[1]} for row in recent]
    
    try:
        response = giga.chat({"messages": messages_history})
        ai_response = response.choices[0].message.content
        
        # Сохраняем ответ ИИ
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO messages (username, role, content) VALUES (?, ?, ?)", (username, 'assistant', ai_response))
        conn.commit()
        conn.close()
        
        return jsonify({'response': ai_response})
    except Exception as e:
        return jsonify({'response': f"Ошибка ИИ: {str(e)}"})

if __name__ == '__main__':
    print("==================================================")
    print("  AI-Трепач — Сервер запущен!")
    print("  Откройте: http://localhost:5000")
    print("==================================================")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
