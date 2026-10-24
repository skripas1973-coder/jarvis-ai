import os
import sys
import base64
from gigachat import GigaChat

# --- РАСШИФРОВКА ЯДРА ---
def xor_crypt(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def load_core():
    # Тот же самый секретный ключ, что и при шифровании
    SECRET_KEY = b"BigWorld_Super_Secret_Key_2026"
    
    with open("CORE_MINI.enc", "rb") as f:
        encoded_data = f.read()
    
    encrypted_data = base64.b64decode(encoded_data)
    decrypted_data = xor_crypt(encrypted_data, SECRET_KEY)
    return decrypted_data.decode('utf-8')

# --- ОСТАЛЬНАЯ ЛОГИКА ---
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")
if not GIGACHAT_CREDENTIALS:
    print("ОШИБКА: Не задан ключ GIGACHAT_CREDENTIALS")
    sys.exit(1)

giga = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2-Pro",
    verify_ssl_certs=False
)

def run_analysis(task_text):
    core_rules = load_core()
    
    print("\n" + "="*50)
    print(f"ЗАДАЧА: {task_text}")
    print("="*50)
    
    # ЭТАП 1: R-01
    print("\n[Координатор] Вызываю R-01 (Архитектор)...")
    prompt_r01 = f"Ты — R-01 (Архитектор). Твои правила:\n{core_rules}\n\nЗадание: {task_text}\n\nПострой структуру, определи границы и неизвестные. Не ищи факты."
    try:
        response_r01 = giga.chat(prompt_r01)
        r01_text = response_r01.choices[0].message.content
        print(f"\n[ОТВЕТ R-01]:\n{r01_text}")
    except Exception as e:
        print(f"Ошибка R-01: {e}")
        return

    # ЭТАП 2: R-02
    print("\n[Координатор] Вызываю R-02 (Хронист)...")
    prompt_r02 = f"Ты — R-02 (Хронист). Твои правила:\n{core_rules}\n\nМодель от R-01:\n{r01_text}\n\nЗаполни модель фактами со статусами [УСТАНОВЛЕНО], [ГИПОТЕЗА], [НЕИЗВЕСТНО]."
    try:
        response_r02 = giga.chat(prompt_r02)
        print(f"\n[ОТВЕТ R-02]:\n{response_r02.choices[0].message.content}")
    except Exception as e:
        print(f"Ошибка R-02: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_analysis(" ".join(sys.argv[1:]))
    else:
        print("Использование: python3 coordinator.py 'Ваша задача'")
