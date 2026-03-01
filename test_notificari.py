import asyncio
from telegram import Bot
from dotenv import load_dotenv
import os

load_dotenv()
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

async def test():
    from scheduler import notificare_salariu, notificare_stoc_terminat, notificare_stoc_vechi
    
    print("Testez notificarea salariu...")
    await notificare_salariu(bot)
    
    print("Testez notificarea stoc terminat...")
    await notificare_stoc_terminat(bot)
    
    print("Testez notificarea stoc vechi...")
    await notificare_stoc_vechi(bot)
    
    print("✅ Toate notificarile au fost trimise!")

asyncio.run(test())
