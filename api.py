# api.py — FastAPI backend pentru Mini App ShopBot
# Pornire: py -m uvicorn api:app --reload --port 8000

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import SessionLocal
from models.user import User
from models.product import Product, UserProduct, PurchaseHistory
from sqlalchemy import func, extract
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper: obține userul după telegram_id ────────────────────────────────────
def get_user(telegram_id: int, db):
    return db.query(User).filter_by(telegram_id=telegram_id).first()


# ══════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════
@app.get("/api/dashboard")
def dashboard(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {"eroare": "User negăsit"}

    luna, an = datetime.now().month, datetime.now().year

    cheltuit = db.query(func.sum(PurchaseHistory.total_price)).filter(
        PurchaseHistory.user_id == user.id,
        extract('month', PurchaseHistory.purchased_at) == luna,
        extract('year',  PurchaseHistory.purchased_at) == an
    ).scalar() or 0

    toate = db.query(UserProduct, Product)\
        .join(Product, UserProduct.product_id == Product.id)\
        .filter(UserProduct.user_id == user.id).all()

    produse_critice, de_cumparat = [], []
    for up, prod in toate:
        dorita  = up.desired_quantity or 0
        curenta = up.quantity or 0
        if dorita > 0:
            pct = round((curenta / dorita) * 100)
            if pct < 30:
                produse_critice.append({"name": prod.name, "procent": pct})
        if dorita - curenta > 0:
            de_cumparat.append({
                "name": prod.name,
                "cantitate": round(dorita - curenta, 1),
                "unit": prod.unit
            })

    db.close()
    return {
        "nume":            user.username or "Utilizator",
        "salary_day":      user.salary_day,
        "buget_total":     user.monthly_budget or 0,
        "cheltuit":        round(cheltuit),
        "produse_critice": produse_critice,
        "de_cumparat":     de_cumparat,
    }


# ══════════════════════════════════════════════
#  LISTĂ CUMPĂRĂTURI
# ══════════════════════════════════════════════
@app.get("/api/lista")
def lista(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {"produse": []}

    toate = db.query(UserProduct, Product)\
        .join(Product, UserProduct.product_id == Product.id)\
        .filter(UserProduct.user_id == user.id).all()

    produse = []
    for up, prod in toate:
        diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
        if diferenta > 0:
            produse.append({
                "up_id":            up.id,
                "product_id":       prod.id,
                "name":             prod.name,
                "category":         prod.category,
                "cantitate":        round(diferenta, 1),
                "desired_quantity": up.desired_quantity,
                "unit":             prod.unit,
                "pret_estimat":     round(diferenta * (prod.avg_price or 0)),
            })

    db.close()
    return {"produse": produse}


# ── Finalizare cumpărături ────────────────────────────────────────────────────
class FinalizeazaBody(BaseModel):
    up_ids: list[int]

@app.post("/api/finalizeaza")
def finalizeaza(telegram_id: int, body: FinalizeazaBody):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {"ok": False}

    for up_id in body.up_ids:
        up = db.query(UserProduct).filter_by(id=up_id, user_id=user.id).first()
        if not up:
            continue
        prod = db.query(Product).filter_by(id=up.product_id).first()
        diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
        if diferenta > 0:
            # Adaugă în istoricul de cumpărături
            db.add(PurchaseHistory(
                user_id=user.id,
                product_id=prod.id,
                quantity=diferenta,
                total_price=diferenta * (prod.avg_price or 0),
                purchased_at=datetime.now()
            ))
            # Actualizează stocul
            up.quantity = up.desired_quantity
        up.in_cart = 0

    db.commit()
    db.close()
    return {"ok": True}


# ── Actualizare cantitate dorită ──────────────────────────────────────────────
class DoритаBody(BaseModel):
    product_id: int
    quantity: float

@app.post("/api/dorita")
def update_dorita(telegram_id: int, body: DoритаBody):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {"ok": False}

    up = db.query(UserProduct).filter_by(user_id=user.id, product_id=body.product_id).first()
    if up:
        up.desired_quantity = body.quantity
    else:
        db.add(UserProduct(
            user_id=user.id, product_id=body.product_id,
            quantity=0, desired_quantity=body.quantity,
            min_quantity=1.0, is_on_list=0
        ))
    db.commit()
    db.close()
    return {"ok": True}


# ══════════════════════════════════════════════
#  STOC
# ══════════════════════════════════════════════
@app.get("/api/stoc")
def stoc(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {"produse": []}

    toate = db.query(UserProduct, Product)\
        .join(Product, UserProduct.product_id == Product.id)\
        .filter(UserProduct.user_id == user.id).all()

    produse = [{
        "product_id": prod.id,
        "name":       prod.name,
        "category":   prod.category,
        "stoc":       round(up.quantity or 0, 1),
        "desired":    round(up.desired_quantity or 0, 1),
        "unit":       prod.unit,
    } for up, prod in toate]

    db.close()
    return {"produse": produse}


# ── Actualizare stoc ──────────────────────────────────────────────────────────
class StocUpdateBody(BaseModel):
    product_id: int
    quantity: float

@app.post("/api/stoc/update")
def update_stoc(telegram_id: int, body: StocUpdateBody):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {"ok": False}

    up = db.query(UserProduct).filter_by(user_id=user.id, product_id=body.product_id).first()
    if up:
        up.quantity = body.quantity
    else:
        db.add(UserProduct(
            user_id=user.id, product_id=body.product_id,
            quantity=body.quantity, desired_quantity=0,
            min_quantity=1.0, is_on_list=0
        ))

    # Actualizează data ultimei modificări (pentru notificarea de stoc vechi)
    user.last_stock_update = datetime.now()
    db.commit()
    db.close()
    return {"ok": True}


# ══════════════════════════════════════════════
#  RAPORT LUNAR
# ══════════════════════════════════════════════
@app.get("/api/raport")
def raport(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {}

    luna, an = datetime.now().month, datetime.now().year
    luna_trecuta = (datetime.now().replace(day=1) - timedelta(days=1))

    # Total cheltuit luna curentă
    cheltuit = db.query(func.sum(PurchaseHistory.total_price)).filter(
        PurchaseHistory.user_id == user.id,
        extract('month', PurchaseHistory.purchased_at) == luna,
        extract('year',  PurchaseHistory.purchased_at) == an
    ).scalar() or 0

    # Total cheltuit luna trecută
    cheltuit_precedent = db.query(func.sum(PurchaseHistory.total_price)).filter(
        PurchaseHistory.user_id == user.id,
        extract('month', PurchaseHistory.purchased_at) == luna_trecuta.month,
        extract('year',  PurchaseHistory.purchased_at) == luna_trecuta.year
    ).scalar() or 0

    # Produse cumpărate luna aceasta (top după preț)
    produse_luna = db.query(
        Product.name, Product.unit,
        func.sum(PurchaseHistory.quantity).label('qty'),
        func.sum(PurchaseHistory.total_price).label('pret')
    ).join(Product, PurchaseHistory.product_id == Product.id)\
     .filter(
        PurchaseHistory.user_id == user.id,
        extract('month', PurchaseHistory.purchased_at) == luna,
        extract('year',  PurchaseHistory.purchased_at) == an
    ).group_by(Product.name, Product.unit)\
     .order_by(func.sum(PurchaseHistory.total_price).desc())\
     .limit(8).all()

    # Produse frecvente (ultimele 3 luni)
    trei_luni = datetime.now() - timedelta(days=90)
    frecvente = db.query(
        Product.name,
        func.count(PurchaseHistory.id).label('frecventa')
    ).join(Product, PurchaseHistory.product_id == Product.id)\
     .filter(
        PurchaseHistory.user_id == user.id,
        PurchaseHistory.purchased_at >= trei_luni
    ).group_by(Product.name)\
     .order_by(func.count(PurchaseHistory.id).desc())\
     .limit(5).all()

    db.close()
    return {
        "buget_total":            user.monthly_budget or 0,
        "cheltuit":               round(cheltuit),
        "cheltuit_luna_trecuta":  round(cheltuit_precedent),
        "produse_luna":           [{"name": n, "unit": u, "qty": round(q,1), "pret": round(p)} for n,u,q,p in produse_luna],
        "produse_frecvente":      [{"name": n, "frecventa": f} for n, f in frecvente],
    }


# ══════════════════════════════════════════════
#  SETĂRI CONT
# ══════════════════════════════════════════════
class SetariBody(BaseModel):
    monthly_budget: int
    salary_day: int

@app.post("/api/setari")
def setari(telegram_id: int, body: SetariBody):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    if not user:
        db.close()
        return {"ok": False}

    if not (1 <= body.salary_day <= 31):
        db.close()
        return {"ok": False, "eroare": "Ziua salariului invalidă"}

    user.monthly_budget = body.monthly_budget
    user.salary_date    = body.salary_day
    db.commit()
    db.close()
    return {"ok": True}


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ── Toate produsele disponibile (pentru sheet adăugare) ───────────────────────
@app.get("/api/produse")
def toate_produsele(telegram_id: int):
    db = SessionLocal()
    user = get_user(telegram_id, db)
    produse_db = db.query(Product).order_by(Product.category, Product.name).all()
    result = [{
        "id":        p.id,
        "name":      p.name,
        "category":  p.category,
        "unit":      p.unit,
        "avg_price": p.avg_price or 0,
    } for p in produse_db]
    db.close()
    return {"produse": result}