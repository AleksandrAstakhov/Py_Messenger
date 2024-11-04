from flask import Flask, request, jsonify
from flask_socketio import SocketIO, send, emit
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)

DATABASE = "./data/database.db"


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """
        )
        conn.commit()


init_db()


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password),
            )
            conn.commit()
            return jsonify({"status": "success"}), 201
        except sqlite3.IntegrityError:
            return (
                jsonify({"status": "error", "message": "Пользователь уже существует"}),
                400,
            )


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        user = c.fetchone()
        if user:
            return jsonify({"status": "success", "user_id": user[0]}), 200
        else:
            return (
                jsonify({"status": "error", "message": "Неверные учетные данные"}),
                400,
            )


@socketio.on("connect")
def handle_connect():
    print("Клиент подключился")


@socketio.on("disconnect")
def handle_disconnect():
    print("Клиент отключился")


@socketio.on("send_message")
def handle_send_message(data):
    user_id = data.get("user_id")
    message = data.get("message")

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages (user_id, message) VALUES (?, ?)", (user_id, message)
        )
        conn.commit()

        c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        username = user[0] if user else "Unknown"

        message_data = {
            "username": username,
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        emit("receive_message", message_data, broadcast=True)


@socketio.on("request_history")
def handle_request_history():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT users.username, messages.message, messages.timestamp
            FROM messages
            JOIN users ON messages.user_id = users.id
            ORDER BY messages.timestamp ASC
        """
        )
        messages = c.fetchall()
        messages_list = [
            {"username": m[0], "message": m[1], "timestamp": m[2]} for m in messages
        ]
        emit("message_history", messages_list)


if __name__ == "__main__":
    host = os.environ.get("SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("SERVER_PORT", "5000"))
    socketio.run(app, host=host, port=port, debug=True)
