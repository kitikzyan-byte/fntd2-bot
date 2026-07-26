import os
import sqlite3
import asyncio
import threading
from flask import Flask, render_template, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_БОТА") # Замени или используй Env Vars
SERVER_URL = "https://fntd2-bot.onrender.com"

# === ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ===
DB_NAME = "database.db"
app = Flask(__name__, template_folder="templates")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            roblox_nick TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_prizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            prize_name TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# === FLASK МАРШРУТЫ (САЙТ И API) ===
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

# АДМИН-АПИ: Выдача приза
@app.route('/api/admin/give_prize', methods=['POST'])
def admin_give_prize():
    data = request.json or {}
    user_id = data.get('user_id')
    prize_name = data.get('prize_name')
    if user_id and prize_name:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO pending_prizes (user_id, prize_name, status) VALUES (?, ?, "delivered")', (user_id, prize_name))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

# === TELEGRAM БОТ ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ИСПРАВЛЕНО: добавлено async def
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎰 Открыть FNTD 2 Upgrader", web_app=WebAppInfo(url=SERVER_URL))
    ]])
    # ИСПРАВЛЕНО: добавлено await
    await message.answer("Привет! Нажми на кнопку ниже, чтобы открыть апгрейдер:", reply_markup=kb)

# === СОВМЕСТНЫЙ ЗАПУСК ===
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    # use_reloader=False блокирует лишние перезапуски в потоке
    app.run(host="0.0.0.0", port=port, use_reloader=False)

async def main():
    # Запускаем Flask на фоне
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота
    print("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
