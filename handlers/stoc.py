# Gestionarea stocului de acasă

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal
from models.product import Product, UserProduct
from models.user import User
from datetime import datetime


# ── Comanda /stoc — afișează categoriile (mesaj nou) ─────────────────────────
async def stoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    categorii = [c[0] for c in db.query(Product.category).distinct().all()]
    db.close()

    butoane = [[InlineKeyboardButton(f"📦 {cat}", callback_data=f"stoc_cat_{cat}")]
               for cat in categorii]
    if context.user_data.get("din_lista"):
        butoane.append([InlineKeyboardButton(
            "✅ Gata, mergi la lista de cumpărături", callback_data="stoc_gata"
        )])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    await update.message.reply_text(
        "📦 *Stocul de acasă*\n\nAlege o categorie:",
        reply_markup=InlineKeyboardMarkup(butoane),
        parse_mode="Markdown"
    )


# ── Afișează categoriile stoc prin editare mesaj existent ────────────────────
async def afiseaza_categorii_stoc_edit(query, context):
    db = SessionLocal()
    categorii = [c[0] for c in db.query(Product.category).distinct().all()]
    db.close()

    butoane = [[InlineKeyboardButton(f"📦 {cat}", callback_data=f"stoc_cat_{cat}")]
               for cat in categorii]
    if context.user_data.get("din_lista"):
        butoane.append([InlineKeyboardButton(
            "✅ Gata, mergi la lista de cumpărături", callback_data="stoc_gata"
        )])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    await query.edit_message_text(
        "📦 *Stocul de acasă*\n\nAlege o categorie:",
        reply_markup=InlineKeyboardMarkup(butoane),
        parse_mode="Markdown"
    )


# ── Handler principal pentru toate callback-urile stocului ───────────────────
async def callback_stoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = SessionLocal()

    try:
        # Gata cu stocul — mergi la lista dorită
        if query.data == "stoc_gata":
            context.user_data["din_lista"] = False
            await afiseaza_lista_dorita(query, context)

        # Înapoi la lista de categorii stoc
        elif query.data == "stoc_inapoi_categorii":
            await afiseaza_categorii_stoc_edit(query, context)

        # Afișează produsele dintr-o categorie
        elif query.data.startswith("stoc_cat_"):
            categorie = query.data.replace("stoc_cat_", "")
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            produse = db.query(Product).filter_by(category=categorie).all()

            text = f"📦 *{categorie}* — Stoc acasă\n\n"
            butoane = []
            are_stoc = False

            for produs in produse:
                up = db.query(UserProduct).filter_by(
                    user_id=user.id if user else 0, product_id=produs.id
                ).first()
                cant = up.quantity if up else 0
                if cant > 0:
                    are_stoc = True
                text += f"• {produs.name}: *{cant} {produs.unit}*\n"
                butoane.append([InlineKeyboardButton(
                    f"✏️ {produs.name} ({cant} {produs.unit})",
                    callback_data=f"stoc_edit_{produs.id}"
                )])

            # Buton golire — doar dacă există produse cu stoc > 0
            if are_stoc:
                butoane.append([InlineKeyboardButton(
                    "🗑️ Golește produse din această categorie",
                    callback_data=f"stoc_goleste_{categorie}"
                )])
            butoane.append([InlineKeyboardButton("🔙 Înapoi la categorii", callback_data="stoc_inapoi_categorii")])
            if context.user_data.get("din_lista"):
                butoane.append([InlineKeyboardButton(
                    "✅ Gata, mergi la lista de cumpărături", callback_data="stoc_gata"
                )])
            butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

            await query.edit_message_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(butoane))

        # Editare cantitate pentru un produs
        elif query.data.startswith("stoc_edit_"):
            product_id = int(query.data.replace("stoc_edit_", ""))
            produs = db.query(Product).filter_by(id=product_id).first()
            context.user_data.update({
                "stoc_product_id":       product_id,
                "stoc_product_name":     produs.name,
                "stoc_product_unit":     produs.unit,
                "stoc_product_category": produs.category
            })
            await query.edit_message_text(
                f"✏️ *{produs.name}*\n\n"
                f"Cât ai acasă acum? (în {produs.unit})\n"
                f"Scrie `0` dacă nu mai ai deloc.",
                parse_mode="Markdown"
            )

        # Selectare produse de golit dintr-o categorie
        elif query.data.startswith("stoc_goleste_"):
            categorie = query.data.replace("stoc_goleste_", "")
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            produse = db.query(Product).filter_by(category=categorie).all()
            selectate = context.user_data.get("goleste_selectate", [])

            text = f"🗑️ *{categorie}* — Alege ce dorești să golești:\n\n"
            butoane = []
            for produs in produse:
                up = db.query(UserProduct).filter_by(
                    user_id=user.id if user else 0, product_id=produs.id
                ).first()
                cant = up.quantity if up else 0
                if cant > 0:
                    bifat = "✅" if produs.id in selectate else "⬜"
                    text += f"• {produs.name}: *{cant} {produs.unit}*\n"
                    butoane.append([InlineKeyboardButton(
                        f"{bifat} {produs.name} ({cant} {produs.unit})",
                        callback_data=f"stoc_toggle_{produs.id}_{categorie}"
                    )])

            if selectate:
                butoane.append([InlineKeyboardButton(
                    f"✅ Confirmă ({len(selectate)} produse)",
                    callback_data=f"stoc_confirma_golire_{categorie}"
                )])
            butoane.append([InlineKeyboardButton("🔙 Înapoi", callback_data=f"stoc_cat_{categorie}")])
            await query.edit_message_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(butoane))

        # Toggle selectare produs pentru golire
        elif query.data.startswith("stoc_toggle_"):
            parti = query.data.replace("stoc_toggle_", "").split("_")
            product_id = int(parti[0])
            categorie = "_".join(parti[1:])

            selectate = context.user_data.get("goleste_selectate", [])
            if product_id in selectate:
                selectate.remove(product_id)
            else:
                selectate.append(product_id)
            context.user_data["goleste_selectate"] = selectate

            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            produse = db.query(Product).filter_by(category=categorie).all()

            text = f"🗑️ *{categorie}* — Alege ce dorești să golești:\n\n"
            butoane = []
            for produs in produse:
                up = db.query(UserProduct).filter_by(
                    user_id=user.id if user else 0, product_id=produs.id
                ).first()
                cant = up.quantity if up else 0
                if cant > 0:
                    bifat = "✅" if produs.id in selectate else "⬜"
                    text += f"• {produs.name}: *{cant} {produs.unit}*\n"
                    butoane.append([InlineKeyboardButton(
                        f"{bifat} {produs.name} ({cant} {produs.unit})",
                        callback_data=f"stoc_toggle_{produs.id}_{categorie}"
                    )])

            if selectate:
                butoane.append([InlineKeyboardButton(
                    f"✅ Confirmă ({len(selectate)} produse)",
                    callback_data=f"stoc_confirma_golire_{categorie}"
                )])
            butoane.append([InlineKeyboardButton("🔙 Înapoi", callback_data=f"stoc_cat_{categorie}")])
            await query.edit_message_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(butoane))

        # Confirmă golirea produselor selectate
        elif query.data.startswith("stoc_confirma_golire_"):
            categorie = query.data.replace("stoc_confirma_golire_", "")
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            selectate = context.user_data.get("goleste_selectate", [])

            text = f"✅ *Produse golite din {categorie}:*\n\n"
            for product_id in selectate:
                up = db.query(UserProduct).filter_by(user_id=user.id, product_id=product_id).first()
                produs = db.query(Product).filter_by(id=product_id).first()
                if up:
                    up.quantity = 0
                    text += f"• {produs.name} — pus pe 0\n"
            db.commit()
            context.user_data["goleste_selectate"] = []

            butoane = [
                [InlineKeyboardButton("🔙 Înapoi la categorie",  callback_data=f"stoc_cat_{categorie}")],
                [InlineKeyboardButton("🔙 Înapoi la categorii", callback_data="stoc_inapoi_categorii")],
            ]
            if context.user_data.get("din_lista"):
                butoane.append([InlineKeyboardButton(
                    "✅ Gata, mergi la lista de cumpărături", callback_data="stoc_gata"
                )])
            await query.edit_message_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(butoane))

    finally:
        db.close()


# ── Primește cantitatea scrisă de utilizator pentru stoc ─────────────────────
async def primeste_cantitate_stoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "stoc_product_id" not in context.user_data:
        return

    text = update.message.text.strip().replace(",", ".")
    try:
        cantitate = float(text)
        if cantitate < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Scrie un număr pozitiv sau `0`.", parse_mode="Markdown")
        return

    product_id       = context.user_data.pop("stoc_product_id")
    product_name     = context.user_data.pop("stoc_product_name")
    product_unit     = context.user_data.pop("stoc_product_unit")
    product_category = context.user_data.pop("stoc_product_category")

    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()

    existent = db.query(UserProduct).filter_by(user_id=user.id, product_id=product_id).first()
    if existent:
        existent.quantity = cantitate
    else:
        db.add(UserProduct(user_id=user.id, product_id=product_id,
                           quantity=cantitate, desired_quantity=0,
                           min_quantity=1.0, is_on_list=0))

    # Actualizează data ultimei modificări de stoc pentru notificări
    user.last_stock_update = datetime.now()
    db.commit()

    # Reafișează categoria cu valorile actualizate
    produse  = db.query(Product).filter_by(category=product_category).all()
    text_msg = f"📦 *{product_category}* — Stoc acasă\n\n"
    butoane  = []
    for produs in produse:
        up = db.query(UserProduct).filter_by(user_id=user.id, product_id=produs.id).first()
        cant = up.quantity if up else 0
        text_msg += f"• {produs.name}: *{cant} {produs.unit}*\n"
        butoane.append([InlineKeyboardButton(
            f"✏️ {produs.name} ({cant} {produs.unit})",
            callback_data=f"stoc_edit_{produs.id}"
        )])

    butoane.append([InlineKeyboardButton("🔙 Înapoi la categorii", callback_data="stoc_inapoi_categorii")])
    if context.user_data.get("din_lista"):
        butoane.append([InlineKeyboardButton(
            "✅ Gata, mergi la lista de cumpărături", callback_data="stoc_gata"
        )])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    await update.message.reply_text(
        f"✅ *{product_name}* actualizat: {cantitate} {product_unit}\n\n" + text_msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(butoane)
    )
    db.close()


# ── Afișează lista dorită (după finalizarea stocului) ─────────────────────────
async def afiseaza_lista_dorita(query, context):
    db = SessionLocal()
    categorii = [c[0] for c in db.query(Product.category).distinct().all()]
    db.close()

    butoane = [[InlineKeyboardButton(f"🛒 {cat}", callback_data=f"dorita_cat_{cat}")]
               for cat in categorii]
    butoane.append([InlineKeyboardButton("🧾 Vezi lista finală de cumpărat", callback_data="vezi_lista_finala")])

    await query.edit_message_text(
        "🛒 *Lista dorită*\n\nAlege categoria și setează cantitățile dorite acasă:",
        reply_markup=InlineKeyboardMarkup(butoane),
        parse_mode="Markdown"
    )