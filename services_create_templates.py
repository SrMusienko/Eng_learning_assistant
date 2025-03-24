from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
LOGIN_PATH = BASE_DIR / "templates" / "login.html"
REGISTER_PATH = BASE_DIR / "templates" / "register.html"
INDEX_PATH = BASE_DIR / "templates" / "index.html"
TEMPLATES_DIR = BASE_DIR / "templates"

def create_templates():
    # Создаем шаблон логина
    if not LOGIN_PATH.exists():
        login_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - English Learning Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f7f9;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .auth-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 30px;
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 24px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #555;
        }
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #45a049;
        }
        .links {
            text-align: center;
            margin-top: 20px;
        }
        .links a {
            color: #4CAF50;
            text-decoration: none;
        }
        .links a:hover {
            text-decoration: underline;
        }
        .error-message {
            color: #f44336;
            margin-bottom: 15px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <h1>Login</h1>
        {% if error %}
        <div class="error-message">{{ error }}</div>
        {% endif %}
        <form method="post" action="/login">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
        <div class="links">
            <p>Don't have an account? <a href="/register">Register</a></p>
        </div>
    </div>
</body>
</html>"""
        LOGIN_PATH.write_text(login_html)

    # Создаем шаблон регистрации
    if not REGISTER_PATH.exists():
        register_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - English Learning Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f7f9;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .auth-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 30px;
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 24px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #555;
        }
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #45a049;
        }
        .links {
            text-align: center;
            margin-top: 20px;
        }
        .links a {
            color: #4CAF50;
            text-decoration: none;
        }
        .links a:hover {
            text-decoration: underline;
        }
        .error-message {
            color: #f44336;
            margin-bottom: 15px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <h1>Register</h1>
        {% if error %}
        <div class="error-message">{{ error }}</div>
        {% endif %}
        <form method="post" action="/register">
            <div class="form-group">
                <label for="username">Name</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <div class="form-group">
                <label for="confirm_password">Confirm Password</label>
                <input type="password" id="confirm_password" name="confirm_password" required>
            </div>
            <button type="submit">Register</button>
        </form>
        <div class="links">
            <p>Already have an account? <a href="/login">Login</a></p>
        </div>
    </div>
</body>
</html>"""
        REGISTER_PATH.write_text(register_html)

def update_index_template():
    if INDEX_PATH.exists():
        index_content = INDEX_PATH.read_text()

        # Если файл уже содержит инфо о пользователе, не меняем его
        if "user-info" in index_content:
            return

        # Добавляем инфо о пользователе в header
        header_replacement = """<header class="header">
            <h1>English learning assistant</h1>
            <div class="user-info">
                <span id="username">Welcome, {{ username }}</span>
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
        </header>"""

        # Добавляем стили для user-info
        style_addition = """
        .user-info {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-left: auto;
        }
        .logout-btn {
            background-color: #f44336;
            color: white;
            padding: 6px 12px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 14px;
        }
        .logout-btn:hover {
            background-color: #d32f2f;
        }
        """

        # Заменяем header в шаблоне
        updated_content = index_content.replace('<header class="header">', header_replacement)

        # Добавляем стили
        head_end_pos = updated_content.find('</head>')
        if head_end_pos != -1:
            updated_content = updated_content[:head_end_pos] + f'<style>{style_addition}</style>' + updated_content[head_end_pos:]

        # Обновляем файл
        INDEX_PATH.write_text(updated_content)