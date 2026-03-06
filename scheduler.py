# scheduler.py — Notificări automate pentru utilizatori
# Job-uri active:
#   1. notificare_salariu       — zilnic la 10:00, în ziua salariului
#   2. notificare_stoc_terminat — la fiecare 2 zile la 09:00, stoc sub 35%
#   3. notificare_stoc_vechi    — zilnic la 11:00, stoc neactualizat 7+ zile

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from database import SessionLocal
from models.user import User
from models.product import Product, UserProduct
import logging

logger = logging.getLogger(__name__)


# ── Notificare 1: Ziua salariului ────────────────────────────────────────────
async def notificare_salariu(bot):
    ziua_azi = datetime.now().day
    db = SessionLocal()
    try:
        useri = db.query(User).filter_by(salary_date=ziua_azi).all()
        for user in useri:
            produse_necesare = db.query(UserProduct, Product)\
                .join(Product, UserProduct.product_id == Product.id)\
                .filter(UserProduct.user_id == user.id).all()

            lista_text = ""
            total = 0
            for up, prod in produse_necesare:
                diferenta = (up.desired_quantity or 0) - (up.quantity or 0)
                if diferenta > 0:
                    lista_text += f"• {prod.name} — {round(diferenta, 2)} {prod.unit}\n"
                    total += 1

            if total == 0:
                mesaj = (
                    "💰 *Ziua salariului — Felicitări!*\n\n"
                    "🎉 Stocul tău este complet! Nu ai nevoie să cumperi nimic acum.\n\n"
                    "Folosește /lista pentru a verifica."
                )
            else:
                mesaj = (
                    f"💰 *Ziua salariului — E timpul să faci cumpărături!*\n\n"
                    f"🛒 Ai *{total} produse* de cumpărat:\n\n"
                    f"{lista_text}\n"
                    f"Deschide /lista pentru a vedea lista completă!"
                )

            try:
                await bot.send_message(chat_id=user.telegram_id, text=mesaj, parse_mode="Markdown")
                logger.info(f"Notificare salariu trimisă la {user.telegram_id}")
            except Exception as e:
                logger.error(f"Eroare notificare salariu la {user.telegram_id}: {e}")
    finally:
        db.close()


# ── Notificare 2: Stoc pe terminate (sub 35%) ─────────────────────────────────
async def notificare_stoc_terminat(bot):
    db = SessionLocal()
    try:
        useri = db.query(User).all()
        for user in useri:
            produse_critice = []
            user_products = db.query(UserProduct, Product)\
                .join(Product, UserProduct.product_id == Product.id)\
                .filter(UserProduct.user_id == user.id).all()

            for up, prod in user_products:
                dorita  = up.desired_quantity or 0
                curenta = up.quantity or 0
                if dorita <= 0:
                    continue
                procent = (curenta / dorita) * 100
                if procent <= 35:
                    produse_critice.append((prod.name, curenta, dorita, prod.unit, round(procent)))

            if not produse_critice:
                continue

            text_produse = "".join(
                f"• {n}: *{c}/{d} {u}* ({p}%)\n"
                for n, c, d, u, p in produse_critice
            )
            mesaj = (
                f"⚠️ *Produse pe terminate!*\n\n"
                f"Următoarele produse au stocul sub 35%:\n\n"
                f"{text_produse}\n"
                f"Folosește /lista pentru a planifica cumpărăturile!"
            )

            try:
                await bot.send_message(chat_id=user.telegram_id, text=mesaj, parse_mode="Markdown")
                logger.info(f"Notificare stoc critic trimisă la {user.telegram_id}")
            except Exception as e:
                logger.error(f"Eroare notificare stoc critic la {user.telegram_id}: {e}")
    finally:
        db.close()


# ── Notificare 3: Stoc neactualizat de 7+ zile ───────────────────────────────
async def notificare_stoc_vechi(bot):
    db = SessionLocal()
    acum   = datetime.now()
    limita = acum - timedelta(days=7)
    try:
        useri = db.query(User).filter(
            (User.last_stock_update == None) |
            (User.last_stock_update < limita)
        ).all()

        for user in useri:
            # Trimite notificare doar dacă userul are produse înregistrate
            are_produse = db.query(UserProduct).filter_by(user_id=user.id).first()
            if not are_produse:
                continue

            if user.last_stock_update is None:
                zile_text = "niciodată"
            else:
                zile = (acum - user.last_stock_update).days
                zile_text = f"acum *{zile} zile*"

            mesaj = (
                f"📦 *Stocul tău nu a fost actualizat!*\n\n"
                f"Ultima actualizare: {zile_text}\n\n"
                f"Pentru o listă de cumpărături corectă, e important să știm ce ai acasă.\n\n"
                f"👉 Apasă /stoc pentru a actualiza stocul acum!"
            )

            try:
                await bot.send_message(chat_id=user.telegram_id, text=mesaj, parse_mode="Markdown")
                logger.info(f"Notificare stoc vechi trimisă la {user.telegram_id}")
            except Exception as e:
                logger.error(f"Eroare notificare stoc vechi la {user.telegram_id}: {e}")
    finally:
        db.close()


# ── Pornire scheduler cu cele 3 job-uri ──────────────────────────────────────
def porneste_scheduler(bot):
    scheduler = AsyncIOScheduler()

    scheduler.add_job(notificare_salariu,       CronTrigger(hour=10, minute=0),          args=[bot], id="notificare_salariu")
    scheduler.add_job(notificare_stoc_terminat, CronTrigger(hour=9,  minute=0, day="*/2"), args=[bot], id="notificare_stoc_terminat")
    scheduler.add_job(notificare_stoc_vechi,    CronTrigger(hour=11, minute=0),          args=[bot], id="notificare_stoc_vechi")

    scheduler.start()
    logger.info("✅ Scheduler pornit cu 3 job-uri active!")
    return scheduler