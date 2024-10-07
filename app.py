import os
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import random

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
socketio = SocketIO(app, cors_allowed_origins="*")

db.init_app(app)

with app.app_context():
    db.create_all()

waiting_queue = []
active_chats = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def on_join(data):
    user_id = data['user_id']
    logger.debug(f"User {user_id} attempting to join")
    if user_id not in waiting_queue:
        waiting_queue.append(user_id)
        join_room(user_id)  # Join the user to their own room
        logger.debug(f"User {user_id} added to waiting queue. Queue size: {len(waiting_queue)}")
    else:
        logger.debug(f"User {user_id} already in waiting queue")
    logger.debug(f"Current waiting queue: {waiting_queue}")
    check_and_create_pair()

@socketio.on('message')
def handle_message(data):
    room = data['room']
    logger.debug(f"Message received in room {room}: {data['message']}")
    emit('message', data, to=room)

@socketio.on('leave')
def on_leave(data):
    user_id = data['user_id']
    room = data['room']
    logger.debug(f"User {user_id} leaving room {room}")
    leave_room(room)
    if room in active_chats:
        if user_id in active_chats[room]:
            active_chats[room].remove(user_id)
        if len(active_chats[room]) == 0:
            del active_chats[room]
        else:
            other_user = active_chats[room][0]
            emit('partner_left', to=other_user)
            waiting_queue.append(other_user)
    logger.debug(f"Current waiting queue after leave: {waiting_queue}")
    check_and_create_pair()

@socketio.on('continue_chat')
def continue_chat(data):
    room = data['room']
    user_id = data['user_id']
    logger.debug(f"User {user_id} wants to continue chat in room {room}")
    if room in active_chats:
        active_chats[room].append(user_id)
        if len(active_chats[room]) == 2:
            logger.debug(f"Both users agreed to continue chat in room {room}")
            emit('chat_continued', to=room)

def check_and_create_pair():
    logger.debug(f"Checking for pairs. Waiting queue size: {len(waiting_queue)}")
    logger.debug(f"Current waiting queue before pairing: {waiting_queue}")
    if len(waiting_queue) >= 2:
        user1 = waiting_queue.pop(0)
        user2 = waiting_queue.pop(0)
        room = f"{user1}_{user2}"
        logger.debug(f"Creating pair: {user1} and {user2} in room {room}")
        join_room(room, sid=user1)
        join_room(room, sid=user2)
        active_chats[room] = [user1, user2]
        logger.debug(f"Emitting start_chat event to room {room}")
        emit('start_chat', {'room': room}, to=room)
        logger.debug(f"Emitted start_chat event to room {room}")
    else:
        logger.debug("Not enough users in the waiting queue to create a pair")
    logger.debug(f"Current waiting queue after pairing: {waiting_queue}")
    logger.debug(f"Current active chats: {active_chats}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
