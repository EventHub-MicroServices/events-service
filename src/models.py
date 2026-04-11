from database import Base
from sqlalchemy import Column, Integer, String, Float

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    date = Column(String)
    capacity = Column(Integer)
    price = Column(Float)
    location = Column(String)
    image_url = Column(String, nullable=True)
    organizer_id = Column(Integer, nullable=True)
