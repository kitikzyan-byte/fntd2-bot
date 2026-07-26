import os
import sqlite3
import asyncio
import threading
from flask import Flask, render_template, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8653136894:AAHpu03Vx-ciIGfWdhlVFwzSCtMnWWkUcxw"
SERVER_URL = "https://fntd2-bot.onrender.com"
ADMIN_ID = 2092773964  # Твой Telegram ID
# =============================================

DB_NAME = "database.db"
app = Flask(__name__, template_folder="templates")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, roblox_nick TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS pending_prizes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, prize_name TEXT, status TEXT DEFAULT 'pending')''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user_info/<int:user_id>', methods=['GET', 'POST'])
def user_info(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json or {}
        nick = data.get('roblox_nick', '')
        cursor.execute('INSERT OR REPLACE INTO users (user_id, roblox_nick) VALUES (?, ?)', (user_id, nick))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    cursor.execute('SELECT roblox_nick FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    cursor.execute('SELECT id, prize_name FROM pending_prizes WHERE user_id = ? AND status = "delivered"', (user_id,))
    delivered_prize = cursor.fetchone()
    conn.close()
    return jsonify({
        "roblox_nick": row[0] if row else "",
        "delivered_prize": {"id": delivered_prize[0], "name": delivered_prize[1]} if delivered_prize else None
    })

@app.route('/api/claim_prize_notification', methods=['POST'])
def claim_prize_notification():
    data = request.json or {}
    prize_id = data.get('prize_id')
    if prize_id:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pending_prizes WHERE id = ?', (prize_id,))
        conn.commit()
        conn.close()
    return jsonify({"status": "ok"})

# --- TELEGRAM BOT ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎰 Открыть FNTD 2 Upgrader", web_app=WebAppInfo(url=SERVER_URL))
    ]])
    await message.answer(f"Привет! Твой ID: {message.from_user.id}\nНажми на кнопку ниже, чтобы открыть апгрейдер:", reply_markup=kb)

# АДМИНСКАЯ КОМАНДА ДЛЯ ВЫДАЧИ ПРИЗА ПРЯМО В ТЕЛЕГРАМЕ
@dp.message(Command("give"))
async def give_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав администратора.")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Формат команды: /give <ID_пользователя> <Название приза>\nПример: /give 123456789 Withered Bonnie")
        return
    
    target_id = args[1]
    prize_name = args[2]
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO pending_prizes (user_id, prize_name, status) VALUES (?, ?, "delivered")', (target_id, prize_name))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Приз '{prize_name}' успешно отправлен пользователю {target_id}! Он увидит уведомление при входе в апп.")
    except Exception as e:
        await message.answer(f"❌ Ошибка базы данных: {e}")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
