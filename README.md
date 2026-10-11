# Agri Mitra / AgriSmart

A smart agriculture prototype combining IoT sensor monitoring, crop-specific irrigation guidance, commodity-price demo charts, and AquaGuard climate-smart water assessment.

## Current capabilities
- React dashboard with simulator and ThingSpeak sensor connection modes.
- FastAPI backend and MongoDB integration.
- Crop profiles and irrigation advisories.
- ThingSpeak motor-command integration for compatible ESP32/NodeMCU hardware.
- AquaGuard water/heat risk assessment based on transparent rules.
- Optional private S3 archival for sensor readings.

## Tech stack
- Frontend: React, Tailwind CSS, Chart.js
- Backend: FastAPI, Pydantic, HTTPX
- Data: MongoDB and optional S3 telemetry archive
- IoT: ThingSpeak, ESP32/NodeMCU (hardware required for real actuation)

## Run locally
Backend:
```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn server:app --reload
```

Frontend:
```bash
cd frontend
yarn install
# Set REACT_APP_BACKEND_URL in frontend/.env to the backend origin
yarn start
```

## AquaGuard
See [AQUAGUARD_AWS_DEPLOYMENT.md](AQUAGUARD_AWS_DEPLOYMENT.md) for S3 setup and permissions. AWS archiving is optional and disabled until configured. The risk engine is rule-based demonstration logic, not a trained ML model. Do not use its output as the sole control for real irrigation equipment.

## Existing deployment
The project includes Vercel configuration and a Vercel deployment guide. Adding optional S3 storage does not itself deploy the backend to AWS.

## Security
- Keep environment files out of Git.
- Never put AWS credentials, ThingSpeak write keys, or database credentials in source code.
- Use least-privilege IAM and keep the S3 bucket private.
