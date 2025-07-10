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
    
    logger.info(f"📋 App config loaded: SECRET_KEY={'set' if app.config.get('SECRET_KEY') else 'NOT SET'}")
    logger.info(f"📋 Debug mode: {app.config.get('DEBUG', False)}")
    
    # Configure CORS with specific origins for credentials support
    logger.info("🌐 Configuring CORS...")
    CORS(app, 
         origins=['http://localhost:3000', 'http://127.0.0.1:3000'],  # Specific origins for credentials
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    logger.info("✅ CORS configured successfully")
    
    # Configure SocketIO with specific origins for credentials support
    logger.info("🔌 Configuring SocketIO...")
    socketio.init_app(app, 
                     cors_allowed_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],  # Specific origins for credentials
                     async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),
                     logger=False,  # Disable verbose logging
                     engineio_logger=False,
                     ping_timeout=60,
                     ping_interval=25,
                     transports=['polling', 'websocket'],
                     manage_session=False)  # Use Flask's session management
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
        
        # Get the origin from the request
        origin = request.headers.get('Origin')
        allowed_origins = ['http://localhost:3000', 'http://127.0.0.1:3000']
        
        # Set specific origin if it's in our allowed list
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
        
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    return app 