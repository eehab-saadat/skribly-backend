import os
import logging
from flask import Flask, request, make_response
from flask_socketio import SocketIO
from flask_cors import CORS
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
    app.config['SESSION_COOKIE_SECURE'] = config_name == 'production'  # Only HTTPS in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'None' if config_name == 'production' else 'Lax'
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow subdomain sharing
    
    logger.info(f"📋 App config loaded: SECRET_KEY={'set' if app.config.get('SECRET_KEY') else 'NOT SET'}")
    logger.info(f"📋 Debug mode: {app.config.get('DEBUG', False)}")
    logger.info(f"📋 Session cookie settings: secure={app.config['SESSION_COOKIE_SECURE']}, samesite={app.config['SESSION_COOKIE_SAMESITE']}")
    
    # Configure CORS to allow all origins
    logger.info("🌐 Configuring CORS...")
    
    # Get allowed origins from environment or use defaults
    allowed_origins = [
        'http://localhost:3000',                          # Local development
        'http://127.0.0.1:3000',                         # Local development
        'https://skribly.netlify.app',                   # Production frontend
        'https://eehabsaadat.pythonanywhere.com',        # Production backend (for health checks)
        'https://app.netlify.com',                       # Netlify preview builds
    ]
    
    # Add any additional origins from environment
    env_origins = os.environ.get('CORS_ORIGINS', '')
    if env_origins:
        additional_origins = [origin.strip() for origin in env_origins.split(',')]
        allowed_origins.extend(additional_origins)
    
    CORS(app, 
         origins=allowed_origins,         # Use specific origins instead of wildcard
         supports_credentials=True,       # Enable credentials with specific origins
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    logger.info(f"✅ CORS configured successfully with origins: {allowed_origins}")
    
    # Configure SocketIO to allow specific origins
    logger.info("🔌 Configuring SocketIO...")
    socketio.init_app(app, 
                     cors_allowed_origins=allowed_origins,  # Use specific origins
                     cors_credentials=True,                 # Enable credentials with specific origins
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
    
    # Add comprehensive CORS headers for all responses
    @app.after_request
    def after_request(response):
        logger.info(f"📡 {request.method} {request.path} -> {response.status_code}")
        
        # Get the origin of the request
        origin = request.headers.get('Origin')
        logger.info(f"🌐 Request origin: {origin}")
        
        # Check if the origin is in our allowed list
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            logger.info(f"✅ CORS allowed for origin: {origin}")
        else:
            logger.warning(f"❌ CORS blocked for origin: {origin}")
            logger.info(f"🔍 Allowed origins: {allowed_origins}")
        
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    return app 