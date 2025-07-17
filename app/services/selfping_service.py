import threading
import time
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SelfPingService:
    """Service to ping the app's own health endpoint periodically to keep it awake"""
    
    def __init__(self):
        self.app = None
        self.base_url: Optional[str] = None
        self.ping_interval = 60  # 60 seconds = 1 minute
        self.ping_thread: Optional[threading.Thread] = None
        self.running = False
        self.health_url = None
        
    def init_app(self, app):
        """Initialize the service with Flask app"""
        self.app = app
        
        # Determine the base URL for health pings
        # Try to get from environment or use default
        import os
        self.base_url = os.environ.get('SELF_PING_URL')
        
        if not self.base_url:
            # Construct URL from HOST and PORT
            host = app.config.get('HOST', '127.0.0.1')
            port = app.config.get('PORT', 5000)
            
            # Use production URL if we're on Render or similar
            if 'onrender.com' in os.environ.get('RENDER_EXTERNAL_URL', ''):
                self.base_url = os.environ.get('RENDER_EXTERNAL_URL', f'https://skribly-backend.onrender.com')
            elif host in ['127.0.0.1', 'localhost']:
                self.base_url = f'http://{host}:{port}'
            else:
                self.base_url = f'https://{host}'
        
        self.health_url = f'{self.base_url}/health'
        
        logger.info(f"🏓 Self-ping service initialized with URL: {self.health_url}")
        
        # Start the ping service
        self.start()
    
    def start(self):
        """Start the self-ping service"""
        if self.running:
            logger.warning("Self-ping service is already running")
            return
            
        self.running = True
        self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.ping_thread.start()
        logger.info(f"🏓 Self-ping service started - pinging {self.health_url} every {self.ping_interval} seconds")
    
    def stop(self):
        """Stop the self-ping service"""
        self.running = False
        if self.ping_thread:
            self.ping_thread.join(timeout=5)
        logger.info("🏓 Self-ping service stopped")
    
    def _ping_loop(self):
        """Main ping loop that runs in a separate thread"""
        # Wait before first ping to let the server fully start
        time.sleep(30)
        
        while self.running:
            try:
                self._perform_ping()
            except Exception as e:
                logger.error(f"🏓 Self-ping error: {e}")
            
            # Wait for the next ping
            time.sleep(self.ping_interval)
    
    def _perform_ping(self):
        """Perform a single ping to the health endpoint"""
        try:
            start_time = time.time()
            
            response = requests.get(
                self.health_url,
                timeout=10,
                headers={
                    'User-Agent': 'Skribly-SelfPing/1.0.0',
                    'X-Self-Ping': 'true'
                }
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.info(f"🏓 Self-ping successful ({response_time:.2f}s) - app is awake")
            else:
                logger.warning(f"🏓 Self-ping returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning("🏓 Self-ping timed out")
        except requests.exceptions.ConnectionError:
            logger.warning("🏓 Self-ping connection failed - app might be starting up")
        except Exception as e:
            logger.error(f"🏓 Self-ping failed: {e}")

# Global instance
selfping_service = SelfPingService() 