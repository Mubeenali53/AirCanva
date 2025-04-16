import cv2
import numpy as np
import mediapipe as mp
from collections import deque
import base64
from flask import Flask, request
from flask_socketio import SocketIO, emit
import threading
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Dictionary to store user states
user_states = {}

# Initialize mediapipe
mpHands = mp.solutions.hands
mpDraw = mp.solutions.drawing_utils

def initialize_user_state():
    """Initialize a new user's canvas and drawing state."""
    logger.debug("Initializing user state")
    state = {
        'bpoints': [deque(maxlen=1024)],
        'gpoints': [deque(maxlen=1024)],
        'rpoints': [deque(maxlen=1024)],
        'ypoints': [deque(maxlen=1024)],
        'blue_index': 0,
        'green_index': 0,
        'red_index': 0,
        'yellow_index': 0,
        'colorIndex': 0,
        'paintWindow': np.zeros((471,636,3), dtype=np.uint8) + 255,
        'cap': None
    }
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            state['cap'] = cap
            logger.debug("Webcam initialized successfully")
        else:
            logger.warning("Webcam not accessible")
    except Exception as e:
        logger.error(f"Failed to initialize webcam: {e}")
    # Canvas setup
    state['paintWindow'] = cv2.rectangle(state['paintWindow'], (40,1), (140,65), (0,0,0), 2)
    state['paintWindow'] = cv2.rectangle(state['paintWindow'], (160,1), (255,65), (255,0,0), 2)
    state['paintWindow'] = cv2.rectangle(state['paintWindow'], (275,1), (370,65), (0,255,0), 2)
    state['paintWindow'] = cv2.rectangle(state['paintWindow'], (390,1), (485,65), (0,0,255), 2)
    state['paintWindow'] = cv2.rectangle(state['paintWindow'], (505,1), (600,65), (0,255,255), 2)
    cv2.putText(state['paintWindow'], "CLEAR", (49, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(state['paintWindow'], "BLUE", (185, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(state['paintWindow'], "GREEN", (298, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(state['paintWindow'], "RED", (420, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(state['paintWindow'], "YELLOW", (520, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
    return state

def process_video(sid):
    """Process video for a specific user."""
    if sid not in user_states:
        logger.error(f"User {sid} not found in user_states")
        return
    state = user_states[sid]
    if state['cap'] is None:
        logger.error(f"No webcam for user {sid}")
        socketio.emit('error', {'message': 'Webcam not available'}, room=sid)
        return
    hands = mpHands.Hands(max_num_hands=1, min_detection_confidence=0.7)
    kernel = np.ones((5,5), np.uint8)
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255)]

    while sid in user_states:
        try:
            ret, frame = state['cap'].read()
            if not ret:
                logger.error(f"Failed to read frame for {sid}")
                break
            logger.debug(f"Processing frame for {sid}")

            x, y, c = frame.shape
            frame = cv2.flip(frame, 1)
            framergb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process hand landmarks
            result = hands.process(framergb)
            if result.multi_hand_landmarks:
                landmarks = []
                for handslms in result.multi_hand_landmarks:
                    for lm in handslms.landmark:
                        lmx = int(lm.x * 640)
                        lmy = int(lm.y * 480)
                        landmarks.append([lmx, lmy])

                    fore_finger = (landmarks[8][0], landmarks[8][1])
                    center = fore_finger
                    thumb = (landmarks[4][0], landmarks[4][1])

                    if (thumb[1] - center[1] < 30):
                        state['bpoints'].append(deque(maxlen=512))
                        state['blue_index'] += 1
                        state['gpoints'].append(deque(maxlen=512))
                        state['green_index'] += 1
                        state['rpoints'].append(deque(maxlen=512))
                        state['red_index'] += 1
                        state['ypoints'].append(deque(maxlen=512))
                        state['yellow_index'] += 1
                    elif center[1] <= 65:
                        if 40 <= center[0] <= 140:  # Clear Button
                            state['bpoints'] = [deque(maxlen=512)]
                            state['gpoints'] = [deque(maxlen=512)]
                            state['rpoints'] = [deque(maxlen=512)]
                            state['ypoints'] = [deque(maxlen=512)]
                            state['blue_index'] = 0
                            state['green_index'] = 0
                            state['red_index'] = 0
                            state['yellow_index'] = 0
                            state['paintWindow'][67:,:,:] = 255
                        elif 160 <= center[0] <= 255:
                            state['colorIndex'] = 0  # Blue
                        elif 275 <= center[0] <= 370:
                            state['colorIndex'] = 1  # Green
                        elif 390 <= center[0] <= 485:
                            state['colorIndex'] = 2  # Red
                        elif 505 <= center[0] <= 600:
                            state['colorIndex'] = 3  # Yellow
                    else:
                        if state['colorIndex'] == 0:
                            state['bpoints'][state['blue_index']].appendleft(center)
                        elif state['colorIndex'] == 1:
                            state['gpoints'][state['green_index']].appendleft(center)
                        elif state['colorIndex'] == 2:
                            state['rpoints'][state['red_index']].appendleft(center)
                        elif state['colorIndex'] == 3:
                            state['ypoints'][state['yellow_index']].appendleft(center)
            else:
                state['bpoints'].append(deque(maxlen=512))
                state['blue_index'] += 1
                state['gpoints'].append(deque(maxlen=512))
                state['green_index'] += 1
                state['rpoints'].append(deque(maxlen=512))
                state['red_index'] += 1
                state['ypoints'].append(deque(maxlen=512))
                state['yellow_index'] += 1

            # Draw lines on canvas
            points = [state['bpoints'], state['gpoints'], state['rpoints'], state['ypoints']]
            for i in range(len(points)):
                for j in range(len(points[i])):
                    for k in range(1, len(points[i][j])):
                        if points[i][j][k - 1] is None or points[i][j][k] is None:
                            continue
                        cv2.line(state['paintWindow'], points[i][j][k - 1], points[i][j][k], colors[i], 2)

            # Encode canvas as JPEG and send to user's socket
            _, buffer = cv2.imencode('.jpg', state['paintWindow'])
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('canvas_frame', {'image': jpg_as_text}, room=sid)
            logger.debug(f"Sent canvas frame to {sid}")
        except Exception as e:
            logger.error(f"Error in video processing for {sid}: {e}")
            break

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    logger.info(f'Client {sid} connected')
    try:
        user_states[sid] = initialize_user_state()
        logger.debug(f"Initialized state for {sid}: {user_states[sid].keys()}")
        # Start video processing for this user
        video_thread = threading.Thread(target=process_video, args=(sid,))
        video_thread.daemon = True
        video_thread.start()
    except Exception as e:
        logger.error(f"Failed to initialize user {sid}: {e}")
        socketio.emit('error', {'message': 'Failed to initialize session'}, room=sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    logger.info(f'Client {sid} disconnected')
    try:
        if sid in user_states:
            if user_states[sid]['cap'] is not None:
                user_states[sid]['cap'].release()
            del user_states[sid]
    except Exception as e:
        logger.error(f"Error during disconnect for {sid}: {e}")

@socketio.on('save_canvas')
def handle_save_canvas():
    sid = request.sid
    logger.info(f"Save canvas request from {sid}")
    try:
        if sid in user_states:
            # Save canvas as PNG with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'canvas_{sid}_{timestamp}.png'
            os.makedirs('saved_canvases', exist_ok=True)
            cv2.imwrite(os.path.join('saved_canvases', filename), user_states[sid]['paintWindow'])
            logger.info(f"Saved canvas for {sid}: {filename}")
            socketio.emit('save_status', {'message': f'Canvas saved as {filename}'}, room=sid)
        else:
            logger.error(f"User session not found for {sid}")
            socketio.emit('save_status', {'message': 'Error: User session not found'}, room=sid)
    except Exception as e:
        logger.error(f"Error saving canvas for {sid}: {e}")
        socketio.emit('save_status', {'message': 'Error: Failed to save canvas'}, room=sid)

if __name__ == '__main__':
    logger.info("Starting backend...")
    try:
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")