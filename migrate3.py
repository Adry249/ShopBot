from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS last_stock_update TIMESTAMP DEFAULT NULL
    """))
    conn.commit()
    print("✅ Coloana last_stock_update adaugata!")