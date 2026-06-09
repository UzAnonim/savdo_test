from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter

from database.queries import (
    get_user, get_branch_stock, update_stock, get_low_stock,
    get_all_products, get_pending_transfers, approve_transfer,
    create_transfer_request, get_nearest_branch_with_product,
    get_branch, get_stats, get_top_products, update_product,
    add_product, delete_product, get_all_branches,
    update_order_status
)
from keyboards.keyboards import (
    moderator_menu_kb, main_menu_kb, stock_actions_kb,
    transfer_approve_kb, stats_period_kb, order_status_kb
)

router = Router()


class IsModerator(Filter):
    async def __call__(self, message: Message) -> bool:
        user = await get_user(message.from_user.id)
        return user and user['role'] in ('moderator', 'admin', 'superadmin')


class ModeratorFSM(StatesGroup):
    stock_add = State()
    stock_sub = State()
    stock_price = State()
    product_name = State()
    product_unit = State()
    product_weekly = State()
    product_monthly = State()
    product_price = State()
    transfer_qty = State()


def format_price(price: float) -> str:
    return f"{int(price):,}".replace(",", " ")


# ─── MODERATOR MENU ──────────────────────────────────
@router.message(F.text == "🛠 Moderator paneli", IsModerator())
async def mod_panel(message: Message):
    await message.answer(
        "🛠 <b>Moderator paneli</b>\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=moderator_menu_kb()
    )


# ─── STOCK ───────────────────────────────────────────
@router.message(F.text == "📦 Zaxira holati", IsModerator())
async def show_stock(message: Message):
    user = await get_user(message.from_user.id)
    stock = await get_branch_stock(user['branch_id'])
    low = await get_low_stock(user['branch_id'])
    low_ids = {s['product_id'] for s in low}

    if not stock:
        await message.answer("📭 Zaxira ma'lumotlari yo'q. Avval mahsulotlarni kiriting.")
        return

    current_cat = None
    lines = ["📦 <b>Zaxira holati</b>\n"]
    for s in stock:
        if s['category_name'] != current_cat:
            current_cat = s['category_name']
            lines.append(f"\n<b>{current_cat}</b>")
        warn = " ⚠️" if s['product_id'] in low_ids else ""
        lines.append(
            f"  • {s['name']}: <b>{s['quantity']} {s['unit']}</b>"
            f" | {format_price(s['price_per_unit'])} so'm{warn}"
        )

    if low_ids:
        lines.append(f"\n⚠️ <b>{len(low_ids)} ta mahsulot tugayapti!</b>")

    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("stock_add_"))
async def stock_add_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    await state.update_data(product_id=product_id)
    await callback.message.answer("📥 Qancha qo'shmoqchisiz? (Miqdor kiriting):")
    await state.set_state(ModeratorFSM.stock_add)


@router.message(ModeratorFSM.stock_add)
async def stock_add_done(message: Message, state: FSMContext):
    try:
        qty = float(message.text.replace(",", "."))
        data = await state.get_data()
        user = await get_user(message.from_user.id)
        await update_stock(user['branch_id'], data['product_id'], qty)
        await message.answer(f"✅ {qty} birlik qo'shildi!")
        await state.clear()
    except ValueError:
        await message.answer("❗ Faqat son kiriting.")


@router.callback_query(F.data.startswith("stock_price_"))
async def stock_price_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    await state.update_data(product_id=product_id)
    await callback.message.answer("💰 Yangi narxni kiriting (so'm):")
    await state.set_state(ModeratorFSM.stock_price)


@router.message(ModeratorFSM.stock_price)
async def stock_price_done(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(" ", "").replace(",", ""))
        data = await state.get_data()
        await update_product(data['product_id'], price_per_unit=price)
        await message.answer(f"✅ Narx {format_price(price)} so'm qilib yangilandi!")
        await state.clear()
    except ValueError:
        await message.answer("❗ Faqat son kiriting.")


# ─── PRODUCT MANAGEMENT ──────────────────────────────
@router.message(F.text == "✏️ Mahsulot tahrirlash", IsModerator())
async def product_edit_menu(message: Message):
    products = await get_all_products()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    current_cat = None
    for p in products:
        if p['category_name'] != current_cat:
            current_cat = p['category_name']
        builder.row(InlineKeyboardButton(
            text=f"{p['category_icon']} {p['name']} — {format_price(p['price_per_unit'])} so'm",
            callback_data=f"edit_prod_{p['id']}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Yangi mahsulot qo'shish", callback_data="add_new_product"))
    await message.answer(
        "✏️ <b>Mahsulotni tanlang:</b>",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("edit_prod_"))
async def edit_product_actions(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[-1])
    await callback.message.answer(
        "📋 Nima qilmoqchisiz?",
        reply_markup=stock_actions_kb(product_id)
    )


@router.callback_query(F.data.startswith("prod_delete_"))
async def delete_product_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[-1])
    await delete_product(product_id)
    await callback.message.edit_text("🗑 Mahsulot o'chirildi (arxivlandi).")


# Yangi mahsulot qo'shish FSM
@router.callback_query(F.data == "add_new_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Mahsulot nomini kiriting:")
    await state.set_state(ModeratorFSM.product_name)


@router.message(ModeratorFSM.product_name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("📏 O'lchov birligini kiriting (kg, dona, l, gr):")
    await state.set_state(ModeratorFSM.product_unit)


@router.message(ModeratorFSM.product_unit)
async def add_product_unit(message: Message, state: FSMContext):
    await state.update_data(unit=message.text.strip())
    await message.answer("📅 1 haftalik miqdor (4 kishi uchun):")
    await state.set_state(ModeratorFSM.product_weekly)


@router.message(ModeratorFSM.product_weekly)
async def add_product_weekly(message: Message, state: FSMContext):
    try:
        await state.update_data(weekly=float(message.text))
        await message.answer("🗓 1 oylik miqdor (4 kishi uchun):")
        await state.set_state(ModeratorFSM.product_monthly)
    except ValueError:
        await message.answer("❗ Son kiriting:")


@router.message(ModeratorFSM.product_monthly)
async def add_product_monthly(message: Message, state: FSMContext):
    try:
        await state.update_data(monthly=float(message.text))
        await message.answer("💰 Narxi (so'mda):")
        await state.set_state(ModeratorFSM.product_price)
    except ValueError:
        await message.answer("❗ Son kiriting:")


@router.message(ModeratorFSM.product_price)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(" ", ""))
        data = await state.get_data()
        pid = await add_product(
            category_id=1,
            name=data['name'],
            unit=data['unit'],
            weekly_qty=data['weekly'],
            monthly_qty=data['monthly'],
            price=price
        )
        await state.clear()
        await message.answer(f"✅ Mahsulot #{pid} muvaffaqiyatli qo'shildi!")
    except ValueError:
        await message.answer("❗ Son kiriting:")


# ─── TRANSFERS ───────────────────────────────────────
@router.message(F.text == "🔄 Transfer so'rovlari", IsModerator())
async def show_transfers(message: Message):
    user = await get_user(message.from_user.id)
    transfers = await get_pending_transfers(user['branch_id'])

    if not transfers:
        await message.answer("📭 Kutilayotgan transfer so'rovlari yo'q.")
        return

    for tr in transfers:
        await message.answer(
            f"🔄 <b>Transfer so'rovi #{tr['id']}</b>\n\n"
            f"📦 Mahsulot: <b>{tr['product_name']}</b>\n"
            f"📊 Miqdor: <b>{tr['quantity']} {tr['unit']}</b>\n"
            f"🏪 Qayerdan: <b>{tr['from_branch']}</b>\n"
            f"🏪 Qayerga: <b>{tr['to_branch']}</b>\n"
            f"📝 Izoh: {tr['note'] or 'Yo\'q'}",
            reply_markup=transfer_approve_kb(tr['id'])
        )


@router.callback_query(F.data.startswith("transfer_yes_"))
async def approve_transfer_handler(callback: CallbackQuery, bot: Bot):
    transfer_id = int(callback.data.split("_")[-1])
    user = await get_user(callback.from_user.id)
    tr = await approve_transfer(transfer_id, user['id'])

    await callback.message.edit_text(
        f"✅ Transfer #{transfer_id} tasdiqlandi!\n"
        f"Zaxira yangilandi."
    )

    # To'branch moderatoriga xabar berish
    from database.queries import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        moderators = await conn.fetch("""
            SELECT telegram_id FROM users
            WHERE branch_id=$1 AND role IN ('moderator','admin','superadmin')
        """, tr['to_branch_id'])
    for mod in moderators:
        try:
            await bot.send_message(
                mod['telegram_id'],
                f"✅ Transfer tasdiqlandi!\n"
                f"Mahsulot filialingizga jo'natilmoqda."
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("transfer_no_"))
async def reject_transfer(callback: CallbackQuery):
    transfer_id = int(callback.data.split("_")[-1])
    from database.queries import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE transfer_requests SET status='rejected', updated_at=NOW() WHERE id=$1",
            transfer_id
        )
    await callback.message.edit_text(f"❌ Transfer #{transfer_id} rad etildi.")


# ─── AUTO TRANSFER SUGGESTION ────────────────────────
async def check_and_suggest_transfer(bot: Bot, branch_id: int, product_id: int,
                                      requested_by_telegram: int):
    """Agar mahsulot tugasa, eng yaqin filialdan so'rash taklif qilinadi"""
    nearest = await get_nearest_branch_with_product(product_id, branch_id)
    if not nearest:
        return

    from database.queries import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        product = await conn.fetchrow("SELECT * FROM products WHERE id=$1", product_id)
        moderators = await conn.fetch("""
            SELECT telegram_id FROM users
            WHERE branch_id=$1 AND role IN ('moderator','admin','superadmin')
        """, branch_id)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for b in nearest[:3]:
        builder.row(InlineKeyboardButton(
            text=f"🏪 {b['name']} ({b['quantity']} {product['unit']})",
            callback_data=f"req_transfer_{branch_id}_{b['id']}_{product_id}"
        ))
    builder.row(InlineKeyboardButton(text="❌ Kerak emas", callback_data="transfer_skip"))

    for mod in moderators:
        try:
            await bot.send_message(
                mod['telegram_id'],
                f"⚠️ <b>{product['name']}</b> tugayapti!\n\n"
                f"Quyidagi filiallardan so'rash mumkin:",
                reply_markup=builder.as_markup()
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("req_transfer_"))
async def request_transfer(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    to_branch = int(parts[2])
    from_branch = int(parts[3])
    product_id = int(parts[4])
    await state.update_data(
        transfer_from=from_branch,
        transfer_to=to_branch,
        transfer_product=product_id
    )
    await callback.message.answer("📊 Qancha miqdor so'ramoqchisiz?")
    await state.set_state(ModeratorFSM.transfer_qty)


@router.message(ModeratorFSM.transfer_qty)
async def transfer_qty_done(message: Message, state: FSMContext, bot: Bot):
    try:
        qty = float(message.text)
        data = await state.get_data()
        user = await get_user(message.from_user.id)

        tr_id = await create_transfer_request(
            from_branch=data['transfer_from'],
            to_branch=data['transfer_to'],
            product_id=data['transfer_product'],
            quantity=qty,
            requested_by=user['id']
        )

        # From filial moderatorlariga xabar yuborish
        from database.queries import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            mods = await conn.fetch("""
                SELECT telegram_id FROM users
                WHERE branch_id=$1 AND role IN ('moderator','admin','superadmin')
            """, data['transfer_from'])
            product = await conn.fetchrow("SELECT * FROM products WHERE id=$1", data['transfer_product'])
            from_branch = await conn.fetchrow("SELECT * FROM branches WHERE id=$1", data['transfer_from'])
            to_branch = await conn.fetchrow("SELECT * FROM branches WHERE id=$1", data['transfer_to'])

        for mod in mods:
            try:
                await bot.send_message(
                    mod['telegram_id'],
                    f"📨 <b>Yangi transfer so'rovi #{tr_id}</b>\n\n"
                    f"📦 Mahsulot: <b>{product['name']}</b>\n"
                    f"📊 Miqdor: <b>{qty} {product['unit']}</b>\n"
                    f"🏪 Qayerga: <b>{to_branch['name']}</b>\n\n"
                    f"Tasdiqlaysizmi?",
                    reply_markup=transfer_approve_kb(tr_id)
                )
            except Exception:
                pass

        await state.clear()
        await message.answer(f"✅ Transfer so'rovi #{tr_id} yuborildi!")
    except ValueError:
        await message.answer("❗ Son kiriting:")


# ─── STATISTICS ──────────────────────────────────────
@router.message(F.text == "📊 Statistika", IsModerator())
async def mod_stats(message: Message):
    await message.answer(
        "📊 Qaysi davr uchun statistika?",
        reply_markup=stats_period_kb("modstats")
    )


@router.callback_query(F.data.startswith("modstats_"))
async def mod_stats_period(callback: CallbackQuery):
    period = callback.data.replace("modstats_", "")
    user = await get_user(callback.from_user.id)
    stats = await get_stats(user['branch_id'], period)
    top = await get_top_products(user['branch_id'], 5)
    branch = await get_branch(user['branch_id'])

    period_names = {
        'daily': 'Kunlik', 'weekly': 'Haftalik',
        'monthly': 'Oylik', 'yearly': 'Yillik'
    }

    lines = [
        f"📊 <b>{period_names.get(period, '')} statistika</b>\n"
        f"🏪 Filial: <b>{branch['name']}</b>\n\n"
        f"📦 Buyurtmalar: <b>{stats['total_orders']}</b>\n"
        f"💰 Daromad: <b>{format_price(stats['total_revenue'])} so'm</b>\n"
        f"👥 Mijozlar: <b>{stats['unique_customers']}</b>\n"
        f"📊 O'rtacha buyurtma: <b>{format_price(stats['avg_order_price'])} so'm</b>\n\n"
        f"🏆 <b>Top 5 mahsulot:</b>"
    ]
    for i, p in enumerate(top, 1):
        lines.append(f"  {i}. {p['name']}: {p['total_qty']} {p['unit']}")

    await callback.message.edit_text("\n".join(lines))
