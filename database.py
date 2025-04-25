# database.py
from sqlalchemy import (create_engine, Column, Integer, String, Float,
                        ForeignKey, Date)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

engine = create_engine("sqlite:///carbon.db", echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True)
    name     = Column(String, unique=True, nullable=False)
    email    = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # hash in prod

    emissions = relationship("Emission", back_populates="user")

class Emission(Base):
    __tablename__ = "emissions"
    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    date      = Column(Date, nullable=False)
    facility  = Column(String, nullable=False)
    category  = Column(String, nullable=False)
    value     = Column(Float, nullable=False)

    user = relationship("User", back_populates="emissions")

def init_db():
    Base.metadata.create_all(engine)
