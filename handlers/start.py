from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from database import SessionLocal
from models.user import User

SALARY_DATE, BUDGET = range(2)

# Tastatura persistenta (apare mereu jos)
def get_reply_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🏠 Meniu"), KeyboardButton("🛒 Lista")],
            [KeyboardButton("📦 Stoc"), KeyboardButton("💰 Buget")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )

# Meniu principal inline
async def afiseaza_meniu(update_or_message, edit=False):
    butoane = [
        [InlineKeyboardButton("🛒 Lista de cumparaturi", callback_data="meniu_lista")],
        [InlineKeyboardButton("📦 Stoc de acasa", callback_data="meniu_stoc_direct")],
        [InlineKeyboardButton("💰 Buget lunar", callback_data="meniu_buget")],
        [InlineKeyboardButton("❓ Ajutor", callback_data="meniu_ajutor")],
    ]
    keyboard = InlineKeyboardMarkup(butoane)
    text = (
        "🏠 *Meniu principal*\n\n"
        "Ce doresti sa faci?\n\n"
        "_Foloseste si butoanele de jos pentru acces rapid!_"
    )

    if edit:
        await update_or_message.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update_or_message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    db.close()

    if user:
        await update.message.reply_text(
            f"👋 Bun venit inapoi, *{update.effective_user.first_name}*!",
            parse_mode="Markdown",
            reply_markup=get_reply_keyboard()
        )
        await afiseaza_meniu(update.message)
        return ConversationHandler.END

    await update.message.reply_text(
        f"👋 Buna, *{update.effective_user.first_name}*! Sunt ShopBot 🛒\n\n"
        f"Te ajut sa iti gestionezi cumparaturile!\n\n"
        f"Hai sa te inregistrez rapid. 📝\n\n"
        f"In ce zi a lunii primesti salariul? (scrie un numar de la 1 la 31)",
        parse_mode="Markdown"
    )
    return SALARY_DATE

async def get_salary_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.isdigit() or not (1 <= int(text) <= 31):
        await update.message.reply_text("❌ Te rog scrie un numar valid intre 1 si 31.")
        return SALARY_DATE

    context.user_data["salary_date"] = int(text)
    await update.message.reply_text(
        f"✅ Ziua salariului: *{text}*\n\n"
        f"💰 Care este bugetul tau lunar pentru cumparaturi? (in lei, ex: 3000)\n"
        f"Sau scrie /skip daca nu vrei sa setezi acum.",
        parse_mode="Markdown"
    )
    return BUDGET

async def get_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "/skip":
        budget = 0
    elif not text.isdigit():
        await update.message.reply_text("❌ Te rog scrie un numar valid, ex: 3000. Sau /skip.")
        return BUDGET
    else:
        budget = int(text)

    db = SessionLocal()
    user_nou = User(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        salary_date=context.user_data["salary_date"],
        monthly_budget=budget
    )
    db.add(user_nou)
    db.commit()
    db.close()

    await update.message.reply_text(
        f"🎉 *Inregistrare completata!*\n\n"
        f"📅 Ziua salariului: {context.user_data['salary_date']}\n"
        f"💰 Buget lunar: {budget if budget > 0 else 'Nesetat'} {'lei' if budget > 0 else ''}\n\n"
        f"Acum poti folosi botul! 🚀",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )
    await afiseaza_meniu(update.message)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Inregistrare anulata. Trimite /start pentru a incerca din nou.")
    return ConversationHandler.END

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