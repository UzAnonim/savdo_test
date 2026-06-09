from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ─── MAIN MENUS ──────────────────────────────────────
def main_menu_kb(role: str = 'customer') -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🛒 Buyurtma berish"))
    builder.row(KeyboardButton(text="📋 Mening buyurtmalarim"))
    builder.row(KeyboardButton(text="👤 Mening profilim"))
    if role in ('moderator', 'admin', 'superadmin'):
        builder.row(KeyboardButton(text="🛠 Moderator paneli"))
    if role in ('admin', 'superadmin'):
        builder.row(KeyboardButton(text="📊 Admin panel"))
    return builder.as_markup(resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )


def back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Orqaga")]],
        resize_keyboard=True
    )


# ─── REGISTRATION ────────────────────────────────────
def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telegram raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


def location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)],
            [KeyboardButton(text="✏️ Qo'lda yozish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


# ─── ORDER ───────────────────────────────────────────
def order_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📦 Barcha mahsulotlar", callback_data="order_all"))
    builder.row(InlineKeyboardButton(text="🗓 1 oylik (4 kishlik)", callback_data="order_monthly"))
    builder.row(InlineKeyboardButton(text="📅 1 haftalik (4 kishlik)", callback_data="order_weekly"))
    return builder.as_markup()


def products_inline_kb(products: list, selected: dict, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page_size = 8
    start = page * page_size
    end = start + page_size
    page_products = products[start:end]

    for p in page_products:
        qty = selected.get(p['id'], 0)
        check = f"✅ {qty}{p['unit']}" if qty > 0 else "➕"
        builder.row(
            InlineKeyboardButton(text=p['name'], callback_data=f"prod_info_{p['id']}"),
            InlineKeyboardButton(text="➖", callback_data=f"prod_minus_{p['id']}"),
            InlineKeyboardButton(text=check, callback_data=f"prod_qty_{p['id']}"),
            InlineKeyboardButton(text="➕", callback_data=f"prod_plus_{p['id']}")
        )

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"prod_page_{page-1}"))
    if end < len(products):
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"prod_page_{page+1}"))
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🛒 Buyurtmani tasdiqlash", callback_data="order_confirm"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order_cancel"))
    return builder.as_markup()


def confirm_order_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="order_submit"),
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="order_edit"),
    )
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order_cancel"))
    return builder.as_markup()


# ─── MODERATOR ───────────────────────────────────────
def moderator_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📦 Zaxira holati"))
    builder.row(KeyboardButton(text="📋 Buyurtmalar ro'yxati"))
    builder.row(KeyboardButton(text="🔄 Transfer so'rovlari"))
    builder.row(KeyboardButton(text="✏️ Mahsulot tahrirlash"))
    builder.row(KeyboardButton(text="📊 Statistika"))
    builder.row(KeyboardButton(text="🏠 Asosiy menyu"))
    return builder.as_markup(resize_keyboard=True)


def stock_actions_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Qo'shish", callback_data=f"stock_add_{product_id}"),
        InlineKeyboardButton(text="➖ Kamaytirish", callback_data=f"stock_sub_{product_id}"),
    )
    builder.row(InlineKeyboardButton(text="✏️ Narxni o'zgartirish", callback_data=f"stock_price_{product_id}"))
    builder.row(InlineKeyboardButton(text="🗑 Mahsulotni o'chirish", callback_data=f"prod_delete_{product_id}"))
    return builder.as_markup()


def transfer_approve_kb(transfer_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"transfer_yes_{transfer_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"transfer_no_{transfer_id}"),
    )
    return builder.as_markup()


def order_status_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Qabul qilindi", callback_data=f"ord_accept_{order_id}"),
        InlineKeyboardButton(text="🚚 Yetkazilmoqda", callback_data=f"ord_delivery_{order_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="✔️ Bajarildi", callback_data=f"ord_done_{order_id}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data=f"ord_cancel_{order_id}"),
    )
    return builder.as_markup()


# ─── ADMIN ───────────────────────────────────────────
def admin_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🏪 Filiallar boshqaruvi"))
    builder.row(KeyboardButton(text="👥 Foydalanuvchilar"))
    builder.row(KeyboardButton(text="📊 Umumiy statistika"))
    builder.row(KeyboardButton(text="📈 Prognozlar"))
    builder.row(KeyboardButton(text="➕ Yangi filial qo'shish"))
    builder.row(KeyboardButton(text="🏠 Asosiy menyu"))
    return builder.as_markup(resize_keyboard=True)


def stats_period_kb(prefix: str = "stats") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Kunlik", callback_data=f"{prefix}_daily"),
        InlineKeyboardButton(text="📆 Haftalik", callback_data=f"{prefix}_weekly"),
    )
    builder.row(
        InlineKeyboardButton(text="🗓 Oylik", callback_data=f"{prefix}_monthly"),
        InlineKeyboardButton(text="📊 Yillik", callback_data=f"{prefix}_yearly"),
    )
    return builder.as_markup()


def branches_kb(branches: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in branches:
        builder.row(InlineKeyboardButton(
            text=f"🏪 {b['name']}",
            callback_data=f"branch_{b['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🌐 Barcha filiallar", callback_data="branch_all"))
    return builder.as_markup()
