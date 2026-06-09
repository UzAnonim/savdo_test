from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter

from database.queries import (
    get_user, get_all_branches, get_branch, create_branch,
    get_stats, get_top_products, get_branch_stock
)
from keyboards.keyboards import (
    admin_menu_kb, main_menu_kb, stats_period_kb, branches_kb
)

router = Router()


class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        user = await get_user(message.from_user.id)
        return user and user['role'] in ('admin', 'superadmin')


class AdminFSM(StatesGroup):
    branch_name = State()
    branch_address = State()
    set_moderator_id = State()
    set_moderator_branch = State()


def format_price(price: float) -> str:
    return f"{int(price):,}".replace(",", " ")


# ─── ADMIN MENU ──────────────────────────────────────
@router.message(F.text == "📊 Admin panel", IsAdmin())
async def admin_panel(message: Message):
    branches = await get_all_branches()
    await message.answer(
        f"👑 <b>Admin panel</b>\n"
        f"🏪 Jami filiallar: <b>{len(branches)}</b>",
        reply_markup=admin_menu_kb()
    )


# ─── BRANCHES ────────────────────────────────────────
@router.message(F.text == "🏪 Filiallar boshqaruvi", IsAdmin())
async def branches_management(message: Message):
    branches = await get_all_branches()
    lines = ["🏪 <b>Barcha filiallar:</b>\n"]
    for b in branches:
        lines.append(f"  #{b['id']} <b>{b['name']}</b> — {b['address'] or 'Manzil yo\'q'}")
    await message.answer("\n".join(lines), reply_markup=branches_kb(branches))


@router.message(F.text == "➕ Yangi filial qo'shish", IsAdmin())
async def add_branch_start(message: Message, state: FSMContext):
    await message.answer("🏪 Yangi filial nomini kiriting:")
    await state.set_state(AdminFSM.branch_name)


@router.message(AdminFSM.branch_name)
async def add_branch_name(message: Message, state: FSMContext):
    await state.update_data(branch_name=message.text.strip())
    await message.answer("📍 Manzilini kiriting:")
    await state.set_state(AdminFSM.branch_address)


@router.message(AdminFSM.branch_address)
async def add_branch_address(message: Message, state: FSMContext):
    data = await state.get_data()
    branch_id = await create_branch(data['branch_name'], message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ <b>{data['branch_name']}</b> (#<b>{branch_id}</b>) muvaffaqiyatli qo'shildi!\n\n"
        f"Moderator tayinlash uchun foydalanuvchi Telegram ID sini yuboring:\n"
        f"<i>/setmod {branch_id} [telegram_id]</i>"
    )


# ─── SET MODERATOR ───────────────────────────────────
@router.message(F.text.startswith("/setmod"), IsAdmin())
async def set_moderator(message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❗ Format: /setmod [branch_id] [telegram_id]")
        return
    try:
        branch_id = int(parts[1])
        telegram_id = int(parts[2])
        from database.queries import set_user_role
        await set_user_role(telegram_id, 'moderator', branch_id)
        branch = await get_branch(branch_id)
        await message.answer(
            f"✅ Foydalanuvchi <b>{telegram_id}</b>\n"
            f"<b>{branch['name']}</b> filiali moderatori etib tayinlandi!"
        )
    except (ValueError, Exception) as e:
        await message.answer(f"❗ Xatolik: {e}")


# ─── GLOBAL STATISTICS ───────────────────────────────
@router.message(F.text == "📊 Umumiy statistika", IsAdmin())
async def global_stats(message: Message):
    await message.answer(
        "📊 Davr tanlang:",
        reply_markup=stats_period_kb("admstats")
    )


@router.callback_query(F.data.startswith("admstats_"))
async def global_stats_period(callback: CallbackQuery):
    period = callback.data.replace("admstats_", "")
    branches = await get_all_branches()

    period_names = {
        'daily': 'Kunlik', 'weekly': 'Haftalik',
        'monthly': 'Oylik', 'yearly': 'Yillik'
    }

    lines = [f"📊 <b>Umumiy {period_names.get(period,'')} statistika</b>\n"]
    total_revenue = 0
    total_orders = 0

    for b in branches:
        stats = await get_stats(b['id'], period)
        total_revenue += stats['total_revenue']
        total_orders += stats['total_orders']
        lines.append(
            f"🏪 <b>{b['name']}</b>\n"
            f"   Buyurtmalar: {stats['total_orders']} | "
            f"Daromad: {format_price(stats['total_revenue'])} so'm"
        )

    lines.append(f"\n💰 <b>Umumiy daromad: {format_price(total_revenue)} so'm</b>")
    lines.append(f"📦 <b>Umumiy buyurtmalar: {total_orders}</b>")

    await callback.message.edit_text("\n".join(lines))


# ─── FORECASTS ───────────────────────────────────────
@router.message(F.text == "📈 Prognozlar", IsAdmin())
async def forecasts(message: Message):
    top = await get_top_products(limit=10)
    lines = ["📈 <b>Eng ko'p sotilayotgan mahsulotlar:</b>\n"]
    for i, p in enumerate(top, 1):
        lines.append(
            f"{i}. <b>{p['name']}</b>\n"
            f"   Jami: {p['total_qty']} {p['unit']} | "
            f"Daromad: {format_price(p['total_revenue'])} so'm"
        )
    await message.answer("\n".join(lines) if top else "📭 Hali buyurtmalar yo'q.")


# ─── USERS LIST ──────────────────────────────────────
@router.message(F.text == "👥 Foydalanuvchilar", IsAdmin())
async def users_list(message: Message):
    from database.queries import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch("""
            SELECT u.*, b.name as branch_name
            FROM users u LEFT JOIN branches b ON u.branch_id=b.id
            ORDER BY u.registered_at DESC LIMIT 20
        """)

    if not users:
        await message.answer("📭 Foydalanuvchilar yo'q.")
        return

    role_icons = {'customer': '🛒', 'moderator': '🛠', 'admin': '👑', 'superadmin': '🔑'}
    lines = [f"👥 <b>So'nggi {len(users)} ta foydalanuvchi:</b>\n"]
    for u in users:
        icon = role_icons.get(u['role'], '👤')
        lines.append(
            f"{icon} <b>{u['full_name']}</b> | {u['phone_main']}\n"
            f"   🏪 {u['branch_name'] or 'Filial yo\'q'} | "
            f"📅 {u['registered_at'].strftime('%d.%m.%Y')}"
        )
    await message.answer("\n".join(lines))
