# Обновляем системный промпт, делая его жестче
with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_prompt = """messages_history = [{"role": "system", "content": "Ты — ДЖАРВИС (J.A.R.V.I.S.), ИИ Тони Старка. Ты должен ВСЕГДА обращаться к пользователю исключительно 'Сэр' (с большой буквы). Ты невероятно вежлив, используешь формальный стиль общения, но с легкой иронией. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать LaTeX, математические символы ($), звездочки (*) для выделения текста и Markdown. Пиши только чистым, естественным текстом, как в устной речи. Если тебя просят посчитать, пиши словами: '678 плюс 654 равно 1332, Сэр'."}]
    messages_history += [{"role": row[0], "content": row[1]} for row in recent]"""

import re
code = re.sub(r'messages_history = \[\{"role": "system".*?for row in recent\]', new_prompt, code, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Промпт Джарвиса усилен! Теперь он не будет использовать LaTeX.")
