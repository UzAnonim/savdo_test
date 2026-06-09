import asyncpg
import logging
from config import config

logger = logging.getLogger(__name__)

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Filiallar
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS branches (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                address TEXT,
                latitude FLOAT,
                longitude FLOAT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Foydalanuvchilar
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                full_name VARCHAR(150),
                phone_main VARCHAR(20),
                phone_extra VARCHAR(20),
                current_location TEXT,
                home_address TEXT,
                latitude FLOAT,
                longitude FLOAT,
                role VARCHAR(20) DEFAULT 'customer',
                branch_id INTEGER REFERENCES branches(id),
                is_active BOOLEAN DEFAULT TRUE,
                registered_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Mahsulotlar kategoriyalari
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                icon VARCHAR(10) DEFAULT '📦'
            )
        """)

        # Mahsulotlar
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                category_id INTEGER REFERENCES categories(id),
                name VARCHAR(150) NOT NULL,
                unit VARCHAR(30) DEFAULT 'kg',
                weekly_qty_4person FLOAT DEFAULT 0,
                monthly_qty_4person FLOAT DEFAULT 0,
                price_per_unit FLOAT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Filial zaxirasi
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS branch_stock (
                id SERIAL PRIMARY KEY,
                branch_id INTEGER REFERENCES branches(id),
                product_id INTEGER REFERENCES products(id),
                quantity FLOAT DEFAULT 0,
                min_quantity FLOAT DEFAULT 0,
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(branch_id, product_id)
            )
        """)

        # Buyurtmalar
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                branch_id INTEGER REFERENCES branches(id),
                status VARCHAR(30) DEFAULT 'pending',
                total_price FLOAT DEFAULT 0,
                note TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Buyurtma elementlari
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id),
                quantity FLOAT NOT NULL,
                price_per_unit FLOAT NOT NULL,
                total_price FLOAT NOT NULL
            )
        """)

        # Filiallararo transfer so'rovlari
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transfer_requests (
                id SERIAL PRIMARY KEY,
                from_branch_id INTEGER REFERENCES branches(id),
                to_branch_id INTEGER REFERENCES branches(id),
                product_id INTEGER REFERENCES products(id),
                quantity FLOAT NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                requested_by INTEGER REFERENCES users(id),
                approved_by INTEGER REFERENCES users(id),
                note TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Default filial va mahsulotlarni qo'shish
        await _seed_defaults(conn)

    logger.info("Ma'lumotlar bazasi tayyor ✅")


async def _seed_defaults(conn):
    # Default filial
    branch_exists = await conn.fetchval("SELECT id FROM branches LIMIT 1")
    if not branch_exists:
        await conn.execute("""
            INSERT INTO branches (name, address) VALUES
            ('Asosiy Filial', 'Qishloq markazi')
        """)

    # Kategoriyalar
    cat_exists = await conn.fetchval("SELECT id FROM categories LIMIT 1")
    if not cat_exists:
        await conn.execute("""
            INSERT INTO categories (name, icon) VALUES
            ('Don mahsulotlari', '🌾'),
            ('Yog'' va sut mahsulotlari', '🧈'),
            ('Sabzavotlar', '🥦'),
            ('Go''sht mahsulotlari', '🥩'),
            ('Dukkaklilar', '🫘'),
            ('Ziravorlar va boshqalar', '🧂')
        """)

    # Mahsulotlar
    prod_exists = await conn.fetchval("SELECT id FROM products LIMIT 1")
    if not prod_exists:
        await conn.execute("""
            INSERT INTO products (category_id, name, unit, weekly_qty_4person, monthly_qty_4person, price_per_unit) VALUES
            (1, 'Un', 'kg', 3.5, 14, 4500),
            (1, 'Guruch', 'kg', 2, 8, 12000),
            (1, 'Makaron', 'kg', 1, 4, 8000),
            (1, 'Shakar', 'kg', 1, 4, 10000),
            (1, 'Tuz', 'kg', 0.25, 1, 3000),
            (2, 'O''simlik yog''i', 'l', 1.5, 6, 18000),
            (2, 'Sariyog''', 'kg', 0.5, 2, 65000),
            (2, 'Qatiq', 'kg', 2, 8, 9000),
            (2, 'Suzma', 'kg', 1, 4, 15000),
            (2, 'Tuxum', 'dona', 20, 80, 1200),
            (3, 'Kartoshka', 'kg', 4, 16, 4000),
            (3, 'Piyoz', 'kg', 2, 8, 3000),
            (3, 'Sabzi', 'kg', 1.5, 6, 4000),
            (3, 'Sarimsoq', 'kg', 0.25, 1, 30000),
            (3, 'Qovoq', 'kg', 2, 8, 3000),
            (3, 'Bodring', 'kg', 1, 4, 8000),
            (3, 'Pomidor', 'kg', 2, 8, 9000),
            (4, 'Mol go''shti', 'kg', 2, 8, 85000),
            (4, 'Qo''y go''shti', 'kg', 1, 4, 95000),
            (4, 'Tovuq go''shti', 'kg', 2, 8, 40000),
            (5, 'Loviya', 'kg', 0.5, 2, 12000),
            (5, 'No''xat', 'kg', 0.5, 2, 14000),
            (5, 'Mosh', 'kg', 0.5, 2, 13000),
            (6, 'Choy', 'gr', 100, 400, 45000),
            (6, 'Zira', 'gr', 50, 200, 25000),
            (6, 'Qalampir', 'gr', 30, 120, 20000)
        """)
