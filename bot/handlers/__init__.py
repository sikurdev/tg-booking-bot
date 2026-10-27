from aiogram import Router

from bot.handlers import admin, booking, common, my_bookings


def setup_routers() -> Router:
    root = Router()
    # Specific handlers first; fallback catch-all last so idle chatter gets the menu.
    root.include_router(booking.router)
    root.include_router(my_bookings.router)
    root.include_router(admin.router)
    root.include_router(common.router)
    root.include_router(common.fallback_router)
    return root
