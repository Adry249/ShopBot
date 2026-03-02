# api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal
from models.user import User
from models.product import Product, UserProduct, PurchaseHistory
from sqlalchemy import func, extract
from datetime import datetime, timedelta

app = FastAPI()

# CORS — permite Mini App-ului să acceseze API-ul
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user(telegram_id: int, db):
    return db.query(User).filter_by(telegram_id=telegram_id).first()

# ── Dashboard ────────────────────────────────────────────────────────────────
@app.get("/api/dashboard")
def dashboard(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        return {"eroare": "User negăsit"}

    luna = datetime.now().month
    an = datetime.now().year

    # Cheltuieli luna curenta
    cheltuit = db.query(func.sum(PurchaseHistory.total_price))\
        .filter(
            PurchaseHistory.user_id == user.id,
            extract('month', PurchaseHistory.purchased_at) == luna,
            extract('year', PurchaseHistory.purchased_at) == an
        ).scalar() or 0

    # Produse critice (sub 30%)
    produse_critice = []
    toate = db.query(UserProduct, Product)\
        .join(Product, UserProduct.product_id == Product.id)\
        .filter(UserProduct.user_id == user.id).all()

    de_cumparat = []
    for up, prod in toate:
        dorita = up.desired_quantity or 0
        curenta = up.quantity or 0
        if dorita > 0:
            procent = round((curenta / dorita) * 100)
            if procent < 30:
                produse_critice.append({
                    "name": prod.name, "procent": procent
                })
        diferenta = dorita - curenta
        if diferenta > 0:
            de_cumparat.append({
                "name": prod.name,
                "cantitate": round(diferenta, 1),
                "unit": prod.unit
            })

    db.close()
    return {
        "nume": user.username or "Utilizator",
        "buget_total": user.monthly_budget or 0,
        "cheltuit": round(cheltuit),
        "produse_critice": produse_critice,
        "de_cumparat": de_cumparat
    }

# ── Listă ────────────────────────────────────────────────────────────────────
@app.get("/api/lista")
def lista(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        return {"produse": []}

    toate = db.query(UserProduct, Product)\
        .join(Product, UserProduct.product_id == Product.id)\
        .filter(UserProduct.user_id == user.id).all()

    produse = []
    for up, prod in toate:
        diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
        if diferenta > 0:
            produse.append({
                "name": prod.name,
                "category": prod.category,
                "cantitate": round(diferenta, 1),
                "unit": prod.unit,
                "pret_estimat": round(diferenta * (prod.avg_price or 0))
            })

    db.close()
    return {"produse": produse}

# ── Stoc ─────────────────────────────────────────────────────────────────────
@app.get("/api/stoc")
def stoc(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        return {"produse": []}

    toate = db.query(UserProduct, Product)\
        .join(Product, UserProduct.product_id == Product.id)\
        .filter(UserProduct.user_id == user.id).all()

    produse = [{"name": prod.name, "category": prod.category,
                "stoc": round(up.quantity or 0, 1),
                "desired": round(up.desired_quantity or 0, 1),
                "unit": prod.unit}
               for up, prod in toate]

    db.close()
    return {"produse": produse}

# ── Buget ────────────────────────────────────────────────────────────────────
@app.get("/api/buget")
def buget(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        return {}

    luna = datetime.now().month
    an = datetime.now().year

    cheltuit = db.query(func.sum(PurchaseHistory.total_price))\
        .filter(
            PurchaseHistory.user_id == user.id,
            extract('month', PurchaseHistory.purchased_at) == luna,
            extract('year', PurchaseHistory.purchased_at) == an
        ).scalar() or 0

    trei_luni = datetime.now() - timedelta(days=90)
    frecvente = db.query(Product.name,
                         func.count(PurchaseHistory.id).label('frecventa'))\
        .join(Product, PurchaseHistory.product_id == Product.id)\
        .filter(PurchaseHistory.user_id == user.id,
                PurchaseHistory.purchased_at >= trei_luni)\
        .group_by(Product.name)\
        .order_by(func.count(PurchaseHistory.id).desc())\
        .limit(5).all()

    db.close()
    return {
        "buget_total": user.monthly_budget or 0,
        "cheltuit": round(cheltuit),
        "produse_frecvente": [{"name": n, "frecventa": f} for n, f in frecvente]
    }
