import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
import socketio

SERVER_URL = "http://127.0.0.1:5000"


class MessengerAPIClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.user_id = None
        self.sio = socketio.Client()
        self.on_receive_message_callback = None
        self.on_message_history_callback = None

    def register_socket_events(self):
        @self.sio.event
        def connect():
            print("Соединение установлено")

        @self.sio.event
        def disconnect():
            print("Соединение разорвано")

        @self.sio.on("receive_message")
        def on_receive_message(data):
            if self.on_receive_message_callback:
                self.on_receive_message_callback(data)
            else:
                print("Нет обработчика для получения сообщения")

        @self.sio.on("message_history")
        def on_message_history(messages):
            if self.on_message_history_callback:
                self.on_message_history_callback(messages)
            else:
                print("Нет обработчика для истории сообщений")

    def set_receive_message_callback(self, callback):
        self.on_receive_message_callback = callback

    def set_message_history_callback(self, callback):
        self.on_message_history_callback = callback

    def connect_socket(self):
        self.register_socket_events()
        try:
            self.sio.connect(self.server_url)
            self.sio.emit("request_history")
        except socketio.exceptions.ConnectionError:
            print("Не удалось установить соединение WebSocket")

    def login(self, username, password):
        try:
            response = requests.post(
                f"{self.server_url}/login",
                json={"username": username, "password": password},
            )
            if response.status_code == 200:
                self.user_id = response.json()["user_id"]
                self.connect_socket()
                return True, None
            else:
                return False, response.json().get("message", "Ошибка авторизации")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу"

    def register(self, username, password):
        try:
            response = requests.post(
                f"{self.server_url}/register",
                json={"username": username, "password": password},
            )
            if response.status_code == 201:
                return True, None
            else:
                return False, response.json().get("message", "Ошибка регистрации")
        except requests.ConnectionError:
            return False, "Не удалось подключиться к серверу"

    def send_message(self, message):
        if self.user_id:
            self.sio.emit("send_message", {"user_id": self.user_id, "message": message})
            return True, None
        else:
            return False, "Пользователь не авторизован"

    def disconnect(self):
        self.sio.disconnect()


class MessengerGUI:
    def __init__(self, master, api_client):
        self.master = master
        self.master.title("Py_messenger")
        self.api_client = api_client

        self.login_frame = tk.Frame(self.master)
        self.chat_frame = tk.Frame(self.master)

        self.create_login_widgets()
        self.create_chat_widgets()

        self.api_client.set_receive_message_callback(self.on_receive_message)
        self.api_client.set_message_history_callback(self.on_message_history)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_login_widgets(self):
        tk.Label(self.login_frame, text="Логин:").grid(row=0, column=0, pady=5)
        self.username_entry = tk.Entry(self.login_frame)
        self.username_entry.grid(row=0, column=1, pady=5)

        tk.Label(self.login_frame, text="Пароль:").grid(row=1, column=0, pady=5)
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)

        tk.Button(self.login_frame, text="Войти", command=self.login).grid(
            row=2, column=0, pady=5
        )
        tk.Button(self.login_frame, text="Регистрация", command=self.register).grid(
            row=2, column=1, pady=5
        )

        self.login_frame.pack(padx=10, pady=10)

    def create_chat_widgets(self):
        self.messages_text = scrolledtext.ScrolledText(
            self.chat_frame, state="disabled", width=50, height=20
        )
        self.messages_text.pack(padx=10, pady=10)

        self.message_entry = tk.Entry(self.chat_frame, width=40)
        self.message_entry.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))

        tk.Button(self.chat_frame, text="Отправить", command=self.send_message).pack(
            side=tk.LEFT, padx=10, pady=(0, 10)
        )

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning("Внимание", "Пожалуйста, заполните все поля")
            return
        success, message = self.api_client.login(username, password)
        if success:
            self.login_frame.pack_forget()
            self.chat_frame.pack()
        else:
            messagebox.showerror("Ошибка", message)

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning("Внимание", "Пожалуйста, заполните все поля")
            return
        success, message = self.api_client.register(username, password)
        if success:
            messagebox.showinfo("Успех", "Регистрация прошла успешно")
        else:
            messagebox.showerror("Ошибка", message)

    def send_message(self):
        message = self.message_entry.get()
        if message:
            success, error_message = self.api_client.send_message(message)
            if success:
                self.message_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Ошибка", error_message)

    def on_receive_message(self, data):
        def update():
            username = data["username"]
            message = data["message"]
            timestamp = data["timestamp"]
            self.display_message(username, message, timestamp)

        self.master.after(0, update)

    def on_message_history(self, messages):
        def update():
            self.messages_text.config(state="normal")
            self.messages_text.delete(1.0, tk.END)
            for msg in messages:
                self.display_message(msg["username"], msg["message"], msg["timestamp"])
            self.messages_text.config(state="disabled")

        self.master.after(0, update)

    def display_message(self, username, message, timestamp):
        self.messages_text.config(state="normal")
        self.messages_text.insert(tk.END, f"[{timestamp}] {username}: {message}\n")
        self.messages_text.config(state="disabled")
        self.messages_text.see(tk.END)

    def on_closing(self):
        self.api_client.disconnect()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    api_client = MessengerAPIClient(SERVER_URL)
    app = MessengerGUI(root, api_client)
    root.mainloop()
