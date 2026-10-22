import os
from gigachat import GigaChat

key = os.environ.get("GIGACHAT_CREDENTIALS", "")

print("Проверяю подключение к GigaChat...")
try:
    giga = GigaChat(
        credentials=key,
        scope="GIGACHAT_API_PERS",
        model="GigaChat-2-Pro",
        verify_ssl_certs=False
    )
    response = giga.chat("Привет! Ты работаешь?")
    print("\n[УСПЕХ] Ответ от ИИ:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"\n[ОШИБКА] {type(e).__name__}: {e}")
