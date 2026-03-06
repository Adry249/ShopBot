from sqlalchemy import Column, Integer, BigInteger, String, DateTime, func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    salary_date = Column(Integer)
    monthly_budget = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    last_stock_update = Column(DateTime, nullable=True)
    