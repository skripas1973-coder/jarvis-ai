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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
    
    # Безопасная миграция: добавляем колонку is_admin, если её нет
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if 'is_admin' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        
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
        
        # Проверяем, есть ли уже пользователи (если нет — первый становится админом)
        c.execute("SELECT COUNT(*) FROM users")
        is_first = c.fetchone()[0] == 0
        is_admin = 1 if (is_first or username.lower() in ["admin", "админ"]) else 0
        
        c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", (username, hashed_pw, is_admin))
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
    c.execute("SELECT password, is_admin FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[0], password):
        session['username'] = username
        session['is_admin'] = bool(user[1])
        return jsonify({'success': 'Вход выполнен', 'is_admin': bool(user[1])})
    else:
        return jsonify({'error': 'Неверное имя или пароль'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
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

# --- АДМИНСКИЕ ЭНДПОИНТЫ ---
@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    if not session.get('is_admin'):
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/admin/delete_user', methods=['POST'])
def admin_delete_user():
    if not session.get('is_admin'):
        return jsonify({'error': 'Доступ запрещен'}), 403
        
    data = request.json
    target_user = data.get('username')
    
    if target_user == session['username']:
        return jsonify({'error': 'Нельзя удалить самого себя!'}), 400
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (target_user,))
    c.execute("DELETE FROM messages WHERE username = ?", (target_user,))
    conn.commit()
    conn.close()
    return jsonify({'success': 'Пользователь удален'})

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
        
    data = request.json
    user_message = data.get('message', '')
    username = session['username']
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, role, content) VALUES (?, ?, ?)", (username, 'user', user_message))
    conn.commit()
    
    c.execute("SELECT role, content FROM messages WHERE username = ? ORDER BY id DESC LIMIT 10", (username,))
    recent = c.fetchall()
    conn.close()
    
    recent.reverse()
    
    system_prompt = """Ты — ДЖАРВИС (J.A.R.V.I.S.), ИИ Тони Старка. Ты должен ВСЕГДА обращаться к пользователю исключительно 'Сэр' (с большой буквы). Ты невероятно вежлив, используешь формальный стиль общения, но с легкой иронией. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать LaTeX, математические символы ($), звездочки (*) для выделения текста и Markdown. Пиши только чистым, естественным текстом, как в устной речи."""
    
    messages_history = [{"role": "system", "content": system_prompt}]
    messages_history += [{"role": row[0], "content": row[1]} for row in recent]
    
    try:
        response = giga.chat({"messages": messages_history})
        ai_response = response.choices[0].message.content
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO messages (username, role, content) VALUES (?, ?, ?)", (username, 'assistant', ai_response))
        conn.commit()
        conn.close()
        
        return jsonify({'response': ai_response})
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "Too Many Requests" in err_str:
            return jsonify({'response': "Прошу прощения, Сэр. Я получил слишком много запросов за короткое время. Пожалуйста, подождите минуту и попробуйте снова."})
        return jsonify({'response': f"Ошибка ИИ: {err_str}"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
