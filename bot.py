# py -m uvicorn api:app --reload --port 8000
# .\ngrok.exe http 8000

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv
from handlers.start import get_conversation_handler, afiseaza_meniu, get_reply_keyboard
from handlers.lista import lista, callback_lista, primeste_cantitate
from handlers.stoc import stoc, callback_stoc, primeste_cantitate_stoc
from scheduler import porneste_scheduler
from handlers.buget import buget_command, callback_buget
import os

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def ajutor(update, context):
    await update.message.reply_text(
        "❓ *Ajutor ShopBot*\n\n"
        "🛒 *Lista* — seteaza cantitatile dorite si vezi ce trebuie sa cumperi\n"
        "📦 *Stoc* — actualizeaza ce ai acasa in prezent\n"
        "💰 *Buget* — seteaza bugetul lunar pentru cumparaturi\n"
        "🏠 *Meniu* — revino la meniul principal\n\n"
        "Foloseste butoanele de jos pentru navigare rapida!",
        parse_mode="Markdown"
    )

async def buget(update, context):
    await buget_command(update, context)
    # from database import SessionLocal
    from models.user import User
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    db.close()

    if not user:
        await update.message.reply_text("❌ Nu esti inregistrat. Trimite /start.")
        return

    await update.message.reply_text(
        f"💰 *Bugetul tau lunar*\n\n"
        f"Buget curent: *{user.monthly_budget} lei*\n\n"
        f"Scrie noul buget in lei (ex: 3000) sau /skip pentru a pastra cel actual:",
        parse_mode="Markdown"
    )
    context.user_data["asteapta_buget"] = True

async def router_text(update, context):
    text = update.message.text.strip()

    # Butoanele de jos de la tastatura
    if text == "🏠 Meniu":
        await afiseaza_meniu(update.message)
        return
    elif text == "🛒 Lista":
        await lista(update, context)
        return
    elif text == "📦 Stoc":
        await stoc(update, context)
        return
    elif text == "💰 Buget":
        await buget_command(update, context)
        return

    # Cantitati
    if "asteapta_buget" in context.user_data:
        from database import SessionLocal
        from models.user import User
        try:
            suma = int(text)
            db = SessionLocal()
            user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
            user.monthly_budget = suma
            db.commit()
            db.close()
            del context.user_data["asteapta_buget"]
            await update.message.reply_text(
                f"✅ Buget actualizat: *{suma} lei*",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ Scrie un numar valid, ex: 3000")
        return

    if "stoc_product_id" in context.user_data:
        await primeste_cantitate_stoc(update, context)
    elif "dorita_product_id" in context.user_data:
        await primeste_cantitate(update, context)

async def router_callback(update, context):
    data = update.callback_query.data

    stoc_prefixes = ["stoc_cat_", "stoc_edit_", "stoc_inapoi", "stoc_gata", "stoc_goleste_", "stoc_toggle_", "stoc_confirma_golire_"]
    if any(data.startswith(p) for p in stoc_prefixes):
        await callback_stoc(update, context)
    elif data == "meniu_principal":
        await update.callback_query.answer()
        await afiseaza_meniu(update.callback_query, edit=True)
    elif data == "meniu_lista":
        await update.callback_query.answer()
        await lista_din_meniu(update, context)
    elif data == "meniu_stoc_direct":
        await update.callback_query.answer()
        context.user_data["din_lista"] = False
        await stoc_din_meniu(update, context)
    elif data == "meniu_buget":
        await update.callback_query.answer()
        from database import SessionLocal
        from models.user import User
        from handlers.buget import afiseaza_meniu_buget
        db = SessionLocal()
        user = db.query(User).filter_by(telegram_id=update.callback_query.from_user.id).first()
        db.close()
        await afiseaza_meniu_buget(update.callback_query, user, edit=True)
    elif data.startswith("buget_") or data == "buget_raport_direct":
        if data == "buget_raport_direct":
            # Redirect catre raport direct din ecranul de finalizare
            from handlers.buget import afiseaza_raport_lunar
            from database import SessionLocal
            from models.user import User
            db = SessionLocal()
            user = db.query(User).filter_by(
                telegram_id=update.callback_query.from_user.id
            ).first()
            db.close()
            await update.callback_query.answer()
            await afiseaza_raport_lunar(update.callback_query, user)
        else:
            await callback_buget(update, context)
    elif data == "meniu_ajutor":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❓ *Ajutor ShopBot*\n\n"
            "/lista *Lista* — seteaza cantitatile dorite si vezi ce trebuie sa cumperi\n"
            "/stoc *Stoc* — actualizeaza ce ai acasa in prezent\n"
            "/buget *Buget* — seteaza bugetul lunar pentru cumparaturi\n\n"
            "Foloseste butoanele de jos pentru navigare rapida!",
            parse_mode="Markdown",
            reply_markup=__import__('telegram').InlineKeyboardMarkup([
                [__import__('telegram').InlineKeyboardButton("🔙 Inapoi", callback_data="meniu_principal")]
            ])
        )
    else:
        await callback_lista(update, context)

async def lista_din_meniu(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    query = update.callback_query
    butoane = [
        [InlineKeyboardButton("✅ Da, continua la lista", callback_data="stoc_actualizat_da")],
        [InlineKeyboardButton("❌ Nu, mergi la stoc", callback_data="stoc_actualizat_nu")],
        [InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")],
    ]
    keyboard = InlineKeyboardMarkup(butoane)
    await query.edit_message_text(
        "📦 *Inainte de lista de cumparaturi...*\n\n"
        "Ai actualizat stocul de acasa?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def stoc_din_meniu(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from database import SessionLocal
    from models.product import Product
    query = update.callback_query
    db = SessionLocal()
    categorii = db.query(Product.category).distinct().all()
    categorii = [c[0] for c in categorii]
    db.close()

    butoane = []
    for categorie in categorii:
        butoane.append([InlineKeyboardButton(f"📦 {categorie}", callback_data=f"stoc_cat_{categorie}")])
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    keyboard = InlineKeyboardMarkup(butoane)
    await query.edit_message_text(
        "📦 *Stocul de acasa*\n\nAlege o categorie:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def buget_inline(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from database import SessionLocal
    from models.user import User
    query = update.callback_query
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=query.from_user.id).first()
    db.close()

    buget_curent = user.monthly_budget if user else 0
    await query.edit_message_text(
        f"💰 *Bugetul tau lunar*\n\n"
        f"Buget curent: *{buget_curent} lei*\n\n"
        f"Scrie noul buget in chat (ex: 3000):",
        parse_mode="Markdown",
        reply_markup=__import__('telegram').InlineKeyboardMarkup([
            [__import__('telegram').InlineKeyboardButton("🔙 Inapoi", callback_data="meniu_principal")]
        ])
    )
    context.user_data["asteapta_buget"] = True

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(get_conversation_handler())
    app.add_handler(CommandHandler("ajutor", ajutor))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CommandHandler("stoc", stoc))
    app.add_handler(CommandHandler("buget", buget))
    app.add_handler(CallbackQueryHandler(router_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router_text))

    async def post_init(application):
        porneste_scheduler(application.bot)

    app.post_init = post_init
    print("✅ ShopBot pornit cu notificari automate! Apasa Ctrl+C pentru a opri.")

    app.run_polling()

if __name__ == "__main__":
    main()
