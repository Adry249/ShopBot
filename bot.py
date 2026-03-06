# API:     py -m uvicorn api:app --reload --port 8000
# Tunel:   .\ngrok.exe http 8000

import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv

from handlers.start import get_conversation_handler, afiseaza_meniu
from handlers.lista import lista, callback_lista, primeste_cantitate
from handlers.stoc import stoc, callback_stoc, primeste_cantitate_stoc
from handlers.buget import buget_command, callback_buget, afiseaza_meniu_buget, afiseaza_raport_lunar
from scheduler import porneste_scheduler
from database import SessionLocal
from models.user import User

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# ── Comanda /ajutor ───────────────────────────────────────────────────────────
async def ajutor(update, context):
    await update.message.reply_text(
        "❓ *Ajutor ShopBot*\n\n"
        "🛒 *Lista* — setează cantitățile dorite și vezi ce trebuie să cumperi\n"
        "📦 *Stoc* — actualizează ce ai acasă în prezent\n"
        "💰 *Buget* — setează bugetul lunar pentru cumpărături\n"
        "🏠 *Meniu* — revino la meniul principal\n\n"
        "Folosește butoanele de jos pentru navigare rapidă!",
        parse_mode="Markdown"
    )


# ── Router pentru mesaje text (butoane tastatura + cantitati) ─────────────────
async def router_text(update, context):
    text = update.message.text.strip()

    # Butoanele persistente de jos
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

    # Actualizare buget (dupa apasarea "Schimba bugetul")
    if "asteapta_buget" in context.user_data:
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
            await update.message.reply_text("❌ Scrie un număr valid, ex: 3000")
        return

    # Cantitati stoc sau lista dorita
    if "stoc_product_id" in context.user_data:
        await primeste_cantitate_stoc(update, context)
    elif "dorita_product_id" in context.user_data:
        await primeste_cantitate(update, context)


# ── Router pentru toate callback-urile (butoane inline) ───────────────────────
async def router_callback(update, context):
    data = update.callback_query.data

    # Callback-uri pentru stoc
    stoc_prefixes = [
        "stoc_cat_", "stoc_edit_", "stoc_inapoi",
        "stoc_gata", "stoc_goleste_", "stoc_toggle_", "stoc_confirma_golire_"
    ]
    if any(data.startswith(p) for p in stoc_prefixes):
        await callback_stoc(update, context)

    # Meniu principal
    elif data == "meniu_principal":
        await update.callback_query.answer()
        await afiseaza_meniu(update.callback_query, edit=True)

    # Lista de cumparaturi
    elif data == "meniu_lista":
        await update.callback_query.answer()
        await lista_din_meniu(update, context)

    # Stoc direct din meniu
    elif data == "meniu_stoc_direct":
        await update.callback_query.answer()
        context.user_data["din_lista"] = False
        await stoc_din_meniu(update, context)

    # Buget din meniu
    elif data == "meniu_buget":
        await update.callback_query.answer()
        db = SessionLocal()
        user = db.query(User).filter_by(telegram_id=update.callback_query.from_user.id).first()
        db.close()
        await afiseaza_meniu_buget(update.callback_query, user, edit=True)

    # Raport buget direct din ecranul de finalizare cumparaturi
    elif data == "buget_raport_direct":
        await update.callback_query.answer()
        db = SessionLocal()
        user = db.query(User).filter_by(telegram_id=update.callback_query.from_user.id).first()
        db.close()
        await afiseaza_raport_lunar(update.callback_query, user)

    # Toate celelalte callback-uri buget
    elif data.startswith("buget_"):
        await callback_buget(update, context)

    # Ajutor
    elif data == "meniu_ajutor":
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❓ *Ajutor ShopBot*\n\n"
            "🛒 *Lista* — setează cantitățile dorite și vezi ce trebuie să cumperi\n"
            "📦 *Stoc* — actualizează ce ai acasă în prezent\n"
            "💰 *Buget* — setează bugetul lunar pentru cumpărături\n\n"
            "Folosește butoanele de jos pentru navigare rapidă!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Înapoi", callback_data="meniu_principal")]
            ])
        )

    # Toate celelalte callback-uri lista
    else:
        await callback_lista(update, context)


# ── Ecran intermediar: ai actualizat stocul? (din meniu → lista) ──────────────
async def lista_din_meniu(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    query = update.callback_query
    await query.edit_message_text(
        "📦 *Înainte de lista de cumpărături...*\n\n"
        "Ai actualizat stocul de acasă?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Da, continuă la listă", callback_data="stoc_actualizat_da")],
            [InlineKeyboardButton("❌ Nu, mergi la stoc", callback_data="stoc_actualizat_nu")],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")],
        ]),
        parse_mode="Markdown"
    )


# ── Afisare stoc din meniu principal ─────────────────────────────────────────
async def stoc_din_meniu(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from models.product import Product
    query = update.callback_query
    db = SessionLocal()
    categorii = [c[0] for c in db.query(Product.category).distinct().all()]
    db.close()

    butoane = [[InlineKeyboardButton(f"📦 {cat}", callback_data=f"stoc_cat_{cat}")]
               for cat in categorii]
    butoane.append([InlineKeyboardButton("🏠 Meniu principal", callback_data="meniu_principal")])

    await query.edit_message_text(
        "📦 *Stocul de acasă*\n\nAlege o categorie:",
        reply_markup=InlineKeyboardMarkup(butoane),
        parse_mode="Markdown"
    )


# ── Configurare si pornire bot ────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # ConversationHandler primul — gestioneaza inregistrarea
    app.add_handler(get_conversation_handler())
    app.add_handler(CommandHandler("ajutor", ajutor))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CommandHandler("stoc", stoc))
    app.add_handler(CommandHandler("buget", buget_command))
    app.add_handler(CallbackQueryHandler(router_callback))
    # MessageHandler ultimul — prinde tot textul netratat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router_text))

    async def post_init(application):
        porneste_scheduler(application.bot)

    app.post_init = post_init
    print("✅ ShopBot pornit cu notificări automate! Apasă Ctrl+C pentru a opri.")
    app.run_polling()


if __name__ == "__main__":
    main()