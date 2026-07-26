import asyncio
import os
import json
import aiohttp
from flask import Flask, render_template, request, jsonify
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "8653136894:AAHpu03Vx-ciIGfWdhlVFwzSCtMnWWkUcxw"
ADMIN_ID = 2092773964
# Render автоматически предоставит URL, либо используем локальный
SERVER_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:5000")

app = Flask(__name__, template_folder="templates")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Хранилище сессий в памяти (так как процесс один, всё работает мгновенно)
GAMES = {}

# ================= FLASK ROUTES =================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/create_bet', methods=['POST'])
def create_bet():
    data = request.json
    user_id = str(data.get('user_id'))
    roblox_nick = data.get('roblox_nick')
    tg_username = data.get('tg_username', 'Не указан')
    bet_item = data.get('bet_item')
    target_item = data.get('target_item')
    chance = data.get('chance')

    GAMES[user_id] = {
        "status": "pending_admin",
        "roblox_nick": roblox_nick,
        "tg_username": tg_username,
        "bet_item": bet_item,
        "target_item": target_item,
        "chance": chance,
        "prize": None
    }

    # Отправляем уведу админу
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить почту", callback_data=f"approve:{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")
    ]])

    asyncio.run_coroutine_threadsafe(
        bot.send_message(
            ADMIN_ID,
            f"📩 **НОВАЯ СТАВКА В FNTD 2 UPGRADER!**\n\n"
            f"🎮 **Roblox Ник:** `{roblox_nick}`\n"
            f"📱 **TG:** @{tg_username} (ID: `{user_id}`)\n\n"
            f"📥 **Ставит:** `{bet_item}`\n"
            f"🎯 **Хочет получить:** `{target_item}`\n"
            f"🎲 **Шанс:** `{chance}%`\n\n"
            f"📌 Проверьте почту от `{roblox_nick}` на нике **fntd2UPGRADER**!",
            reply_markup=kb,
            parse_mode="Markdown"
        ),
        loop
    )

    return jsonify({"status": "ok"})

@app.route('/api/check_status/<user_id>', methods=['GET'])
def check_status(user_id):
    game = GAMES.get(str(user_id))
    if not game:
        return jsonify({"status": "not_found"})
    return jsonify({"status": game["status"]})

@app.route('/api/claim_win', methods=['POST'])
def claim_win():
    data = request.json
    user_id = str(data.get('user_id'))
    win_item = data.get('win_item')
    
    game = GAMES.get(user_id)
    if game:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🎁 ПРИЗ ВЫДАН В ИГРЕ", callback_data=f"delivered:{user_id}")
        ]])
        
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                ADMIN_ID,
                f"🎉 **ПОЛЬЗОВАТЕЛЬ ВЫИГРАЛ В АПГРЕЙДЕРЕ!**\n\n"
                f"🎮 **Roblox Ник:** `{game['roblox_nick']}`\n"
                f"📱 **TG:** @{game['tg_username']}\n"
                f"🏆 **Выигрыш:** `{win_item}`\n\n"
                f"Отправьте приз по почте и нажмите кнопку ниже!",
                reply_markup=kb,
                parse_mode="Markdown"
            ),
            loop
        )
    return jsonify({"status": "ok"})

# ================= TELEGRAM BOT HANDLERS =================

@router.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎰 ОТКРЫТЬ FNTD 2 UPGRADER", web_app=WebAppInfo(url=SERVER_URL))
    ]])
    await message.answer(
        "ДОБРО ПОЖАЛОВАТЬ В FNTD 2 UPGRADER, УЛУЧШАЙ СВОИХ ЮНИТОВ, УДВАИВАЙ ИХ, И ЗАРАБАТЫВАЙ ДУШИ!",
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("approve:"))
async def approve(cb: CallbackQuery):
    uid = cb.data.split(":")[1]
    if uid in GAMES:
        GAMES[uid]["status"] = "approved"
        await cb.message.edit_text(f"{cb.message.text}\n\n🟢 **ПОЧТА ПОДТВЕРЖДЕНА! КРУТИТ.**")

@router.callback_query(F.data.startswith("reject:"))
async def reject(cb: CallbackQuery):
    uid = cb.data.split(":")[1]
    if uid in GAMES:
        GAMES[uid]["status"] = "rejected"
        await cb.message.edit_text(f"{cb.message.text}\n\n🔴 **ОТКЛОНЕНО.**")

@router.callback_query(F.data.startswith("delivered:"))
async def delivered(cb: CallbackQuery):
    uid = cb.data.split(":")[1]
    await bot.send_message(int(uid), "✅ **Ваш приз успешно выдан по почте в FNTD 2! Приятной игры!**")
    await cb.message.edit_text(f"{cb.message.text}\n\n✅ **ПРИЗ УСПЕШНО ВЫДАН ИГРОКУ!**")

# ================= MULTI-THREAD RUNNER =================

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

async def main():
    global loop
    loop = asyncio.get_running_loop()
    # Запускаем Flask в отдельном потоке
    import threading
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 FNTD 2 UPGRADER SERVER STARTED!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
