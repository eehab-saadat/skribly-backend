clea# Production Deployment Guide

## Backend (PythonAnywhere)

Set these environment variables in your PythonAnywhere console:

```bash
# Flask Configuration
export FLASK_ENV=production
export FLASK_DEBUG=False
export SECRET_KEY=your-super-secret-production-key-here

# CORS Configuration
export CORS_ORIGINS=https://skribly.netlify.app,https://app.netlify.com

# Server Configuration
export HOST=0.0.0.0
export PORT=5000

# Socket.IO Configuration
export SOCKETIO_ASYNC_MODE=threading

# Game Configuration
export WORD_SELECTION_TIME=10
export DRAWING_TIME=80
export RESULT_DISPLAY_TIME=5
```

Or create a `.env` file in your project root with these values.

## Frontend (Netlify)

Set these environment variables in your Netlify dashboard:

```bash
# Backend API Configuration
NEXT_PUBLIC_API_URL=https://eehabsaadat.pythonanywhere.com
NEXT_PUBLIC_SOCKET_URL=https://eehabsaadat.pythonanywhere.com

# Application Configuration
NEXT_PUBLIC_APP_NAME=Skribly
NEXT_PUBLIC_APP_VERSION=1.0.0

# Build Configuration
NODE_ENV=production
```

## CORS Configuration

The backend is now configured to allow these specific origins:
- `http://localhost:3000` (local development)
- `http://127.0.0.1:3000` (local development)
- `https://skribly.netlify.app` (production frontend)
- `https://eehabsaadat.pythonanywhere.com` (production backend)
- `https://app.netlify.com` (Netlify preview builds)

## Deployment Steps

### Backend (PythonAnywhere)
1. Upload your code to PythonAnywhere
2. Set environment variables as shown above
3. Install dependencies: `pip install -r requirements.txt`
4. Restart your web app

### Frontend (Netlify)
1. Connect your GitHub repository to Netlify
2. Set environment variables in Netlify dashboard
3. Set build command: `npm run build`
4. Set publish directory: `.next`
5. Deploy

## Testing CORS

After deployment, check the backend logs for CORS debug messages:
- ✅ `CORS allowed for origin: https://skribly.netlify.app`
- ❌ `CORS blocked for origin: [blocked-origin]`

If you see blocked origins, add them to the `CORS_ORIGINS` environment variable.

## Troubleshooting

1. **Authentication Errors**: Make sure `SECRET_KEY` is set and consistent
2. **CORS Errors**: Check that your frontend URL exactly matches the allowed origins
3. **Socket.IO Issues**: Ensure both frontend and backend use the same credentials settings (now both use `true`)
4. **Session Issues**: Verify that cookies are working across domains (they should with the current setup) 