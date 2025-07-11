from flask import session, request
from flask_socketio import emit
from app import socketio
from app.services.memory_service import memory_service
from app.services.word_service import word_service
from app.services.timer_service import timer_service
from app.socket_handlers import room_handlers
from app.socket_handlers.room_handlers import authenticated_sockets
import random
import time
import threading

@socketio.on('start_game')
def handle_start_game(data):
    """Handle game start request"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== START GAME REQUEST ===")
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
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            emit('error', {'message': 'Not in a room'})
            return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is host
        if room_data['host'] != user_id:
            emit('error', {'message': 'Only host can start the game'})
            return
        
        # Check if enough players
        if len(room_data['players']) < 2:
            emit('error', {'message': 'Need at least 2 players to start'})
            return
        
        # Check if game is already running
        if room_data['status'] == 'playing':
            emit('error', {'message': 'Game already in progress'})
            return
        
        # Initialize game state
        room_data['status'] = 'playing'
        room_data['game_state'] = {
            'current_round': 1,
            'current_drawer': None,
            'current_word': None,
            'scores': {player_id: 0 for player_id in room_data['players']},
            'turn_start_time': None,
            'words_used': [],
            'players_guessed': [],
            'drawer_order': room_data['players'].copy(),
            'current_drawer_index': 0
        }
        
        # Shuffle drawer order for fairness
        random.shuffle(room_data['game_state']['drawer_order'])
        
        # Save updated room data with playing status
        memory_service.update_room(room_id, room_data)
        
        # Emit game_started event to notify frontend
        socketio.emit('game_started', {
            'room_id': room_id,
            'room': memory_service.get_room_with_player_details(room_id),
            'current_round': 1,
            'total_rounds': room_data['settings']['rounds']
        }, room=room_id)
        
        # Emit room updated to sync status change
        socketio.emit('room_updated', {
            'room': memory_service.get_room_with_player_details(room_id),
            'event': 'game_started'
        }, room=room_id)
        
        # Start the first round
        _start_new_round(room_id)
        
    except Exception as e:
        print(f"❌ Error starting game: {e}")
        emit('error', {'message': str(e)})

@socketio.on('select_word')
def handle_select_word(data):
    """Handle word selection by drawer"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== SELECT WORD REQUEST ===")
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
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            # Attempt to restore from payload
            fallback_room = data.get('room_id')
            if fallback_room:
                room_fallback = memory_service.get_room(fallback_room)
                if room_fallback and user_id in room_fallback['players']:
                    user_data['current_room'] = fallback_room
                    print(f"ℹ️ Restored current_room for user {user_id} via select_word fallback")
                else:
                    emit('error', {'message': 'Not in a room'})
                    return
            else:
                emit('error', {'message': 'Not in a room'})
                return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is current drawer
        if room_data['game_state']['current_drawer'] != user_id:
            emit('error', {'message': 'Not your turn to select word'})
            return
        
        word = data.get('word')
        if not word:
            emit('error', {'message': 'Word is required'})
            return
        
        # Validate word
        difficulty = room_data['settings'].get('word_difficulty', 'medium')
        if not word_service.validate_word(word, difficulty):
            emit('error', {'message': 'Invalid word selected'})
            return
        
        # Update game state
        room_data['game_state']['current_word'] = word
        room_data['game_state']['words_used'].append(word)
        room_data['game_state']['turn_start_time'] = time.time()
        room_data['game_state']['players_guessed'] = []
        
        memory_service.update_room(room_id, room_data)
        
        print(f"🎯 Word '{word}' selected for room {room_id}")
        
        # Stop word selection timer
        timer_service.stop_timer(room_id)
        
        # Find drawer's session_id for proper event targeting
        drawer_session_id = None
        for session_id, user_info in room_handlers.authenticated_sockets.items():
            if user_info['user_id'] == user_id:
                drawer_session_id = session_id
                break
        
        if drawer_session_id:
            print(f"🎯 Sending word_selected event to drawer {user_id} via session {drawer_session_id} with word '{word}'")
            # Notify drawer with the full word
            socketio.emit('word_selected', {
                'word': word,
                'time_limit': room_data['settings']['draw_time'],
                'drawer_id': user_id,
                'phase': 'drawing'
            }, room=drawer_session_id)  # Send to drawer's session
        else:
            print(f"❌ Could not find session for drawer {user_id}")
        
        print(f"🎯 Sending word_selected event to non-drawers with hint")
        # Notify other players without the actual word
        word_hint = '_' * len(word.replace(' ', ''))
        for session_id, user_info in room_handlers.authenticated_sockets.items():
            if user_info['user_id'] in room_data['players'] and user_info['user_id'] != user_id:
                print(f"🎯 Sending to non-drawer {user_info['user_id']} via session {session_id}")
                socketio.emit('word_selected', {
                    'word_hint': word_hint,
                    'word_length': len(word),
                    'time_limit': room_data['settings']['draw_time'],
                    'drawer_id': user_id,
                    'phase': 'drawing'
                }, room=session_id)
        
        # Start drawing phase
        _start_drawing_phase(room_id)
        
    except Exception as e:
        print(f"❌ Error selecting word: {e}")
        emit('error', {'message': str(e)})

@socketio.on('submit_guess')
def handle_guess(data):
    """Handle player guess"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== SUBMIT GUESS REQUEST ===")
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
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            # attempt fallback from payload
            fallback_room = data.get('room_id')
            if fallback_room:
                room_data_fallback = memory_service.get_room(fallback_room)
                if room_data_fallback and user_id in room_data_fallback['players']:
                    user_data['current_room'] = fallback_room
                else:
                    emit('error', {'message': 'Not in a room'})
                    return
            else:
                emit('error', {'message': 'Not in a room'})
                return
        
        room_id = user_data['current_room']
        room_data = memory_service.get_room(room_id)
        
        if not room_data:
            emit('error', {'message': 'Room not found'})
            return
        
        # Check if user is not the current drawer
        if room_data['game_state']['current_drawer'] == user_id:
            emit('error', {'message': 'You cannot guess your own drawing'})
            return
        
        # Check if user already guessed correctly
        if user_id in room_data['game_state'].get('players_guessed', []):
            emit('error', {'message': 'You already guessed correctly'})
            return
        
        guess = data.get('guess', '').strip().lower()
        current_word = room_data['game_state'].get('current_word', '').lower()
        
        if not guess:
            emit('error', {'message': 'Guess cannot be empty'})
            return
        
        # Calculate time-based score using improved Skribbl.io-style formula
        turn_start = room_data['game_state'].get('turn_start_time', time.time())
        time_elapsed = time.time() - turn_start
        draw_time = room_data['settings']['draw_time']
        time_remaining = max(0, draw_time - time_elapsed)
        
        # Check if guess is correct
        if guess == current_word:
            # New scoring scheme
            # Base score for correct guess
            base_score = 100

            # Bonus: 5 points for each whole second remaining
            speed_bonus = int(time_remaining * 5)

            final_score = base_score + speed_bonus
            
            # Award points to guesser
            if user_id not in room_data['game_state']['scores']:
                room_data['game_state']['scores'][user_id] = 0
            room_data['game_state']['scores'][user_id] += final_score
            
            # Track who guessed correctly
            room_data['game_state']['players_guessed'].append(user_id)
            
            memory_service.update_room(room_id, room_data)
            
            print(f"✅ Correct guess '{guess}' by {user_data['username']} in room {room_id} - Score: {final_score} (base: {base_score}, speed: {speed_bonus})")
            
            # Notify all players of correct guess
            emit('correct_guess', {
                'player': user_data['username'],
                'player_id': user_id,
                'word': current_word,
                'score': final_score,
                'speed_bonus': speed_bonus,
                'scores': room_data['game_state']['scores'],
                'time_elapsed': round(time_elapsed, 1),
                'time_remaining': round(time_remaining, 1)
            }, room=room_id)
            
            # Notify the specific user they guessed correctly (disables their chat)
            emit('guess_correct', {
                'message': f'Correct! You guessed "{current_word}"! +{final_score} points',
                'score': final_score,
                'word': current_word
            }, room=user_id)  # Only to the user who guessed correctly
            
            # Check if all players guessed correctly (except drawer)
            eligible_players = [p for p in room_data['players'] if p != user_id]
            if len(room_data['game_state']['players_guessed']) >= len(eligible_players):
                # All players guessed, end turn early
                timer_service.stop_timer(room_id)
                _end_turn(room_id, all_guessed=True)
            
        else:
            # Show guess in chat
            emit('chat_message', {
                'user': user_data['username'],
                'user_id': user_id,
                'message': guess,
                'type': 'guess',
                'timestamp': time.time()
            }, room=room_id)
        
    except Exception as e:
        print(f"❌ Error handling guess: {e}")
        emit('error', {'message': str(e)})

@socketio.on('turn_timeout')
def handle_turn_timeout(data):
    """Handle turn timeout event from timer"""
    try:
        room_id = data.get('room_id')
        if room_id:
            print(f"⏰ Processing turn timeout for room {room_id}")
            _end_turn(room_id, timeout=True)
    except Exception as e:
        print(f"❌ Error processing turn timeout: {e}")

@socketio.on('send_chat_message')
def handle_chat_message(data):
    """Handle regular chat messages (not guesses)"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== SEND CHAT MESSAGE REQUEST ===")
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
        
        user_data = memory_service.get_user_session(user_id)
        if not user_data or not user_data.get('current_room'):
            # Fallback: try to use room_id provided by client
            fallback_room = data.get('room_id')
            if fallback_room:
                room_data_fallback = memory_service.get_room(fallback_room)
                if room_data_fallback and user_id in room_data_fallback['players']:
                    user_data['current_room'] = fallback_room  # restore
                    print(f"ℹ️ Restored current_room for user {user_id} to {fallback_room} via fallback room_id")
                else:
                    emit('error', {'message': 'Not in a room'})
                    return
            else:
                emit('error', {'message': 'Not in a room'})
                return
        
        room_id = user_data['current_room']
        message = data.get('message', '').strip()
        
        if not message:
            emit('error', {'message': 'Message cannot be empty'})
            return
        
        if len(message) > 200:
            emit('error', {'message': 'Message too long'})
            return
        
        # Broadcast chat message
        emit('chat_message', {
            'user': user_data['username'],
            'user_id': user_id,
            'message': message,
            'type': 'chat',
            'timestamp': time.time()
        }, room=room_id)
        
    except Exception as e:
        print(f"❌ Error handling chat message: {e}")
        emit('error', {'message': str(e)})

# Internal helper functions

def _start_new_round(room_id):
    """Start a new round"""
    try:
        room_data = memory_service.get_room(room_id)
        if not room_data:
            return
        
        current_round = room_data['game_state']['current_round']
        max_rounds = room_data['settings']['rounds']
        
        print(f"🎮 Starting round {current_round} in room {room_id}")
        
        # Check if game should end
        if current_round > max_rounds:
            _end_game(room_id)
            return
        
        # Select next drawer
        drawer_order = room_data['game_state']['drawer_order']
        drawer_index = room_data['game_state']['current_drawer_index']
        
        # Ensure we have a valid drawer
        if drawer_index >= len(drawer_order):
            print(f"❌ Invalid drawer index {drawer_index} for drawer order length {len(drawer_order)}")
            _end_game(room_id)
            return
        
        current_drawer = drawer_order[drawer_index]
        room_data['game_state']['current_drawer'] = current_drawer
        
        # Reset turn-specific state for new turn
        room_data['game_state']['current_word'] = None
        room_data['game_state']['players_guessed'] = []
        room_data['game_state']['turn_start_time'] = None
        
        # Don't increment drawer_index here - that should happen in _start_next_turn_or_round
        # when the turn actually ends
        
        memory_service.update_room(room_id, room_data)
        
        # Get socketio instance for context-free emission
        from app import socketio
        
        # Notify all players
        socketio.emit('round_started', {
            'round': current_round,
            'drawer': current_drawer,
            'drawer_name': memory_service.get_user_session(current_drawer)['username'],
            'total_rounds': max_rounds
        }, room=room_id)
        
        # Start word selection phase
        _start_word_selection_phase(room_id)
        
    except Exception as e:
        print(f"❌ Error starting new round: {e}")

def _start_word_selection_phase(room_id):
    """Start word selection phase"""
    try:
        room_data = memory_service.get_room(room_id)
        if not room_data:
            return
        
        drawer_id = room_data['game_state']['current_drawer']
        difficulty = room_data['settings'].get('word_difficulty', 'medium')
        
        # Get word options
        words = word_service.get_random_words(difficulty, 3)
        
        print(f"📝 Starting word selection for drawer {drawer_id} in room {room_id}")
        
        # Get socketio instance for context-free emission
        from app import socketio
        
        # Emit word selection started to ALL players (frontend expects this event)
        socketio.emit('word_selection_started', {
            'drawer_id': drawer_id,
            'drawer_name': memory_service.get_user_session(drawer_id)['username'],
            'words': words,  # Only drawer will see these in frontend
            'time_limit': 10,
            'phase': 'word_selection'
        }, room=room_id)
        
        # Start word selection timer
        timer_service.start_word_selection_timer(room_id, 10)
        
    except Exception as e:
        print(f"❌ Error starting word selection phase: {e}")

def _start_drawing_phase(room_id):
    """Start drawing phase"""
    try:
        room_data = memory_service.get_room(room_id)
        if not room_data:
            return
        
        drawer_id = room_data['game_state']['current_drawer']
        current_word = room_data['game_state']['current_word']
        draw_time = room_data['settings']['draw_time']
        
        print(f"🎨 Starting drawing phase for room {room_id}")
        
        # Get socketio instance for context-free emission
        from app import socketio
        
        # Set turn start time for progressive hints
        room_data['game_state']['turn_start_time'] = time.time()
        memory_service.update_room(room_id, room_data)
        
        # Send drawing_started to all players in room (frontend will handle filtering)
        word_hint = '_' * len(current_word.replace(' ', ''))
        
        print(f"🎨 Broadcasting drawing_started for room {room_id}")
        
        socketio.emit('drawing_started', {
            'drawer_id': drawer_id,
            'drawer_name': memory_service.get_user_session(drawer_id)['username'],
            'word_hint': word_hint,
            'word_length': len(current_word),
            'time_limit': draw_time,
            'phase': 'drawing'
        }, room=room_id)
        
        # Start drawing timer
        def on_drawing_timeout():
            _end_turn(room_id, timeout=True)
        
        # Start progressive hint timer (send hints every 10 seconds)
        def send_progressive_hints():
            try:
                room_data = memory_service.get_room(room_id)
                if not room_data or room_data['game_state'].get('current_word') != current_word:
                    return  # Game state changed, stop sending hints
                
                turn_start = room_data['game_state'].get('turn_start_time', time.time())
                elapsed_time = time.time() - turn_start
                
                if elapsed_time < draw_time:  # Still in drawing phase
                    # Generate progressive hint
                    progressive_hint = word_service.get_progressive_hint(current_word, elapsed_time)
                    
                    print(f"🔍 Sending progressive hint: '{progressive_hint}' after {elapsed_time:.1f}s")
                    
                    # Send hint update to the room (frontend will filter for non-drawers)
                    socketio.emit('hint_update', {
                        'word_hint': progressive_hint,
                        'word_length': len(current_word),
                        'elapsed_time': elapsed_time,
                        'drawer_id': drawer_id  # Frontend uses this to filter
                    }, room=room_id)
                    
                    # Schedule next hint update if game is still ongoing
                    if elapsed_time + 10 < draw_time:
                        threading.Timer(10.0, send_progressive_hints).start()
            except Exception as e:
                print(f"❌ Error sending progressive hints: {e}")
        
        # Start the progressive hint system after 10 seconds
        threading.Timer(10.0, send_progressive_hints).start()
        
        timer_service.start_drawing_timer(room_id, draw_time, on_drawing_timeout)
        
    except Exception as e:
        print(f"❌ Error starting drawing phase: {e}")

def _end_turn(room_id, timeout=False, all_guessed=False):
    """End current turn"""
    try:
        room_data = memory_service.get_room(room_id)
        if not room_data:
            return
        
        current_word = room_data['game_state'].get('current_word')
        drawer_id = room_data['game_state']['current_drawer']
        scores = room_data['game_state']['scores']
        players_guessed = room_data['game_state'].get('players_guessed', [])
        
        print(f"🏁 Turn ended in room {room_id} - Word: '{current_word}'")
        
        # Prepare turn results with player names
        results = []
        enriched_room = memory_service.get_room_with_player_details(room_id)
        for player in enriched_room['players']:
            player_id = player['session_id']
            results.append({
                'player_id': player_id,
                'username': player['username'],
                'score': room_data['game_state']['scores'].get(player_id, 0)
            })
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Notify all players turn ended
        socketio.emit('turn_ended', {
            'word': current_word,
            'drawer': drawer_id,
            'drawer_name': memory_service.get_user_session(drawer_id)['username'] if drawer_id else 'Unknown',
            'results': results,
            'scores': room_data['game_state']['scores'],
            'timeout': timeout,
            'all_guessed': all_guessed,
            'next_phase_in': 5
        }, room=room_id)
        
        # Start results timer
        timer_service.start_results_timer(room_id, 5)
        
        # Award drawer bonus if all players guessed correctly
        if all_guessed and drawer_id:
            if drawer_id not in scores:
                scores[drawer_id] = 0
            scores[drawer_id] += 50
            print(f"🏅 Drawer {drawer_id} awarded 50 bonus points for everyone guessing the word")
        
    except Exception as e:
        print(f"❌ Error ending turn: {e}")

def _start_next_turn_or_round(room_id):
    """Start next turn or round"""
    try:
        room_data = memory_service.get_room(room_id)
        if not room_data:
            return
        
        # Increment the drawer index since the current turn is complete
        drawer_order = room_data['game_state']['drawer_order']
        current_index = room_data['game_state']['current_drawer_index']
        next_index = current_index + 1
        
        print(f"🎮 Next turn/round: current_index={current_index}, next_index={next_index}, drawer_order_length={len(drawer_order)}")
        
        if next_index >= len(drawer_order):
            # Round complete, start next round
            current_round = room_data['game_state']['current_round']
            next_round = current_round + 1
            
            print(f"🎮 Round {current_round} complete, starting round {next_round}")
            
            room_data['game_state']['current_round'] = next_round
            room_data['game_state']['current_drawer_index'] = 0  # Reset to first player
            memory_service.update_room(room_id, room_data)
            
            # Check if game should end
            if next_round > room_data['settings']['rounds']:
                _end_game(room_id)
                return
            
            # Get socketio instance for context-free emission
            from app import socketio
            
            # Start intermission before next round
            socketio.emit('round_complete', {
                'next_round': next_round,
                'intermission_time': 3
            }, room=room_id)
            
            timer_service.start_intermission_timer(room_id, 3)
        else:
            # Continue with next turn in same round
            room_data['game_state']['current_drawer_index'] = next_index
            memory_service.update_room(room_id, room_data)
            
            print(f"🎮 Starting next turn in same round, drawer_index now {next_index}")
            _start_new_round(room_id)
        
    except Exception as e:
        print(f"❌ Error starting next turn/round: {e}")

def _end_game(room_id):
    """End the game"""
    try:
        room_data = memory_service.get_room(room_id)
        if not room_data:
            return
        
        scores = room_data['game_state']['scores']
        
        # Calculate final results
        final_results = []
        for player_id in room_data['players']:
            user_data = memory_service.get_user_session(player_id)
            if user_data:
                final_results.append({
                    'player_id': player_id,
                    'username': user_data['username'],
                    'score': scores.get(player_id, 0)
                })
        
        # Sort by score
        final_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Determine winner
        winner = final_results[0] if final_results else None
        
        print(f"🏆 Game ended in room {room_id} - Winner: {winner['username'] if winner else 'None'}")
        
        # Update room status
        room_data['status'] = 'ended'
        memory_service.update_room(room_id, room_data)
        
        # Get socketio instance for context-free emission
        from app import socketio
        
        # Notify all players
        socketio.emit('game_ended', {
            'winner': winner,
            'final_results': final_results,
            'total_rounds': room_data['settings']['rounds']
        }, room=room_id)
        
        # Clean up timers
        timer_service.cleanup_room_timer(room_id)
        
    except Exception as e:
        print(f"❌ Error ending game: {e}") 