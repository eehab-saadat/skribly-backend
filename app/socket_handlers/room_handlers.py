from flask import session, request
from flask_socketio import emit, join_room, leave_room, disconnect
from app import socketio
from app.services.memory_service import memory_service
from datetime import datetime

# In-memory store for authenticated socket connections
authenticated_sockets = {}

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = session.get('user_id')
    logger.info(f"=== SOCKET CONNECT ===")
    logger.info(f"Session data: {dict(session)}")
    logger.info(f"User ID from session: {user_id}")
    
    if user_id:
        user_data = memory_service.get_user_session(user_id)
        logger.info(f"User data: {user_data}")
        
        if user_data:
            logger.info(f"🔗 Socket.IO Client connected: {user_data['username']} ({user_id})")
            # Send connection confirmation with user info
            emit('connection_confirmed', {
                'message': 'Successfully connected to server via Socket.IO',
                'user_id': user_id,
                'username': user_data['username'],
                'status': 'connected'
            })
        else:
            logger.warning(f"🔗 Socket.IO Client connected but no user data found for ID: {user_id}")
            emit('connection_confirmed', {
                'message': 'Connected but session invalid',
                'user_id': user_id,
                'status': 'connected_no_session'
            })
    else:
        logger.warning(f"🔗 Socket.IO Client connected but no user ID in session")
        emit('connection_confirmed', {
            'message': 'Connected but not authenticated',
            'status': 'connected_anonymous'
        })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== SOCKET DISCONNECT ===")
    logger.info(f"Socket ID: {request.sid}")
    
    # Clean up authenticated socket
    authenticated_user = authenticated_sockets.pop(request.sid, None)
    if authenticated_user:
        logger.info(f"Cleaned up authenticated socket for user: {authenticated_user['username']}")
    
    user_id = authenticated_user['user_id'] if authenticated_user else session.get('user_id')
    if user_id:
        user_data = memory_service.get_user_session(user_id)
        # NOTE: We no longer remove the user from the room on transient disconnects.
        # Users may momentarily lose connection due to network issues or page reloads.
        # They will automatically rejoin their room when the socket reconnects and emits the join_room event.
        if user_data and user_data.get('current_room'):
            room_id = user_data['current_room']
            logger.info(f"User {user_id} temporarily disconnected from room {room_id}, preserving room membership")
            # We simply emit a player_disconnected event so others can show offline status if desired.
            emit('player_disconnected', {
                'player_id': user_id,
                'username': user_data.get('username', 'Unknown')
            }, room=room_id)
        logger.info(f"Client disconnected: {user_id}")
    else:
        logger.info("Anonymous client disconnected")

@socketio.on('authenticate')
def handle_authenticate(data):
    """Handle socket authentication with session ID"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== SOCKET AUTHENTICATE ===")
    logger.info(f"Data: {data}")
    logger.info(f"Socket ID: {request.sid}")
    
    try:
        # Try to get user_id from the data or session
        user_id = data.get('user_id') or session.get('user_id')
        logger.info(f"User ID: {user_id}")
        
        if not user_id:
            logger.warning("No user ID provided")
            emit('authentication_failed', {'message': 'User ID required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        logger.info(f"User data: {user_data}")
        
        if not user_data:
            logger.warning(f"No user data found for ID: {user_id}")
            # Try to get username from session as fallback
            username = session.get('username')
            if username:
                logger.info(f"Creating new user session for {username} with ID {user_id}")
                # Recreate user session from available session data
                user_data = {
                    'session_id': user_id,
                    'username': username,
                    'avatar_url': None,
                    'created_at': datetime.utcnow().isoformat(),
                    'current_room': None
                }
                memory_service.add_user_session(user_id, user_data)
            else:
                emit('authentication_failed', {'message': 'Invalid user session - please refresh page'})
                return
        
        # Store authenticated user in socket store keyed by socket ID
        authenticated_sockets[request.sid] = {
            'user_id': user_id,
            'username': user_data['username'],
            'authenticated_at': user_data.get('created_at')
        }
        
        # Also update session as fallback
        session['user_id'] = user_id
        logger.info(f"Socket authenticated for user: {user_data['username']} (socket: {request.sid})")
        
        emit('authentication_success', {
            'message': 'Socket authenticated successfully',
            'user': user_data
        })
        
    except Exception as e:
        logger.error(f"❌ Socket authentication error: {str(e)}", exc_info=True)
        emit('authentication_failed', {'message': str(e)})

@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining a room via socket"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== SOCKET JOIN ROOM REQUEST ===")
    logger.info(f"Data: {data}")
    logger.info(f"Socket ID: {request.sid}")
    
    try:
        # Try to get user_id from authenticated sockets store first, then fallback to session
        authenticated_user = authenticated_sockets.get(request.sid)
        user_id = authenticated_user['user_id'] if authenticated_user else session.get('user_id')
        
        logger.info(f"Authenticated socket user: {authenticated_user}")
        logger.info(f"User ID: {user_id}")
        
        if not user_id:
            logger.warning("No user ID found - user not authenticated")
            emit('error', {'message': 'Authentication required. Please authenticate your socket connection first.'})
            return
        
        room_id = data.get('room_id')
        logger.info(f"Room ID: {room_id}")
        if not room_id:
            logger.warning("No room ID provided")
            emit('error', {'message': 'Room ID required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        logger.info(f"User data: {user_data}")
        if not user_data:
            logger.warning(f"No user data found for user ID {user_id}")
            emit('error', {'message': 'Invalid session. Please authenticate your socket connection first.'})
            return
        
        room_data = memory_service.get_room(room_id)
        logger.info(f"Room data: {room_data}")
        if not room_data:
            logger.warning(f"Room {room_id} not found - room may have been lost on server restart")
            emit('error', {'message': 'Room not found - please refresh page to create a new room'})
            return
        
        # Check if user is actually in the room (they should have joined via HTTP first)
        logger.info(f"Room players: {room_data['players']}")
        logger.info(f"User {user_id} in room: {user_id in room_data['players']}")
        if user_id not in room_data['players']:
            logger.warning(f"User {user_id} not in room {room_id} players list")
            emit('error', {'message': 'User not in room. Please join via HTTP first.'})
            return
        
        # Join the socket room (this is idempotent - safe to call multiple times)
        join_room(room_id)
        logger.info(f"User {user_id} joined socket room {room_id}")
        
        # Update user session
        user_data['current_room'] = room_id
        logger.info(f"Updated user session current_room to {room_id}")
        
        # Get fresh room data with all players
        fresh_room_data = memory_service.get_room_with_player_details(room_id)
        
        # Notify user they joined with detailed room info
        emit('room_joined', {
            'room': fresh_room_data,
            'user': user_data
        })
        
        # Notify other players in the room with detailed info
        emit('player_joined', {
            'player_id': user_id,
            'username': user_data['username'],
            'room': fresh_room_data
        }, room=room_id, include_self=False)
        
        logger.info(f"✅ User {user_data['username']} successfully joined room {room_id} via socket")
        
    except Exception as e:
        logger.error(f"❌ Socket join_room error: {str(e)}", exc_info=True)
        emit('error', {'message': str(e)})

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle leaving a room via socket"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        room_id = data.get('room_id')
        if not room_id:
            emit('error', {'message': 'Room ID required'})
            return
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data:
            emit('error', {'message': 'Invalid session'})
            return
        
        # Leave the socket room
        leave_room(room_id)
        
        # Remove player from room
        updated_room = memory_service.remove_player_from_room(room_id, user_id)
        
        # Update user session
        user_data['current_room'] = None
        
        # Notify user they left
        emit('room_left', {'success': True})
        
        # Notify other players in the room
        if updated_room:
            emit('player_left', {
                'player_id': user_id,
                'username': user_data['username'],
                'room': updated_room
            }, room=room_id)

            # Sync room state for all clients (public room info)
            emit('room_updated', {
                'room': memory_service.get_room_with_player_details(room_id)
            }, room=room_id)
        
        print(f"User {user_data['username']} left room {room_id}")
        
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('get_room_info')
def handle_get_room_info(data):
    """Get current room information"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
        
        room_id = data.get('room_id')
        if not room_id:
            emit('error', {'message': 'Room ID required'})
            return
        
        room_data = memory_service.get_room_with_player_details(room_id)
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        emit('room_info', {
            'room': room_data
        })
        
    except Exception as e:
        emit('error', {'message': str(e)}) 