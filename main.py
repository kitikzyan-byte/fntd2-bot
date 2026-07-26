import os
import json
import threading
import requests
from flask import Flask, render_template, request, jsonify, send_from_directory
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8653136894:AAHpu03Vx-ciIGfWdhlVFwzSCtMnWWkUcxw"
SERVER_URL = "https://fntd2-bot.onrender.com"
ADMIN_ID = 2092773964  # Твой Telegram ID
DB_FILE = "database.json"
# =============================================

# Указываем папки для шаблонов и статики
app = Flask(__name__, template_folder="templates", static_folder="templates")

# МАРШРУТ ДЛЯ АВТОМАТИЧЕСКОЙ ОТДАЧИ КАРТИНОК ИЗ ПАПКИ TEMPLATES
@app.route('/<path:filename>')
def serve_image(filename):
    # Если запрашивают картинку или файл, отдаем его из папки templates
    templates_dir = os.path.join(app.root_path, 'templates')
    if os.path.exists(os.path.join(templates_dir, filename)):
        return send_from_directory(templates_dir, filename)
    return "File not found", 404

# Загрузка базы данных
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

users_data = load_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user_info/<user_id>', methods=['GET', 'POST'])
def user_info(user_id):
    if user_id not in users_data:
        users_data[user_id] = {"nick": "", "bet": "", "status": "none"}
    
    if request.method == 'POST':
        data = request.json or {}
        if 'roblox_nick' in data:
            users_data[user_id]["nick"] = data['roblox_nick']
            save_db(users_data)
        return jsonify({"status": "ok"})
        
    return jsonify(users_data[user_id])

@app.route('/api/submit_upgrade', methods=['POST'])
def submit_upgrade():
    data = request.json or {}
    user_id = str(data.get('user_id'))
    roblox_nick = data.get('roblox_nick', 'Неизвестно')
    bet_info = data.get('bet_info', 'Ставка')
    
    if user_id not in users_data:
        users_data[user_id] = {}
    users_data[user_id]["nick"] = roblox_nick
    users_data[user_id]["bet"] = bet_info
    users_data[user_id]["status"] = "pending"
    save_db(users_data)

    try:
        text = f'🔔 Пользователь "{roblox_nick}" отправил вам по почте "{bet_info}"!'
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Принять", "callback_data": f"approve_{user_id}"},
                {"text": "❌ Отказать", "callback_data": f"reject_{user_id}"}
            ]]
        }
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": ADMIN_ID,
            "text": text,
            "reply_markup": keyboard
        }, timeout=5)
    except Exception as e:
        print("Ошибка отправки админу:", e)
    
    return jsonify({"status": "sent"})

@app.route('/api/check_status/<user_id>', methods=['GET'])
def check_status(user_id):
    user = users_data.get(str(user_id), {"status": "none"})
    return jsonify({"status": user.get("status")})

@app.route('/api/reset_status/<user_id>', methods=['POST'])
def reset_status(user_id):
    if str(user_id) in users_data:
        users_data[str(user_id)]["status"] = "none"
        save_db(users_data)
    return jsonify({"status": "reset"})


# --- TELEGRAM BOT ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎰 Открыть FNTD 2 UPGRADER", web_app=WebAppInfo(url=SERVER_URL))
    ]])
    await message.answer("Привет, улучшай своих юнитов в FNTD 2 UPGRADER!", reply_markup=kb)

@dp.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def callback_handler(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("У вас нет прав!", show_alert=True)
        return

    action, user_id = call.data.split("_")
    
    if user_id in users_data:
        if action == "approve":
            users_data[user_id]["status"] = "approved"
            save_db(users_data)
            await call.message.edit_text(call.message.text + "\n\n✅ СТАВКА ПРИНЯТА")
        else:
            users_data[user_id]["status"] = "rejected"
            save_db(users_data)
            await call.message.edit_text(call.message.text + "\n\n❌ СТАВКА ОТКЛОНЕНА")
    
    await call.answer()

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

import asyncio

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    print("Бот и сервер запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
