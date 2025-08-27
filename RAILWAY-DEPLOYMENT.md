# Railway Deployment Guide

This guide explains how to deploy your application with the integrated admin dashboard to Railway.

## Overview

The application is configured to deploy as a single service that includes:
- FastAPI backend (your main application)
- Admin dashboard backend (integrated into main backend)
- Admin dashboard frontend (built and served as static files)

## URLs After Deployment

- **Main Application**: `https://your-app.railway.app/`
- **Admin Dashboard**: `https://your-app.railway.app/admin/dashboard/`
- **Admin API**: `https://your-app.railway.app/admin/api/`
- **API Documentation**: `https://your-app.railway.app/docs`

## Deployment Steps

### 1. Connect Repository to Railway
1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository

### 2. Configure Environment Variables
In your Railway project settings, add these environment variables:

**Required:**
```
ANTHROPIC_API_KEY=your-anthropic-api-key
ADMIN_TOKEN=your-secure-admin-token-here
```

**Optional:**
```
GOOGLE_API_KEY=your-google-api-key
PORT=8000
WATCHFILES_FORCE_POLLING=true
```

**Generate a secure admin token:**
```bash
openssl rand -hex 32
```

### 3. Deploy
Railway will automatically:
1. Use the `Dockerfile` to build your application
2. Build the admin frontend during the Docker build process
3. Serve both backend API and frontend static files
4. Deploy to your custom domain

## Local Testing

Test the integrated setup locally:

```bash
# Build admin frontend
npm run admin:build

# Build and run with Docker
npm run backend:build
npm run backend:dev
```

Then visit:
- Backend API: `http://localhost:8000/docs`
- Admin Dashboard: `http://localhost:8000/admin/dashboard/`

## File Structure

```
/
├── Dockerfile                 # Multi-stage build with Node.js and Python
├── railway.toml              # Railway configuration
├── backend/                  # Python FastAPI backend
├── admin/
│   └── frontend/
│       └── dist/            # Built admin frontend (served at /admin/dashboard/)
└── public/                  # Your main application content
```

## Troubleshooting

### Admin Dashboard Not Loading
- Check that `ADMIN_TOKEN` environment variable is set
- Verify admin frontend built correctly (`admin/frontend/dist/` should exist)
- Check Railway logs for any build errors

### API Errors
- Ensure all required environment variables are set
- Check Railway application logs for backend errors
- Verify your API keys are valid

### Build Failures
- Ensure Node.js dependencies in `admin/frontend/package.json` are correct
- Check that Python dependencies in `backend/requirements.txt` are up to date
- Review Railway build logs for specific error messages

## Security Notes

- Always use a strong, unique `ADMIN_TOKEN` 
- Never commit API keys or tokens to your repository
- The admin dashboard is protected by token authentication
- All traffic uses HTTPS on Railway by default