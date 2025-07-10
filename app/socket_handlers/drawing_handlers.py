from flask import session, request
from flask_socketio import emit
from app import socketio
from app.services.memory_service import memory_service
from app.socket_handlers.room_handlers import authenticated_sockets
import time

# Drawing-related socket handlers will be implemented in Phase 2
# This is a placeholder for Phase 1

@socketio.on('draw_start')
def handle_draw_start(data):
    """Handle start of a drawing stroke"""
    try:
        # Try to get user_id from authenticated sockets store first, then fallback to session
        authenticated_user = authenticated_sockets.get(request.sid)
        user_id = authenticated_user['user_id'] if authenticated_user else session.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            emit('error', {'message': 'Not in a room'})
            return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is allowed to draw (current drawer)
        current_drawer = room_data['game_state'].get('current_drawer')
        if current_drawer and current_drawer != user_id:
            emit('error', {'message': 'Not your turn to draw'})
            return
        
        # Validate drawing data
        x = data.get('x')
        y = data.get('y')
        color = data.get('color', '#000000')
        size = data.get('size', 5)
        tool = data.get('tool', 'brush')
        
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            emit('error', {'message': 'Invalid coordinates'})
            return
        
        if not isinstance(size, (int, float)) or size < 1 or size > 50:
            emit('error', {'message': 'Invalid brush size'})
            return
        
        if tool not in ['brush', 'eraser']:
            emit('error', {'message': 'Invalid tool'})
            return
        
        # Broadcast drawing data to all players in room except sender
        drawing_data = {
            'type': 'start',
            'x': x,
            'y': y,
            'color': color,
            'size': size,
            'tool': tool,
            'timestamp': time.time()
        }
        
        print(f"🎨 Broadcasting draw_start: {drawing_data}")
        emit('draw_data', drawing_data, room=room_id, include_self=False)
        
    except Exception as e:
        print(f"❌ Error in draw_start: {e}")
        emit('error', {'message': str(e)})

@socketio.on('draw_move')
def handle_draw_move(data):
    """Handle drawing stroke movement"""
    try:
        # Try to get user_id from authenticated sockets store first, then fallback to session
        authenticated_user = authenticated_sockets.get(request.sid)
        user_id = authenticated_user['user_id'] if authenticated_user else session.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            emit('error', {'message': 'Not in a room'})
            return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is allowed to draw
        current_drawer = room_data['game_state'].get('current_drawer')
        if current_drawer and current_drawer != user_id:
            emit('error', {'message': 'Not your turn to draw'})
            return
        
        # Validate drawing data
        x = data.get('x')
        y = data.get('y')
        
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            emit('error', {'message': 'Invalid coordinates'})
            return
        
        # Broadcast drawing data to all players in room except sender
        drawing_data = {
            'type': 'move',
            'x': x,
            'y': y,
            'timestamp': time.time()
        }
        
        emit('draw_data', drawing_data, room=room_id, include_self=False)
        
    except Exception as e:
        print(f"❌ Error in draw_move: {e}")
        emit('error', {'message': str(e)})

@socketio.on('draw_end')
def handle_draw_end(data):
    """Handle end of a drawing stroke"""
    try:
        # Try to get user_id from authenticated sockets store first, then fallback to session
        authenticated_user = authenticated_sockets.get(request.sid)
        user_id = authenticated_user['user_id'] if authenticated_user else session.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            emit('error', {'message': 'Not in a room'})
            return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is allowed to draw
        current_drawer = room_data['game_state'].get('current_drawer')
        if current_drawer and current_drawer != user_id:
            emit('error', {'message': 'Not your turn to draw'})
            return
        
        # Broadcast drawing end to all players in room except sender
        drawing_data = {
            'type': 'end',
            'timestamp': time.time()
        }
        
        emit('draw_data', drawing_data, room=room_id, include_self=False)
        
    except Exception as e:
        print(f"❌ Error in draw_end: {e}")
        emit('error', {'message': str(e)})

@socketio.on('clear_canvas')
def handle_clear_canvas(data):
    """Handle canvas clearing"""
    try:
        # Try to get user_id from authenticated sockets store first, then fallback to session
        authenticated_user = authenticated_sockets.get(request.sid)
        user_id = authenticated_user['user_id'] if authenticated_user else session.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            emit('error', {'message': 'Not in a room'})
            return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is allowed to clear (current drawer or host)
        current_drawer = room_data['game_state'].get('current_drawer')
        is_host = room_data['host'] == user_id
        
        if not (current_drawer == user_id or is_host):
            emit('error', {'message': 'Not authorized to clear canvas'})
            return
        
        print(f"🎨 Broadcasting canvas_cleared")
        # Broadcast canvas clear to all players in room
        emit('canvas_cleared', {
            'timestamp': time.time(),
            'cleared_by': user_data['username']
        }, room=room_id)
        
    except Exception as e:
        print(f"❌ Error in clear_canvas: {e}")
        emit('error', {'message': str(e)})

@socketio.on('change_tool')
def handle_change_tool(data):
    """Handle drawing tool change"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            emit('error', {'message': 'Not in a room'})
            return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is current drawer
        current_drawer = room_data['game_state'].get('current_drawer')
        if current_drawer != user_id:
            emit('error', {'message': 'Not your turn to draw'})
            return
        
        tool = data.get('tool')
        color = data.get('color')
        size = data.get('size')
        
        # Validate tool data
        if tool and tool not in ['brush', 'eraser']:
            emit('error', {'message': 'Invalid tool'})
            return
        
        if size and (not isinstance(size, (int, float)) or size < 1 or size > 50):
            emit('error', {'message': 'Invalid size'})
            return
        
        # Broadcast tool change to other players for UI updates
        tool_data = {
            'tool': tool,
            'color': color,
            'size': size,
            'user': user_data['username']
        }
        
        emit('tool_changed', tool_data, room=room_id, include_self=False)
        
    except Exception as e:
        emit('error', {'message': str(e)})
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            emit('error', {'message': 'Not in a room'})
            return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is current drawer
        current_drawer = room_data['game_state'].get('current_drawer')
        if current_drawer != user_id:
            emit('error', {'message': 'Not your turn to draw'})
            return
        
        tool = data.get('tool')
        color = data.get('color')
        size = data.get('size')
        
        # Validate tool data
        if tool and tool not in ['brush', 'eraser']:
            emit('error', {'message': 'Invalid tool'})
            return
        
        if size and (not isinstance(size, (int, float)) or size < 1 or size > 50):
            emit('error', {'message': 'Invalid size'})
            return
        
        # Broadcast tool change to other players for UI updates
        tool_data = {
            'tool': tool,
            'color': color,
            'size': size,
            'user': user_data['username']
        }
        
        emit('tool_changed', tool_data, room=room_id, include_self=False)
        
    except Exception as e:
        emit('error', {'message': str(e)}) 