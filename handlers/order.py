from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.queries import (
    get_user, get_all_products, create_order, get_user_orders, get_order_items
)
from keyboards.keyboards import (
    order_type_kb, products_inline_kb, confirm_order_kb, main_menu_kb
)

router = Router()


class OrderFSM(StatesGroup):
    choosing_type = State()
    selecting_products = State()
    confirming = State()
    note = State()


def format_price(price: float) -> str:
    return f"{int(price):,}".replace(",", " ")


@router.message(F.text == "🛒 Buyurtma berish")
async def start_order(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❗ Avval ro'yxatdan o'ting. /start bosing.")
        return

    await message.answer(
        "🛒 <b>Buyurtma turi tanlang:</b>\n\n"
        "📦 <b>Barcha mahsulotlar</b> — to'liq katalog\n"
        "🗓 <b>1 oylik</b> — 4 kishlik oilaga tavsiya\n"
        "📅 <b>1 haftalik</b> — 4 kishlik oilaga tavsiya",
        reply_markup=order_type_kb()
    )
    await state.set_state(OrderFSM.choosing_type)


@router.callback_query(F.data.in_({"order_all", "order_monthly", "order_weekly"}))
async def choose_order_type(callback: CallbackQuery, state: FSMContext):
    order_type = callback.data.replace("order_", "")
    products = await get_all_products()

    # Default miqdorlarni o'rnatish
    selected = {}
    if order_type == "monthly":
        selected = {p['id']: p['monthly_qty_4person'] for p in products if p['monthly_qty_4person'] > 0}
    elif order_type == "weekly":
        selected = {p['id']: p['weekly_qty_4person'] for p in products if p['weekly_qty_4person'] > 0}

    await state.update_data(
        products=[dict(p) for p in products],
        selected=selected,
        page=0,
        order_type=order_type
    )

    total = sum(selected.get(p['id'], 0) * p['price_per_unit'] for p in products)
    text = (
        f"🛍 <b>Mahsulotlar ro'yxati</b>\n"
        f"{'(1 oylik tavsiya miqdori sozlandi)' if order_type=='monthly' else ''}"
        f"{'(1 haftalik tavsiya miqdori sozlandi)' if order_type=='weekly' else ''}\n\n"
        f"➕/➖ tugmalari bilan miqdorni o'zgartiring\n"
        f"💰 Jami: <b>{format_price(total)} so'm</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=products_inline_kb(products, selected, 0)
    )
    await state.set_state(OrderFSM.selecting_products)


@router.callback_query(F.data.startswith("prod_plus_"))
async def product_plus(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected = data.get('selected', {})
    products = data.get('products', [])
    product = next((p for p in products if p['id'] == product_id), None)

    if product:
        step = 0.5 if product['unit'] == 'kg' else (100 if product['unit'] == 'gr' else 1)
        selected[product_id] = round(selected.get(product_id, 0) + step, 2)
        await state.update_data(selected=selected)
        await _refresh_products(callback, state)


@router.callback_query(F.data.startswith("prod_minus_"))
async def product_minus(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected = data.get('selected', {})
    products = data.get('products', [])
    product = next((p for p in products if p['id'] == product_id), None)

    if product and product_id in selected:
        step = 0.5 if product['unit'] == 'kg' else (100 if product['unit'] == 'gr' else 1)
        new_qty = round(selected[product_id] - step, 2)
        if new_qty <= 0:
            del selected[product_id]
        else:
            selected[product_id] = new_qty
        await state.update_data(selected=selected)
        await _refresh_products(callback, state)


@router.callback_query(F.data.startswith("prod_page_"))
async def product_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    await state.update_data(page=page)
    await _refresh_products(callback, state)


async def _refresh_products(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data.get('products', [])
    selected = data.get('selected', {})
    page = data.get('page', 0)

    total = sum(selected.get(p['id'], 0) * p['price_per_unit'] for p in products)
    count = len([k for k, v in selected.items() if v > 0])

    text = (
        f"🛍 <b>Mahsulotlar ro'yxati</b>\n\n"
        f"✅ Tanlangan: <b>{count} ta mahsulot</b>\n"
        f"💰 Jami: <b>{format_price(total)} so'm</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=products_inline_kb(products, selected, page)
    )


@router.callback_query(F.data == "order_confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data.get('products', [])
    selected = data.get('selected', {})

    if not selected:
        await callback.answer("❗ Hech narsa tanlanmagan!", show_alert=True)
        return

    lines = ["📋 <b>Buyurtmangiz:</b>\n"]
    total = 0
    for p in products:
        qty = selected.get(p['id'], 0)
        if qty > 0:
            price = qty * p['price_per_unit']
            total += price
            lines.append(f"• {p['name']}: <b>{qty} {p['unit']}</b> — {format_price(price)} so'm")

    lines.append(f"\n💰 <b>Jami: {format_price(total)} so'm</b>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=confirm_order_kb()
    )
    await state.set_state(OrderFSM.confirming)


@router.callback_query(F.data == "order_submit")
async def submit_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data.get('products', [])
    selected = data.get('selected', {})

    user = await get_user(callback.from_user.id)
    items = [
        {
            'product_id': p['id'],
            'qty': selected[p['id']],
            'price': p['price_per_unit']
        }
        for p in products if selected.get(p['id'], 0) > 0
    ]

    order_id = await create_order(user['id'], user['branch_id'], items)
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Buyurtma #{order_id} qabul qilindi!</b>\n\n"
        f"📦 Sizning buyurtmangiz ko'rib chiqilmoqda.\n"
        f"Holati haqida xabar beramiz.",
    )
    await callback.message.answer(
        "Bosh menyuga qaytdingiz 👇",
        reply_markup=main_menu_kb(user['role'])
    )


@router.callback_query(F.data == "order_edit")
async def edit_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data.get('products', [])
    selected = data.get('selected', {})
    page = data.get('page', 0)
    total = sum(selected.get(p['id'], 0) * p['price_per_unit'] for p in products)
    await callback.message.edit_text(
        f"✏️ <b>Buyurtmani tahrirlash</b>\n\n"
        f"💰 Jami: <b>{format_price(total)} so'm</b>",
        reply_markup=products_inline_kb(products, selected, page)
    )
    await state.set_state(OrderFSM.selecting_products)


@router.callback_query(F.data == "order_cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Buyurtma bekor qilindi.")


# ─── MY ORDERS ───────────────────────────────────────
@router.message(F.text == "📋 Mening buyurtmalarim")
async def my_orders(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❗ /start bosing.")
        return

    orders = await get_user_orders(user['id'])
    if not orders:
        await message.answer("📭 Hali buyurtmalaringiz yo'q.")
        return

    status_icons = {
        'pending': '⏳', 'accepted': '✅', 'delivery': '🚚',
        'done': '✔️', 'cancelled': '❌'
    }
    lines = ["📋 <b>Oxirgi buyurtmalaringiz:</b>\n"]
    for o in orders:
        icon = status_icons.get(o['status'], '❓')
        lines.append(
            f"{icon} <b>#{o['id']}</b> — {format_price(o['total_price'])} so'm\n"
            f"   📅 {o['created_at'].strftime('%d.%m.%Y %H:%M')}"
        )
    await message.answer("\n".join(lines))


# ─── MY PROFILE ──────────────────────────────────────
@router.message(F.text == "👤 Mening profilim")
async def my_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❗ /start bosing.")
        return

    role_names = {
        'customer': '🛒 Xaridor', 'moderator': '🛠 Moderator',
        'admin': '👑 Admin', 'superadmin': '🔑 Super Admin'
    }
    await message.answer(
        f"👤 <b>Profilingiz</b>\n\n"
        f"📛 Ism: <b>{user['full_name']}</b>\n"
        f"📱 Asosiy tel: <b>{user['phone_main']}</b>\n"
        f"📞 Qo'shimcha: <b>{user['phone_extra'] or 'Yo\'q'}</b>\n"
        f"📍 Joylashuv: <b>{user['current_location'] or 'Ko\'rsatilmagan'}</b>\n"
        f"🏠 Uy manzili: <b>{user['home_address'] or 'Ko\'rsatilmagan'}</b>\n"
        f"🎭 Rol: <b>{role_names.get(user['role'], user['role'])}</b>\n"
        f"📅 Ro'yxatdan: <b>{user['registered_at'].strftime('%d.%m.%Y')}</b>"
    )
