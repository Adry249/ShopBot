# Gestionarea listei de cumpărături și coșului

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal
from models.product import Product, UserProduct
from models.user import User
from datetime import datetime


# ── Comanda /lista — întreabă dacă stocul e actualizat ───────────────────────
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 *Înainte de lista de cumpărături...*\n\n"
        "Ai actualizat stocul de acasă?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Da, continuă la listă",  callback_data="stoc_actualizat_da")],
            [InlineKeyboardButton("❌ Nu, mergi la stoc", callback_data="stoc_actualizat_nu")],
        ]),
        parse_mode="Markdown"
    )


# ── Afișează categoriile din lista dorită ─────────────────────────────────────
async def afiseaza_categorii_dorite(target, context, db):
    categorii = [c[0] for c in db.query(Product.category).distinct().all()]

    butoane = [[InlineKeyboardButton(f"🛒 {cat}", callback_data=f"dorita_cat_{cat}")]
               for cat in categorii]
    butoane.append([InlineKeyboardButton("🧾 Vezi lista finală de cumpărat", callback_data="vezi_lista_finala")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal",               callback_data="meniu_principal")])

    await target.edit_message_text(
        "🛒 *Lista dorită*\n\nAlege categoria și setează cantitățile dorite acasă:",
        reply_markup=InlineKeyboardMarkup(butoane),
        parse_mode="Markdown"
    )


# ── Afișează categoriile din stoc (când vine din lista) ──────────────────────
async def afiseaza_categorii_stoc_din_lista(query, context, db):
    categorii = [c[0] for c in db.query(Product.category).distinct().all()]

    butoane = [[InlineKeyboardButton(f"📦 {cat}", callback_data=f"stoc_cat_{cat}")]
               for cat in categorii]
    butoane.append([InlineKeyboardButton("✅ Gata, mergi la lista de cumpărături", callback_data="stoc_gata")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    await query.edit_message_text(
        "📦 *Stocul de acasă*\n\nActualizează stocul și apoi mergi la listă:",
        reply_markup=InlineKeyboardMarkup(butoane),
        parse_mode="Markdown"
    )


# ── Afișează lista finală cu coșul de cumpărături ────────────────────────────
async def afiseaza_lista_finala_cu_cos(query, context, db):
    user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
    if not user:
        await query.edit_message_text("❌ Nu ești înregistrat. Trimite /start.")
        return

    toate = db.query(UserProduct, Product)\
        .join(Product, UserProduct.product_id == Product.id)\
        .filter(UserProduct.user_id == user.id).all()

    de_cumparat, in_cos = [], []
    for up, prod in toate:
        diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
        if diferenta > 0:
            (in_cos if up.in_cart == 1 else de_cumparat).append((up, prod, diferenta))

    if not de_cumparat and not in_cos:
        await query.edit_message_text(
            "🎉 *Nu ai nevoie să cumperi nimic!*\n\nStocul tău acoperă tot ce dorești.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Înapoi la lista dorită", callback_data="dorita_inapoi")],
                [InlineKeyboardButton("🏠 Meniu principal",        callback_data="meniu_principal")],
            ])
        )
        return

    text, butoane = "", []

    if de_cumparat:
        text += "🧾 *De cumpărat:*\n"
        for up, prod, cant in de_cumparat:
            text += f"• {prod.name} — {round(cant, 2)} {prod.unit}\n"
            butoane.append([
                InlineKeyboardButton(f"🛒 {prod.name} în coș",  callback_data=f"cos_adauga_{up.id}"),
                InlineKeyboardButton(f"🗑️ Șterge",              callback_data=f"dorita_sterge_{up.id}")
            ])

    if in_cos:
        text += "\n🛒 *Coșul tău:*\n"
        for up, prod, cant in in_cos:
            text += f"✅ {prod.name} — {round(cant, 2)} {prod.unit}\n"
            butoane.append([InlineKeyboardButton(
                f"↩️ Scoate {prod.name} din coș", callback_data=f"cos_scoate_{up.id}"
            )])
        butoane.append([InlineKeyboardButton("🏁 Am finalizat cumpărăturile!", callback_data="cos_finalizeaza")])

    butoane.append([InlineKeyboardButton("🔙 Înapoi la lista dorită", callback_data="dorita_inapoi")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal",        callback_data="meniu_principal")])

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(butoane)
    )


# ── Handler principal pentru toate callback-urile listei ─────────────────────
async def callback_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = SessionLocal()

    try:
        # Răspuns la întrebarea despre stoc
        if query.data == "stoc_actualizat_da":
            await afiseaza_categorii_dorite(query, context, db)

        elif query.data == "stoc_actualizat_nu":
            context.user_data["din_lista"] = True
            await afiseaza_categorii_stoc_din_lista(query, context, db)

        elif query.data == "stoc_gata":
            context.user_data["din_lista"] = False
            await afiseaza_categorii_dorite(query, context, db)

        # Navigare categorii lista dorită
        elif query.data == "dorita_inapoi":
            await afiseaza_categorii_dorite(query, context, db)

        elif query.data.startswith("dorita_cat_"):
            categorie = query.data.replace("dorita_cat_", "")
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            produse = db.query(Product).filter_by(category=categorie).all()

            text = f"🛒 *{categorie}* — Cantități dorite acasă\n\n"
            butoane = []
            for produs in produse:
                up = db.query(UserProduct).filter_by(
                    user_id=user.id if user else 0, product_id=produs.id
                ).first()
                dorita = up.desired_quantity if up else 0
                text += f"• {produs.name}: *{dorita} {produs.unit}*\n"
                butoane.append([InlineKeyboardButton(
                    f"✏️ {produs.name} (doresc: {dorita} {produs.unit})",
                    callback_data=f"dorita_edit_{produs.id}"
                )])
            butoane.append([InlineKeyboardButton("🔙 Înapoi la categorii",  callback_data="dorita_inapoi")])
            butoane.append([InlineKeyboardButton("🧾 Vezi lista finală",     callback_data="vezi_lista_finala")])
            butoane.append([InlineKeyboardButton("🏠 Meniu principal",       callback_data="meniu_principal")])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(butoane))

        # Editare cantitate dorită pentru un produs
        elif query.data.startswith("dorita_edit_"):
            product_id = int(query.data.replace("dorita_edit_", ""))
            produs = db.query(Product).filter_by(id=product_id).first()
            context.user_data.update({
                "dorita_product_id":       product_id,
                "dorita_product_name":     produs.name,
                "dorita_product_unit":     produs.unit,
                "dorita_product_category": produs.category
            })
            await query.edit_message_text(
                f"✏️ *{produs.name}*\n\n"
                f"Cât dorești să ai acasă? (în {produs.unit})\n"
                f"Scrie `0` dacă nu vrei acest produs.",
                parse_mode="Markdown"
            )

        # Stergere produs din lista dorită
        elif query.data.startswith("dorita_sterge_"):
            up_id = int(query.data.replace("dorita_sterge_", ""))
            up = db.query(UserProduct).filter_by(id=up_id).first()
            if up:
                up.desired_quantity = 0
                up.in_cart = 0
                db.commit()
            await afiseaza_lista_finala_cu_cos(query, context, db)

        # Lista finală și coș
        elif query.data == "vezi_lista_finala":
            await afiseaza_lista_finala_cu_cos(query, context, db)

        elif query.data.startswith("cos_adauga_"):
            up_id = int(query.data.replace("cos_adauga_", ""))
            up = db.query(UserProduct).filter_by(id=up_id).first()
            if up:
                up.in_cart = 1
                db.commit()
            await afiseaza_lista_finala_cu_cos(query, context, db)

        elif query.data.startswith("cos_scoate_"):
            up_id = int(query.data.replace("cos_scoate_", ""))
            up = db.query(UserProduct).filter_by(id=up_id).first()
            if up:
                up.in_cart = 0
                db.commit()
            await afiseaza_lista_finala_cu_cos(query, context, db)

        # Finalizare cumpărături — actualizează stocul și înregistrează în istoric
        elif query.data == "cos_finalizeaza":
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            produse_cos = db.query(UserProduct, Product)\
                .join(Product, UserProduct.product_id == Product.id)\
                .filter(UserProduct.user_id == user.id, UserProduct.in_cart == 1).all()

            from handlers.buget import inregistreaza_cumparaturi
            await inregistreaza_cumparaturi(user.id, produse_cos, db)

            text = "🎉 *Cumpărături finalizate!*\n\n*Produse cumpărate:*\n"
            total_cheltuit = 0
            for up, prod in produse_cos:
                diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
                if diferenta > 0:
                    pret = diferenta * (prod.avg_price or 0)
                    total_cheltuit += pret
                    up.quantity = up.desired_quantity
                    up.in_cart = 0
                    text += f"✅ {prod.name} — {round(diferenta, 1)} {prod.unit}"
                    if pret > 0:
                        text += f" (~{round(pret)} lei)"
                    text += "\n"
            db.commit()

            if total_cheltuit > 0:
                text += f"\n💰 *Total estimat: ~{round(total_cheltuit)} lei*"

            # Verificare buget rămas
            from sqlalchemy import func, extract
            from models.product import PurchaseHistory
            luna, an = datetime.now().month, datetime.now().year
            total_luna = db.query(func.sum(PurchaseHistory.total_price))\
                .filter(
                    PurchaseHistory.user_id == user.id,
                    extract('month', PurchaseHistory.purchased_at) == luna,
                    extract('year',  PurchaseHistory.purchased_at) == an
                ).scalar() or 0

            if user.monthly_budget and user.monthly_budget > 0:
                ramas = user.monthly_budget - total_luna
                text += f"\n💚 *Buget rămas: {round(ramas)} lei*" if ramas >= 0 \
                    else f"\n🔴 *Buget depășit cu {round(abs(ramas))} lei!*"

            # Produse rămase necumpărate
            ramase = [(p.name, (up.desired_quantity or 0) - (up.quantity or 0), p.unit)
                      for up, p in db.query(UserProduct, Product)
                          .join(Product, UserProduct.product_id == Product.id)
                          .filter(UserProduct.user_id == user.id).all()
                      if (up.desired_quantity or 0) - (up.quantity or 0) > 0]

            text += "\n\n📦 *Stocul de acasă a fost actualizat automat!*"
            if ramase:
                text += f"\n⚠️ *Ai {len(ramase)} produs(e) rămase de cumpărat!*"

            butoane = []
            if ramase:
                butoane.append([InlineKeyboardButton("🔍 Vezi ce a rămas",    callback_data="vezi_ramase")])
            butoane.append([InlineKeyboardButton("📊 Raport buget",           callback_data="buget_raport_direct")])
            butoane.append([InlineKeyboardButton("🛒 Listă nouă",             callback_data="stoc_actualizat_da")])
            butoane.append([InlineKeyboardButton("🏠 Meniu principal",        callback_data="meniu_principal")])

            await query.edit_message_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(butoane))

        # Produse rămase după finalizare parțială
        elif query.data == "vezi_ramase":
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            toate = db.query(UserProduct, Product)\
                .join(Product, UserProduct.product_id == Product.id)\
                .filter(UserProduct.user_id == user.id).all()

            produse_ramase = [(up, prod, (up.desired_quantity or 0) - (up.quantity or 0))
                              for up, prod in toate
                              if (up.desired_quantity or 0) - (up.quantity or 0) > 0]

            text = "🔍 *Produse rămase de cumpărat:*\n\n"
            butoane = []
            for up, prod, cant in produse_ramase:
                text += f"• {prod.name} — {round(cant, 2)} {prod.unit}\n"
                butoane.append([InlineKeyboardButton(
                    f"🛒 {prod.name} în coș", callback_data=f"cos_adauga_{up.id}"
                )])
            text += "\n_Adaugă în coș ce găsești și finalizează din nou!_"
            butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

            await query.edit_message_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(butoane))

    finally:
        db.close()


# ── Primește cantitatea dorită scrisă de utilizator ───────────────────────────
async def primeste_cantitate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "dorita_product_id" not in context.user_data:
        return

    text = update.message.text.strip().replace(",", ".")
    try:
        cantitate = float(text)
        if cantitate < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Scrie un număr pozitiv sau `0`.", parse_mode="Markdown")
        return

    product_id       = context.user_data.pop("dorita_product_id")
    product_name     = context.user_data.pop("dorita_product_name")
    product_unit     = context.user_data.pop("dorita_product_unit")
    product_category = context.user_data.pop("dorita_product_category")

    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()

    existent = db.query(UserProduct).filter_by(user_id=user.id, product_id=product_id).first()
    if existent:
        existent.desired_quantity = cantitate
    else:
        db.add(UserProduct(user_id=user.id, product_id=product_id,
                           quantity=0, desired_quantity=cantitate,
                           min_quantity=1.0, is_on_list=0))
    db.commit()

    # Reafișează categoria curentă cu valorile actualizate
    produse  = db.query(Product).filter_by(category=product_category).all()
    text_msg = f"🛒 *{product_category}* — Cantități dorite acasă\n\n"
    butoane  = []
    for produs in produse:
        up = db.query(UserProduct).filter_by(user_id=user.id, product_id=produs.id).first()
        dorita = up.desired_quantity if up else 0
        text_msg += f"• {produs.name}: *{dorita} {produs.unit}*\n"
        butoane.append([InlineKeyboardButton(
            f"✏️ {produs.name} (doresc: {dorita} {produs.unit})",
            callback_data=f"dorita_edit_{produs.id}"
        )])
    butoane.append([InlineKeyboardButton("🔙 Înapoi la categorii", callback_data="dorita_inapoi")])
    butoane.append([InlineKeyboardButton("🧾 Vezi lista finală",    callback_data="vezi_lista_finala")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal",      callback_data="meniu_principal")])

    await update.message.reply_text(
        f"✅ *{product_name}* — doresc {cantitate} {product_unit}\n\n" + text_msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(butoane)
    )
    db.close()