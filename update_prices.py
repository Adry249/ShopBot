# update_prices.py
from database import SessionLocal
from models.product import Product

preturi = {
    "Lapte": 18, "Branza": 90, "Unt": 120, "Smantana": 45,
    "Iaurt": 12, "Oua": 3, "Paine alba": 8, "Paine neagra": 9,
    "Chifle": 3, "Piept de pui": 75, "Carne de porc": 95,
    "Carne de vita": 130, "Carnati": 85, "Peste": 80,
    "Cartofi": 8, "Rosii": 20, "Castraveti": 15, "Ceapa": 7,
    "Usturoi": 30, "Morcovi": 8, "Varza": 6, "Mere": 18,
    "Banane": 22, "Portocale": 25, "Paste fainoase": 20,
    "Orez": 18, "Hrisca": 25, "Faina": 12, "Fulgi de ovaz": 22,
    "Ulei": 35, "Zahar": 15, "Sare": 5, "Maioneza": 28,
    "Ketchup": 25, "Apa plata": 8, "Suc de portocale": 30,
    "Ceai": 25, "Cafea": 55, "Sampon": 45, "Sapun": 12,
    "Pasta de dinti": 30, "Hartie igienica": 8,
}

db = SessionLocal()
for nume, pret in preturi.items():
    produs = db.query(Product).filter_by(name=nume).first()
    if produs:
        produs.avg_price = pret
db.commit()
db.close()
print("✅ Preturi actualizate!")