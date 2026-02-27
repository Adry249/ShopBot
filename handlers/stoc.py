from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal
from models.product import Product, UserProduct
from models.user import User

async def stoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await afiseaza_categorii_stoc_msg(update, context)

async def afiseaza_categorii_stoc_msg(update, context):
    db = SessionLocal()
    categorii = db.query(Product.category).distinct().all()
    categorii = [c[0] for c in categorii]
    db.close()

    butoane = []
    for categorie in categorii:
        butoane.append([InlineKeyboardButton(
            f"📦 {categorie}",
            callback_data=f"stoc_cat_{categorie}"
        )])

    if context.user_data.get("din_lista"):
        butoane.append([InlineKeyboardButton(
            "✅ Gata, mergi la lista de cumparaturi",
            callback_data="stoc_gata"
        )])

    keyboard = InlineKeyboardMarkup(butoane)
    await update.message.reply_text(
        "📦 *Stocul de acasa*\n\nAlege o categorie:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def afiseaza_categorii_stoc_edit(query, context):
    db = SessionLocal()
    categorii = db.query(Product.category).distinct().all()
    categorii = [c[0] for c in categorii]
    db.close()

    butoane = []
    for categorie in categorii:
        butoane.append([InlineKeyboardButton(
            f"📦 {categorie}",
            callback_data=f"stoc_cat_{categorie}"
        )])

    if context.user_data.get("din_lista"):
        butoane.append([InlineKeyboardButton(
            "✅ Gata, mergi la lista de cumparaturi",
            callback_data="stoc_gata"
        )])

    keyboard = InlineKeyboardMarkup(butoane)
    await query.edit_message_text(
        "📦 *Stocul de acasa*\n\nAlege o categorie:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def callback_stoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = SessionLocal()

    if query.data == "stoc_gata":
        context.user_data["din_lista"] = False
        db.close()
        await afiseaza_lista_dorita(query, context)
        return

    elif query.data == "stoc_inapoi_categorii":
        db.close()
        await afiseaza_categorii_stoc_edit(query, context)
        return

    elif query.data.startswith("stoc_cat_"):
        categorie = query.data.replace("stoc_cat_", "")
        user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
        produse = db.query(Product).filter_by(category=categorie).all()

        text = f"📦 *{categorie}* — Stoc acasa\n\n"
        butoane = []

        for produs in produse:
            up = db.query(UserProduct).filter_by(
                user_id=user.id if user else 0,
                product_id=produs.id
            ).first()
            cantitate_curenta = up.quantity if up else 0
            text += f"• {produs.name}: *{cantitate_curenta} {produs.unit}*\n"
            butoane.append([InlineKeyboardButton(
                f"✏️ {produs.name} ({cantitate_curenta} {produs.unit})",
                callback_data=f"stoc_edit_{produs.id}"
            )])

        butoane.append([InlineKeyboardButton("🔙 Inapoi la categorii", callback_data="stoc_inapoi_categorii")])

        if context.user_data.get("din_lista"):
            butoane.append([InlineKeyboardButton(
                "✅ Gata, mergi la lista de cumparaturi",
                callback_data="stoc_gata"
            )])

        keyboard = InlineKeyboardMarkup(butoane)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif query.data.startswith("stoc_edit_"):
        product_id = int(query.data.replace("stoc_edit_", ""))
        produs = db.query(Product).filter_by(id=product_id).first()

        context.user_data["stoc_product_id"] = product_id
        context.user_data["stoc_product_name"] = produs.name
        context.user_data["stoc_product_unit"] = produs.unit
        context.user_data["stoc_product_category"] = produs.category

        await query.edit_message_text(
            f"✏️ *{produs.name}*\n\n"
            f"Cat ai acasa acum? (in {produs.unit})\n"
            f"Scrie `0` daca nu mai ai deloc.",
            parse_mode="Markdown"
        )

    db.close()

async def primeste_cantitate_stoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "stoc_product_id" not in context.user_data:
        return

    text = update.message.text.strip().replace(",", ".")

    try:
        cantitate = float(text)
        if cantitate < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Scrie un numar pozitiv sau `0`.", parse_mode="Markdown")
        return

    product_id = context.user_data["stoc_product_id"]
    product_name = context.user_data["stoc_product_name"]
    product_unit = context.user_data["stoc_product_unit"]
    product_category = context.user_data["stoc_product_category"]

    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()

    existent = db.query(UserProduct).filter_by(
        user_id=user.id, product_id=product_id
    ).first()

    if existent:
        existent.quantity = cantitate
    else:
        db.add(UserProduct(
            user_id=user.id, product_id=product_id,
            quantity=cantitate, desired_quantity=0,
            min_quantity=1.0, is_on_list=0
        ))

    db.commit()

    del context.user_data["stoc_product_id"]
    del context.user_data["stoc_product_name"]
    del context.user_data["stoc_product_unit"]
    del context.user_data["stoc_product_category"]

    # Reafisam categoria cu buton inapoi
    produse = db.query(Product).filter_by(category=product_category).all()
    text_msg = f"📦 *{product_category}* — Stoc acasa\n\n"
    butoane = []

    for produs in produse:
        up = db.query(UserProduct).filter_by(
            user_id=user.id, product_id=produs.id
        ).first()
        cantitate_curenta = up.quantity if up else 0
        text_msg += f"• {produs.name}: *{cantitate_curenta} {produs.unit}*\n"
        butoane.append([InlineKeyboardButton(
            f"✏️ {produs.name} ({cantitate_curenta} {produs.unit})",
            callback_data=f"stoc_edit_{produs.id}"
        )])

    butoane.append([InlineKeyboardButton("🔙 Inapoi la categorii", callback_data="stoc_inapoi_categorii")])

    if context.user_data.get("din_lista"):
        butoane.append([InlineKeyboardButton(
            "✅ Gata, mergi la lista de cumparaturi",
            callback_data="stoc_gata"
        )])

    keyboard = InlineKeyboardMarkup(butoane)
    await update.message.reply_text(
        f"✅ *{product_name}* actualizat: {cantitate} {product_unit}\n\n" + text_msg,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    db.close()

async def afiseaza_lista_dorita(query, context):
    db = SessionLocal()
    categorii = db.query(Product.category).distinct().all()
    categorii = [c[0] for c in categorii]
    db.close()

    butoane = []
    for categorie in categorii:
        butoane.append([InlineKeyboardButton(
            f"🛒 {categorie}",
            callback_data=f"dorita_cat_{categorie}"
        )])
    butoane.append([InlineKeyboardButton(
        "🧾 Vezi lista finala de cumparat",
        callback_data="vezi_lista_finala"
    )])

    keyboard = InlineKeyboardMarkup(butoane)
    await query.edit_message_text(
        "🛒 *Lista dorita*\n\nAlege categoria si seteaza cantitatile dorite acasa:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )