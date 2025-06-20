from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, Boolean, BigInteger, func

Base = declarative_base()

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True)
    username = Column(String, index=True)
    message = Column(String)
    created_at = Column(BigInteger, default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(Text)
    firstname = Column(Text)
    lastname = Column(Text)
    balance = Column(Integer)
    is_banned = Column(Boolean, default=False)

class PseudoName(Base):
    __tablename__ = "pseudo_names"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    cost = Column(Integer, nullable=False)
    is_sold = Column(Boolean, default=False)

class UserPseudoName(Base):
    __tablename__ = "user_pseudo_names"
    user_id = Column(BigInteger, primary_key=True)
    pseudo_name_id = Column(Integer, primary_key=True)
 