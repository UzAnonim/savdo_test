from database.db import get_pool


# ─── USERS ───────────────────────────────────────────
async def get_user(telegram_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", telegram_id)


async def create_user(telegram_id: int, full_name: str, phone_main: str,
                      phone_extra: str = None, current_location: str = None,
                      home_address: str = None, latitude: float = None,
                      longitude: float = None, branch_id: int = 1):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO users (telegram_id, full_name, phone_main, phone_extra,
                               current_location, home_address, latitude, longitude, branch_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (telegram_id) DO UPDATE
            SET full_name=$2, phone_main=$3, phone_extra=$4,
                current_location=$5, home_address=$6, latitude=$7, longitude=$8
            RETURNING *
        """, telegram_id, full_name, phone_main, phone_extra,
            current_location, home_address, latitude, longitude, branch_id)


async def set_user_role(telegram_id: int, role: str, branch_id: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users SET role=$2, branch_id=COALESCE($3, branch_id)
            WHERE telegram_id=$1
        """, telegram_id, role, branch_id)


# ─── PRODUCTS ────────────────────────────────────────
async def get_all_products():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT p.*, c.name as category_name, c.icon as category_icon
            FROM products p JOIN categories c ON p.category_id=c.id
            WHERE p.is_active=TRUE ORDER BY c.id, p.name
        """)


async def get_products_by_category():
    pool = await get_pool()
    async with pool.acquire() as conn:
        categories = await conn.fetch("SELECT * FROM categories ORDER BY id")
        result = {}
        for cat in categories:
            products = await conn.fetch("""
                SELECT * FROM products WHERE category_id=$1 AND is_active=TRUE
            """, cat['id'])
            result[cat] = products
        return result


async def update_product(product_id: int, **kwargs):
    pool = await get_pool()
    async with pool.acquire() as conn:
        sets = ", ".join([f"{k}=${i+2}" for i, k in enumerate(kwargs.keys())])
        values = list(kwargs.values())
        await conn.execute(
            f"UPDATE products SET {sets} WHERE id=$1",
            product_id, *values
        )


async def add_product(category_id: int, name: str, unit: str,
                      weekly_qty: float, monthly_qty: float, price: float):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            INSERT INTO products (category_id, name, unit, weekly_qty_4person,
                                  monthly_qty_4person, price_per_unit)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
        """, category_id, name, unit, weekly_qty, monthly_qty, price)


async def delete_product(product_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE products SET is_active=FALSE WHERE id=$1", product_id)


# ─── BRANCHES ────────────────────────────────────────
async def get_all_branches():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM branches WHERE is_active=TRUE ORDER BY id")


async def get_branch(branch_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM branches WHERE id=$1", branch_id)


async def create_branch(name: str, address: str, latitude: float = None, longitude: float = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            INSERT INTO branches (name, address, latitude, longitude)
            VALUES ($1,$2,$3,$4) RETURNING id
        """, name, address, latitude, longitude)


async def get_nearest_branch_with_product(product_id: int, exclude_branch_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT b.*, bs.quantity,
                   SQRT(POWER(b.latitude - eb.latitude,2) + POWER(b.longitude - eb.longitude,2)) as distance
            FROM branch_stock bs
            JOIN branches b ON bs.branch_id=b.id
            JOIN branches eb ON eb.id=$2
            WHERE bs.product_id=$1 AND bs.quantity > 0 AND bs.branch_id != $2 AND b.is_active=TRUE
            ORDER BY distance ASC
            LIMIT 5
        """, product_id, exclude_branch_id)


# ─── STOCK ───────────────────────────────────────────
async def get_branch_stock(branch_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT bs.*, p.name, p.unit, p.price_per_unit, c.name as category_name
            FROM branch_stock bs
            JOIN products p ON bs.product_id=p.id
            JOIN categories c ON p.category_id=c.id
            WHERE bs.branch_id=$1
            ORDER BY c.id, p.name
        """, branch_id)


async def update_stock(branch_id: int, product_id: int, quantity: float, min_quantity: float = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO branch_stock (branch_id, product_id, quantity, min_quantity)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (branch_id, product_id) DO UPDATE
            SET quantity=$3, min_quantity=COALESCE($4, branch_stock.min_quantity), updated_at=NOW()
        """, branch_id, product_id, quantity, min_quantity)


async def get_low_stock(branch_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT bs.*, p.name, p.unit
            FROM branch_stock bs JOIN products p ON bs.product_id=p.id
            WHERE bs.branch_id=$1 AND bs.quantity <= bs.min_quantity
        """, branch_id)


# ─── ORDERS ──────────────────────────────────────────
async def create_order(user_id: int, branch_id: int, items: list, note: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            total = sum(i['qty'] * i['price'] for i in items)
            order_id = await conn.fetchval("""
                INSERT INTO orders (user_id, branch_id, total_price, note)
                VALUES ($1,$2,$3,$4) RETURNING id
            """, user_id, branch_id, total, note)
            for item in items:
                item_total = item['qty'] * item['price']
                await conn.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price_per_unit, total_price)
                    VALUES ($1,$2,$3,$4,$5)
                """, order_id, item['product_id'], item['qty'], item['price'], item_total)
            return order_id


async def get_user_orders(user_id: int, limit: int = 10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT o.*, b.name as branch_name
            FROM orders o JOIN branches b ON o.branch_id=b.id
            WHERE o.user_id=$1 ORDER BY o.created_at DESC LIMIT $2
        """, user_id, limit)


async def get_order_items(order_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT oi.*, p.name, p.unit
            FROM order_items oi JOIN products p ON oi.product_id=p.id
            WHERE oi.order_id=$1
        """, order_id)


async def update_order_status(order_id: int, status: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders SET status=$2, updated_at=NOW() WHERE id=$1
        """, order_id, status)


# ─── TRANSFERS ───────────────────────────────────────
async def create_transfer_request(from_branch: int, to_branch: int,
                                   product_id: int, quantity: float,
                                   requested_by: int, note: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            INSERT INTO transfer_requests
            (from_branch_id, to_branch_id, product_id, quantity, requested_by, note)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
        """, from_branch, to_branch, product_id, quantity, requested_by, note)


async def get_pending_transfers(branch_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT tr.*, p.name as product_name, p.unit,
                   b1.name as from_branch, b2.name as to_branch
            FROM transfer_requests tr
            JOIN products p ON tr.product_id=p.id
            JOIN branches b1 ON tr.from_branch_id=b1.id
            JOIN branches b2 ON tr.to_branch_id=b2.id
            WHERE tr.from_branch_id=$1 AND tr.status='pending'
        """, branch_id)


async def approve_transfer(transfer_id: int, approved_by: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            tr = await conn.fetchrow("SELECT * FROM transfer_requests WHERE id=$1", transfer_id)
            if tr and tr['status'] == 'pending':
                await conn.execute("""
                    UPDATE transfer_requests SET status='approved', approved_by=$2, updated_at=NOW()
                    WHERE id=$1
                """, transfer_id, approved_by)
                await conn.execute("""
                    INSERT INTO branch_stock (branch_id, product_id, quantity)
                    VALUES ($1,$2,$3)
                    ON CONFLICT (branch_id, product_id) DO UPDATE
                    SET quantity=branch_stock.quantity - $3, updated_at=NOW()
                """, tr['from_branch_id'], tr['product_id'], tr['quantity'])
                await conn.execute("""
                    INSERT INTO branch_stock (branch_id, product_id, quantity)
                    VALUES ($1,$2,$3)
                    ON CONFLICT (branch_id, product_id) DO UPDATE
                    SET quantity=branch_stock.quantity + $3, updated_at=NOW()
                """, tr['to_branch_id'], tr['product_id'], tr['quantity'])
            return tr


# ─── STATISTICS ──────────────────────────────────────
async def get_stats(branch_id: int = None, period: str = 'daily'):
    pool = await get_pool()
    async with pool.acquire() as conn:
        period_map = {
            'daily': "NOW() - INTERVAL '1 day'",
            'weekly': "NOW() - INTERVAL '7 days'",
            'monthly': "NOW() - INTERVAL '30 days'",
            'yearly': "NOW() - INTERVAL '365 days'",
        }
        since = period_map.get(period, period_map['daily'])
        branch_filter = "AND o.branch_id=$2" if branch_id else ""
        params = [since] if not branch_id else [since, branch_id]

        return await conn.fetchrow(f"""
            SELECT
                COUNT(DISTINCT o.id) as total_orders,
                COALESCE(SUM(o.total_price), 0) as total_revenue,
                COUNT(DISTINCT o.user_id) as unique_customers,
                COALESCE(AVG(o.total_price), 0) as avg_order_price
            FROM orders o
            WHERE o.created_at >= $1 {branch_filter}
        """, *params)


async def get_top_products(branch_id: int = None, limit: int = 10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        branch_filter = "AND o.branch_id=$2" if branch_id else ""
        params = [limit] if not branch_id else [limit, branch_id]
        return await conn.fetch(f"""
            SELECT p.name, p.unit, SUM(oi.quantity) as total_qty,
                   SUM(oi.total_price) as total_revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id=o.id
            JOIN products p ON oi.product_id=p.id
            WHERE 1=1 {branch_filter}
            GROUP BY p.id, p.name, p.unit
            ORDER BY total_qty DESC LIMIT $1
        """, *params)
