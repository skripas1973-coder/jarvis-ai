import os
import sqlite3
import base64
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

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ЯДРОМ ---
def xor_crypt(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def load_core():
    try:
        SECRET_KEY = os.environ.get("CORE_SECRET_KEY", "BigWorld_Super_Secret_Key_2026").encode('utf-8')
        with open("CORE_MINI.enc", "rb") as f:
            encoded_data = f.read()
        encrypted_data = base64.b64decode(encoded_data)
        decrypted_data = xor_crypt(encrypted_data, SECRET_KEY)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"Ошибка загрузки Ядра: {e}")
        return "Ядро недоступно. Работаю в базовом режиме."

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT)''')
    c.commit()
    c.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username, password = data.get('username'), data.get('password')
    if not username or not password: return jsonify({'error': 'Все поля обязательны'}), 400
    hashed_pw = generate_password_hash(password)
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
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
    username, password = data.get('username'), data.get('password')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password, is_admin FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user[0], password):
        session['username'] = username
        is_admin = bool(user[1]) or (username.lower() in ["admin", "админ"])
        session['is_admin'] = is_admin
        return jsonify({'success': 'Вход выполнен', 'is_admin': is_admin})
    return jsonify({'error': 'Неверное имя или пароль'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': 'Выход выполнен'})

@app.route('/api/history', methods=['GET'])
def history():
    if 'username' not in session: return jsonify({'error': 'Не авторизован'}), 401
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE username = ? ORDER BY id ASC", (session['username'],))
    rows = c.fetchall()
    conn.close()
    return jsonify([{'role': r[0], 'content': r[1]} for r in rows])

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    if not session.get('is_admin'): return jsonify({'error': 'Доступ запрещен'}), 403
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/admin/delete_user', methods=['POST'])
def admin_delete_user():
    if not session.get('is_admin'): return jsonify({'error': 'Доступ запрещен'}), 403
    target = request.json.get('username')
    if target == session['username']: return jsonify({'error': 'Нельзя удалить себя'}), 400
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (target,))
    c.execute("DELETE FROM messages WHERE username = ?", (target,))
    conn.commit()
    conn.close()
    return jsonify({'success': 'Пользователь удален'})

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'username' not in session: return jsonify({'error': 'Не авторизован'}), 401
    
    data = request.json
    user_message = data.get('message', '')
    mode = data.get('mode', 'jarvis') # Получаем режим
    username = session['username']
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, role, content) VALUES (?, ?, ?)", (username, 'user', user_message))
    conn.commit()

    # --- РЕЖИМ АНАЛИТИКА (R-01 + R-02) ---
    if mode == 'analyst':
        core_rules = load_core()
        
        # R-01
        prompt_r01 = f"Ты — R-01 (Архитектор). Твои правила:\n{core_rules}\n\nЗадание: {user_message}\n\nПострой структуру, определи границы и неизвестные. Не ищи факты."
        try:
            res_r01 = giga.chat(prompt_r01)
            r01_text = res_r01.choices[0].message.content
        except Exception as e:
            return jsonify({'response': f"Ошибка R-01: {e}"})

        # R-02
        prompt_r02 = f"Ты — R-02 (Хронист). Твои правила:\n{core_rules}\n\nМодель от R-01:\n{r01_text}\n\nЗаполни модель фактами со статусами [УСТАНОВЛЕНО], [ГИПОТЕЗА], [НЕИЗВЕСТНО]."
        try:
            res_r02 = giga.chat(prompt_r02)
            ai_response = res_r02.choices[0].message.content
        except Exception as e:
            return jsonify({'response': f"Ошибка R-02: {e}"})

    # --- ОБЫЧНЫЙ РЕЖИМ (Джарвис) ---
    else:
        c.execute("SELECT role, content FROM messages WHERE username = ? ORDER BY id DESC LIMIT 10", (username,))
        recent = c.fetchall()
        recent.reverse()
        
        system_prompt = """Ты — ДЖАРВИС (J.A.R.V.I.S.), ИИ Тони Старка. Ты должен ВСЕГДА обращаться к пользователю исключительно 'Сэр' (с большой буквы). Ты невероятно вежлив, используешь формальный стиль общения, но с легкой иронией. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать LaTeX, математические символы ($), звездочки (*) для выделения текста и Markdown. Пиши только чистым, естественным текстом, как в устной речи."""
        
        messages_history = [{"role": "system", "content": system_prompt}]
        messages_history += [{"role": r[0], "content": r[1]} for r in recent]
        
        try:
            response = giga.chat({"messages": messages_history})
            ai_response = response.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                ai_response = "Прошу прощения, Сэр. Слишком много запросов. Подождите минуту."
            else:
                ai_response = f"Ошибка ИИ: {e}"

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, role, content) VALUES (?, ?, ?)", (username, 'assistant', ai_response))
    conn.commit()
    conn.close()
    
    return jsonify({'response': ai_response})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
