import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import random

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
    if user_id not in waiting_queue:
        waiting_queue.append(user_id)
        join_room(user_id)  # Join the user to their own room
    check_and_create_pair()

@socketio.on('message')
def handle_message(data):
    room = data['room']
    emit('message', data, room=room)

@socketio.on('leave')
def on_leave(data):
    user_id = data['user_id']
    room = data['room']
    leave_room(room)
    if room in active_chats:
        if user_id in active_chats[room]:
            active_chats[room].remove(user_id)
        if len(active_chats[room]) == 0:
            del active_chats[room]
        else:
            other_user = active_chats[room][0]
            emit('partner_left', room=other_user)
            waiting_queue.append(other_user)
    check_and_create_pair()

@socketio.on('continue_chat')
def continue_chat(data):
    room = data['room']
    user_id = data['user_id']
    if room in active_chats:
        active_chats[room].append(user_id)
        if len(active_chats[room]) == 2:
            emit('chat_continued', room=room)

def check_and_create_pair():
    if len(waiting_queue) >= 2:
        user1 = waiting_queue.pop(0)
        user2 = waiting_queue.pop(0)
        room = f"{user1}_{user2}"
        join_room(room, sid=user1)
        join_room(room, sid=user2)
        active_chats[room] = [user1, user2]
        emit('start_chat', {'room': room}, room=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
