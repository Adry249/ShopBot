from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))
    unit = Column(String(50))

class UserProduct(Base):
    __tablename__ = "user_products"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float, default=0)        # stoc acasa
    desired_quantity = Column(Float, default=0) # cantitatea dorita
    min_quantity = Column(Float, default=1)
    is_on_list = Column(Integer, default=0)
    added_at = Column(DateTime, default=func.now())