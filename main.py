import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Токен твоего бота и твой Telegram ID (куда присылать уведомления)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ТВОЙ_ТОКЕН_БОТА")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "ТВОЙ_TELEGRAM_ID")

# Временная база данных в памяти (для продакшна лучше заменить на SQLite/Postgres)
users_db = {}
pending_upgrades = {}

def send_telegram_message(chat_id, text):
    if not chat_id or chat_id == "ТВОЙ_TELEGRAM_ID":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print("Telegram API Error:", e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user_info/<user_id>', methods=['GET', 'POST'])
def user_info(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            "roblox_nick": "",
            "status": "waiting_approval", # waiting_approval, approved, rejected
            "last_bet": ""
        }
    
    if request.method == 'POST':
        data = request.json
        if 'roblox_nick' in data:
            users_db[user_id]["roblox_nick"] = data['roblox_nick']
        return jsonify({"status": "success"})
        
    return jsonify(users_db[user_id])

@app.route('/api/submit_upgrade', methods=['POST'])
def submit_upgrade():
    data = request.json
    user_id = str(data.get('user_id'))
    roblox_nick = data.get('roblox_nick', 'Неизвестно')
    bet_info = data.get('bet_info', 'Ставка')
    
    users_db[user_id] = users_db.get(user_id, {})
    users_db[user_id]["roblox_nick"] = roblox_nick
    users_db[user_id]["last_bet"] = bet_info
    users_db[user_id]["status"] = "pending"

    # Отправляем тебе уведомление в Telegram
    msg = f'🔔 Новая ставка на апгрейд!\nПользователь "{roblox_nick}" отправил вам "{bet_info}".\n\nПодтвердите или отклоните в панели управления.'
    send_telegram_message(ADMIN_CHAT_ID, msg)
    
    return jsonify({"status": "sent"})

@app.route('/api/check_status/<user_id>', methods=['GET'])
def check_status(user_id):
    user = users_db.get(str(user_id), {"status": "none"})
    return jsonify({"status": user.get("status")})

@app.route('/api/reset_status/<user_id>', methods=['POST'])
def reset_status(user_id):
    if str(user_id) in users_db:
        users_db[str(user_id)]["status"] = "none"
    return jsonify({"status": "reset"})

# Пример эндпоинта для тебя (админа), чтобы подтвердить ставку через браузер или скрипт: /api/admin/approve/<user_id>
@app.route('/api/admin/approve/<user_id>', methods=['GET'])
def admin_approve(user_id):
    if str(user_id) in users_db:
        users_db[str(user_id)]["status"] = "approved"
        return f"Ставка для пользователя {user_id} подтверждена! Теперь у него начнется апгрейд."
    return "Пользователь не найден", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
