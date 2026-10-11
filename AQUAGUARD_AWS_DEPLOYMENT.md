# AquaGuard AWS setup

AquaGuard adds a rule-based water/heat assessment endpoint and optional JSON telemetry archival to Amazon S3. The existing app can continue running on Vercel; S3 archival requires AWS configuration on the backend runtime.

## 1. Configure S3
1. Create a private S3 bucket in your chosen AWS Region.
2. Keep Block Public Access enabled.
3. Give the backend runtime identity only s3:PutObject permission for arn:aws:s3:::YOUR_BUCKET/aquaguard/telemetry/*.
4. Prefer an IAM role/instance profile or the hosting provider's supported secret environment variables. Do not commit access keys.

## 2. Backend environment variables
Set AQUAGUARD_S3_BUCKET=your-private-bucket-name and AWS_REGION=ap-south-1 (or your bucket's region).
The AWS SDK uses its standard credential chain. An EC2 IAM role is available only when the backend actually runs on EC2. Never expose AWS secrets to the React app.

## 3. API endpoints
- POST /api/aquaguard/analyze — body: {"moisture": 32, "temperature": 38, "humidity": 28, "rain": 0, "crop": "tomato"}
- POST /api/aquaguard/telemetry — same body; writes one JSON object to S3 when configured.
- GET /api/ — existing API health endpoint.

## 4. Local verification
From backend/, install requirements and run uvicorn server:app --reload. Open /docs to test the two endpoints. The analysis is an explainable rule-based demonstration, not a trained prediction model or agronomic guarantee. Calibrate thresholds and validate sensor readings before any automated irrigation.

## 5. Safety
This feature does not turn the pump on automatically. Keep pump control manual until hardware interlocks, dry-run protection, maximum run time, and sensor-failure handling have been tested.
