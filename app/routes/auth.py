import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app.services.memory_service import memory_service

# Configure logger
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/session', methods=['POST'])
def create_session():
    """Create a new user session"""
    logger.info("=== CREATE SESSION REQUEST ===")
    try:
        # Log request details
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request content type: {request.content_type}")
        
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        username = data.get('username', '').strip() if data else ''
        logger.info(f"Extracted username: '{username}'")
        
        if not username:
            logger.warning("Username validation failed: empty username")
            return jsonify({'error': 'Username is required'}), 400
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Generated session ID: {session_id}")
        
        # Create user session data
        user_data = {
            'session_id': session_id,
            'username': username,
            'avatar_url': data.get('avatar_url') if data else None,
            'created_at': datetime.utcnow().isoformat(),
            'current_room': None
        }
        logger.info(f"Created user data: {user_data}")
        
        # Store in memory service
        logger.info("Attempting to store in memory service...")
        memory_service.add_user_session(session_id, user_data)
        logger.info("Successfully stored in memory service")
        
        # Set session cookie
        logger.info("Setting session cookies...")
        session['user_id'] = session_id
        session['username'] = username
        logger.info(f"Session cookies set. Current session: {dict(session)}")
        
        response_data = {
            'success': True,
            'session_id': session_id,
            'user': user_data
        }
        logger.info(f"Returning response: {response_data}")
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Exception in create_session: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@auth_bp.route('/session', methods=['GET'])
def get_session():
    """Get current user session"""
    try:
        session_id = session.get('user_id')
        
        if not session_id:
            return jsonify({'error': 'No active session'}), 401
        
        user_data = memory_service.get_user_session(session_id)
        
        if not user_data:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/session', methods=['DELETE'])
def destroy_session():
    """Destroy user session"""
    try:
        session_id = session.get('user_id')
        
        if session_id:
            memory_service.remove_user_session(session_id)
        
        # Clear session
        session.clear()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/validate', methods=['POST'])
def validate_username():
    """Validate username availability"""
    logger.info("=== VALIDATE USERNAME REQUEST ===")
    try:
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        username = data.get('username', '').strip() if data else ''
        logger.info(f"Username to validate: '{username}'")
        
        if not username:
            logger.warning("Username validation failed: empty")
            return jsonify({'valid': False, 'error': 'Username is required'}), 400
        
        if len(username) < 3 or len(username) > 20:
            logger.warning(f"Username validation failed: length {len(username)}")
            return jsonify({'valid': False, 'error': 'Username must be 3-20 characters'}), 400
        
        # Check if username is already taken in active sessions
        logger.info("Checking username availability...")
        logger.info(f"Current user sessions: {list(memory_service.user_sessions.keys())}")
        
        for session_data in memory_service.user_sessions.values():
            existing_username = session_data.get('username', '')
            logger.info(f"Comparing '{username.lower()}' with '{existing_username.lower()}'")
            if existing_username.lower() == username.lower():
                logger.warning(f"Username '{username}' is already taken")
                return jsonify({'valid': False, 'error': 'Username is already taken'}), 400
        
        logger.info(f"Username '{username}' is available")
        return jsonify({'valid': True}), 200
        
    except Exception as e:
        logger.error(f"Exception in validate_username: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@auth_bp.route('/socket-test', methods=['GET'])
def socket_test():
    """Test Socket.IO availability"""
    try:
        from app import socketio
        return jsonify({
            'socketio_available': socketio is not None,
            'status': 'Socket.IO is configured and available',
            'endpoint': '/socket.io/',
            'transports': ['polling', 'websocket'],
            'session_active': session.get('user_id') is not None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500 