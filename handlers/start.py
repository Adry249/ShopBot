# Înregistrare utilizator și meniu principal

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                       ReplyKeyboardMarkup, KeyboardButton, WebAppInfo)
from telegram.ext import (ContextTypes, ConversationHandler,
                           CommandHandler, MessageHandler, filters)
from database import SessionLocal
from models.user import User

SALARY_DATE, BUDGET = range(2)


# ── Tastatura persistentă (apare mereu jos) ───────────────────────────────────
def get_reply_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🏠 Meniu"), KeyboardButton("🛒 Lista")],
            [KeyboardButton("📦 Stoc"),  KeyboardButton("💰 Buget")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )


# ── Meniu principal inline ────────────────────────────────────────────────────
async def afiseaza_meniu(update_or_message, edit=False):
    butoane = [
        [InlineKeyboardButton("👾 Deschide Mini App",
            web_app=WebAppInfo(url="https://adry249.github.io/ShopBot/"))],
        [InlineKeyboardButton("🛒 Lista de cumpărături", callback_data="meniu_lista")],
        [InlineKeyboardButton("📦 Stoc de acasă",        callback_data="meniu_stoc_direct")],
        [InlineKeyboardButton("💰 Buget lunar",           callback_data="meniu_buget")],
        [InlineKeyboardButton("❓ Ajutor",                callback_data="meniu_ajutor")],
    ]
    text = (
        "🏠 *Meniu principal*\n\n"
        "Ce dorești să faci?\n\n"
        "_Folosește și butoanele de jos pentru acces rapid!_"
    )
    keyboard = InlineKeyboardMarkup(butoane)

    if edit:
        await update_or_message.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update_or_message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    db.close()

    # Utilizator deja înregistrat
    if user:
        await update.message.reply_text(
            f"👋 Bun venit înapoi, *{update.effective_user.first_name}*!",
            parse_mode="Markdown",
            reply_markup=get_reply_keyboard()
        )
        await afiseaza_meniu(update.message)
        return ConversationHandler.END

    # Utilizator nou — start înregistrare
    await update.message.reply_text(
        f"👋 Bună, *{update.effective_user.first_name}*! Sunt ShopBot 🛒\n\n"
        f"Te ajut să îți gestionezi cumpărăturile!\n\n"
        f"Hai să te înregistrez rapid. 📝\n\n"
        f"În ce zi a lunii primești salariul? (scrie un număr de la 1 la 31)",
        parse_mode="Markdown"
    )
    return SALARY_DATE


# ── Pas 1: ziua salariului ────────────────────────────────────────────────────
async def get_salary_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.isdigit() or not (1 <= int(text) <= 31):
        await update.message.reply_text("❌ Te rog scrie un număr valid între 1 și 31.")
        return SALARY_DATE

    context.user_data["salary_date"] = int(text)
    await update.message.reply_text(
        f"✅ Ziua salariului: *{text}*\n\n"
        f"💰 Care este bugetul tău lunar pentru cumpărături? (în lei, ex: 3000)\n"
        f"Sau scrie /skip dacă nu vrei să setezi acum.",
        parse_mode="Markdown"
    )
    return BUDGET


# ── Pas 2: buget lunar ────────────────────────────────────────────────────────
async def get_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.lower() in ("/skip", "skip"):
        budget = 0
    else:
        try:
            budget = int(float(text))
            if budget < 0:
                await update.message.reply_text(
                    "❌ Bugetul nu poate fi negativ. Scrie un număr pozitiv, ex: 3000."
                )
                return BUDGET
        except ValueError:
            await update.message.reply_text(
                "❌ Te rog scrie un număr valid, ex: 3000. Sau /skip."
            )
            return BUDGET

    # Salvare utilizator în baza de date
    db = SessionLocal()
    try:
        user_nou = User(
            telegram_id=update.effective_user.id,
            username=update.effective_user.username or update.effective_user.first_name,
            salary_date=context.user_data["salary_date"],
            monthly_budget=budget
        )
        db.add(user_nou)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"EROARE DB: {e}")
        await update.message.reply_text(f"❌ Eroare la salvare: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()

    await update.message.reply_text(
        f"🎉 *Înregistrare completată!*\n\n"
        f"📅 Ziua salariului: {context.user_data['salary_date']}\n"
        f"💰 Buget lunar: {budget if budget > 0 else 'Nesetat'} {'lei' if budget > 0 else ''}\n\n"
        f"Acum poți folosi botul! 🚀",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )
    await afiseaza_meniu(update.message)
    return ConversationHandler.END


# ── Anulare înregistrare ──────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Înregistrare anulată. Trimite /start pentru a încerca din nou."
    )
    return ConversationHandler.END


# ── ConversationHandler pentru înregistrare ───────────────────────────────────
def get_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SALARY_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_salary_date)],
            BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_budget),
                CommandHandler("skip", get_budget)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )