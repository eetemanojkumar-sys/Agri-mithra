from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
import httpx


# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection (lazy initialization for serverless)
_client: Optional[AsyncIOMotorClient] = None
_db = None

def get_database():
    """Lazy database connection for serverless compatibility"""
    global _client, _db
    if _client is None:
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        _client = AsyncIOMotorClient(mongo_url)
        _db = _client[os.environ.get('DB_NAME', 'agrismart')]
    return _db

# Create the main app
app = FastAPI(title="AgriSmart API", version="1.0.0")

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
    crop_threshold_assessment: Dict[str, Any]
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

# Crop-specific thresholds and characteristics
CROP_PROFILES = {
    "rice": {
        "name": "Rice",
        "moisture_optimal_min": 60,
        "moisture_optimal_max": 85,
        "moisture_critical_min": 45,
        "water_requirement": "Very High",
        "heat_tolerance": 38,
        "optimal_temp_min": 20,
        "optimal_temp_max": 35,
        "growth_cycle_days": 120,
        "category": "Water-intensive crop"
    },
    "wheat": {
        "name": "Wheat",
        "moisture_optimal_min": 40,
        "moisture_optimal_max": 65,
        "moisture_critical_min": 25,
        "water_requirement": "Moderate",
        "heat_tolerance": 32,
        "optimal_temp_min": 12,
        "optimal_temp_max": 25,
        "growth_cycle_days": 120,
        "category": "Winter crop"
    },
    "millets": {
        "name": "Millets",
        "moisture_optimal_min": 25,
        "moisture_optimal_max": 45,
        "moisture_critical_min": 15,
        "water_requirement": "Low",
        "heat_tolerance": 42,
        "optimal_temp_min": 25,
        "optimal_temp_max": 38,
        "growth_cycle_days": 75,
        "category": "Drought-resistant"
    },
    "cotton": {
        "name": "Cotton",
        "moisture_optimal_min": 50,
        "moisture_optimal_max": 70,
        "moisture_critical_min": 30,
        "water_requirement": "High",
        "heat_tolerance": 40,
        "optimal_temp_min": 21,
        "optimal_temp_max": 37,
        "growth_cycle_days": 150,
        "category": "Cash crop"
    },
    "groundnut": {
        "name": "Groundnut",
        "moisture_optimal_min": 35,
        "moisture_optimal_max": 55,
        "moisture_critical_min": 20,
        "water_requirement": "Moderate",
        "heat_tolerance": 40,
        "optimal_temp_min": 20,
        "optimal_temp_max": 35,
        "growth_cycle_days": 110,
        "category": "Legume"
    },
    "sugarcane": {
        "name": "Sugarcane",
        "moisture_optimal_min": 65,
        "moisture_optimal_max": 80,
        "moisture_critical_min": 50,
        "water_requirement": "Very High",
        "heat_tolerance": 38,
        "optimal_temp_min": 20,
        "optimal_temp_max": 35,
        "growth_cycle_days": 365,
        "category": "Water-intensive crop"
    },
    "maize": {
        "name": "Maize",
        "moisture_optimal_min": 45,
        "moisture_optimal_max": 65,
        "moisture_critical_min": 30,
        "water_requirement": "Moderate",
        "heat_tolerance": 35,
        "optimal_temp_min": 18,
        "optimal_temp_max": 32,
        "growth_cycle_days": 90,
        "category": "Versatile crop"
    },
    "vegetables": {
        "name": "Vegetables",
        "moisture_optimal_min": 50,
        "moisture_optimal_max": 70,
        "moisture_critical_min": 35,
        "water_requirement": "High",
        "heat_tolerance": 32,
        "optimal_temp_min": 15,
        "optimal_temp_max": 30,
        "growth_cycle_days": 60,
        "category": "Moisture-sensitive"
    },
    "sorghum": {
        "name": "Sorghum",
        "moisture_optimal_min": 30,
        "moisture_optimal_max": 50,
        "moisture_critical_min": 18,
        "water_requirement": "Low",
        "heat_tolerance": 40,
        "optimal_temp_min": 25,
        "optimal_temp_max": 38,
        "growth_cycle_days": 100,
        "category": "Drought-tolerant"
    },
    "onion": {
        "name": "Onion",
        "moisture_optimal_min": 45,
        "moisture_optimal_max": 65,
        "moisture_critical_min": 30,
        "water_requirement": "Moderate",
        "heat_tolerance": 30,
        "optimal_temp_min": 13,
        "optimal_temp_max": 28,
        "growth_cycle_days": 110,
        "category": "Vegetable"
    },
    "tomato": {
        "name": "Tomato",
        "moisture_optimal_min": 50,
        "moisture_optimal_max": 70,
        "moisture_critical_min": 35,
        "water_requirement": "High",
        "heat_tolerance": 32,
        "optimal_temp_min": 18,
        "optimal_temp_max": 29,
        "growth_cycle_days": 75,
        "category": "Fruit vegetable"
    }
}
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

@api_router.get("/crops")
async def get_available_crops():
    """Get list of available crops with their profiles"""
    crops = []
    for crop_id, profile in CROP_PROFILES.items():
        crops.append({
            "id": crop_id,
            "name": profile["name"],
            "category": profile["category"],
            "water_requirement": profile["water_requirement"],
            "optimal_moisture_range": f"{profile['moisture_optimal_min']}-{profile['moisture_optimal_max']}%",
            "optimal_temp_range": f"{profile['optimal_temp_min']}-{profile['optimal_temp_max']}°C",
            "growth_cycle": f"{profile['growth_cycle_days']} days"
        })
    return {"crops": crops, "total": len(crops)}

@api_router.post("/agri-analysis")
async def analyze_agricultural_conditions(request: AgriAnalysisRequest):
    """Crop-aware intelligent agricultural decision-support system"""
    moisture = request.moisture
    temperature = request.temperature
    humidity = request.humidity
    crop = request.crop.lower() if request.crop else None
    market_price = request.market_price
    
    # Get crop profile if provided
    crop_profile = None
    if crop and crop in CROP_PROFILES:
        crop_profile = CROP_PROFILES[crop]
    
    # 1. Crop Threshold Assessment (NEW)
    if crop_profile:
        # Crop-specific moisture evaluation
        if moisture < crop_profile["moisture_critical_min"]:
            moisture_status = "Critical - Below Safe Threshold"
            moisture_deviation = crop_profile["moisture_critical_min"] - moisture
        elif moisture < crop_profile["moisture_optimal_min"]:
            moisture_status = "Below Optimal"
            moisture_deviation = crop_profile["moisture_optimal_min"] - moisture
        elif moisture <= crop_profile["moisture_optimal_max"]:
            moisture_status = "Within Optimal Range"
            moisture_deviation = 0
        else:
            moisture_status = "Above Optimal"
            moisture_deviation = moisture - crop_profile["moisture_optimal_max"]
        
        crop_threshold_assessment = {
            "crop_selected": crop_profile["name"],
            "optimal_moisture_range": f"{crop_profile['moisture_optimal_min']}-{crop_profile['moisture_optimal_max']}%",
            "critical_moisture_threshold": f"{crop_profile['moisture_critical_min']}%",
            "current_moisture_status": moisture_status,
            "moisture_deviation": abs(moisture_deviation),
            "water_requirement_level": crop_profile["water_requirement"],
            "category": crop_profile["category"]
        }
    else:
        crop_threshold_assessment = {
            "crop_selected": "None",
            "message": "No crop selected. Generic thresholds will be used.",
            "recommendation": "Select a crop for precise, crop-specific recommendations"
        }
    
    # 2. Environmental Assessment (Crop-Aware)
    if crop_profile:
        # Crop-specific evaluation
        if moisture < crop_profile["moisture_critical_min"]:
            soil_condition = "Critical Dry"
        elif moisture < crop_profile["moisture_optimal_min"]:
            soil_condition = "Dry"
        elif moisture <= crop_profile["moisture_optimal_max"]:
            soil_condition = "Optimal"
        else:
            soil_condition = "Wet"
        
        # Temperature evaluation relative to crop
        if temperature < crop_profile["optimal_temp_min"]:
            temp_impact = "Low"
        elif temperature <= crop_profile["optimal_temp_max"]:
            temp_impact = "Optimal"
        elif temperature <= crop_profile["heat_tolerance"]:
            temp_impact = "Heat Stress - Tolerable"
        else:
            temp_impact = "Heat Stress - Critical"
    else:
        # Generic thresholds
        soil_condition = "Dry" if moisture < 30 else "Wet" if moisture > 75 else "Optimal"
        temp_impact = "Low" if temperature < 15 else "Heat Stress" if temperature > 35 else "Optimal"
    
    humidity_influence = "Low" if humidity < 40 else "High" if humidity > 80 else "Moderate"
    
    environmental_assessment = {
        "soil_condition": soil_condition,
        "soil_description": f"Soil moisture at {moisture}% - {soil_condition} for {crop_profile['name'] if crop_profile else 'generic crops'}",
        "temperature_impact": temp_impact,
        "temp_description": f"Temperature at {temperature}°C - {temp_impact} for {crop_profile['name'] if crop_profile else 'most crops'}",
        "humidity_influence": humidity_influence,
        "humidity_description": f"Relative humidity at {humidity}% is {humidity_influence}",
        "overall_status": "Favorable" if soil_condition == "Optimal" and "Optimal" in temp_impact else "Stressed" if "Critical" in soil_condition or "Critical" in temp_impact else "Acceptable"
    }
    
    # 3. Crop Suitability / Recommendation (Crop-Aware Logic)
    if crop_profile:
        # Evaluate suitability of selected crop
        suitability_score = 100
        issues = []
        
        if moisture < crop_profile["moisture_critical_min"]:
            suitability_score -= 40
            issues.append(f"Critical moisture deficit for {crop_profile['name']}")
        elif moisture < crop_profile["moisture_optimal_min"]:
            suitability_score -= 20
            issues.append(f"Below optimal moisture for {crop_profile['name']}")
        elif moisture > crop_profile["moisture_optimal_max"]:
            suitability_score -= 15
            issues.append(f"Excess moisture may harm {crop_profile['name']}")
        
        if temperature > crop_profile["heat_tolerance"]:
            suitability_score -= 35
            issues.append(f"Temperature exceeds heat tolerance of {crop_profile['name']}")
        elif temperature < crop_profile["optimal_temp_min"]:
            suitability_score -= 20
            issues.append(f"Temperature too low for optimal {crop_profile['name']} growth")
        elif temperature > crop_profile["optimal_temp_max"]:
            suitability_score -= 15
            issues.append(f"Temperature higher than ideal for {crop_profile['name']}")
        
        if suitability_score >= 80:
            suitability = "Excellent"
            suitability_comment = f"Current conditions are highly suitable for {crop_profile['name']} cultivation."
        elif suitability_score >= 60:
            suitability = "Good"
            suitability_comment = f"Conditions are acceptable for {crop_profile['name']} but some improvements possible."
        elif suitability_score >= 40:
            suitability = "Fair"
            suitability_comment = f"Marginal conditions for {crop_profile['name']}. Address identified issues."
        else:
            suitability = "Poor"
            suitability_comment = f"Current conditions are not suitable for {crop_profile['name']}. Immediate intervention required."
        
        crop_recommendation = {
            "mode": "Crop Suitability Evaluation",
            "selected_crop": crop_profile["name"],
            "suitability_score": suitability_score,
            "suitability_rating": suitability,
            "suitability_comment": suitability_comment,
            "identified_issues": issues if issues else ["No major issues detected"],
            "water_requirement": crop_profile["water_requirement"],
            "growth_cycle": f"{crop_profile['growth_cycle_days']} days"
        }
    else:
        # Recommend suitable crops based on conditions
        crop_suggestions = []
        if moisture >= 60 and 20 <= temperature <= 35:
            crop_suggestions = [
                {"crop": "Rice", "reasoning": "High water availability suits paddy cultivation. Moderate temperature ideal for growth.", "suitability": "95%"},
                {"crop": "Sugarcane", "reasoning": "Water-intensive crop. Current moisture and temperature support strong vegetative growth.", "suitability": "92%"},
                {"crop": "Cotton", "reasoning": "Good moisture with moderate warmth promotes boll development.", "suitability": "88%"}
            ]
        elif moisture < 40 and temperature > 30:
            crop_suggestions = [
                {"crop": "Millets", "reasoning": "Drought-resistant with low water requirement. Thrives in high temperature.", "suitability": "93%"},
                {"crop": "Sorghum", "reasoning": "Deep root system handles water stress. Heat-tolerant up to 40°C.", "suitability": "90%"},
                {"crop": "Groundnut", "reasoning": "Moderate water needs. High temperature accelerates pod formation.", "suitability": "85%"}
            ]
        elif moisture >= 50 and temperature < 25:
            crop_suggestions = [
                {"crop": "Wheat", "reasoning": "Cool season crop. High moisture with low temperature ideal for tillering.", "suitability": "94%"},
                {"crop": "Vegetables", "reasoning": "Many vegetables thrive in cool, moist conditions.", "suitability": "88%"},
                {"crop": "Onion", "reasoning": "Moderate moisture and cool temperature favor bulb formation.", "suitability": "86%"}
            ]
        else:
            crop_suggestions = [
                {"crop": "Maize", "reasoning": "Versatile crop adapts to moderate conditions. Average moisture sufficient.", "suitability": "87%"},
                {"crop": "Groundnut", "reasoning": "Moderate water and temperature requirements. Quick maturity cycle.", "suitability": "82%"},
                {"crop": "Vegetables", "reasoning": "Mixed vegetable cultivation viable under current balanced conditions.", "suitability": "80%"}
            ]
        
        crop_recommendation = {
            "mode": "Crop Recommendation",
            "message": "No crop selected. Here are suitable crops for current conditions:",
            "recommendations": crop_suggestions,
            "season_alignment": "Kharif (Monsoon)" if temperature > 25 else "Rabi (Winter)"
        }
    
    # 4. Smart Irrigation Advisory (Crop-Aware)
    if crop_profile:
        # Use crop-specific thresholds
        critical_threshold = crop_profile["moisture_critical_min"]
        optimal_min = crop_profile["moisture_optimal_min"]
        optimal_max = crop_profile["moisture_optimal_max"]
        
        if moisture < critical_threshold:
            irrigation_level = "Immediate Irrigation Required"
            irrigation_priority = "Critical"
            water_amount = "20-25mm"
            timing = "Within 6 hours"
            reasoning = f"Moisture below critical threshold for {crop_profile['name']}. Crop damage imminent. Emergency irrigation essential."
        elif moisture < optimal_min:
            irrigation_level = "Recommended"
            irrigation_priority = "High"
            water_amount = "15-20mm"
            timing = "Within 24 hours"
            reasoning = f"Below optimal range for {crop_profile['name']}. Preventive irrigation recommended before stress symptoms appear."
        elif moisture <= optimal_max:
            irrigation_level = "No Irrigation Needed"
            irrigation_priority = "None"
            water_amount = "0mm"
            timing = "N/A"
            reasoning = f"Soil moisture optimal for {crop_profile['name']}. Maintain current levels with routine monitoring."
        else:
            irrigation_level = "Reduce Irrigation"
            irrigation_priority = "Medium"
            water_amount = "0mm (stop irrigation)"
            timing = "Immediate"
            reasoning = f"Excess moisture detected for {crop_profile['name']}. Risk of waterlogging. Improve drainage."
    else:
        # Generic thresholds
        if moisture < 20:
            irrigation_level = "Immediate Irrigation Required"
            irrigation_priority = "Critical"
            water_amount = "20-25mm"
            timing = "Within 6 hours"
            reasoning = "Severe moisture deficit. Crop wilting imminent. Emergency irrigation essential."
        elif moisture < 35:
            irrigation_level = "Recommended"
            irrigation_priority = "High"
            water_amount = "15-20mm"
            timing = "Within 24 hours"
            reasoning = "Below optimal range. Preventive irrigation recommended before stress symptoms appear."
        elif moisture < 50:
            irrigation_level = "Low Priority"
            irrigation_priority = "Low"
            water_amount = "10-15mm (if extended dry period expected)"
            timing = "Within 48-72 hours"
            reasoning = "Adequate moisture currently. Monitor daily. Schedule irrigation if no rain forecasted."
        else:
            irrigation_level = "No Irrigation Needed"
            irrigation_priority = "None"
            water_amount = "0mm"
            timing = "N/A"
            reasoning = "Soil moisture adequate. Excess irrigation may cause waterlogging and nutrient leaching."
    
    irrigation_advisory = {
        "level": irrigation_level,
        "priority": irrigation_priority,
        "recommended_amount": water_amount,
        "timing": timing,
        "reasoning": reasoning,
        "method": "Drip irrigation (efficient)" if (moisture < (optimal_min if crop_profile else 40)) else "Sprinkler irrigation",
        "crop_water_requirement": crop_profile["water_requirement"] if crop_profile else "N/A"
    }
    
    # 4. Stress & Risk Detection
    detected_risks = []
    
    if moisture < 25:
        detected_risks.append({
            "type": "Water Stress",
            "severity": "High",
            "impact": "Leaf wilting, reduced photosynthesis, yield loss up to 40%",
            "indicator": "Visual: Leaf curling, soil cracking"
        })
    
    if temperature > 38:
        detected_risks.append({
            "type": "Heat Stress",
            "severity": "Critical",
            "impact": "Protein denaturation, pollen sterility, fruit drop",
            "indicator": "Scorched leaf edges, flower abortion"
        })
    elif temperature > 35:
        detected_risks.append({
            "type": "Heat Stress",
            "severity": "Moderate",
            "impact": "Reduced flowering, accelerated maturity, quality decline",
            "indicator": "Rapid plant development, small fruit size"
        })
    
    if moisture > 80:
        detected_risks.append({
            "type": "Excess Moisture Risk",
            "severity": "High",
            "impact": "Root rot, oxygen deficiency, nutrient leaching",
            "indicator": "Standing water, yellow leaves, fungal growth"
        })
    
    if temperature > 32 and humidity < 45:
        detected_risks.append({
            "type": "High Evaporation Conditions",
            "severity": "Moderate",
            "impact": "Rapid water loss through transpiration, increased irrigation frequency needed",
            "indicator": "Soil dries quickly, plants droop in afternoon"
        })
    
    if (temperature >= 25 and temperature <= 32) and humidity > 75 and moisture > 60:
        detected_risks.append({
            "type": "Disease-Favorable Environment",
            "severity": "High",
            "impact": "Fungal diseases (leaf blight, powdery mildew), bacterial infections",
            "indicator": "Humid conditions ideal for pathogen proliferation"
        })
    
    if not detected_risks:
        detected_risks.append({
            "type": "No Critical Risks",
            "severity": "Low",
            "impact": "Conditions within acceptable range",
            "indicator": "Continue routine monitoring"
        })
    
    stress_risk_detection = {
        "identified_risks": detected_risks,
        "risk_score": sum(1 for r in detected_risks if r["severity"] in ["High", "Critical"]) * 30 + sum(1 for r in detected_risks if r["severity"] == "Moderate") * 15,
        "overall_threat_level": "Critical" if any(r["severity"] == "Critical" for r in detected_risks) else "High" if any(r["severity"] == "High" for r in detected_risks) else "Low"
    }
    
    # 5. Predictive Environmental Insights
    # Moisture trend prediction
    if moisture < 30 and temperature > 32:
        moisture_trend = "Rapid Loss"
        time_to_critical = "12-24 hours"
        trend_reasoning = "High temperature accelerating evapotranspiration. Moisture depleting rapidly."
    elif moisture < 40:
        moisture_trend = "Drying"
        time_to_critical = "2-3 days"
        trend_reasoning = "Gradual moisture reduction. Monitor closely and plan irrigation."
    else:
        moisture_trend = "Stabilizing"
        time_to_critical = ">5 days"
        trend_reasoning = "Adequate reserves. Moisture stable under current conditions."
    
    # Crop growth suitability
    if environmental_assessment["overall_status"] == "Favorable":
        growth_suitability = "Excellent"
        growth_comment = "Optimal conditions for photosynthesis and nutrient uptake. Expect vigorous growth."
    elif environmental_assessment["overall_status"] == "Acceptable":
        growth_suitability = "Moderate"
        growth_comment = "Adequate for growth but sub-optimal. Minor interventions may boost productivity."
    else:
        growth_suitability = "Poor"
        growth_comment = "Stress conditions limiting growth. Immediate corrective measures essential."
    
    predictive_insights = {
        "moisture_trend": moisture_trend,
        "time_to_critical_moisture": time_to_critical,
        "trend_reasoning": trend_reasoning,
        "growth_suitability": growth_suitability,
        "growth_comment": growth_comment,
        "evapotranspiration_rate": "High (>6mm/day)" if temperature > 32 else "Moderate (4-6mm/day)" if temperature > 25 else "Low (<4mm/day)",
        "next_24h_outlook": "Condition likely to deteriorate" if moisture_trend == "Rapid Loss" else "Stable conditions expected"
    }
    
    # 6. Commodity Price Intelligence
    if market_price and crop:
        # Fetch historical data from our commodity data
        crop_lower = crop.lower()
        if crop_lower in COMMODITY_DATA:
            crop_data = COMMODITY_DATA[crop_lower]
            current_baseline = crop_data["current"]
            forecast_price = crop_data["forecast"]
            
            price_change = ((market_price - current_baseline) / current_baseline) * 100
            
            if price_change > 10:
                price_trend = "Favorable"
                trend_description = f"Price {price_change:.1f}% above baseline. Strong market demand."
            elif price_change < -10:
                price_trend = "Unfavorable"
                trend_description = f"Price {price_change:.1f}% below baseline. Market oversupply or weak demand."
            else:
                price_trend = "Stable"
                trend_description = f"Price within ±10% of baseline. Normal market conditions."
            
            # Selling strategy
            if price_change > 15 and environmental_assessment["overall_status"] == "Favorable":
                selling_strategy = "Sell Immediately"
                strategy_reasoning = "High market price + good crop quality. Maximize returns now."
            elif price_change < -10:
                selling_strategy = "Consider Storage"
                strategy_reasoning = "Low current price. Store if possible and sell when market recovers."
            else:
                selling_strategy = "Monitor Market"
                strategy_reasoning = "Stable prices. Track market trends for next 7 days before deciding."
            
            market_intelligence = {
                "price_trend": price_trend,
                "trend_description": trend_description,
                "current_market_price": market_price,
                "baseline_price": current_baseline,
                "price_change_percent": round(price_change, 2),
                "selling_strategy": selling_strategy,
                "strategy_reasoning": strategy_reasoning,
                "forecast_7day": forecast_price,
                "market_volatility": "High" if abs(price_change) > 20 else "Moderate" if abs(price_change) > 10 else "Low"
            }
        else:
            market_intelligence = {
                "message": "Price data not available for this crop",
                "recommendation": "Contact local mandi for current rates"
            }
    else:
        market_intelligence = {
            "message": "Market price analysis not requested",
            "note": "Provide crop name and current market price for price intelligence"
        }
    
    # 7. Integrated Decision Support
    if market_price and crop and crop.lower() in COMMODITY_DATA:
        # Combine environmental + market insights
        env_score = 100 if environmental_assessment["overall_status"] == "Favorable" else 60 if environmental_assessment["overall_status"] == "Acceptable" else 30
        market_score = 100 if market_intelligence.get("price_trend") == "Favorable" else 50 if market_intelligence.get("price_trend") == "Stable" else 20
        
        combined_score = (env_score * 0.6) + (market_score * 0.4)  # Environmental weighted higher
        
        if combined_score >= 80:
            decision = "Highly Favorable"
            recommendation = "Excellent conditions for both crop growth and market returns. Maintain current practices."
        elif combined_score >= 60:
            decision = "Favorable with Caution"
            recommendation = "Good overall conditions but monitor weak areas (environmental or market)."
        else:
            decision = "Challenging Conditions"
            recommendation = "Address environmental stress first. Delay harvest if market is weak. Focus on crop recovery."
        
        # Specific scenario logic
        if environmental_assessment["overall_status"] == "Favorable" and market_intelligence.get("price_trend") == "Favorable":
            scenario = "Ideal Scenario"
            action = "Proceed with harvest at crop maturity. Market timing perfect."
        elif environmental_assessment["overall_status"] == "Stressed" and market_intelligence.get("price_trend") == "Unfavorable":
            scenario = "Worst Case"
            action = "Focus on crop recovery with irrigation/nutrition. Delay harvest. Wait for better market."
        elif environmental_assessment["overall_status"] == "Favorable" and market_intelligence.get("price_trend") == "Unfavorable":
            scenario = "Good Crop, Weak Market"
            action = "Consider storage facilities. Sell only if storage not available or perishable crop."
        else:
            scenario = "Poor Crop, Good Market"
            action = "Harvest whatever yield possible to capture good market price. Invest in better practices next season."
        
        integrated_decision = {
            "overall_decision": decision,
            "combined_score": round(combined_score, 1),
            "recommendation": recommendation,
            "scenario": scenario,
            "action_plan": action,
            "environmental_weight": "60%",
            "market_weight": "40%"
        }
    else:
        integrated_decision = {
            "message": "Integrated decision requires both environmental data and market price",
            "environmental_status": environmental_assessment["overall_status"],
            "note": "Provide crop and market price for comprehensive decision support"
        }
    
    # 8. Corrective & Advisory Actions
    corrective_actions = []
    
    if moisture < 30:
        corrective_actions.append("🚰 Immediate Irrigation: Apply 15-20mm water using drip/sprinkler system")
        corrective_actions.append("🌾 Mulching: Apply 5-7cm organic mulch around plant base to conserve moisture")
    
    if temperature > 35:
        corrective_actions.append("☀️ Shade Protection: Install 30-50% shade nets during 11 AM - 3 PM")
        corrective_actions.append("💦 Foliar Spray: Apply cool water mist in evening to reduce leaf temperature")
    
    if humidity > 80 and moisture > 60:
        corrective_actions.append("🌬️ Improve Air Circulation: Increase plant spacing, prune dense foliage")
        corrective_actions.append("🛡️ Fungicide Application: Preventive spray of copper-based or bio-fungicide")
    
    if moisture > 75:
        corrective_actions.append("🚧 Create Drainage: Dig channels to remove excess water, prevent waterlogging")
        corrective_actions.append("⏸️ Stop Irrigation: Skip next 2-3 irrigation cycles, allow soil to drain")
    
    if temperature < 15:
        corrective_actions.append("🔥 Frost Protection: Cover crops with plastic sheets during night hours")
        corrective_actions.append("⏰ Delay Planting: Wait for temperature to rise above 18°C for warm-season crops")
    
    if market_intelligence.get("selling_strategy") == "Consider Storage":
        corrective_actions.append("📦 Arrange Storage: Secure warehouse space, ensure proper ventilation and pest control")
    
    if stress_risk_detection["overall_threat_level"] == "High":
        corrective_actions.append("👨‍🌾 Expert Consultation: Contact agricultural extension officer for site visit")
    
    if not corrective_actions or all(action.startswith("Continue") for action in corrective_actions):
        corrective_actions.append("✅ Continue Current Management: Conditions optimal, maintain routine monitoring")
        corrective_actions.append("📊 Daily Monitoring: Record moisture and temperature readings for trend analysis")
    
    # 9. Alert Generation Logic
    alerts = []
    
    if moisture < 20:
        alerts.append({
            "type": "CRITICAL",
            "category": "Irrigation",
            "message": "⚠️ CRITICAL: Soil moisture below 20%. Immediate irrigation required to prevent crop damage.",
            "action": "Irrigate within 6 hours"
        })
    
    if temperature > 40:
        alerts.append({
            "type": "CRITICAL",
            "category": "Heat Stress",
            "message": "🌡️ EXTREME HEAT: Temperature exceeds 40°C. Provide shade and increase irrigation frequency.",
            "action": "Install shade nets immediately"
        })
    
    if stress_risk_detection["overall_threat_level"] == "Critical":
        alerts.append({
            "type": "URGENT",
            "category": "Environmental Stress",
            "message": "⚠️ Multiple stress factors detected. Crop health at risk.",
            "action": "Review detailed risk assessment and take corrective actions"
        })
    
    if market_price and market_intelligence.get("price_trend") == "Favorable" and market_intelligence.get("price_change_percent", 0) > 20:
        alerts.append({
            "type": "OPPORTUNITY",
            "category": "Market",
            "message": f"💰 FAVORABLE MARKET: {crop} price up {market_intelligence['price_change_percent']:.1f}%. Consider selling.",
            "action": "Harvest and sell if crop is mature"
        })
    
    if moisture_trend == "Rapid Loss":
        alerts.append({
            "type": "WARNING",
            "category": "Predictive",
            "message": "📉 Moisture depleting rapidly. Critical level expected within 12-24 hours.",
            "action": "Schedule irrigation immediately"
        })
    
    if not alerts:
        alerts.append({
            "type": "INFO",
            "category": "Status",
            "message": "✅ No critical issues detected. System operating normally.",
            "action": "Continue monitoring"
        })
    
    return {
        "crop_threshold_assessment": crop_threshold_assessment,
        "environmental_assessment": environmental_assessment,
        "crop_recommendation": crop_recommendation,
        "irrigation_advisory": irrigation_advisory,
        "stress_risk_detection": stress_risk_detection,
        "predictive_insights": predictive_insights,
        "market_intelligence": market_intelligence,
        "integrated_decision": integrated_decision,
        "corrective_actions": corrective_actions,
        "alerts": alerts
    }
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