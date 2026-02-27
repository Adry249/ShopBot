from database import engine, SessionLocal, Base
from models.user import User
from models.product import Product, UserProduct
from sqlalchemy import text

# Creaza tabelele daca nu exista
Base.metadata.create_all(engine)

db = SessionLocal()

# ============ PRODUSE ============
produse = [
    # Lactate
    Product(name="Lapte", category="Lactate", unit="litri"),
    Product(name="Branza", category="Lactate", unit="kg"),
    Product(name="Unt", category="Lactate", unit="kg"),
    Product(name="Smantana", category="Lactate", unit="kg"),
    Product(name="Iaurt", category="Lactate", unit="bucati"),
    Product(name="Oua", category="Lactate", unit="bucati"),

    # Paine si Patiserie
    Product(name="Paine alba", category="Paine", unit="bucati"),
    Product(name="Paine neagra", category="Paine", unit="bucati"),
    Product(name="Chifle", category="Paine", unit="bucati"),

    # Carne
    Product(name="Piept de pui", category="Carne", unit="kg"),
    Product(name="Carne de porc", category="Carne", unit="kg"),
    Product(name="Carne de vita", category="Carne", unit="kg"),
    Product(name="Carnati", category="Carne", unit="kg"),
    Product(name="Peste", category="Carne", unit="kg"),

    # Legume
    Product(name="Cartofi", category="Legume", unit="kg"),
    Product(name="Rosii", category="Legume", unit="kg"),
    Product(name="Castraveti", category="Legume", unit="kg"),
    Product(name="Ceapa", category="Legume", unit="kg"),
    Product(name="Usturoi", category="Legume", unit="kg"),
    Product(name="Morcovi", category="Legume", unit="kg"),
    Product(name="Varza", category="Legume", unit="kg"),

    # Fructe
    Product(name="Mere", category="Fructe", unit="kg"),
    Product(name="Banane", category="Fructe", unit="kg"),
    Product(name="Portocale", category="Fructe", unit="kg"),

    # Cereale si Paste
    Product(name="Paste fainoase", category="Cereale", unit="kg"),
    Product(name="Orez", category="Cereale", unit="kg"),
    Product(name="Hrisca", category="Cereale", unit="kg"),
    Product(name="Faina", category="Cereale", unit="kg"),
    Product(name="Fulgi de ovaz", category="Cereale", unit="kg"),

    # Conserve si Altele
    Product(name="Ulei", category="Altele", unit="litri"),
    Product(name="Zahar", category="Altele", unit="kg"),
    Product(name="Sare", category="Altele", unit="kg"),
    Product(name="Maioneza", category="Altele", unit="bucati"),
    Product(name="Ketchup", category="Altele", unit="bucati"),

    # Bauturi
    Product(name="Apa plata", category="Bauturi", unit="litri"),
    Product(name="Suc de portocale", category="Bauturi", unit="litri"),
    Product(name="Ceai", category="Bauturi", unit="bucati"),
    Product(name="Cafea", category="Bauturi", unit="bucati"),

    # Igiena
    Product(name="Sampon", category="Igiena", unit="bucati"),
    Product(name="Sapun", category="Igiena", unit="bucati"),
    Product(name="Pasta de dinti", category="Igiena", unit="bucati"),
    Product(name="Hartie igienica", category="Igiena", unit="bucati"),
]

db.add_all(produse)

# ============ UTILIZATOR TEST ============
user_test = User(
    telegram_id=123456789,
    username="test_user",
    salary_date=1,  # ziua 1 a lunii
    monthly_budget=3000
)
db.add(user_test)
db.commit()
db.refresh(user_test)

# ============ PRODUSE UTILIZATOR TEST ============
# Luam primele produse din baza de date
lapte = db.query(Product).filter_by(name="Lapte").first()
paine = db.query(Product).filter_by(name="Paine alba").first()
oua = db.query(Product).filter_by(name="Oua").first()
cartofi = db.query(Product).filter_by(name="Cartofi").first()

user_products = [
    UserProduct(user_id=user_test.id, product_id=lapte.id, quantity=2.0, min_quantity=1.0, is_on_list=1),
    UserProduct(user_id=user_test.id, product_id=paine.id, quantity=0.5, min_quantity=1.0, is_on_list=1),
    UserProduct(user_id=user_test.id, product_id=oua.id, quantity=6.0, min_quantity=5.0, is_on_list=0),
    UserProduct(user_id=user_test.id, product_id=cartofi.id, quantity=0.3, min_quantity=1.0, is_on_list=1),
]

db.add_all(user_products)
db.commit()

print("✅ Baza de date populata cu succes!")
print(f"✅ {len(produse)} produse adaugate")
print(f"✅ 1 utilizator test adaugat")
print(f"✅ 4 produse asociate utilizatorului test")

db.close()
