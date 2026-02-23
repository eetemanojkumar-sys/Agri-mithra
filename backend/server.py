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
    crop: str = None
    market_price: float = None

class AgriAnalysisResponse(BaseModel):
    environmental_assessment: Dict[str, Any]
    crop_recommendation: Dict[str, Any]
    irrigation_advisory: Dict[str, Any]
    stress_risk_detection: Dict[str, Any]
    predictive_insights: Dict[str, Any]
    market_intelligence: Dict[str, Any]
    integrated_decision: Dict[str, Any]
    corrective_actions: List[str]
    alerts: List[Dict[str, Any]]

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

@api_router.post("/agri-analysis")
async def analyze_agricultural_conditions(request: AgriAnalysisRequest):
    """Intelligent agricultural decision-support system"""
    moisture = request.moisture
    temperature = request.temperature
    humidity = request.humidity
    
    # Environmental Assessment
    soil_condition = "dry" if moisture < 30 else "wet" if moisture > 75 else "optimal"
    temp_stress = "low" if temperature < 15 else "heat stress" if temperature > 35 else "optimal"
    humidity_effect = "low" if humidity < 40 else "high" if humidity > 80 else "moderate"
    
    environmental_assessment = {
        "soil_condition": soil_condition,
        "soil_description": f"Soil moisture at {moisture}% indicates {soil_condition} conditions",
        "temperature_stress": temp_stress,
        "temp_description": f"Temperature at {temperature}°C represents {temp_stress} conditions",
        "humidity_effect": humidity_effect,
        "humidity_description": f"Relative humidity at {humidity}% is {humidity_effect}"
    }
    
    # Crop Recommendation
    recommended_crops = []
    if moisture >= 40 and 20 <= temperature <= 30:
        recommended_crops = ["Rice", "Sugarcane", "Cotton"]
        reasoning = "High moisture and moderate temperature suit water-intensive crops"
    elif moisture < 40 and temperature > 30:
        recommended_crops = ["Millets", "Sorghum", "Groundnut"]
        reasoning = "Low moisture and high temperature favor drought-resistant crops"
    elif moisture >= 50 and temperature < 25:
        recommended_crops = ["Wheat", "Barley", "Peas"]
        reasoning = "Good moisture with cool temperature ideal for winter crops"
    else:
        recommended_crops = ["Maize", "Beans", "Vegetables"]
        reasoning = "Moderate conditions support versatile crop options"
    
    crop_recommendation = {
        "recommended_crops": recommended_crops,
        "reasoning": reasoning,
        "season_alignment": "Kharif season" if temperature > 25 else "Rabi season"
    }
    
    # Irrigation Decision
    if moisture < 25:
        urgency = "immediate"
        irrigation_needed = True
        irrigation_reason = "Critical soil moisture deficit detected. Crop water stress imminent."
        water_amount = "15-20mm"
    elif moisture < 40:
        urgency = "moderate"
        irrigation_needed = True
        irrigation_reason = "Soil moisture below optimal range. Schedule irrigation within 24 hours."
        water_amount = "10-15mm"
    elif moisture > 75:
        urgency = "none"
        irrigation_needed = False
        irrigation_reason = "Soil moisture adequate. Excess irrigation may cause waterlogging."
        water_amount = "0mm"
    else:
        urgency = "low"
        irrigation_needed = False
        irrigation_reason = "Soil moisture optimal. Monitor daily and irrigate if moisture drops below 40%."
        water_amount = "0mm"
    
    irrigation_decision = {
        "irrigation_needed": irrigation_needed,
        "urgency": urgency,
        "reasoning": irrigation_reason,
        "recommended_water_amount": water_amount,
        "timing": "Early morning (5-7 AM) or evening (5-7 PM)" if irrigation_needed else "N/A"
    }
    
    # Yield & Growth Insight
    stress_factors = []
    if moisture < 30:
        stress_factors.append("water stress")
    if temperature > 35:
        stress_factors.append("heat stress")
    if humidity > 85:
        stress_factors.append("excess humidity")
    
    if len(stress_factors) == 0:
        yield_status = "favorable"
        yield_prediction = "90-100% of expected yield potential"
        growth_description = "Conditions are optimal for healthy crop growth and development"
    elif len(stress_factors) == 1:
        yield_status = "moderate stress"
        yield_prediction = "70-85% of expected yield potential"
        growth_description = f"Mild stress from {stress_factors[0]} may slightly reduce yield"
    else:
        yield_status = "high risk"
        yield_prediction = "50-70% of expected yield potential"
        growth_description = f"Multiple stress factors ({', '.join(stress_factors)}) pose significant risk"
    
    yield_insight = {
        "yield_status": yield_status,
        "predicted_yield": yield_prediction,
        "growth_description": growth_description,
        "stress_factors": stress_factors
    }
    
    # Fertilizer Advisory
    fertilizer_recommendations = []
    if moisture < 35:
        fertilizer_recommendations.append("Avoid fertilizer application until soil moisture improves (risk of salt stress)")
    else:
        if temperature > 30:
            fertilizer_recommendations.append("Apply nitrogen in split doses to reduce volatilization losses")
        if moisture > 60:
            fertilizer_recommendations.append("Apply potassium to strengthen cell walls and improve water regulation")
        if humidity > 70:
            fertilizer_recommendations.append("Zinc and manganese foliar spray to prevent deficiency in high humidity")
    
    if not fertilizer_recommendations:
        fertilizer_recommendations.append("Standard NPK application as per crop requirement")
    
    fertilizer_advisory = {
        "recommendations": fertilizer_recommendations,
        "soil_management": "Add organic matter to improve water retention" if moisture < 40 else "Ensure proper drainage to prevent nutrient leaching",
        "timing": "Apply fertilizers 2-3 days after irrigation for optimal uptake"
    }
    
    # Risk Detection
    risks = []
    if moisture < 25:
        risks.append({
            "type": "Water Stress",
            "severity": "high",
            "description": "Severe soil moisture deficit leading to wilting and yield loss"
        })
    if temperature > 38:
        risks.append({
            "type": "Heat Stress",
            "severity": "high",
            "description": "Extreme temperature causing protein denaturation and photosynthesis inhibition"
        })
    if moisture > 75 and humidity > 80:
        risks.append({
            "type": "Disease Risk",
            "severity": "high",
            "description": "High moisture and humidity create favorable conditions for fungal diseases"
        })
    if moisture > 80:
        risks.append({
            "type": "Waterlogging",
            "severity": "medium",
            "description": "Excess soil moisture may cause root oxygen deficiency"
        })
    if temperature > 35 and humidity < 40:
        risks.append({
            "type": "Transpiration Stress",
            "severity": "medium",
            "description": "High temperature with low humidity increases water loss through transpiration"
        })
    
    if not risks:
        risks.append({
            "type": "No Major Risks",
            "severity": "low",
            "description": "Environmental conditions are within acceptable range"
        })
    
    risk_detection = {
        "identified_risks": risks,
        "risk_count": len([r for r in risks if r["severity"] in ["high", "medium"]])
    }
    
    # Corrective Actions
    corrective_actions = []
    
    if moisture < 30:
        corrective_actions.append("Immediate irrigation: Apply 15-20mm water through drip or sprinkler system")
        corrective_actions.append("Mulching: Apply 5-7cm organic mulch to conserve soil moisture")
    
    if temperature > 35:
        corrective_actions.append("Provide shade: Use shade nets (30-50% shade) during peak heat hours (11 AM - 3 PM)")
        corrective_actions.append("Foliar spray: Apply water spray in evening to cool leaf surface")
    
    if humidity > 80:
        corrective_actions.append("Improve ventilation: Increase plant spacing to enhance air circulation")
        corrective_actions.append("Fungicide application: Preventive spray of broad-spectrum fungicide")
    
    if moisture > 75:
        corrective_actions.append("Drainage management: Create drainage channels to remove excess water")
        corrective_actions.append("Reduce irrigation frequency: Skip next 2-3 irrigation cycles")
    
    if temperature < 15:
        corrective_actions.append("Frost protection: Cover crops with plastic sheets during night")
        corrective_actions.append("Delay planting: Wait for temperature to rise above 18°C for warm-season crops")
    
    if not corrective_actions:
        corrective_actions.append("Continue current management practices")
        corrective_actions.append("Monitor conditions daily and adjust as needed")
    
    return {
        "environmental_assessment": environmental_assessment,
        "crop_recommendation": crop_recommendation,
        "irrigation_decision": irrigation_decision,
        "yield_insight": yield_insight,
        "fertilizer_advisory": fertilizer_advisory,
        "risk_detection": risk_detection,
        "corrective_actions": corrective_actions
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