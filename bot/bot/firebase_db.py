from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

from .config import FIREBASE_SERVICE_ACCOUNT

cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred)
db = firestore.client()

def now_iso() -> str:
    return datetime.utcnow().isoformat()

# Collections
def users():
    return db.collection("users")

def deposits():
    return db.collection("deposits")

def withdraws():
    return db.collection("withdraws")

def products():
    return db.collection("products")

# Users
def get_user_doc(tg_id: int):
    return users().document(str(tg_id))

def ensure_user(tg_id: int, name: str):
    doc = get_user_doc(tg_id)
    snap = doc.get()
    if not snap.exists:
        doc.set({"tg_id": tg_id, "name": name, "balance": 0.0, "created_at": now_iso()})

def get_balance(tg_id: int) -> float:
    snap = get_user_doc(tg_id).get()
    if not snap.exists:
        return 0.0
    return float(snap.to_dict().get("balance", 0.0))

def add_balance(tg_id: int, amount: float):
    doc = get_user_doc(tg_id)

    def txn(tx):
        snap = doc.get(transaction=tx)
        bal = float(snap.to_dict().get("balance", 0.0)) if snap.exists else 0.0
        tx.set(doc, {"balance": bal + amount}, merge=True)

    db.run_transaction(txn)

def deduct_balance(tg_id: int, amount: float) -> bool:
    doc = get_user_doc(tg_id)

    def txn(tx):
        snap = doc.get(transaction=tx)
        if not snap.exists:
            return False
        bal = float(snap.to_dict().get("balance", 0.0))
        if bal < amount:
            return False
        tx.update(doc, {"balance": bal - amount})
        return True

    return db.run_transaction(txn)

# Counts (simple stream count)
def count_users() -> int:
    return sum(1 for _ in users().stream())

# Products
def create_product(name: str, price: float, stock: int, delivery: str) -> str:
    doc = products().document()
    doc.set({
        "name": name, "price": price, "stock": stock, "delivery": delivery,
        "created_at": now_iso()
    })
    return doc.id

def list_products():
    out = []
    for s in products().stream():
        p = s.to_dict()
        out.append((s.id, p))
    return out

def get_product(pid: str):
    doc = products().document(pid)
    snap = doc.get()
    if not snap.exists:
        return None
    return snap.to_dict()

def update_product(pid: str, data: dict):
    products().document(pid).update(data)

def delete_product(pid: str):
    products().document(pid).delete()
