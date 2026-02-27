from sqlalchemy import Column, Integer, String, Date, DateTime, func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    salary_date = Column(Integer)  # ziua din luna cand primeste salariul
    monthly_budget = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())