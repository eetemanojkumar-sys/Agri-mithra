from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any
import uuid
from datetime import datetime, timezone
import httpx


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class ThingSpeakRequest(BaseModel):
    channel_id: str
    read_api_key: str

class MotorControlRequest(BaseModel):
    status: str  # "on" or "off"

class CommodityPrice(BaseModel):
    crop: str
    prices: List[float]
    dates: List[str]
    recommendation: str
    change_percent: float

class AgriAnalysisRequest(BaseModel):
    moisture: float
    temperature: float
    humidity: float

class AgriAnalysisResponse(BaseModel):
    environmental_assessment: Dict[str, Any]
    crop_recommendation: Dict[str, Any]
    irrigation_decision: Dict[str, Any]
    yield_insight: Dict[str, Any]
    fertilizer_advisory: Dict[str, Any]
    risk_detection: Dict[str, Any]
    corrective_actions: List[str]

# Motor state (in-memory for demo)
motor_state = {"status": "off", "last_updated": datetime.now(timezone.utc).isoformat()}

# Sample commodity price data
COMMODITY_DATA = {
    "rice": {
        "prices": [2100, 2150, 2180, 2200, 2250, 2300, 2350],
        "dates": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"],
        "current": 2100,
        "forecast": 2350
    },
    "onion": {
        "prices": [45, 48, 46, 44, 42, 40, 38],
        "dates": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"],
        "current": 45,
        "forecast": 38
    },
    "tomato": {
        "prices": [35, 38, 42, 45, 48, 52, 55],
        "dates": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"],
        "current": 35,
        "forecast": 55
    },
    "cotton": {
        "prices": [5800, 5750, 5700, 5650, 5600, 5550, 5500],
        "dates": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"],
        "current": 5800,
        "forecast": 5500
    },
    "groundnut": {
        "prices": [6200, 6250, 6300, 6400, 6500, 6600, 6700],
        "dates": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"],
        "current": 6200,
        "forecast": 6700
    }
}

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "AgriSmart API v1.0", "status": "active"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

@api_router.post("/thingspeak/fetch")
async def fetch_thingspeak_data(request: ThingSpeakRequest):
    """Fetch data from ThingSpeak channel"""
    try:
        url = f"https://api.thingspeak.com/channels/{request.channel_id}/feeds.json"
        params = {
            "api_key": request.read_api_key,
            "results": 1
        }
        
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(url, params=params)
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch ThingSpeak data")
            
            data = response.json()
            
            if not data.get("feeds"):
                raise HTTPException(status_code=404, detail="No data found in channel")
            
            latest_feed = data["feeds"][-1]
            
            return {
                "success": True,
                "data": {
                    "moisture": float(latest_feed.get("field1", 0)) if latest_feed.get("field1") else 0,
                    "temperature": float(latest_feed.get("field2", 0)) if latest_feed.get("field2") else 0,
                    "humidity": float(latest_feed.get("field3", 0)) if latest_feed.get("field3") else 0,
                    "rain": float(latest_feed.get("field4", 0)) if latest_feed.get("field4") else 0,
                    "timestamp": latest_feed.get("created_at")
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"ThingSpeak fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.post("/motor/control")
async def control_motor(request: MotorControlRequest):
    """Control motor on/off (UI simulation)"""
    global motor_state
    
    if request.status not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="Status must be 'on' or 'off'")
    
    motor_state = {
        "status": request.status,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    
    return {
        "success": True,
        "motor_status": motor_state["status"],
        "message": f"Motor turned {request.status}",
        "timestamp": motor_state["last_updated"]
    }

@api_router.get("/motor/status")
async def get_motor_status():
    """Get current motor status"""
    return motor_state

@api_router.get("/commodity-prices/{crop}")
async def get_commodity_prices(crop: str):
    """Get commodity price forecast for a specific crop"""
    crop_lower = crop.lower()
    
    if crop_lower not in COMMODITY_DATA:
        raise HTTPException(status_code=404, detail="Crop not found")
    
    data = COMMODITY_DATA[crop_lower]
    change = ((data["forecast"] - data["current"]) / data["current"]) * 100
    
    if change > 5:
        recommendation = "Hold & Sell Later"
    elif change < -5:
        recommendation = "Sell Now"
    else:
        recommendation = "Market Stable"
    
    return {
        "crop": crop.title(),
        "prices": data["prices"],
        "dates": data["dates"],
        "current_price": data["current"],
        "forecast_price": data["forecast"],
        "recommendation": recommendation,
        "change_percent": round(change, 2),
        "accuracy": 94.5
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()