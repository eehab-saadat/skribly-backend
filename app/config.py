# Backend Application Configuration
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'skribbl-clone-dev-secret-key-123456789'
    
    # CORS configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # Server configuration
    HOST = os.environ.get('HOST') or '127.0.0.1'
    PORT = int(os.environ.get('PORT') or 5000)
    
    # Socket.IO configuration
    SOCKETIO_ASYNC_MODE = os.environ.get('SOCKETIO_ASYNC_MODE') or 'threading'
    
    # Game configuration
    WORD_SELECTION_TIME = int(os.environ.get('WORD_SELECTION_TIME') or 10)
    DRAWING_TIME = int(os.environ.get('DRAWING_TIME') or 80)
    RESULT_DISPLAY_TIME = int(os.environ.get('RESULT_DISPLAY_TIME') or 5)

# Game Configuration Constants
class GameConfig:
    # Default Game Settings
    DEFAULT_ROUNDS = 3
    DEFAULT_DRAW_TIME = 80
    DEFAULT_MAX_PLAYERS = 8
    DEFAULT_WORD_DIFFICULTY = 'medium'
    
    # Game Limits
    MIN_PLAYERS = 2
    MAX_PLAYERS = 12
    MIN_ROUNDS = 1
    MAX_ROUNDS = 10
    MIN_DRAW_TIME = 30
    MAX_DRAW_TIME = 300  # Backend allows higher than frontend
    
    # Valid Options
    WORD_DIFFICULTIES = ['easy', 'medium', 'hard']

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 