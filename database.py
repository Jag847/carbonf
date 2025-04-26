from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
import bcrypt

engine = create_engine("sqlite:///carbon.db", echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # hashed password

    emissions = relationship("Emission", back_populates="user")

class Emission(Base):
    __tablename__ = "emissions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    facility = Column(String, nullable=False)
    category = Column(String, nullable=False)
    value = Column(Float, nullable=False)

    user = relationship("User", back_populates="emissions")

def init_db():
    Base.metadata.create_all(engine)

def create_user(name, email, password):
    """Create a new user with hashed password."""
    session = Session()
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(name=name, email=email, password=hashed)
    session.add(user)
    try:
        session.commit()
        return user
    except IntegrityError:
        session.rollback()
        return None

def authenticate(email, password):
    """Check user credentials. Return User if valid, else None."""
    session = Session()
    user = session.query(User).filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return user
    return None
