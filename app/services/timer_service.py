import threading
import time
from typing import Dict, Callable, Optional
from flask_socketio import emit
from app.services.memory_service import memory_service
from app.socket_handlers import room_handlers

class GameTimer:
    def __init__(self, room_id: str, duration: int, callback: Callable, timer_type: str = 'generic'):
        self.room_id = room_id
        self.duration = duration
        self.callback = callback
        self.timer_type = timer_type
        self.start_time = None
        self.is_running = False
        self.timer_thread = None
        self.stop_event = threading.Event()
    
    def start(self):
        """Start the timer"""
        if self.is_running:
            return
        
        self.start_time = time.time()
        self.is_running = True
        self.stop_event.clear()
        
        # Start the timer thread
        self.timer_thread = threading.Thread(target=self._run_timer)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        
        print(f"⏰ Started {self.timer_type} timer for room {self.room_id} ({self.duration}s)")
    
    def stop(self):
        """Stop the timer"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1.0)
        
        print(f"⏹️ Stopped {self.timer_type} timer for room {self.room_id}")
    
    def get_remaining_time(self) -> int:
        """Get remaining time in seconds"""
        if not self.is_running or not self.start_time:
            return 0
        
        elapsed = time.time() - self.start_time
        remaining = max(0, self.duration - int(elapsed))
        return remaining
    
    def _run_timer(self):
        """Run the timer with regular updates"""
        try:
            # Get timer service instance to access socketio
            from app.services.timer_service import timer_service
            
            for remaining in range(self.duration, 0, -1):
                if self.stop_event.wait(1):  # Wait 1 second or until stop event
                    return
                
                # Emit timer update using stored socketio instance
                if timer_service.socketio:
                    timer_service.socketio.emit('timer_update', {
                        'time_remaining': remaining,
                        'phase': self.timer_type,
                        'room_id': self.room_id
                    }, room=self.room_id)
                
                # Check if room still exists
                room_data = memory_service.get_room(self.room_id)
                if not room_data:
                    print(f"⚠️ Room {self.room_id} not found, stopping timer")
                    return
            
            # Timer finished, execute callback
            if self.is_running:
                self.is_running = False
                print(f"⏰ Timer {self.timer_type} finished for room {self.room_id}")
                self.callback()
                
        except Exception as e:
            print(f"❌ Error in timer {self.timer_type} for room {self.room_id}: {e}")
            self.is_running = False

class TimerService:
    def __init__(self):
        self.active_timers: Dict[str, GameTimer] = {}
        self.app = None
        self.socketio = None
    
    def init_app(self, app):
        """Initialize the timer service with Flask app"""
        self.app = app
        # Import socketio after app is created to avoid circular imports
        from app import socketio
        self.socketio = socketio
        print("⏰ Timer service initialized")
    
    def start_word_selection_timer(self, room_id: str, duration: int = 10) -> bool:
        """Start word selection timer"""
        def timeout_callback():
            self._handle_word_selection_timeout(room_id)
        
        return self._start_timer(room_id, duration, timeout_callback, 'word_selection')
    
    def start_drawing_timer(self, room_id: str, duration: int = 80, custom_callback: Callable = None) -> bool:
        """Start drawing timer"""
        def timeout_callback():
            if custom_callback:
                custom_callback()
            else:
                self._handle_drawing_timeout(room_id)
        
        return self._start_timer(room_id, duration, timeout_callback, 'drawing')
    
    def start_results_timer(self, room_id: str, duration: int = 5) -> bool:
        """Start results display timer"""
        def timeout_callback():
            self._handle_results_timeout(room_id)
        
        return self._start_timer(room_id, duration, timeout_callback, 'results')
    
    def start_intermission_timer(self, room_id: str, duration: int = 3) -> bool:
        """Start intermission timer between rounds"""
        def timeout_callback():
            self._handle_intermission_timeout(room_id)
        
        return self._start_timer(room_id, duration, timeout_callback, 'intermission')
    
    def _start_timer(self, room_id: str, duration: int, callback: Callable, timer_type: str) -> bool:
        """Internal method to start any timer"""
        try:
            # Stop any existing timer for this room
            self.stop_timer(room_id)
            
            # Create and start new timer
            timer = GameTimer(room_id, duration, callback, timer_type)
            self.active_timers[room_id] = timer
            timer.start()
            
            return True
        except Exception as e:
            print(f"❌ Error starting {timer_type} timer for room {room_id}: {e}")
            return False
    
    def stop_timer(self, room_id: str) -> bool:
        """Stop timer for a room"""
        try:
            if room_id in self.active_timers:
                timer = self.active_timers[room_id]
                timer.stop()
                del self.active_timers[room_id]
                return True
            return False
        except Exception as e:
            print(f"❌ Error stopping timer for room {room_id}: {e}")
            return False
    
    def get_remaining_time(self, room_id: str) -> int:
        """Get remaining time for a room's timer"""
        if room_id in self.active_timers:
            return self.active_timers[room_id].get_remaining_time()
        return 0
    
    def is_timer_running(self, room_id: str) -> bool:
        """Check if timer is running for a room"""
        if room_id in self.active_timers:
            return self.active_timers[room_id].is_running
        return False
    
    def cleanup_room_timer(self, room_id: str):
        """Clean up timer when room is deleted"""
        self.stop_timer(room_id)
    
    def _handle_word_selection_timeout(self, room_id: str):
        """Handle word selection timeout - auto-select random word"""
        try:
            from app.services.word_service import word_service
            from app import socketio
            
            room_data = memory_service.get_room(room_id)
            if not room_data:
                return
            
            # Auto-select random word
            difficulty = room_data['settings'].get('word_difficulty', 'medium')
            word = word_service.get_random_word(difficulty)
            
            room_data['game_state']['current_word'] = word
            room_data['game_state']['words_used'].append(word)
            room_data['game_state']['turn_start_time'] = time.time()
            room_data['game_state']['players_guessed'] = []
            memory_service.update_room(room_id, room_data)
            
            print(f"⏰ Auto-selected word '{word}' for room {room_id}")
            
            # Get drawer and draw time from room data
            drawer_id = room_data['game_state']['current_drawer']
            draw_time = room_data['settings']['draw_time']
            
            # Start drawing phase manually to avoid context issues
            print(f"🔥 DEBUG: About to start drawing phase for room {room_id}")
            try:
                # Notify all players that word has been auto-selected
                if self.socketio:
                    # Find drawer's session_id for proper event targeting
                    from app.socket_handlers.room_handlers import authenticated_sockets
                    drawer_session_id = None
                    for session_id, user_info in authenticated_sockets.items():
                        if user_info['user_id'] == drawer_id:
                            drawer_session_id = session_id
                            break
                    
                    if drawer_session_id:
                        # Notify drawer with full word
                        self.socketio.emit('word_selected', {
                            'word': word,
                            'time_limit': draw_time,
                            'drawer_id': drawer_id,
                            'phase': 'drawing',
                            'auto_selected': True
                        }, room=drawer_session_id)
                    
                    # Notify other players without the actual word
                    word_hint = '_' * len(word.replace(' ', ''))
                    for session_id, user_info in authenticated_sockets.items():
                        if user_info['user_id'] in room_data['players'] and user_info['user_id'] != drawer_id:
                            self.socketio.emit('word_selected', {
                                'word_hint': word_hint,
                                'word_length': len(word),
                                'time_limit': draw_time,
                                'drawer_id': drawer_id,
                                'phase': 'drawing',
                                'auto_selected': True
                            }, room=session_id)
                    
                    print(f"🔥 DEBUG: Word auto-selection events emitted successfully")
                else:
                    print(f"🔥 DEBUG: No socketio instance available")
                
                # Start drawing timer using the manual approach
                def on_drawing_timeout():
                    try:
                        if self.socketio:
                            self.socketio.emit('turn_timeout', {
                                'room_id': room_id,
                                'message': 'Time is up!'
                            }, room=room_id)
                    except Exception as e:
                        print(f"❌ Error in drawing timeout: {e}")
                
                timer_service.start_drawing_timer(room_id, draw_time, on_drawing_timeout)
                
                print(f"🔥 DEBUG: Drawing phase started successfully for room {room_id}")
                
            except Exception as e:
                print(f"🔥 DEBUG: Error starting drawing phase: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"❌ Error handling word selection timeout for room {room_id}: {e}")
    
    def _handle_drawing_timeout(self, room_id: str):
        """Handle drawing timeout - end current turn"""
        try:
            from app import socketio
            
            room_data = memory_service.get_room(room_id)
            if not room_data:
                return
            
            print(f"⏰ Drawing time ended for room {room_id}")
            
            # End turn without context dependencies
            try:
                if self.socketio:
                    self.socketio.emit('turn_timeout', {
                        'room_id': room_id,
                        'message': 'Time is up!'
                    }, room=room_id)
                    print(f"⏰ Turn timeout event emitted for room {room_id}")
                else:
                    print(f"❌ No socketio instance for turn timeout in room {room_id}")
            except Exception as e:
                print(f"❌ Error ending turn: {e}")
            
        except Exception as e:
            print(f"❌ Error handling drawing timeout for room {room_id}: {e}")
    
    def _handle_results_timeout(self, room_id: str):
        """Handle results timeout - start next turn or end game"""
        try:
            from app import socketio
            
            room_data = memory_service.get_room(room_id)
            if not room_data:
                return
            
            print(f"⏰ Results time ended for room {room_id}")
            
            # Start next turn/round with proper Flask context
            try:
                if self.app:
                    with self.app.app_context():
                        from app.socket_handlers.game_handlers import _start_next_turn_or_round
                        _start_next_turn_or_round(room_id)
                else:
                    from app.socket_handlers.game_handlers import _start_next_turn_or_round
                    _start_next_turn_or_round(room_id)
            except Exception as e:
                print(f"❌ Error starting next turn/round in context: {e}")
            
        except Exception as e:
            print(f"❌ Error handling results timeout for room {room_id}: {e}")
    
    def _handle_intermission_timeout(self, room_id: str):
        """Handle intermission timeout - start new round"""
        try:
            from app import socketio
            
            room_data = memory_service.get_room(room_id)
            if not room_data:
                return
            
            print(f"⏰ Intermission ended for room {room_id}")
            
            # Start new round with proper Flask context
            try:
                if self.app:
                    with self.app.app_context():
                        from app.socket_handlers.game_handlers import _start_new_round
                        _start_new_round(room_id)
                else:
                    from app.socket_handlers.game_handlers import _start_new_round
                    _start_new_round(room_id)
            except Exception as e:
                print(f"❌ Error starting new round in context: {e}")
            
        except Exception as e:
            print(f"❌ Error handling intermission timeout for room {room_id}: {e}")
    
    def get_timer_stats(self) -> Dict[str, any]:
        """Get statistics about active timers"""
        stats = {
            'active_timers': len(self.active_timers),
            'timers': {}
        }
        
        for room_id, timer in self.active_timers.items():
            stats['timers'][room_id] = {
                'type': timer.timer_type,
                'remaining': timer.get_remaining_time(),
                'duration': timer.duration,
                'is_running': timer.is_running
            }
        
        return stats

# Global instance
timer_service = TimerService() 