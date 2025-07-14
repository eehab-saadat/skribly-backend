import random
import string
from flask import Blueprint, request, jsonify, session
from app.services.memory_service import memory_service
from app import socketio

rooms_bp = Blueprint('rooms', __name__)

def generate_room_id():
    """Generate a random 6-character room ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@rooms_bp.route('/create', methods=['POST'])
def create_room():
    """Create a new game room"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=== CREATE ROOM REQUEST ===")
    
    try:
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request origin: {request.headers.get('Origin')}")
        logger.info(f"Session data: {dict(session)}")
        
        # Check if user is authenticated
        user_id = session.get('user_id')
        logger.info(f"User ID from session: {user_id}")
        
        if not user_id:
            logger.warning("No user ID in session - user not authenticated")
            return jsonify({'error': 'Authentication required. Please create a username first.'}), 401
        
        user_data = memory_service.get_user_session(user_id)
        logger.info(f"User data from memory: {user_data}")
        
        if not user_data:
            logger.warning(f"No user data found for user ID {user_id} - session expired or invalid")
            return jsonify({'error': 'Your session has expired. Please create a username again.'}), 401
        
        data = request.get_json() or {}
        
        # Generate unique room ID
        room_id = generate_room_id()
        while memory_service.get_room(room_id):  # Ensure uniqueness
            room_id = generate_room_id()
        
        # Parse room settings
        settings = {
            'rounds': data.get('rounds', 3),
            'draw_time': data.get('draw_time', 80),
            'word_difficulty': data.get('word_difficulty', 'medium'),
            'max_players': data.get('max_players', 8)
        }
        
        # Validate settings
        if not (1 <= settings['rounds'] <= 10):
            return jsonify({'error': 'Rounds must be between 1 and 10'}), 400
        
        if not (30 <= settings['draw_time'] <= 300):
            return jsonify({'error': 'Draw time must be between 30 and 300 seconds'}), 400
        
        if settings['word_difficulty'] not in ['easy', 'medium', 'hard']:
            return jsonify({'error': 'Invalid word difficulty'}), 400
        
        if not (2 <= settings['max_players'] <= 12):
            return jsonify({'error': 'Max players must be between 2 and 12'}), 400
        
        # Create room
        room_name = data.get('name', f"{user_data['username']}'s Room")
        room_data = memory_service.create_room(
            room_id=room_id,
            host_id=user_id,
            settings=settings,
            name=room_name
        )
        
        # Update user session
        user_data['current_room'] = room_id
        
        return jsonify({
            'success': True,
            'room': room_data
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/<room_id>', methods=['GET'])
def get_room(room_id):
    """Get room information"""
    try:
        room_data = memory_service.get_room_with_player_details(room_id)
        
        if not room_data:
            return jsonify({'error': 'Room not found'}), 404
        
        return jsonify({
            'success': True,
            'room': room_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rooms_bp.route('/<room_id>/join', methods=['POST'])
def join_room(room_id):
    """Join an existing room"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== JOIN ROOM REQUEST: {room_id} ===")
    
    try:
        # Check if user is authenticated
        user_id = session.get('user_id')
        logger.info(f"User ID from session: {user_id}")
        logger.info(f"Full session data: {dict(session)}")
        
        if not user_id:
            logger.warning("No user ID in session - user not authenticated")
            return jsonify({
                'error': 'Authentication required. Please create a username first.',
                'code': 'NOT_AUTHENTICATED'
            }), 401
        
        user_data = memory_service.get_user_session(user_id)
        logger.info(f"User data from memory: {user_data}")
        
        if not user_data:
            logger.warning(f"No user data found for user ID {user_id} - session expired or invalid")
            return jsonify({
                'error': 'Your session has expired. Please create a username again.',
                'code': 'SESSION_EXPIRED'
            }), 401
        
        # Check if room exists
        room_data = memory_service.get_room(room_id)
        logger.info(f"Room data: {room_data}")
        
        if not room_data:
            logger.warning(f"Room {room_id} not found")
            return jsonify({
                'error': f'Room {room_id} not found. It may have been deleted or expired.',
                'code': 'ROOM_NOT_FOUND'
            }), 404
        
        # Check if room is joinable
        logger.info(f"Room status: {room_data['status']}")
        if room_data['status'] != 'waiting':
            logger.warning(f"Room status is {room_data['status']}, not waiting")
            return jsonify({
                'error': 'This game is already in progress and cannot be joined.',
                'code': 'GAME_IN_PROGRESS'
            }), 400
        
        # Check if user is already in the room
        logger.info(f"Current players: {room_data['players']}")
        logger.info(f"User {user_id} already in room: {user_id in room_data['players']}")
        
        if user_id in room_data['players']:
            logger.info(f"User {user_id} already in room {room_id}, returning current room data")
            # User is already in room (e.g., they're the host), just return the room data
            return jsonify({
                'success': True,
                'room': room_data,
                'message': 'You are already in this room'
            }), 200
        
        # Check if room is full
        if len(room_data['players']) >= room_data['max_players']:
            logger.warning(f"Room {room_id} is full ({len(room_data['players'])}/{room_data['max_players']})")
            return jsonify({
                'error': f'Room is full ({len(room_data["players"])}/{room_data["max_players"]} players)',
                'code': 'ROOM_FULL'
            }), 400
        
        # Try to add player
        logger.info(f"Attempting to add player {user_id} ({user_data['username']}) to room {room_id}")
        if memory_service.add_player_to_room(room_id, user_id):
            # Update user session
            user_data['current_room'] = room_id
            logger.info(f"Successfully added player {user_data['username']} to room {room_id}")
            
            # Get updated room data with player details
            updated_room = memory_service.get_room_with_player_details(room_id)
            logger.info(f"Updated room has {len(updated_room['players'])} players")
            
            # Notify other players in the room via socket
            socketio.emit('player_joined', {
                'player_id': user_id,
                'username': user_data['username'],
                'room': updated_room
            }, room=room_id)
            
            # Also emit room_updated event for broader state sync
            socketio.emit('room_updated', {
                'room': updated_room,
                'event': 'player_joined',
                'player_id': user_id
            }, room=room_id)
            
            logger.info(f"Emitted socket events for player {user_data['username']} joining room {room_id}")
            
            return jsonify({
                'success': True,
                'room': updated_room,
                'message': f'Successfully joined {updated_room.get("name", "room")}'
            }), 200
        else:
            logger.error(f"Failed to add player to room - unexpected error")
            return jsonify({
                'error': 'Failed to join room due to an unexpected error',
                'code': 'JOIN_FAILED'
            }), 500
        
    except Exception as e:
        logger.error(f"Exception in join_room: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An unexpected server error occurred',
            'code': 'INTERNAL_ERROR'
        }), 500

@rooms_bp.route('/list', methods=['GET'])
def list_rooms():
    """List all active rooms"""
    try:
        all_rooms = memory_service.get_all_rooms()
        
        # Filter out sensitive information and only show waiting rooms
        public_rooms = []
        for room in all_rooms:
            if room['status'] == 'waiting':
                host_session = memory_service.get_user_session(room['host'])
                public_rooms.append({
                    'id': room['id'],
                    'name': room.get('name', 'Unnamed Room'),
                    'players': len(room['players']),
                    'max_players': room['max_players'],
                    'status': room['status'],
                    'host': host_session['username'] if host_session else 'Unknown'
                })
        
        return jsonify({
            'success': True,
            'rooms': public_rooms,
            'total_rooms': memory_service.get_room_count(),
            'total_players': memory_service.get_active_players_count()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 