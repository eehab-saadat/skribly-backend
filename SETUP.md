# Backend Setup Instructions

## Environment Configuration

Create a `.env` file in the `backend/` directory with the following content:

```bash
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=skribbl-clone-dev-secret-key-123456789

# Database Configuration
DATABASE_URL=sqlite:///instance/database.db

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Server Configuration
HOST=127.0.0.1
PORT=5000

# Memory Service Configuration
BACKUP_INTERVAL=300

# Socket.IO Configuration
SOCKETIO_ASYNC_MODE=threading

# Game Configuration
WORD_SELECTION_TIME=10
DRAWING_TIME=80
RESULT_DISPLAY_TIME=5
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create the .env file** (copy the content above)

3. **Run the server:**
   ```bash
   python run.py
   ```

4. **Verify it's working:**
   - Server should start on http://127.0.0.1:5000
   - Visit http://127.0.0.1:5000/health to check status

## Troubleshooting

- **Database issues**: Make sure `instance/` directory exists
- **Port conflicts**: Change PORT in .env file
- **CORS errors**: Verify CORS_ORIGINS includes your frontend URL 