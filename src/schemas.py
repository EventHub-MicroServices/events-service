from pydantic import BaseModel

from typing import Optional

class EventBase(BaseModel):
    title: str
    description: str
    date: str
    capacity: int
    price: float
    location: str
    image_url: Optional[str] = None
    organizer_id: Optional[int] = None

class EventCreate(EventBase):
    organizer_id: int

class EventOut(EventBase):
    id: int
    
    class Config:
        from_attributes = True
        extra = "ignore"
