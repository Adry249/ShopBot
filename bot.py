import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configurare logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Comanda /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bună! Sunt ShopBot!\n\n"
        "Te ajut să îți gestionezi cumpărăturile.\n\n"
        "📋 Comenzi disponibile:\n"
        "/lista — lista ta de cumpărături\n"
        "/stoc — stocul de acasă\n"
        "/buget — bugetul lunar\n"
        "/ajutor — toate comenzile"
    )

# Comanda /ajutor
async def ajutor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Comenzi disponibile:\n\n"
        "/start — mesaj de bun venit\n"
        "/lista — vezi lista de cumpărături\n"
        "/stoc — verifică stocul de acasă\n"
        "/buget — setează bugetul lunar\n"
        "/ajutor — acest mesaj"
    )

# Comanda /lista
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛒 Lista ta de cumpărături:\n\n"
        "Lista este goală momentan.\n"
        "În curând vei putea adăuga produse!"
    )

# Comanda /stoc
async def stoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 Stocul tău de acasă:\n\n"
        "Nu ai produse înregistrate încă."
    )

# Pornirea botului
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajutor", ajutor))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CommandHandler("stoc", stoc))

    print("✅ ShopBot pornit! Apasă Ctrl+C pentru a opri.")
    app.run_polling()

if __name__ == "__main__":
    main()
