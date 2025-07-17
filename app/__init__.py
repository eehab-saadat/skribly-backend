import os
import logging
from flask import Flask, request, make_response
from flask_socketio import SocketIO
# from flask_cors import CORS  # Commented out - using manual CORS handling
from app.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get logger
logger = logging.getLogger(__name__)

# Initialize extensions
socketio = SocketIO()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    logger.info(f"🚀 Starting Flask app with config: {config_name}")
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Configure session settings for cross-origin requests
    # For SameSite=None to work, Secure must be True, but we're on HTTP localhost
    # So we'll use Lax and implement a different solution
    app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in development
    app.config['SESSION_COOKIE_HTTPONLY'] = False  # Allow JS access for debugging
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # More permissive for development
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow subdomain sharing
    
    logger.info(f"📋 App config loaded: SECRET_KEY={'set' if app.config.get('SECRET_KEY') else 'NOT SET'}")
    logger.info(f"📋 Debug mode: {app.config.get('DEBUG', False)}")
    logger.info(f"📋 Session cookie settings: secure={app.config['SESSION_COOKIE_SECURE']}, samesite={app.config['SESSION_COOKIE_SAMESITE']}")
    
    # Configure CORS to allow all origins with credentials
    logger.info("🌐 Configuring CORS...")
    
    # Disable Flask-CORS and handle CORS manually for better control
    # CORS(app, resources={r"/*": {"origins": "*"}})
    logger.info(f"✅ CORS will be handled manually in after_request")
    
    # Configure SocketIO to allow all origins with credentials
    logger.info("🔌 Configuring SocketIO...")
    

    
    # Define explicit allowed origins for Socket.IO (no wildcards allowed)
    socketio_allowed_origins = [
        'https://immortal-allowed-bulldog.ngrok-free.app',
        'https://heron-ruling-deadly.ngrok-free.app',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5000',
        'http://127.0.0.1:5000'
    ]
    
    logger.info(f"🔌 Socket.IO allowed origins: {socketio_allowed_origins}")
    
    socketio.init_app(app, 
                     cors_allowed_origins=socketio_allowed_origins,  # Use explicit list instead of function
                     cors_credentials=True,                          # Enable credentials
                     async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),
                     logger=True,   # Enable logging for debugging
                     engineio_logger=True,  # Enable engine.io logging
                     ping_timeout=60,       # Optimize for ngrok
                     ping_interval=25,      # Optimize for ngrok
                     transports=['polling', 'websocket'], # Allow both transports for ngrok
                     manage_session=False,  # Use Flask's session management
                     allow_upgrades=True,   # Enable WebSocket upgrades for better ngrok performance
                     cookie=None)           # Disable cookies for CORS compatibility
    logger.info("✅ SocketIO configured successfully with explicit origins list")
    
    # Register blueprints
    logger.info("📚 Registering blueprints...")
    from app.routes.auth import auth_bp
    from app.routes.rooms import rooms_bp
    from app.routes.game import game_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(rooms_bp, url_prefix='/api/rooms')
    app.register_blueprint(game_bp, url_prefix='/api/game')
    logger.info("✅ Blueprints registered successfully")
    
    # Register socket handlers
    logger.info("🔌 Registering socket handlers...")
    from app.socket_handlers import room_handlers, game_handlers, drawing_handlers
    logger.info("✅ Socket handlers registered successfully")
    
    # Initialize services
    logger.info("🧠 Initializing memory service...")
    from app.services.memory_service import memory_service
    memory_service.init_app(app)
    logger.info("✅ Memory service initialized successfully")
    
    logger.info("📚 Initializing word service...")
    from app.services.word_service import word_service
    word_service.init_app(app)
    logger.info("✅ Word service initialized successfully")
    
    logger.info("⏰ Initializing timer service...")
    from app.services.timer_service import timer_service
    timer_service.init_app(app)
    logger.info("✅ Timer service initialized successfully")
    
    @app.route('/health')
    def health_check():
        from flask import jsonify
        response = jsonify({'status': 'healthy', 'service': 'skribbl-clone-backend'})
        response.headers['Content-Type'] = 'application/json'
        return response
    
    @app.route('/api/health')
    def api_health_check():
        from flask import jsonify
        response = jsonify({
            'status': 'healthy', 
            'service': 'skribbl-clone-backend', 
            'api': 'working',
            'cors_configured': True,
            'socket_available': True
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    
    # Handle preflight OPTIONS requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            logger.info(f"🔄 Handling preflight request for {request.path}")
            origin = request.headers.get('Origin')
            
            # Define allowed origins
            allowed_origins = [
                'https://immortal-allowed-bulldog.ngrok-free.app',
                'https://heron-ruling-deadly.ngrok-free.app',
                'http://localhost:3000',
                'http://127.0.0.1:3000',
                'http://localhost:5000',
                'http://127.0.0.1:5000'
            ]
            
            response = make_response()
            
            # Never use wildcard with credentials - always specify exact origin
            if origin and (origin in allowed_origins or 
                          '.ngrok-free.app' in origin or 
                          '.ngrok.app' in origin or 
                          '.ngrok.io' in origin or
                          origin.startswith('http://localhost:') or 
                          origin.startswith('http://127.0.0.1:')):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                logger.info(f"✅ Preflight origin allowed: {origin}")
            elif origin:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                logger.info(f"⚠️ Preflight origin allowed (fallback): {origin}")
            else:
                # No origin - this shouldn't happen with modern browsers
                logger.warning("❌ Preflight request without origin header")
                return response
                
            response.headers['Vary'] = 'Origin'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,X-Session-ID,ngrok-skip-browser-warning,User-Agent'
            response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
            response.headers['Access-Control-Max-Age'] = '3600'
            logger.info(f"✅ Preflight request handled for origin: {origin}")
            return response

    # Add comprehensive CORS headers for all responses
    @app.after_request
    def after_request(response):
        logger.info(f"📡 {request.method} {request.path} -> {response.status_code}")
        
        # Get the origin of the request
        origin = request.headers.get('Origin')
        logger.info(f"🌐 Request origin: {origin}")
        
        # Define allowed origins
        allowed_origins = [
            'https://immortal-allowed-bulldog.ngrok-free.app',
            'https://heron-ruling-deadly.ngrok-free.app',
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:5000',
            'http://127.0.0.1:5000'
        ]
        
        # Set CORS headers - never use wildcard with credentials
        if origin and (origin in allowed_origins or 
                      '.ngrok-free.app' in origin or 
                      '.ngrok.app' in origin or 
                      '.ngrok.io' in origin or
                      origin.startswith('http://localhost:') or 
                      origin.startswith('http://127.0.0.1:')):
            response.headers['Access-Control-Allow-Origin'] = origin
            logger.info(f"✅ CORS origin allowed: {origin}")
        elif origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            logger.info(f"⚠️ CORS origin allowed (fallback): {origin}")
        else:
            # No origin header - don't set CORS headers
            logger.info("ℹ️ No origin header, skipping CORS")
            return response
            
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,X-Session-ID,ngrok-skip-browser-warning,User-Agent'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        
        logger.info(f"✅ CORS headers manually added for origin: {origin}")
        
        return response
    
    return app 