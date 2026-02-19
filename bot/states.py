from aiogram.fsm.state import State, StatesGroup

class DepositFlow(StatesGroup):
    amount = State()
    method = State()
    screenshot = State()
    sender = State()
    txid = State()

class WithdrawFlow(StatesGroup):
    method = State()
    address = State()
    amount = State()

class AdminAddProduct(StatesGroup):
    name = State()
    price = State()
    stock = State()
    delivery = State()

class AdminBroadcast(StatesGroup):
    content = State()
