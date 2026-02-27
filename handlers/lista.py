from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal
from models.product import Product, UserProduct
from models.user import User

# ── Meniu principal ──
async def afiseaza_meniu_principal(target, edit=False):
    butoane = [
        [InlineKeyboardButton("🛒 Lista dorita", callback_data="meniu_lista_dorita")],
        [InlineKeyboardButton("📦 Stoc de acasa", callback_data="meniu_stoc")],
        [InlineKeyboardButton("🧾 Vezi lista finala de cumparat", callback_data="vezi_lista_finala")],
    ]
    keyboard = InlineKeyboardMarkup(butoane)
    text = "🏠 *Meniu principal*\n\nCe doresti sa faci?"

    if edit:
        await target.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await target.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ── Comanda /lista ──
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    butoane = [
        [InlineKeyboardButton("✅ Da, continua la lista", callback_data="stoc_actualizat_da")],
        [InlineKeyboardButton("❌ Nu, mergi la stoc", callback_data="stoc_actualizat_nu")],
    ]
    keyboard = InlineKeyboardMarkup(butoane)
    await update.message.reply_text(
        "📦 *Inainte de lista de cumparaturi...*\n\n"
        "Ai actualizat stocul de acasa?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ── Afiseaza categorii lista dorita ──
async def afiseaza_categorii_dorite(target, context, db):
    categorii = db.query(Product.category).distinct().all()
    categorii = [c[0] for c in categorii]

    butoane = []
    for categorie in categorii:
        butoane.append([InlineKeyboardButton(
            f"🛒 {categorie}",
            callback_data=f"dorita_cat_{categorie}"
        )])
    butoane.append([InlineKeyboardButton("🧾 Vezi lista finala de cumparat", callback_data="vezi_lista_finala")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    keyboard = InlineKeyboardMarkup(butoane)
    await target.edit_message_text(
        "🛒 *Lista dorita*\n\nAlege categoria si seteaza cantitatile dorite acasa:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ── Afiseaza categorii stoc (din lista) ──
async def afiseaza_categorii_stoc_din_lista(target, context, db):
    categorii = db.query(Product.category).distinct().all()
    categorii = [c[0] for c in categorii]

    butoane = []
    for categorie in categorii:
        butoane.append([InlineKeyboardButton(
            f"📦 {categorie}",
            callback_data=f"stoc_cat_{categorie}"
        )])
    butoane.append([InlineKeyboardButton("✅ Gata, mergi la lista dorita", callback_data="stoc_gata")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    keyboard = InlineKeyboardMarkup(butoane)
    await target.edit_message_text(
        "📦 *Stocul de acasa*\n\nActualizeaza ce ai acasa, apoi apasa Gata:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ── Handler principal pentru toate callback-urile listei ──
async def callback_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = SessionLocal()

    try:
        # ── Meniu principal ──
        if query.data == "meniu_principal":
            await afiseaza_meniu_principal(query, edit=True)

        elif query.data == "meniu_lista_dorita":
            await afiseaza_categorii_dorite(query, context, db)

        elif query.data == "meniu_stoc":
            context.user_data["din_lista"] = True
            await afiseaza_categorii_stoc_din_lista(query, context, db)

        # ── Intrebare stoc actualizat ──
        elif query.data == "stoc_actualizat_da":
            await afiseaza_categorii_dorite(query, context, db)

        elif query.data == "stoc_actualizat_nu":
            context.user_data["din_lista"] = True
            await afiseaza_categorii_stoc_din_lista(query, context, db)

        elif query.data == "stoc_gata":
            context.user_data["din_lista"] = False
            await afiseaza_categorii_dorite(query, context, db)

        # ── Categorii lista dorita ──
        elif query.data.startswith("dorita_cat_"):
            categorie = query.data.replace("dorita_cat_", "")
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
            produse = db.query(Product).filter_by(category=categorie).all()

            text = f"🛒 *{categorie}* — Cantitati dorite acasa\n\n"
            butoane = []

            for produs in produse:
                up = db.query(UserProduct).filter_by(
                    user_id=user.id if user else 0,
                    product_id=produs.id
                ).first()
                dorita = up.desired_quantity if up else 0
                text += f"• {produs.name}: *{dorita} {produs.unit}*\n"
                butoane.append([InlineKeyboardButton(
                    f"✏️ {produs.name} (doresc: {dorita} {produs.unit})",
                    callback_data=f"dorita_edit_{produs.id}"
                )])

            butoane.append([InlineKeyboardButton("🔙 Inapoi la categorii", callback_data="dorita_inapoi")])
            butoane.append([InlineKeyboardButton("🧾 Vezi lista finala", callback_data="vezi_lista_finala")])
            butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])
            keyboard = InlineKeyboardMarkup(butoane)
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

        elif query.data == "dorita_inapoi":
            await afiseaza_categorii_dorite(query, context, db)

        elif query.data.startswith("dorita_edit_"):
            product_id = int(query.data.replace("dorita_edit_", ""))
            produs = db.query(Product).filter_by(id=product_id).first()

            context.user_data["dorita_product_id"] = product_id
            context.user_data["dorita_product_name"] = produs.name
            context.user_data["dorita_product_unit"] = produs.unit
            context.user_data["dorita_product_category"] = produs.category

            await query.edit_message_text(
                f"✏️ *{produs.name}*\n\n"
                f"Cat doresti sa ai acasa? (in {produs.unit})\n"
                f"Scrie `0` daca nu vrei acest produs.",
                parse_mode="Markdown"
            )

        # ── Lista finala ──
        elif query.data == "vezi_lista_finala":
            user = db.query(User).filter_by(telegram_id=query.from_user.id).first()

            if not user:
                await query.edit_message_text("❌ Nu esti inregistrat. Trimite /start.")
                return

            toate = db.query(UserProduct, Product)\
                .join(Product, UserProduct.product_id == Product.id)\
                .filter(UserProduct.user_id == user.id)\
                .all()

            lista_finala = []
            for up, prod in toate:
                diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
                if diferenta > 0:
                    lista_finala.append((prod.name, diferenta, prod.unit))

            if not lista_finala:
                text = "🎉 *Nu ai nevoie sa cumperi nimic!*\n\nStocul tau acopera tot ce doresti."
            else:
                text = "🧾 *Lista finala de cumparat:*\n\n"
                for nume, cant, unit in lista_finala:
                    text += f"• {nume} — *{round(cant, 2)} {unit}*\n"
                text += "\n_Calculata din diferenta dintre ce doresti si ce ai acasa._"

            butoane = [
                [InlineKeyboardButton("🔙 Inapoi la lista dorita", callback_data="dorita_inapoi")],
                [InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")]
            ]
            keyboard = InlineKeyboardMarkup(butoane)
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    finally:
        db.close()

# ── Primeste cantitate dorita ──
async def primeste_cantitate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "dorita_product_id" not in context.user_data:
        return

    text = update.message.text.strip().replace(",", ".")

    try:
        cantitate = float(text)
        if cantitate < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Scrie un numar pozitiv sau `0`.", parse_mode="Markdown")
        return

    product_id = context.user_data["dorita_product_id"]
    product_name = context.user_data["dorita_product_name"]
    product_unit = context.user_data["dorita_product_unit"]
    product_category = context.user_data["dorita_product_category"]

    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()

    existent = db.query(UserProduct).filter_by(
        user_id=user.id, product_id=product_id
    ).first()

    if existent:
        existent.desired_quantity = cantitate
    else:
        db.add(UserProduct(
            user_id=user.id, product_id=product_id,
            quantity=0, desired_quantity=cantitate,
            min_quantity=1.0, is_on_list=0
        ))

    db.commit()

    del context.user_data["dorita_product_id"]
    del context.user_data["dorita_product_name"]
    del context.user_data["dorita_product_unit"]
    del context.user_data["dorita_product_category"]

    # Reafisam categoria
    produse = db.query(Product).filter_by(category=product_category).all()
    text_msg = f"🛒 *{product_category}* — Cantitati dorite acasa\n\n"
    butoane = []

    for produs in produse:
        up = db.query(UserProduct).filter_by(
            user_id=user.id, product_id=produs.id
        ).first()
        dorita = up.desired_quantity if up else 0
        text_msg += f"• {produs.name}: *{dorita} {produs.unit}*\n"
        butoane.append([InlineKeyboardButton(
            f"✏️ {produs.name} (doresc: {dorita} {produs.unit})",
            callback_data=f"dorita_edit_{produs.id}"
        )])

    butoane.append([InlineKeyboardButton("🔙 Inapoi la categorii", callback_data="dorita_inapoi")])
    butoane.append([InlineKeyboardButton("🧾 Vezi lista finala", callback_data="vezi_lista_finala")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])
    keyboard = InlineKeyboardMarkup(butoane)

    await update.message.reply_text(
        f"✅ *{product_name}* — doresc {cantitate} {product_unit}\n\n" + text_msg,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    db.close()