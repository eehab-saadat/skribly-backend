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
    socketio.init_app(app, 
                     cors_allowed_origins="*",                  # Allow all origins
                     cors_credentials=True,                     # Enable credentials (manual CORS handling)
                     async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),
                     logger=True,   # Enable logging for debugging
                     engineio_logger=True,  # Enable engine.io logging
                     ping_timeout=120,      # Increase timeout for PythonAnywhere
                     ping_interval=60,      # Increase ping interval
                     transports=['polling'], # Only use polling for PythonAnywhere
                     manage_session=False,  # Use Flask's session management
                     allow_upgrades=False,  # Disable WebSocket upgrades for PythonAnywhere
                     cookie=None)           # Disable cookies for CORS compatibility
    logger.info("✅ SocketIO configured successfully")
    
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
        return {'status': 'healthy', 'service': 'skribbl-clone-backend'}
    
    @app.route('/api/health')
    def api_health_check():
        return {'status': 'healthy', 'service': 'skribbl-clone-backend', 'api': 'working'}
    
    # Handle preflight OPTIONS requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            logger.info(f"🔄 Handling preflight request for {request.path}")
            origin = request.headers.get('Origin')
            response = make_response()
            if origin:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Vary'] = 'Origin'
            else:
                response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,X-Session-ID'
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
        
        # Manually add CORS headers to ensure they work with any origin
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Vary'] = 'Origin'  # Important for caching
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
        
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,X-Session-ID'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        
        logger.info(f"✅ CORS headers manually added for origin: {origin}")
        
        return response
    
    return app 