from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="💰 Wallet"), KeyboardButton(text="➕ Deposit")],
        [KeyboardButton(text="🏧 Withdraw"), KeyboardButton(text="🛒 Products")],
        [KeyboardButton(text="🧾 History"), KeyboardButton(text="🆘 Support")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🛠 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def deposit_methods() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 bKash"), KeyboardButton(text="📱 Nagad")],
            [KeyboardButton(text="💱 Binance"), KeyboardButton(text="🪙 Crypto Address")],
            [KeyboardButton(text="⬅️ Back")],
        ],
        resize_keyboard=True
    )

def withdraw_methods() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 bKash"), KeyboardButton(text="📱 Nagad")],
            [KeyboardButton(text="💱 Binance")],
            [KeyboardButton(text="⬅️ Back")],
        ],
        resize_keyboard=True
    )

def admin_panel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Total Users"), KeyboardButton(text="📦 Products")],
            [KeyboardButton(text="➕ Add Product"), KeyboardButton(text="📢 Broadcast")],
            [KeyboardButton(text="⬅️ Back")],
        ],
        resize_keyboard=True
    )

def approve_reject(kind: str, req_id: str) -> InlineKeyboardMarkup:
    # kind: dep | wd
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"{kind}:ok:{req_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"{kind}:no:{req_id}"),
        ]
    ])
