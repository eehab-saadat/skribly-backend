from flask import Blueprint, request, jsonify, session
from app.services.memory_service import memory_service

game_bp = Blueprint('game', __name__)

@game_bp.route('/stats', methods=['GET'])
def get_game_stats():
    """Get overall game statistics"""
    try:
        return jsonify({
            'success': True,
            'stats': {
                'active_rooms': memory_service.get_room_count(),
                'active_players': memory_service.get_active_players_count(),
                'server_status': 'healthy'
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@game_bp.route('/room/<room_id>/status', methods=['GET'])
def get_room_status(room_id):
    """Get current room and game status"""
    try:
        # Check if user is authenticated
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        room_data = memory_service.get_room(room_id)
        if not room_data:
            return jsonify({'error': 'Room not found'}), 404
        
        # Check if user is in the room
        if user_id not in room_data['players']:
            return jsonify({'error': 'Not in this room'}), 403
        
        return jsonify({
            'success': True,
            'room': room_data,
            'game_state': room_data['game_state']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 