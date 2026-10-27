"""UI strings: Ukrainian default, optional Russian."""

from __future__ import annotations

from typing import Any


TEXTS: dict[str, dict[str, str]] = {
    "uk": {
        "btn_book": "📅 Записатися",
        "btn_my": "🗂 Мої записи",
        "btn_contacts": "ℹ️ Контакти",
        "btn_admin": "👤 Адмін",
        "btn_cancel": "❌ Скасувати",
        "btn_back": "⬅️ Назад",
        "btn_home": "🏠 Головне меню",
        "btn_confirm": "✅ Підтвердити",
        "btn_share_phone": "📱 Поділитися номером",
        "btn_type_phone": "✏️ Ввести номер текстом",
        "btn_use_name": "Використати: {name}",
        "btn_cancel_booking": "Скасувати запис",
        "btn_book_again": "Записатися ще",
        "choose_service": "Оберіть послугу:",
        "choose_date": "Оберіть дату:",
        "choose_time": "Оберіть час:",
        "no_dates": "Немає доступних дат у горизонті бронювання.",
        "no_slots": "На цю дату немає вільних слотів. Оберіть іншу дату.",
        "ask_name": "Введіть ваше ім'я або натисніть кнопку нижче:",
        "ask_phone": "Поділіться номером телефону кнопкою нижче або введіть його текстом:",
        "invalid_phone": "Невірний номер. Приклад: +380XXXXXXXXX або 0XXXXXXXXX",
        "confirm_title": "Перевірте запис:",
        "booked_ok": "✅ Запис створено!\n\n{details}",
        "cancelled_ok": "Запис скасовано.",
        "cancel_client_notify": "Ваш запис скасовано власником:\n{details}",
        "my_empty": "У вас немає активних записів.",
        "my_list": "Ваші записи:",
        "admin_denied": "Доступ лише для власника.",
        "admin_header": "🔧 Адмін-панель",
        "admin_today": "📅 Сьогодні",
        "admin_tomorrow": "📅 Завтра",
        "admin_block": "🚫 Заблокувати час",
        "admin_cancel": "❌ Скасувати",
        "admin_empty": "Записів немає.",
        "admin_cancel_booking": "Скасувати запис",
        "block_ask_day": (
            "Оберіть швидке блокування або надішліть день у форматі YYYY-MM-DD\n"
            "чи діапазон: YYYY-MM-DD HH:MM — YYYY-MM-DD HH:MM"
        ),
        "block_today": "🚫 Сьогодні (весь день)",
        "block_tomorrow": "🚫 Завтра (весь день)",
        "block_ok": "Блокування збережено.",
        "block_bad": (
            "Невірний формат. Приклад дня: 2026-11-01\n"
            "Приклад діапазону: 2026-11-01 14:00 — 2026-11-01 16:00"
        ),
        "owner_new": "🆕 Новий запис\n\n{details}",
        "owner_cancel": "🗑 Скасування запису\n\n{details}",
        "demo_owner_copy": "👁 [ДЕМО] Копія повідомлення власнику:\n\n{body}",
        "booked_ok_owner_combined": "{booked}\n\n{owner_body}",
        "service_line": "{name} · {duration} хв · {price}",
        "details": (
            "📍 {business}\n"
            "🛎 {service}\n"
            "🗓 {when}\n"
            "⏱ {duration} хв\n"
            "👤 {client_name}\n"
            "📞 {phone}"
        ),
        "menu_hint": "Оберіть дію кнопкою нижче 👇",
        "contacts_header": "ℹ️ Контакти",
        "hours_header": "Графік роботи",
        "day_off": "вихідний",
        "weekday_0": "Пн",
        "weekday_1": "Вт",
        "weekday_2": "Ср",
        "weekday_3": "Чт",
        "weekday_4": "Пт",
        "weekday_5": "Сб",
        "weekday_6": "Нд",
    },
    "ru": {
        "btn_book": "📅 Записаться",
        "btn_my": "🗂 Мои записи",
        "btn_contacts": "ℹ️ Контакты",
        "btn_admin": "👤 Админ",
        "btn_cancel": "❌ Отменить",
        "btn_back": "⬅️ Назад",
        "btn_home": "🏠 Главное меню",
        "btn_confirm": "✅ Подтвердить",
        "btn_share_phone": "📱 Поделиться номером",
        "btn_type_phone": "✏️ Ввести номер текстом",
        "btn_use_name": "Использовать: {name}",
        "btn_cancel_booking": "Отменить запись",
        "btn_book_again": "Записаться ещё",
        "choose_service": "Выберите услугу:",
        "choose_date": "Выберите дату:",
        "choose_time": "Выберите время:",
        "no_dates": "Нет доступных дат в горизонте бронирования.",
        "no_slots": "На эту дату нет свободных слотов. Выберите другую дату.",
        "ask_name": "Введите ваше имя или нажмите кнопку ниже:",
        "ask_phone": "Поделитесь номером кнопкой ниже или введите его текстом:",
        "invalid_phone": "Неверный номер. Пример: +380XXXXXXXXX или 0XXXXXXXXX",
        "confirm_title": "Проверьте запись:",
        "booked_ok": "✅ Запись создана!\n\n{details}",
        "cancelled_ok": "Запись отменена.",
        "cancel_client_notify": "Ваша запись отменена владельцем:\n{details}",
        "my_empty": "У вас нет активных записей.",
        "my_list": "Ваши записи:",
        "admin_denied": "Доступ только для владельца.",
        "admin_header": "🔧 Админ-панель",
        "admin_today": "📅 Сегодня",
        "admin_tomorrow": "📅 Завтра",
        "admin_block": "🚫 Заблокировать время",
        "admin_cancel": "❌ Отменить",
        "admin_empty": "Записей нет.",
        "admin_cancel_booking": "Отменить запись",
        "block_ask_day": (
            "Выберите быструю блокировку или отправьте день в формате YYYY-MM-DD\n"
            "или диапазон: YYYY-MM-DD HH:MM — YYYY-MM-DD HH:MM"
        ),
        "block_today": "🚫 Сегодня (весь день)",
        "block_tomorrow": "🚫 Завтра (весь день)",
        "block_ok": "Блокировка сохранена.",
        "block_bad": (
            "Неверный формат. Пример дня: 2026-11-01\n"
            "Пример диапазона: 2026-11-01 14:00 — 2026-11-01 16:00"
        ),
        "owner_new": "🆕 Новая запись\n\n{details}",
        "owner_cancel": "🗑 Отмена записи\n\n{details}",
        "demo_owner_copy": "👁 [ДЕМО] Копия сообщения владельцу:\n\n{body}",
        "booked_ok_owner_combined": "{booked}\n\n{owner_body}",
        "service_line": "{name} · {duration} мин · {price}",
        "details": (
            "📍 {business}\n"
            "🛎 {service}\n"
            "🗓 {when}\n"
            "⏱ {duration} мин\n"
            "👤 {client_name}\n"
            "📞 {phone}"
        ),
        "menu_hint": "Выберите действие кнопкой ниже 👇",
        "contacts_header": "ℹ️ Контакты",
        "hours_header": "График работы",
        "day_off": "выходной",
        "weekday_0": "Пн",
        "weekday_1": "Вт",
        "weekday_2": "Ср",
        "weekday_3": "Чт",
        "weekday_4": "Пт",
        "weekday_5": "Сб",
        "weekday_6": "Вс",
    },
}


def t(lang: str, key: str, **kwargs: Any) -> str:
    pack = TEXTS.get(lang) or TEXTS["uk"]
    template = pack.get(key) or TEXTS["uk"].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


def all_langs(key: str) -> set[str]:
    """Return the button/label text for every language pack."""
    return {pack[key] for pack in TEXTS.values() if key in pack}
