import os
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, 
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)

import database as db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

GROUPS = {
    'home': int(os.getenv("GROUP_HOME_SERVICES_ID", "0")),
    'rental': int(os.getenv("GROUP_RENTAL_ID", "0")),
    'realestate': int(os.getenv("GROUP_REAL_ESTATE_ID", "0"))
}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# ----------------- ТЕКСТЫ И ЛОКАЛИЗАЦИЯ -----------------

TEXTS = {
    'en': {
        'welcome': "👋 Welcome to IndoFix! Choose language:",
        'main_menu': "Main Menu:",
        'btn_new': "🛠️ New Request",
        'btn_my_req': "📋 My Requests",
        'select_main_cat': "Select category:",
        'select_sub_cat': "Select subcategory:",
        'enter_desc': "Describe your issue/request:",
        'enter_loc': "Specify location (Area or Google Maps Link):",
        'select_time': "Desired time:",
        'enter_contacts': "Enter Phone / WhatsApp for communication:",
        'confirm_created': "✅ Request #A{id} registered! Searching for a master (usually 5-15 mins).",
        'asap': "⚡ ASAP",
        'today': "📅 Today",
        'tomorrow': "📆 Tomorrow",
        'assigned_client': "🎉 Master found for request #A{id}!\nWorker: @{worker_username}\nPhone/WA: Contacting you soon.",
        'rate_request': "Rate the completed job for #A{id} (1 to 5 stars):",
        'thanks_rating': "Thank you for your feedback!"
    },
    'ru': {
        'welcome': "👋 Добро пожаловать в IndoFix! Выберите язык:",
        'main_menu': "Главное меню:",
        'btn_new': "🛠️ Новая заявка",
        'btn_my_req': "📋 Мои заявки",
        'select_main_cat': "Выберите категорию:",
        'select_sub_cat': "Выберите подкатегорию:",
        'enter_desc': "Опишите проблему или запрос:",
        'enter_loc': "Укажите локацию (Район или ссылку на Google Maps):",
        'select_time': "Желаемое время:",
        'enter_contacts': "Укажите ваш Телефон / WhatsApp для связи:",
        'confirm_created': "✅ Заявка #A{id} принята! Ищем мастера (обычно 5-15 минут).",
        'asap': "⚡ Как можно скорее",
        'today': "📅 Сегодня",
        'tomorrow': "📆 Завтра",
        'assigned_client': "🎉 Мастер найден для заявки #A{id}!\nМастер: @{worker_username}\nСвяжется с вами в ближайшее время.",
        'rate_request': "Работа по заявке #A{id} завершена. Оцените качество от 1 до 5:",
        'thanks_rating': "Спасибо за вашу оценку!"
    },
    'id': {
        'welcome': "👋 Selamat datang di IndoFix! Pilih bahasa:",
        'main_menu': "Menu Utama:",
        'btn_new': "🛠️ Buat Pesanan",
        'btn_my_req': "📋 Pesanan Saya",
        'select_main_cat': "Pilih kategori:",
        'select_sub_cat': "Pilih subkategori:",
        'enter_desc': "Jelaskan masalah Anda:",
        'enter_loc': "Tentukan lokasi (Area / Link Google Maps):",
        'select_time': "Waktu yang diinginkan:",
        'enter_contacts': "Masukkan Nomor Telepon / WhatsApp:",
        'confirm_created': "✅ Pesanan #A{id} dibuat! Mencari teknisi (5-15 menit).",
        'asap': "⚡ Secepatnya",
        'today': "📅 Hari ini",
        'tomorrow': "📆 Besok",
        'assigned_client': "🎉 Teknisi ditemukan untuk pesanan #A{id}!\nTeknisi: @{worker_username}",
        'rate_request': "Pekerjaan #A{id} selesai. Beri nilai (1-5):",
        'thanks_rating': "Terima kasih atas penilaian Anda!"
    }
}

CAT_MAP = {
    'home': {
        'title': '🛠️ Home Services',
        'subs': ['Electrician', 'Plumber', 'AC Repair', 'Cleaning', 'Other Home']
    },
    'rental': {
        'title': '🛵 Bike & Car Rental',
        'subs': ['Scooter / Bike', 'Car Rental']
    },
    'realestate': {
        'title': '🏠 Real Estate',
        'subs': ['Long-term Rent', 'Villa Search']
    }
}

class FormState(StatesGroup):
    main_cat = State()
    sub_cat = State()
    desc = State()
    location = State()
    desired_time = State()
    contacts = State()

# ----------------- ХЕНДЛЕРЫ КЛИЕНТА -----------------

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇬🇧 EN", callback_data="lang_en"),
        InlineKeyboardButton(text="🇷🇺 RU", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇮🇩 ID", callback_data="lang_id")
    ]])
    await message.answer(TEXTS['en']['welcome'], reply_markup=kb)

@router.callback_query(F.data.startswith("lang_"))
async def cb_lang(call: CallbackQuery):
    lang = call.data.split("_")[1]
    await db.set_user_language(call.from_user.id, lang)
    await call.message.delete()
    
    t = TEXTS[lang]
    menu = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t['btn_new'])], [KeyboardButton(text=t['btn_my_req'])]],
        resize_keyboard=True
    )
    await call.message.answer(t['main_menu'], reply_markup=menu)

@router.message(F.text.in_([TEXTS['en']['btn_new'], TEXTS['ru']['btn_new'], TEXTS['id']['btn_new']]))
@router.message(Command("new"))
async def start_new_req(message: Message, state: FSMContext):
    lang = await db.get_user_language(message.from_user.id)
    await state.update_data(lang=lang)
    
    buttons = [[InlineKeyboardButton(text=v['title'], callback_data=f"mcat_{k}")] for k, v in CAT_MAP.items()]
    await state.set_state(FormState.main_cat)
    await message.answer(TEXTS[lang]['select_main_cat'], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(FormState.main_cat, F.data.startswith("mcat_"))
async def cb_main_cat(call: CallbackQuery, state: FSMContext):
    mcat = call.data.split("_")[1]
    await state.update_data(main_cat=mcat)
    data = await state.get_data()
    lang = data['lang']
    
    subs = CAT_MAP[mcat]['subs']
    buttons = [[InlineKeyboardButton(text=s, callback_data=f"scat_{s}")] for s in subs]
    
    await state.set_state(FormState.sub_cat)
    await call.message.edit_text(TEXTS[lang]['select_sub_cat'], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(FormState.sub_cat, F.data.startswith("scat_"))
async def cb_sub_cat(call: CallbackQuery, state: FSMContext):
    scat = call.data.split("_")[1]
    await state.update_data(sub_cat=scat)
    data = await state.get_data()
    lang = data['lang']
    
    await state.set_state(FormState.desc)
    await call.message.edit_text(TEXTS[lang]['enter_desc'])

@router.message(FormState.desc)
async def process_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text or "No text description")
    data = await state.get_data()
    lang = data['lang']
    
    await state.set_state(FormState.location)
    await message.answer(TEXTS[lang]['enter_loc'])

@router.message(FormState.location)
async def process_loc(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    data = await state.get_data()
    lang = data['lang']
    
    t = TEXTS[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t['asap'], callback_data="time_ASAP"),
        InlineKeyboardButton(text=t['today'], callback_data="time_Today"),
        InlineKeyboardButton(text=t['tomorrow'], callback_data="time_Tomorrow")
    ]])
    await state.set_state(FormState.desired_time)
    await message.answer(t['select_time'], reply_markup=kb)

@router.callback_query(FormState.desired_time, F.data.startswith("time_"))
async def cb_time(call: CallbackQuery, state: FSMContext):
    time_val = call.data.split("_")[1]
    await state.update_data(desired_time=time_val)
    data = await state.get_data()
    lang = data['lang']
    
    await state.set_state(FormState.contacts)
    await call.message.edit_text(TEXTS[lang]['enter_contacts'])

@router.message(FormState.contacts)
async def process_contacts(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    
    req_id = await db.create_request(
        client_id=message.from_user.id,
        client_username=message.from_user.username or "NoUser",
        main_cat=data['main_cat'],
        sub_cat=data['sub_cat'],
        desc=data['desc'],
        loc=data['location'],
        time_str=data['desired_time'],
        contacts=message.text
    )
    
    await state.clear()
    await message.answer(TEXTS[lang]['confirm_created'].format(id=req_id))
    
    # Публикация карточки в соответствующую группу
    target_group = GROUPS.get(data['main_cat'])
    card_text = (
        f"🆕 **ЗАЯВКА #A{req_id}**\n\n"
        f"📌 Категория: {data['sub_cat']}\n"
        f"📍 Район: {data['location']}\n"
        f"⏰ Когда: {data['desired_time']}\n"
        f"📝 Описание: {data['desc']}\n"
    )
    btn = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"✅ Беру (#A{req_id})", callback_data=f"take_{req_id}")
    ]])
    
    if target_group:
        try:
            await bot.send_message(chat_id=target_group, text=card_text, reply_markup=btn, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Group send error: {e}")
            
    # Таймаут-задача на 15 минут
    asyncio.create_task(check_sla_timeout(req_id))

# ----------------- ДИСПЕТЧЕРИЗАЦИЯ И ИСПОЛНИТЕЛИ -----------------

async def check_sla_timeout(req_id: int):
    await asyncio.sleep(900)  # 15 минут
    req = await db.get_request(req_id)
    if req and req['status'] == 'new':
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID, 
                f"⚠️ **ВНИМАНИЕ!** Заявка **#A{req_id}** ({req['sub_category']}) зависла! Прошло 15 минут, никто не взял."
            )

@router.callback_query(F.data.startswith("take_"))
async def cb_take_job(call: CallbackQuery):
    req_id = int(call.data.split("_")[1])
    worker = call.from_user
    
    success = await db.assign_request(req_id, worker.id, worker.username or "NoUser")
    if not success:
        await call.answer("❌ Заявка уже занята другим мастером!", show_alert=True)
        return

    req = await db.get_request(req_id)
    
    # Обновление карточки в группе
    await call.message.edit_text(
        call.message.text + f"\n\n🤝 **Взял в работу:** @{worker.username or worker.id}",
        reply_markup=None
    )
    await call.answer("Вы успешно взяли заказ!")

    # Контакты клиенту
    c_lang = await db.get_user_language(req['client_id'])
    try:
        await bot.send_message(
            req['client_id'], 
            TEXTS[c_lang]['assigned_client'].format(id=req_id, worker_username=worker.username or worker.first_name)
        )
    except Exception as e:
        logging.error(f"Error notifying client: {e}")

    # Контакты мастеру
    msg_worker = (
        f"✅ **Вы приняли заявку #A{req_id}**\n\n"
        f"👤 Клиент: @{req['client_username']}\n"
        f"📞 Тел/WA: {req['contacts']}\n"
        f"📍 Локация: {req['location']}\n"
        f"📝 Детали: {req['description']}\n\n"
        f"После выполнения нажмите кнопку ниже:"
    )
    done_btn = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Завершено", callback_data=f"finish_{req_id}")
    ]])
    await bot.send_message(worker.id, msg_worker, reply_markup=done_btn)

@router.callback_query(F.data.startswith("finish_"))
async def cb_finish_job(call: CallbackQuery):
    req_id = int(call.data.split("_")[1])
    req = await db.complete_request(req_id)
    
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(f"🎉 Заявка #A{req_id} отмечена как завершённая!")
    
    # Отправка запроса оценки клиенту
    c_lang = await db.get_user_language(req['client_id'])
    stars_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"⭐ {i}", callback_data=f"rate_{req_id}_{i}") for i in range(1, 6)
    ]])
    try:
        await bot.send_message(
            req['client_id'], 
            TEXTS[c_lang]['rate_request'].format(id=req_id), 
            reply_markup=stars_kb
        )
    except Exception as e:
        logging.error(f"Error asking rating: {e}")

@router.callback_query(F.data.startswith("rate_"))
async def cb_rate_job(call: CallbackQuery):
    _, req_id, rating = call.data.split("_")
    await db.set_rating(int(req_id), int(rating))
    
    lang = await db.get_user_language(call.from_user.id)
    await call.message.edit_text(TEXTS[lang]['thanks_rating'])

# ----------------- КОМАНДЫ АДМИНА И ПРОЧЕЕ -----------------

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = await db.get_stats()
    await message.answer(
        f"📊 **Статистика IndoFix:**\n\n"
        f"• Всего заявок: `{stats['total']}`\n"
        f"• Выполнено: `{stats['completed']}`\n"
        f"• Средний рейтинг: `{stats['avg_rating']} / 5.0`",
        parse_mode="Markdown"
    )

@router.message(Command("myjobs"))
async def cmd_myjobs(message: Message):
    jobs = await db.get_worker_jobs(message.from_user.id)
    if not jobs:
        await message.answer("У вас нет активных взятых заказов.")
        return
    for j in jobs:
        btn = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Завершено", callback_data=f"finish_{j['request_id']}")
        ]])
        await message.answer(f"Заказ #A{j['request_id']} | {j['sub_category']} | {j['location']}", reply_markup=btn)

# ----------------- ЗАПУСК -----------------

async def main():
    await db.init_db()
    dp.include_router(router)
    logging.info("Бот IndoFix (MVP vA) успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
