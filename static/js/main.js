const socket = io();
let currentRoom = null;
let userId = null;
let timer = null;

function generateUserId() {
    return Math.random().toString(36).substr(2, 9);
}

function startTimer(duration, display) {
    let timer = duration, minutes, seconds;
    return setInterval(function () {
        minutes = parseInt(timer / 60, 10);
        seconds = parseInt(timer % 60, 10);

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        display.textContent = minutes + ":" + seconds;

        if (--timer < 0) {
            clearInterval(timer);
            document.getElementById('timer-container').classList.add('hidden');
            document.getElementById('choice-container').classList.remove('hidden');
        }
    }, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
    userId = generateUserId();
    console.log(`Generated user ID: ${userId}`);
    socket.emit('join', { user_id: userId });
    console.log(`Emitted join event for user ${userId}`);

    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const continueBtn = document.getElementById('continue-btn');
    const nextBtn = document.getElementById('next-btn');

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (chatInput.value) {
            console.log(`Sending message in room ${currentRoom}: ${chatInput.value}`);
            socket.emit('message', { room: currentRoom, message: chatInput.value, user_id: userId });
            chatInput.value = '';
        }
    });

    continueBtn.addEventListener('click', () => {
        console.log(`User ${userId} clicked continue in room ${currentRoom}`);
        socket.emit('continue_chat', { room: currentRoom, user_id: userId });
        document.getElementById('choice-container').classList.add('hidden');
    });

    nextBtn.addEventListener('click', () => {
        console.log(`User ${userId} clicked next in room ${currentRoom}`);
        socket.emit('leave', { room: currentRoom, user_id: userId });
        chatMessages.innerHTML = '';
        document.getElementById('choice-container').classList.add('hidden');
        document.getElementById('waiting-message').classList.remove('hidden');
        document.getElementById('chat-container').classList.add('hidden');
        currentRoom = null;
    });

    socket.on('start_chat', (data) => {
        console.log(`Received start_chat event for room ${data.room}`);
        currentRoom = data.room;
        document.getElementById('waiting-message').classList.add('hidden');
        document.getElementById('chat-container').classList.remove('hidden');
        document.getElementById('timer-container').classList.remove('hidden');
        const timerDisplay = document.querySelector('#timer');
        timer = startTimer(60, timerDisplay);
    });

    socket.on('message', (data) => {
        console.log(`Received message in room ${currentRoom}: ${data.message}`);
        const messageElement = document.createElement('div');
        messageElement.textContent = `${data.user_id === userId ? 'You' : 'Partner'}: ${data.message}`;
        messageElement.classList.add('mb-2');
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });

    socket.on('partner_left', () => {
        console.log(`Partner left the chat in room ${currentRoom}`);
        const messageElement = document.createElement('div');
        messageElement.textContent = 'Your partner has left the chat. Waiting for a new partner...';
        messageElement.classList.add('mb-2', 'text-red-500');
        chatMessages.appendChild(messageElement);
        document.getElementById('chat-container').classList.add('hidden');
        document.getElementById('waiting-message').classList.remove('hidden');
        clearInterval(timer);
        currentRoom = null;
        socket.emit('join', { user_id: userId });
    });

    socket.on('chat_continued', () => {
        console.log(`Chat continued in room ${currentRoom}`);
        document.getElementById('timer-container').classList.add('hidden');
        const messageElement = document.createElement('div');
        messageElement.textContent = 'Both users have agreed to continue the chat. Enjoy your extended conversation!';
        messageElement.classList.add('mb-2', 'text-green-500');
        chatMessages.appendChild(messageElement);
    });

    // Add a connection event listener
    socket.on('connect', () => {
        console.log('Connected to server');
    });

    // Add a disconnection event listener
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });
});
