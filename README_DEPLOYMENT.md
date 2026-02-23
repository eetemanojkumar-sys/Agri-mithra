# AgriSmart - Vercel Deployment Guide

## Prerequisites
1. Vercel account (sign up at vercel.com)
2. MongoDB Atlas account (for cloud database)
3. Vercel CLI installed: `npm i -g vercel`

## Deployment Steps

### 1. Prepare MongoDB Atlas
```bash
# Create MongoDB Atlas cluster at mongodb.com/cloud/atlas
# Get connection string (looks like):
# mongodb+srv://username:password@cluster.mongodb.net/
```

### 2. Install Vercel CLI
```bash
npm install -g vercel
```

### 3. Login to Vercel
```bash
vercel login
```

### 4. Deploy Backend (FastAPI)
```bash
cd /app/backend
vercel --prod

# Set environment variables in Vercel dashboard:
# MONGO_URL=your_mongodb_connection_string
# DB_NAME=agrismart
# CORS_ORIGINS=*
```

### 5. Update Frontend Environment
```bash
# Update /app/frontend/.env with your backend URL
REACT_APP_BACKEND_URL=https://your-backend.vercel.app
```

### 6. Deploy Frontend (React)
```bash
cd /app/frontend
yarn build
vercel --prod
```

## Environment Variables

### Backend (.env)
```
MONGO_URL=mongodb+srv://...
DB_NAME=agrismart
CORS_ORIGINS=*
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=https://your-backend-url.vercel.app
```

## Post-Deployment

1. **Test API**: Visit `https://your-backend.vercel.app/api/`
2. **Test Frontend**: Visit `https://your-frontend.vercel.app`
3. **Check Crop Selector**: Ensure all 11 crops load
4. **Start Simulator**: Test sensor data generation
5. **Connect ThingSpeak**: Test IoT integration

## Troubleshooting

### Backend Issues
- Check Vercel logs: `vercel logs`
- Verify MongoDB connection string
- Ensure all environment variables are set

### Frontend Issues
- Clear build cache: `rm -rf build node_modules && yarn install`
- Check REACT_APP_BACKEND_URL points to correct backend
- Verify CORS settings on backend

### CORS Errors
- Add frontend URL to CORS_ORIGINS in backend env
- Format: `https://frontend.vercel.app,https://www.yourdomain.com`

## Custom Domain (Optional)

1. Go to Vercel dashboard
2. Select your project
3. Go to Settings > Domains
4. Add your custom domain
5. Update DNS records as instructed

## Scaling Considerations

- **MongoDB**: Use Atlas M10+ cluster for production
- **Vercel**: Pro plan for better performance
- **Rate Limiting**: Add rate limiting for API endpoints
- **Caching**: Implement caching for crop profiles

## Support

For issues, check:
- Vercel documentation: vercel.com/docs
- MongoDB Atlas docs: docs.atlas.mongodb.com
- AgriSmart features: All 11 crop profiles with dynamic thresholds
