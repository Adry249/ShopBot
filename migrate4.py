from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Tabel pentru istoricul cumparaturilor
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS purchase_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            product_id INTEGER REFERENCES products(id),
            quantity FLOAT,
            total_price FLOAT DEFAULT 0,
            purchased_at TIMESTAMP DEFAULT NOW()
        )
    """))
    
    # Adaugam pretul mediu la produse daca nu exista
    conn.execute(text("""
        ALTER TABLE products 
        ADD COLUMN IF NOT EXISTS avg_price FLOAT DEFAULT 0
    """))
    
    conn.commit()
    print("✅ Tabel purchase_history creat!")