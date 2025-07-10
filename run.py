#!/usr/bin/env python3
import os
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Starting Skribly server...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"   Mode: In-Memory Only (no database)")
    print(f"   Health check: http://{host}:{port}/health")
    
    socketio.run(app, host=host, port=port, debug=debug) 