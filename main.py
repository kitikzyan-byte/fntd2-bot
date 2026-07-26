import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
SERVER_URL = "https://fntd2-bot.onrender.com"

app = Flask(__name__, template_folder="templates")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# --- ИНИЦИАЛИЗА БАЗЫ ДАННЫХ (SQLite) ---
DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            roblox_nick TEXT
        )
    ''')
    # Таблица незабранных/доставленных призов
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

# --- МАРШРУТЫ FLASK ---

@app.route('/')
def index():
    return render_template('index.html')

# Сохранение или получение ника
@app.route('/api/user_info/<int:user_id>', methods=['GET', 'POST'])
def user_info(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        nick = data.get('roblox_nick', '')
        cursor.execute('INSERT OR REPLACE INTO users (user_id, roblox_nick) VALUES (?, ?)', (user_id, nick))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    
    cursor.execute('SELECT roblox_nick FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    # Проверяем, есть ли доставка приза для показывания всплывашки
    cursor.execute('SELECT id, prize_name FROM pending_prizes WHERE user_id = ? AND status = "delivered"', (user_id,))
    delivered_prize = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        "roblox_nick": row[0] if row else "",
        "delivered_prize": {"id": delivered_prize[0], "name": delivered_prize[1]} if delivered_prize else None
    })

# Подтверждение получения уведомления о призе
@app.route('/api/claim_prize_notification', methods=['POST'])
def claim_prize_notification():
    data = request.json
    prize_id = data.get('prize_id')
    if prize_id:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pending_prizes WHERE id = ?', (prize_id,))
        conn.commit()
        conn.close()
    return jsonify({"status": "ok"})

# Создание ставки администратору
@app.route('/api/create_bet', methods=['POST'])
def create_bet():
    data = request.json
    user_id = data['user_id']
    roblox_nick = data['roblox_nick']
    
    # Сохраняем ник
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, roblox_nick) VALUES (?, ?)', (user_id, roblox_nick))
    conn.commit()
    conn.close()
    
    # Регистрация заявки
    return jsonify({"status": "pending"})

# АДМИН-АПИ: Выдача приза в офлайн пользователю
@app.route('/api/admin/give_prize', methods=['POST'])
def admin_give_prize():
    data = request.json
    user_id = data.get('user_id')
    prize_name = data.get('prize_name')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO pending_prizes (user_id, prize_name, status) VALUES (?, ?, "delivered")', (user_id, prize_name))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Приз {prize_name} записан юзеру {user_id}"})

# --- AIOGRAM BOT ---

@router.message(CommandStart())
def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎰 Открыть FNTD 2 Upgrader", web_app=WebAppInfo(url=SERVER_URL))
    ]])
    message.answer("Привет! Нажми на кнопку ниже, чтобы открыть апгрейдер:", reply_markup=kb)

dp.include_router(router)

if __name__ == "__main__":
    import threading
    import asyncio
    
    def run_flask():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
        
    threading.Thread(target=run_flask).start()
    asyncio.run(dp.start_polling(bot))
