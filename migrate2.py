from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE user_products ADD COLUMN IF NOT EXISTS in_cart INTEGER DEFAULT 0"))
    conn.commit()
    print("✅ Coloana in_cart adaugata!")