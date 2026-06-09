from aiogram import Dispatcher
from .registration import router as reg_router
from .order import router as order_router
from .moderator import router as mod_router
from .admin import router as admin_router


def register_all_handlers(dp: Dispatcher):
    dp.include_router(reg_router)
    dp.include_router(order_router)
    dp.include_router(mod_router)
    dp.include_router(admin_router)
