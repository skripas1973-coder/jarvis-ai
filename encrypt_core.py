import base64

def xor_crypt(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

# Твой секретный пароль для шифрования ядра
SECRET_KEY = b"BigWorld_Super_Secret_Key_2026"

# Читаем файл
with open("CORE_MINI.md", "rb") as f:
    core_data = f.read()

# Шифруем и кодируем в base64 (чтобы файл был текстовым, но нечитаемым)
encrypted_data = xor_crypt(core_data, SECRET_KEY)
encoded_data = base64.b64encode(encrypted_data)

# Сохраняем
with open("CORE_MINI.enc", "wb") as f:
    f.write(encoded_data)

print("Ядро успешно зашифровано в файл CORE_MINI.enc!")
print("Ключ шифрования зашит в скрипте. Никому его не показывай.")
