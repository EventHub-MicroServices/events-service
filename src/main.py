from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import get_db
from schemas import EventCreate, EventOut
import os
from typing import List
from dotenv import load_dotenv
import random
from pymongo import ReturnDocument

load_dotenv()

app = FastAPI(title="events-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail}},
    )

@app.get("/")
def read_root():
    return {"service": "events-service", "status": "running", "db": "mongodb"}

def format_event(doc):
    if not doc: return None
    # Use our custom integer id
    if "_id" in doc:
        del doc["_id"]
    return doc

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/events", response_model=List[EventOut])
def get_events(search: str = Query(None), skip: int = 0, limit: int = 100, coll = Depends(get_db)):
    query = {}
    if search:
        # Case-insensitive search on title
        query = {"title": {"$regex": search, "$options": "i"}}
    
    cursor = coll.find(query).skip(skip).limit(limit)
    events = [format_event(doc) for doc in cursor]
    return events

@app.post("/events", response_model=EventOut)
def create_event(event: EventCreate, coll = Depends(get_db)):
    event_dict = event.model_dump()
    # Generate integer ID to be compatible with other SQL services
    event_dict["id"] = random.randint(10000, 99999999)
    coll.insert_one(event_dict)
    return event_dict

@app.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, coll = Depends(get_db)):
    doc = coll.find_one({"id": event_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return format_event(doc)

@app.put("/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, event_update: EventCreate, coll = Depends(get_db)):
    update_data = event_update.model_dump(exclude_unset=True)
    res = coll.find_one_and_update(
        {"id": event_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    if not res:
        raise HTTPException(status_code=404, detail="Event not found")
    return format_event(res)

@app.put("/events/{event_id}/capacity")
def reduce_capacity(event_id: int, amount: int = 1, coll = Depends(get_db)):
    doc = coll.find_one({"id": event_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if doc.get("capacity", 0) < amount:
        raise HTTPException(status_code=400, detail="Not enough capacity")
    
    res = coll.find_one_and_update(
        {"id": event_id},
        {"$inc": {"capacity": -amount}},
        return_document=ReturnDocument.AFTER
    )
    return format_event(res)

@app.get("/events/organizer/{organizer_id}", response_model=List[EventOut])
def get_organizer_events(organizer_id: int, coll = Depends(get_db)):
    cursor = coll.find({"organizer_id": organizer_id})
    return [format_event(doc) for doc in cursor]

@app.delete("/events/{event_id}")
def delete_event(event_id: int, coll = Depends(get_db)):
    res = coll.delete_one({"id": event_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted successfully"}
