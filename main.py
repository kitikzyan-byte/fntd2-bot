import os
import json
import threading
import random
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

app = Flask(__name__, template_folder="templates", static_folder="templates")

@app.route('/<path:filename>')
def serve_image(filename):
    templates_dir = os.path.join(app.root_path, 'templates')
    if os.path.exists(os.path.join(templates_dir, filename)):
        return send_from_directory(templates_dir, filename)
    return "File not found", 404

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

users_data = load_db()

def get_user(user_id):
    uid = str(user_id)
    if uid not in users_data:
        users_data[uid] = {"nick": "", "status": "none", "notifications": [], "last_chance": 0, "last_target": "", "last_bet": ""}
    return users_data[uid]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user_info/<user_id>', methods=['GET', 'POST'])
def user_info(user_id):
    user = get_user(user_id)
    if request.method == 'POST':
        data = request.json or {}
        if 'roblox_nick' in data:
            user["nick"] = data['roblox_nick']
            save_db(users_data)
        return jsonify({"status": "ok"})
    return jsonify(user)

@app.route('/api/submit_upgrade', methods=['POST'])
def submit_upgrade():
    data = request.json or {}
    user_id = str(data.get('user_id'))
    user = get_user(user_id)
    
    user["nick"] = data.get('roblox_nick', user["nick"])
    user["last_bet"] = data.get('bet_info', 'Ставка')
    user["last_target"] = data.get('target_info', 'Цель')
    user["last_chance"] = float(data.get('chance', 0))
    user["status"] = "pending"
    save_db(users_data)

    try:
        text = f'🔔 Пользователь "{user["nick"]}" хочет сделать апгрейд!\nСтавит: {user["last_bet"]}\nНа: {user["last_target"]}\nШанс: {user["last_chance"]}%'
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Принять", "callback_data": f"approve_{user_id}"},
                {"text": "❌ Отказать", "callback_data": f"reject_{user_id}"}
            ]]
        }
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": ADMIN_ID, "text": text, "reply_markup": keyboard
        }, timeout=5)
    except Exception as e:
        print("Ошибка:", e)
    
    return jsonify({"status": "sent"})

@app.route('/api/check_status/<user_id>', methods=['GET'])
def check_status(user_id):
    user = get_user(user_id)
    return jsonify({"status": user.get("status", "none")})

@app.route('/api/reset_status/<user_id>', methods=['POST'])
def reset_status(user_id):
    user = get_user(user_id)
    user["status"] = "none"
    save_db(users_data)
    return jsonify({"status": "reset"})

@app.route('/api/notifications/<user_id>', methods=['GET', 'POST'])
def handle_notifications(user_id):
    user = get_user(user_id)
    if request.method == 'POST':
        # Отметить все как прочитанные
        for n in user["notifications"]:
            n["read"] = True
        save_db(users_data)
        return jsonify({"status": "ok"})
    return jsonify({"notifications": user["notifications"]})


# --- TELEGRAM BOT ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎰 Открыть FNTD 2 UPGRADER", web_app=WebAppInfo(url=SERVER_URL))
    ]])
    await message.answer("Привет, улучшай своих юнитов!", reply_markup=kb)

@dp.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_") | F.data.startswith("sentprize_"))
async def callback_handler(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("У вас нет прав!", show_alert=True)

    data_parts = call.data.split("_")
    action = data_parts[0]
    user_id = data_parts[1]
    
    user = get_user(user_id)

    if action == "approve":
        # ЧЕСТНЫЙ РАНДОМ!
        roll = random.uniform(0, 100)
        is_win = roll <= user["last_chance"]
        
        if is_win:
            user["status"] = "approved_win"
            save_db(users_data)
            await call.message.edit_text(call.message.text + f"\n\n✅ СТАВКА ПРИНЯТА\n🎲 Выпало: {roll:.2f}%\n🎉 ИГРОК ВЫИГРАЛ!")
            
            # Отправляем сообщение админу о победе игрока
            win_text = f"🏆 Пользователь {user['nick']} ВЫИГРАЛ {user['last_target']}!"
            win_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Я отправил приз", callback_data=f"sentprize_{user_id}")
            ]])
            await bot.send_message(chat_id=ADMIN_ID, text=win_text, reply_markup=win_kb)

        else:
            user["status"] = "approved_lose"
            save_db(users_data)
            await call.message.edit_text(call.message.text + f"\n\n✅ СТАВКА ПРИНЯТА\n🎲 Выпало: {roll:.2f}%\n💀 Игрок проиграл.")

    elif action == "reject":
        user["status"] = "rejected"
        save_db(users_data)
        await call.message.edit_text(call.message.text + "\n\n❌ СТАВКА ОТКЛОНЕНА")

    elif action == "sentprize":
        # Админ отправил приз, добавляем уведомление игроку
        notif = {"id": random.randint(1000, 9999), "text": f"🎉 Администратор отправил вам {user['last_target']} по почте!", "read": False}
        user["notifications"].insert(0, notif)
        save_db(users_data)
        await call.message.edit_text(call.message.text + "\n\n✅ Уведомление отправлено игроку!")

    await call.answer()

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

import asyncio
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
           
