import threading
from datetime import datetime

class MemoryService:
    def __init__(self):
        self.active_rooms = {}
        self.user_sessions = {}
        self.room_timers = {}
        self.app = None
        self._lock = threading.Lock()
    
    def init_app(self, app):
        """Initialize the memory service with Flask app"""
        self.app = app
        print("🧠 Memory service initialized - fully in-memory mode")
    
    def create_room(self, room_id, host_id, settings=None, name=None):
        """Create a new room in memory"""
        with self._lock:
            if settings is None:
                settings = {
                    'rounds': 3,
                    'draw_time': 80,
                    'word_difficulty': 'medium',
                    'max_players': 8
                }
            
            room_data = {
                'id': room_id,
                'host': host_id,
                'name': name,
                'players': [host_id],
                'max_players': 8,
                'status': 'waiting',
                'settings': settings,
                'game_state': {
                    'current_round': 0,
                    'current_drawer': None,
                    'current_word': None,
                    'scores': {host_id: 0},
                    'turn_start_time': None,
                    'words_used': []
                },
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.active_rooms[room_id] = room_data
            print(f"🏠 Created room {room_id} with host {host_id}")
            return room_data
    
    def get_room(self, room_id):
        """Get room data by ID"""
        return self.active_rooms.get(room_id)
    
    def update_room(self, room_id, updates):
        """Update room data"""
        with self._lock:
            if room_id in self.active_rooms:
                self.active_rooms[room_id].update(updates)
                return self.active_rooms[room_id]
            return None
    
    def delete_room(self, room_id):
        """Delete room from memory"""
        with self._lock:
            if room_id in self.active_rooms:
                print(f"🗑️ Deleting room {room_id}")
                del self.active_rooms[room_id]
            if room_id in self.room_timers:
                timer = self.room_timers[room_id]
                if timer and timer.is_alive():
                    timer.cancel()
                del self.room_timers[room_id]
    
    def add_player_to_room(self, room_id, player_id):
        """Add a player to a room"""
        with self._lock:
            room = self.active_rooms.get(room_id)
            if room and player_id not in room['players']:
                if len(room['players']) < room['max_players']:
                    room['players'].append(player_id)
                    room['game_state']['scores'][player_id] = 0
                    print(f"👤 Added player {player_id} to room {room_id}")
                    return True
            return False
    
    def remove_player_from_room(self, room_id, player_id):
        """Remove a player from a room"""
        with self._lock:
            room = self.active_rooms.get(room_id)
            if room and player_id in room['players']:
                room['players'].remove(player_id)
                if player_id in room['game_state']['scores']:
                    del room['game_state']['scores'][player_id]
                
                print(f"👋 Removed player {player_id} from room {room_id}")
                
                # If host left, assign new host
                if room['host'] == player_id and room['players']:
                    room['host'] = room['players'][0]
                    print(f"👑 New host for room {room_id}: {room['host']}")
                
                # Delete room if empty
                if not room['players']:
                    self.delete_room(room_id)
                    return None
                
                return room
            return None
    
    def add_user_session(self, session_id, user_data):
        """Add user session data"""
        self.user_sessions[session_id] = user_data
        print(f"🔐 Created session for {user_data.get('username', 'Anonymous')}")
    
    def get_user_session(self, session_id):
        """Get user session data"""
        return self.user_sessions.get(session_id)
    
    def remove_user_session(self, session_id):
        """Remove user session data"""
        if session_id in self.user_sessions:
            user_data = self.user_sessions[session_id]
            del self.user_sessions[session_id]
            print(f"🚪 Removed session for {user_data.get('username', 'Anonymous')}")
    
    def get_all_rooms(self):
        """Get all active rooms"""
        return list(self.active_rooms.values())
    
    def get_room_count(self):
        """Get total number of active rooms"""
        return len(self.active_rooms)
    
    def get_active_players_count(self):
        """Get total number of active players"""
        total = 0
        for room in self.active_rooms.values():
            total += len(room['players'])
        return total
    
    def cleanup_inactive_rooms(self):
        """Clean up empty or old rooms"""
        with self._lock:
            rooms_to_delete = []
            for room_id, room_data in self.active_rooms.items():
                # Delete empty rooms
                if not room_data['players']:
                    rooms_to_delete.append(room_id)
                    continue
                
                # Delete very old rooms (over 24 hours)
                created_at = datetime.fromisoformat(room_data['created_at'])
                if (datetime.utcnow() - created_at).total_seconds() > 86400:  # 24 hours
                    rooms_to_delete.append(room_id)
            
            for room_id in rooms_to_delete:
                self.delete_room(room_id)
            
            if rooms_to_delete:
                print(f"🧹 Cleaned up {len(rooms_to_delete)} inactive rooms")
    
    def get_room_with_player_details(self, room_id):
        """Get room data enriched with player details (usernames, etc)"""
        room = self.get_room(room_id)
        if not room:
            return None
        
        # Create a copy of the room data with enriched player information
        enriched_room = room.copy()
        enriched_players = []
        
        for player_id in room['players']:
            player_session = self.get_user_session(player_id)
            if player_session:
                enriched_players.append({
                    'session_id': player_id,
                    'username': player_session['username']
                })
        
        enriched_room['players'] = enriched_players
        return enriched_room

# Global instance
memory_service = MemoryService() 