import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from firebase_admin import firestore

from .config import (
    BOT_TOKEN, ADMIN_ID,
    WITHDRAW_GROUP_ID, DEPOSIT_GROUP_ID,
    BANNER_IMAGE_URL,
    BKASH_NUMBER, NAGAD_NUMBER, BINANCE_ID, CRYPTO_ADDRESS,
    MIN_WITHDRAW_BDT, WITHDRAW_FEE_PCT, USD_RATE_BDT,
    SUPPORT_USERNAME,
)
from .states import DepositFlow, WithdrawFlow, AdminAddProduct, AdminBroadcast
from .keyboards import main_menu, deposit_methods, withdraw_methods, admin_panel, approve_reject
from . import firebase_db as db

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def method_norm(text: str) -> str:
    t = (text or "").lower()
    if "bkash" in t: return "bkash"
    if "nagad" in t: return "nagad"
    if "binance" in t: return "binance"
    if "crypto" in t: return "crypto"
    return ""

def payment_details(method: str) -> str:
    if method == "bkash":
        return f"📱 bKash Send Money: {BKASH_NUMBER}"
    if method == "nagad":
        return f"📱 Nagad Send Money: {NAGAD_NUMBER}"
    if method == "binance":
        return f"💱 Binance Pay ID: {BINANCE_ID}"
    if method == "crypto":
        return f"🪙 Crypto Address: {CRYPTO_ADDRESS}"
    return "N/A"

# ---------------- Start ----------------
@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    db.ensure_user(m.from_user.id, m.from_user.full_name)
    await m.answer("✅ Welcome! Use menu ⬇️", reply_markup=main_menu(is_admin(m.from_user.id)))

# ---------------- Back ----------------
@dp.message(F.text == "⬅️ Back")
async def back(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("✅ Back to menu", reply_markup=main_menu(is_admin(m.from_user.id)))

# ---------------- Wallet ----------------
@dp.message(F.text == "💰 Wallet")
async def wallet(m: Message):
    bal = db.get_balance(m.from_user.id)
    await m.answer(f"💰 Balance: {bal:.2f} BDT")

# ---------------- Support ----------------
@dp.message(F.text == "🆘 Support")
async def support(m: Message):
    await m.answer(f"🆘 Support: {SUPPORT_USERNAME}")

# ---------------- History ----------------
@dp.message(F.text == "🧾 History")
async def history(m: Message):
    # last 5 deposits + withdraws + purchases
    deps = db.deposits().where("tg_id", "==", m.from_user.id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(5).stream()
    wds = db.withdraws().where("tg_id", "==", m.from_user.id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(5).stream()

    lines = ["🧾 History (last 5)\n", "➕ Deposits:"]
    dep_list = list(deps)
    if dep_list:
        for s in dep_list:
            d = s.to_dict()
            lines.append(f"• {d.get('method')} | {d.get('amount')} | {d.get('status')}")
    else:
        lines.append("• None")

    lines.append("\n🏧 Withdraws:")
    wd_list = list(wds)
    if wd_list:
        for s in wd_list:
            d = s.to_dict()
            lines.append(f"• {d.get('method')} | {d.get('amount')} | {d.get('status')}")
    else:
        lines.append("• None")

    await m.answer("\n".join(lines))

# ---------------- Deposit ----------------
@dp.message(F.text == "➕ Deposit")
async def deposit_start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("💵 Enter deposit amount (BDT)\nExample: 500", reply_markup=main_menu(False))
    await state.set_state(DepositFlow.amount)

@dp.message(DepositFlow.amount)
async def deposit_amount(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)
    try:
        amt = float(m.text.strip())
        if amt <= 0: raise ValueError
    except:
        return await m.answer("❌ Invalid amount. Example: 200")
    await state.update_data(amount=amt)
    await m.answer("✅ Select method:", reply_markup=deposit_methods())
    await state.set_state(DepositFlow.method)

@dp.message(DepositFlow.method)
async def deposit_method(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)

    method = method_norm(m.text)
    if method not in {"bkash", "nagad", "binance", "crypto"}:
        return await m.answer("❌ Choose from buttons.", reply_markup=deposit_methods())

    await state.update_data(method=method)
    await m.answer(
        f"✅ Method: {method.upper()}\n\n{payment_details(method)}\n\n📸 Now send payment screenshot (photo).",
        reply_markup=deposit_methods()
    )
    await state.set_state(DepositFlow.screenshot)

@dp.message(DepositFlow.screenshot)
async def deposit_screenshot(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)

    if not m.photo:
        return await m.answer("❌ Please send a screenshot photo.")

    await state.update_data(photo_file_id=m.photo[-1].file_id)
    await m.answer("✍️ Sender info (number/ID/address you paid from):")
    await state.set_state(DepositFlow.sender)

@dp.message(DepositFlow.sender)
async def deposit_sender(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)
    await state.update_data(sender=m.text.strip())
    await m.answer("🔑 Enter Transaction ID / Txn Hash:")
    await state.set_state(DepositFlow.txid)

@dp.message(DepositFlow.txid)
async def deposit_txid(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)

    data = await state.get_data()
    txid = m.text.strip()

    doc = db.deposits().document()
    req_id = doc.id
    doc.set({
        "req_id": req_id,
        "tg_id": m.from_user.id,
        "name": m.from_user.full_name,
        "amount": float(data["amount"]),
        "method": data["method"],
        "sender": data["sender"],
        "txid": txid,
        "photo_file_id": data["photo_file_id"],
        "status": "pending",
        "created_at": db.now_iso(),
        "admin_reply_sent": False,
    })

    caption = (
        f"🧾 *NEW DEPOSIT*\n\n"
        f"👤 User: `{m.from_user.id}`\n"
        f"👤 Name: {m.from_user.full_name}\n"
        f"💳 Method: *{data['method'].upper()}*\n"
        f"💵 Amount: *{data['amount']} BDT*\n"
        f"📌 Sender: `{data['sender']}`\n"
        f"🔑 TxID: `{txid}`\n\n"
        f"🆔 Request ID: `{req_id}`"
    )

    try:
        await bot.send_photo(
            chat_id=DEPOSIT_GROUP_ID,
            photo=URLInputFile(BANNER_IMAGE_URL),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=approve_reject("dep", req_id),
        )
        await bot.send_photo(
            chat_id=DEPOSIT_GROUP_ID,
            photo=data["photo_file_id"],
            caption=f"📸 User Screenshot | Request `{req_id}`",
            parse_mode="Markdown",
        )
    except:
        await bot.send_message(DEPOSIT_GROUP_ID, caption, parse_mode="Markdown", reply_markup=approve_reject("dep", req_id))
        await bot.send_photo(DEPOSIT_GROUP_ID, data["photo_file_id"], caption=f"📸 Screenshot | Request {req_id}")

    await m.answer("✅ Deposit request submitted. Please wait for admin verification.", reply_markup=main_menu(is_admin(m.from_user.id)))
    await state.clear()

# ---------------- Withdraw ----------------
@dp.message(F.text == "🏧 Withdraw")
async def withdraw_start(m: Message, state: FSMContext):
    await state.clear()
    bal = db.get_balance(m.from_user.id)
    await m.answer(
        f"🏧 Withdraw\n\n• Minimum: {MIN_WITHDRAW_BDT} BDT\n• Fee: {WITHDRAW_FEE_PCT}%\n• Rate info: 1$={USD_RATE_BDT} BDT\n\n💰 Balance: {bal:.2f} BDT\n\nSelect method:",
        reply_markup=withdraw_methods()
    )
    await state.set_state(WithdrawFlow.method)

@dp.message(WithdrawFlow.method)
async def withdraw_method(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)

    method = method_norm(m.text)
    if method not in {"bkash", "nagad", "binance"}:
        return await m.answer("❌ Choose from buttons.", reply_markup=withdraw_methods())

    await state.update_data(method=method)
    await m.answer("✍️ Enter correct Number / Binance ID:", reply_markup=withdraw_methods())
    await state.set_state(WithdrawFlow.address)

@dp.message(WithdrawFlow.address)
async def withdraw_address(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)
    await state.update_data(address=m.text.strip())
    await m.answer("💵 Enter withdraw amount (BDT):")
    await state.set_state(WithdrawFlow.amount)

@dp.message(WithdrawFlow.amount)
async def withdraw_amount(m: Message, state: FSMContext):
    if m.text == "⬅️ Back":
        return await back(m, state)

    data = await state.get_data()
    try:
        amt = float(m.text.strip())
    except:
        return await m.answer("❌ Invalid amount. Example: 500")

    if amt < MIN_WITHDRAW_BDT:
        return await m.answer(f"❌ Minimum withdraw is {MIN_WITHDRAW_BDT} BDT.")

    bal = db.get_balance(m.from_user.id)
    if amt > bal:
        return await m.answer(f"❌ Insufficient balance. Your balance: {bal:.2f} BDT")

    fee = round(amt * WITHDRAW_FEE_PCT / 100, 2)
    receive = round(amt - fee, 2)

    doc = db.withdraws().document()
    req_id = doc.id
    doc.set({
        "req_id": req_id,
        "tg_id": m.from_user.id,
        "name": m.from_user.full_name,
        "method": data["method"],
        "address": data["address"],
        "amount": amt,
        "fee": fee,
        "receive": receive,
        "status": "pending",
        "created_at": db.now_iso(),
        "admin_reply_sent": False,
    })

    caption = (
        f"🏧 *NEW WITHDRAW REQUEST*\n\n"
        f"👤 User: `{m.from_user.id}`\n"
        f"👤 Name: {m.from_user.full_name}\n"
        f"💳 Method: *{data['method'].upper()}*\n"
        f"📌 Address: `{data['address']}`\n"
        f"💵 Withdraw: *{amt} BDT*\n"
        f"📉 Fee (5%): *{fee}*\n"
        f"✅ Payable: *{receive} BDT*\n\n"
        f"🆔 Request ID: `{req_id}`\n"
        f"⚠️ Approve করলে user balance থেকে *{amt}* কেটে যাবে।"
    )

    try:
        await bot.send_photo(
            chat_id=WITHDRAW_GROUP_ID,
            photo=URLInputFile(BANNER_IMAGE_URL),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=approve_reject("wd", req_id),
        )
    except:
        await bot.send_message(WITHDRAW_GROUP_ID, caption, parse_mode="Markdown", reply_markup=approve_reject("wd", req_id))

    await m.answer(
        f"✅ Withdraw request submitted.\nFee: {fee} BDT | You will receive: {receive} BDT\n⏳ Wait for admin approval.",
        reply_markup=main_menu(is_admin(m.from_user.id))
    )
    await state.clear()

# ---------------- Group Approve/Reject callbacks ----------------
@dp.callback_query(F.data.startswith("dep:"))
async def deposit_approve_reject(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("Not allowed", show_alert=True)

    _, action, req_id = c.data.split(":")
    ref = db.deposits().document(req_id)
    snap = ref.get()
    if not snap.exists:
        return await c.answer("Not found", show_alert=True)
    d = snap.to_dict()

    if d.get("status") != "pending":
        return await c.answer("Already handled", show_alert=True)

    if action == "ok":
        db.add_balance(int(d["tg_id"]), float(d["amount"]))
        ref.update({"status": "approved", "approved_at": db.now_iso()})
        await bot.send_message(int(d["tg_id"]), f"✅ Deposit approved! +{float(d['amount']):.2f} BDT added.")
        await c.answer("Approved ✅", show_alert=True)
    else:
        ref.update({"status": "rejected", "rejected_at": db.now_iso()})
        await bot.send_message(int(d["tg_id"]), "❌ Deposit rejected. Please submit correct info.")
        await c.answer("Rejected ❌", show_alert=True)

@dp.callback_query(F.data.startswith("wd:"))
async def withdraw_approve_reject(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("Not allowed", show_alert=True)

    _, action, req_id = c.data.split(":")
    ref = db.withdraws().document(req_id)
    snap = ref.get()
    if not snap.exists:
        return await c.answer("Not found", show_alert=True)
    d = snap.to_dict()

    if d.get("status") != "pending":
        return await c.answer("Already handled", show_alert=True)

    if action == "ok":
        ok = db.deduct_balance(int(d["tg_id"]), float(d["amount"]))
        if not ok:
            ref.update({"status": "rejected", "rejected_at": db.now_iso(), "reason": "insufficient_balance"})
            await bot.send_message(int(d["tg_id"]), "❌ Withdraw rejected (insufficient balance).")
            return await c.answer("Insufficient balance", show_alert=True)

        ref.update({"status": "approved", "approved_at": db.now_iso()})
        await bot.send_message(
            int(d["tg_id"]),
            f"✅ Withdraw approved!\nAmount deducted: {float(d['amount']):.2f} BDT\nFee: {float(d['fee']):.2f} BDT\nPayable: {float(d['receive']):.2f} BDT"
        )
        await c.answer("Approved ✅ (deducted)", show_alert=True)
    else:
        ref.update({"status": "rejected", "rejected_at": db.now_iso()})
        await bot.send_message(int(d["tg_id"]), "❌ Withdraw rejected.")
        await c.answer("Rejected ❌", show_alert=True)

# ---------------- Admin reply in groups -> forward to user ----------------
@dp.message(F.chat.id.in_({DEPOSIT_GROUP_ID, WITHDRAW_GROUP_ID}))
async def admin_reply_forward(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    if not m.reply_to_message:
        return

    base = (m.reply_to_message.text or m.reply_to_message.caption or "")
    req_id = None
    if "`" in base:
        parts = base.split("`")
        if len(parts) >= 3:
            req_id = parts[-2].strip()
    if not req_id:
        return

    # decide which collection
    col = db.deposits() if m.chat.id == DEPOSIT_GROUP_ID else db.withdraws()
    ref = col.document(req_id)
    snap = ref.get()
    if not snap.exists:
        return
    d = snap.to_dict()
    if d.get("admin_reply_sent"):
        return

    uid = int(d["tg_id"])
    try:
        if m.photo:
            await bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption or "✅ Admin message")
        elif m.document:
            await bot.send_document(uid, m.document.file_id, caption=m.caption or "✅ Admin message")
        else:
            await bot.send_message(uid, m.text or (m.caption or "✅ Admin message"))
        ref.update({"admin_reply_sent": True, "admin_reply_at": db.now_iso()})
    except:
        pass

# ---------------- Products (site-like shop) ----------------
def products_inline(items):
    rows = []
    for pid, p in items:
        name = p.get("name", "Item")
        price = p.get("price", 0)
        stock = p.get("stock", 0)
        rows.append([InlineKeyboardButton(text=f"🛒 Buy: {name} ({price} BDT) | Stock {stock}", callback_data=f"buy:{pid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.message(F.text == "🛒 Products")
async def products_list(m: Message):
    items = db.list_products()
    if not items:
        return await m.answer("📦 No products available yet.")
    lines = ["🛒 Products:\n"]
    for pid, p in items:
        lines.append(f"• {p.get('name')} | {p.get('price')} BDT | Stock: {p.get('stock')}")
    await m.answer("\n".join(lines))
    await m.answer("👇 Tap to buy:", reply_markup=products_inline(items))

@dp.callback_query(F.data.startswith("buy:"))
async def buy(c: CallbackQuery):
    pid = c.data.split(":")[1]
    p = db.get_product(pid)
    if not p:
        return await c.answer("Not found", show_alert=True)

    stock = int(p.get("stock", 0))
    price = float(p.get("price", 0))

    if stock <= 0:
        return await c.answer("Out of stock", show_alert=True)

    bal = db.get_balance(c.from_user.id)
    if bal < price:
        return await c.answer("Insufficient balance", show_alert=True)

    ok = db.deduct_balance(c.from_user.id, price)
    if not ok:
        return await c.answer("Insufficient balance", show_alert=True)

    db.update_product(pid, {"stock": stock - 1})

    delivery = p.get("delivery", "✅ Delivered!")
    await bot.send_message(c.from_user.id, f"✅ Purchase successful!\n\n{delivery}")
    await c.answer("Purchased ✅", show_alert=True)

# ---------------- Admin Panel ----------------
@dp.message(F.text == "🛠 Admin Panel")
async def admin_panel_open(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    await m.answer("🛠 Admin Panel", reply_markup=admin_panel())

@dp.message(F.text == "👥 Total Users")
async def admin_total_users(m: Message):
    if not is_admin(m.from_user.id):
        return
    total = db.count_users()
    await m.answer(f"👥 Total Users: {total}")

@dp.message(F.text == "📦 Products")
async def admin_products(m: Message):
    if not is_admin(m.from_user.id):
        return
    items = db.list_products()
    if not items:
        return await m.answer("No products yet.")
    lines = ["📦 Products:\n"]
    for pid, p in items:
        lines.append(f"ID: {pid}\n• {p.get('name')} | Price {p.get('price')} | Stock {p.get('stock')}\n")
    await m.answer("\n".join(lines))

@dp.message(F.text == "➕ Add Product")
async def admin_add_product(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    await m.answer("📦 Product name লিখো:")
    await state.set_state(AdminAddProduct.name)

@dp.message(AdminAddProduct.name)
async def prod_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await m.answer("💵 Price (BDT) লিখো:")
    await state.set_state(AdminAddProduct.price)

@dp.message(AdminAddProduct.price)
async def prod_price(m: Message, state: FSMContext):
    try:
        price = float(m.text.strip())
        if price < 0: raise ValueError
    except:
        return await m.answer("❌ Invalid price. Example: 250")
    await state.update_data(price=price)
    await m.answer("📦 Stock / কতো জন পাবে লিখো (number):")
    await state.set_state(AdminAddProduct.stock)

@dp.message(AdminAddProduct.stock)
async def prod_stock(m: Message, state: FSMContext):
    try:
        stock = int(m.text.strip())
        if stock < 0: raise ValueError
    except:
        return await m.answer("❌ Invalid stock. Example: 50")
    await state.update_data(stock=stock)
    await m.answer("📩 Delivery text (যা user পাবে) লিখো:")
    await state.set_state(AdminAddProduct.delivery)

@dp.message(AdminAddProduct.delivery)
async def prod_delivery(m: Message, state: FSMContext):
    data = await state.get_data()
    pid = db.create_product(data["name"], float(data["price"]), int(data["stock"]), m.text)
    await state.clear()
    await m.answer(f"✅ Product added!\nID: {pid}", reply_markup=admin_panel())

@dp.message(F.text == "📢 Broadcast")
async def broadcast_start(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    await m.answer("📢 Send/forward message (text/photo/doc) to broadcast to all users.")
    await state.set_state(AdminBroadcast.content)

@dp.message(AdminBroadcast.content)
async def broadcast_send(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    # collect user ids
    user_ids = []
    for s in db.users().stream():
        user_ids.append(int(s.to_dict().get("tg_id")))

    sent = 0
    for uid in user_ids:
        try:
            if m.photo:
                await bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption or "")
            elif m.document:
                await bot.send_document(uid, m.document.file_id, caption=m.caption or "")
            else:
                await bot.send_message(uid, m.text or "")
            sent += 1
        except:
            continue

    await state.clear()
    await m.answer(f"✅ Broadcast done: {sent}/{len(user_ids)}", reply_markup=admin_panel())

# ---------------- Runner ----------------
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing. Put it in .env")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
