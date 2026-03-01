from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal
from models.user import User
from models.product import Product, UserProduct, PurchaseHistory
from datetime import datetime, timedelta
from sqlalchemy import func, extract


# ── Înregistrează cumpărăturile când userul finalizează ──────────────────────
async def inregistreaza_cumparaturi(user_id_db, produse_cumparate, db):
    """
    Apelat automat din lista.py când userul apasă 'Am finalizat cumpărăturile!'
    produse_cumparate = lista de (UserProduct, Product)
    """
    for up, prod in produse_cumparate:
        diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
        if diferenta <= 0:
            continue

        pret_total = diferenta * (prod.avg_price or 0)

        intrare = PurchaseHistory(
            user_id=user_id_db,
            product_id=prod.id,
            quantity=diferenta,
            total_price=pret_total,
            purchased_at=datetime.now()
        )
        db.add(intrare)

    db.commit()


# ── Comanda /buget ────────────────────────────────────────────────────────────
async def buget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    db.close()

    if not user:
        await update.message.reply_text("❌ Nu ești înregistrat. Trimite /start.")
        return

    await afiseaza_meniu_buget(update.message, user, edit=False)


# ── Meniu principal buget ─────────────────────────────────────────────────────
async def afiseaza_meniu_buget(target, user, edit=False):
    db = SessionLocal()

    # Cheltuieli luna curenta
    luna_curenta = datetime.now().month
    an_curent = datetime.now().year

    cheltuieli_luna = db.query(func.sum(PurchaseHistory.total_price))\
        .filter(
            PurchaseHistory.user_id == user.id,
            extract('month', PurchaseHistory.purchased_at) == luna_curenta,
            extract('year', PurchaseHistory.purchased_at) == an_curent
        ).scalar() or 0

    db.close()

    buget = user.monthly_budget or 0
    ramas = buget - cheltuieli_luna
    procent = (cheltuieli_luna / buget * 100) if buget > 0 else 0

    # Bara de progres vizuala
    bara = genereaza_bara_progres(procent)

    if buget == 0:
        status = "⚠️ Buget nesetat"
        ramas_text = "—"
    elif ramas >= 0:
        status = f"✅ Mai ai *{round(ramas)} lei*"
        ramas_text = f"{round(ramas)} lei"
    else:
        status = f"🔴 Depășit cu *{round(abs(ramas))} lei*"
        ramas_text = f"-{round(abs(ramas))} lei"

    text = (
        f"💰 *Bugetul tău lunar*\n\n"
        f"📅 Luna: {datetime.now().strftime('%B %Y')}\n\n"
        f"💵 Buget total: *{buget} lei*\n"
        f"🛒 Cheltuit: *{round(cheltuieli_luna)} lei*\n"
        f"💚 Rămas: *{ramas_text}*\n\n"
        f"{bara}\n"
        f"{status}"
    )

    butoane = [
        [InlineKeyboardButton("📊 Raport lunar", callback_data="buget_raport")],
        [InlineKeyboardButton("✏️ Schimbă bugetul", callback_data="buget_schimba")],
        [InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")],
    ]

    keyboard = InlineKeyboardMarkup(butoane)

    if edit:
        await target.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await target.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ── Bara de progres vizuală ───────────────────────────────────────────────────
def genereaza_bara_progres(procent):
    total_blocuri = 10
    pline = min(int(procent / 10), total_blocuri)
    goale = total_blocuri - pline

    if procent < 60:
        culoare = "🟩"
    elif procent < 85:
        culoare = "🟨"
    else:
        culoare = "🟥"

    bara = culoare * pline + "⬜" * goale
    return f"{bara} {round(procent)}%"


# ── Raport lunar complet ──────────────────────────────────────────────────────
async def afiseaza_raport_lunar(query, user):
    db = SessionLocal()

    luna_curenta = datetime.now().month
    an_curent = datetime.now().year
    luna_trecuta = (datetime.now().replace(day=1) - timedelta(days=1))

    # ── Total cheltuit luna curenta ──
    total_luna = db.query(func.sum(PurchaseHistory.total_price))\
        .filter(
            PurchaseHistory.user_id == user.id,
            extract('month', PurchaseHistory.purchased_at) == luna_curenta,
            extract('year', PurchaseHistory.purchased_at) == an_curent
        ).scalar() or 0

    # ── Total cheltuit luna trecuta ──
    total_luna_trecuta = db.query(func.sum(PurchaseHistory.total_price))\
        .filter(
            PurchaseHistory.user_id == user.id,
            extract('month', PurchaseHistory.purchased_at) == luna_trecuta.month,
            extract('year', PurchaseHistory.purchased_at) == luna_trecuta.year
        ).scalar() or 0

    # ── Lista produselor cumpărate luna asta ──
    produse_luna = db.query(
            Product.name,
            Product.unit,
            func.sum(PurchaseHistory.quantity).label('total_qty'),
            func.sum(PurchaseHistory.total_price).label('total_pret')
        )\
        .join(Product, PurchaseHistory.product_id == Product.id)\
        .filter(
            PurchaseHistory.user_id == user.id,
            extract('month', PurchaseHistory.purchased_at) == luna_curenta,
            extract('year', PurchaseHistory.purchased_at) == an_curent
        )\
        .group_by(Product.name, Product.unit)\
        .order_by(func.sum(PurchaseHistory.total_price).desc())\
        .all()

    # ── Produse cumpărate cel mai des (ultimele 3 luni) ──
    trei_luni_in_urma = datetime.now() - timedelta(days=90)
    produse_frecvente = db.query(
            Product.name,
            func.count(PurchaseHistory.id).label('frecventa')
        )\
        .join(Product, PurchaseHistory.product_id == Product.id)\
        .filter(
            PurchaseHistory.user_id == user.id,
            PurchaseHistory.purchased_at >= trei_luni_in_urma
        )\
        .group_by(Product.name)\
        .order_by(func.count(PurchaseHistory.id).desc())\
        .limit(5)\
        .all()

    db.close()

    buget = user.monthly_budget or 0

    # ── Construim textul raportului ──
    text = f"📊 *Raport lunar — {datetime.now().strftime('%B %Y')}*\n\n"

    # Total cheltuit vs buget
    text += "💰 *Total cheltuit vs. buget:*\n"
    text += f"• Buget: {buget} lei\n"
    text += f"• Cheltuit: {round(total_luna)} lei\n"

    if buget > 0:
        diferenta = buget - total_luna
        if diferenta >= 0:
            text += f"• ✅ Economii: *{round(diferenta)} lei*\n"
        else:
            text += f"• 🔴 Depășire: *{round(abs(diferenta))} lei*\n"

    # Economii față de luna trecută
    text += "\n📈 *Față de luna trecută:*\n"
    if total_luna_trecuta > 0:
        diferenta_luni = total_luna_trecuta - total_luna
        if diferenta_luni > 0:
            text += f"• ✅ Ai cheltuit cu *{round(diferenta_luni)} lei mai puțin* față de luna trecută!\n"
        elif diferenta_luni < 0:
            text += f"• 📈 Ai cheltuit cu *{round(abs(diferenta_luni))} lei mai mult* față de luna trecută.\n"
        else:
            text += "• Similar cu luna trecută.\n"
    else:
        text += "• Nu există date pentru luna trecută.\n"

    # Lista produselor cumpărate
    if produse_luna:
        text += "\n🛒 *Produse cumpărate luna aceasta:*\n"
        for nume, unit, qty, pret in produse_luna[:8]:
            text += f"• {nume}: {round(qty, 1)} {unit} — *{round(pret)} lei*\n"
        if len(produse_luna) > 8:
            text += f"_... și alte {len(produse_luna) - 8} produse_\n"

    # Produse cumpărate cel mai des
    if produse_frecvente:
        text += "\n⭐ *Produse cumpărate cel mai des (3 luni):*\n"
        medalii = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, (nume, frecventa) in enumerate(produse_frecvente):
            text += f"{medalii[i]} {nume} — {frecventa}x\n"

    butoane = [
        [InlineKeyboardButton("🔙 Înapoi la buget", callback_data="buget_inapoi")],
        [InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")],
    ]

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(butoane)
    )


# ── Callback handler pentru buget ────────────────────────────────────────────
async def callback_buget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
    db.close()

    if query.data == "buget_raport":
        await afiseaza_raport_lunar(query, user)

    elif query.data == "buget_schimba":
        await query.edit_message_text(
            "✏️ *Schimbă bugetul lunar*\n\n"
            f"Buget curent: *{user.monthly_budget} lei*\n\n"
            "Scrie noul buget în lei (ex: 3000):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Anulează", callback_data="buget_inapoi")]
            ])
        )
        context.user_data["asteapta_buget"] = True

    elif query.data == "buget_inapoi":
        await afiseaza_meniu_buget(query, user, edit=True)