from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.queries import get_user, create_user, get_all_branches
from keyboards.keyboards import (
    main_menu_kb, phone_kb, location_kb, skip_kb, cancel_kb
)

router = Router()


class RegisterFSM(StatesGroup):
    full_name = State()
    phone_main = State()
    phone_extra = State()
    location = State()
    home_address = State()
    branch = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        await message.answer(
            f"👋 Xush kelibsiz, <b>{user['full_name']}</b>!\n"
            f"Nima qilmoqchisiz?",
            reply_markup=main_menu_kb(user['role'])
        )
        return

    await message.answer(
        "🌟 <b>Savdo botiga xush kelibsiz!</b>\n\n"
        "Buyurtma berish uchun avval ro'yxatdan o'ting.\n\n"
        "👤 Ism va familyangizni kiriting:",
        reply_markup=cancel_kb()
    )
    await state.set_state(RegisterFSM.full_name)


@router.message(RegisterFSM.full_name)
async def reg_full_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        return

    if len(message.text.strip()) < 3:
        await message.answer("❗ Ism kamida 3 ta harf bo'lishi kerak. Qayta kiriting:")
        return

    await state.update_data(full_name=message.text.strip())
    await message.answer(
        f"✅ <b>{message.text.strip()}</b>\n\n"
        "📱 Telefon raqamingizni yuboring:\n"
        "<i>(Tugmani bosing yoki qo'lda kiriting: +998901234567)</i>",
        reply_markup=phone_kb()
    )
    await state.set_state(RegisterFSM.phone_main)


@router.message(RegisterFSM.phone_main, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone_main=phone)
    await _ask_phone_extra(message, state)


@router.message(RegisterFSM.phone_main, F.text)
async def reg_phone_text(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        return
    phone = message.text.strip()
    if not (phone.startswith("+998") and len(phone) == 13 and phone[1:].isdigit()):
        await message.answer("❗ Noto'g'ri format. +998901234567 ko'rinishida kiriting:")
        return
    await state.update_data(phone_main=phone)
    await _ask_phone_extra(message, state)


async def _ask_phone_extra(message: Message, state: FSMContext):
    await message.answer(
        "📞 Qo'shimcha telefon raqam kiriting:\n"
        "<i>(Ixtiyoriy — o'tkazib yuborish mumkin)</i>",
        reply_markup=skip_kb()
    )
    await state.set_state(RegisterFSM.phone_extra)


@router.message(RegisterFSM.phone_extra)
async def reg_phone_extra(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        return

    if message.text != "⏭ O'tkazib yuborish":
        phone = message.text.strip()
        if phone.startswith("+998") and len(phone) == 13 and phone[1:].isdigit():
            await state.update_data(phone_extra=phone)
        else:
            await message.answer("❗ Noto'g'ri format. +998901234567 ko'rinishida kiriting yoki o'tkazib yuboring:")
            return

    await message.answer(
        "📍 Hozirgi joylashuvingizni yuboring:\n"
        "<i>(Lokatsiya tugmasini bosing yoki qo'lda yozing)</i>",
        reply_markup=location_kb()
    )
    await state.set_state(RegisterFSM.location)


@router.message(RegisterFSM.location, F.location)
async def reg_location_geo(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    await state.update_data(
        latitude=lat, longitude=lon,
        current_location=f"📍 {lat:.4f}, {lon:.4f}"
    )
    await _ask_home_address(message, state)


@router.message(RegisterFSM.location, F.text)
async def reg_location_text(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        return
    await state.update_data(current_location=message.text.strip())
    await _ask_home_address(message, state)


async def _ask_home_address(message: Message, state: FSMContext):
    await message.answer(
        "🏠 Uy manzilingizni kiriting:\n"
        "<i>(Ko'cha, uy raqami va h.k. — ixtiyoriy)</i>",
        reply_markup=skip_kb()
    )
    await state.set_state(RegisterFSM.home_address)


@router.message(RegisterFSM.home_address)
async def reg_home_address(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        return

    if message.text != "⏭ O'tkazib yuborish":
        await state.update_data(home_address=message.text.strip())

    data = await state.get_data()
    user = await create_user(
        telegram_id=message.from_user.id,
        full_name=data.get('full_name'),
        phone_main=data.get('phone_main'),
        phone_extra=data.get('phone_extra'),
        current_location=data.get('current_location'),
        home_address=data.get('home_address'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        branch_id=1
    )
    await state.clear()
    await message.answer(
        f"🎉 <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n"
        f"👤 Ism: <b>{user['full_name']}</b>\n"
        f"📱 Tel: <b>{user['phone_main']}</b>\n"
        f"📍 Joylashuv: <b>{user['current_location'] or 'Ko\'rsatilmagan'}</b>\n\n"
        "Buyurtma berishni boshlaylik! 👇",
        reply_markup=main_menu_kb('customer')
    )
