import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
import threading
import time
import socketio
import os

SERVER_URL = 'http://127.0.0.1:5000'

class MessengerClient:
    def __init__(self, master):
        self.master = master
        self.master.title('Py_messenger')
        self.user_id = None

        self.sio = socketio.Client()

        self.login_frame = tk.Frame(self.master)
        self.chat_frame = tk.Frame(self.master)

        self.create_login_widgets()
        self.create_chat_widgets()

        self.register_socket_events()

    def create_login_widgets(self):
        tk.Label(self.login_frame, text='Логин:').grid(row=0, column=0, pady=5)
        self.username_entry = tk.Entry(self.login_frame)
        self.username_entry.grid(row=0, column=1, pady=5)

        tk.Label(self.login_frame, text='Пароль:').grid(row=1, column=0, pady=5)
        self.password_entry = tk.Entry(self.login_frame, show='*')
        self.password_entry.grid(row=1, column=1, pady=5)

        tk.Button(self.login_frame, text='Войти', command=self.login).grid(row=2, column=0, pady=5)
        tk.Button(self.login_frame, text='Регистрация', command=self.register).grid(row=2, column=1, pady=5)

        self.login_frame.pack(padx=10, pady=10)

    def create_chat_widgets(self):
        self.messages_text = scrolledtext.ScrolledText(self.chat_frame, state='disabled', width=50, height=20)
        self.messages_text.pack(padx=10, pady=10)

        self.message_entry = tk.Entry(self.chat_frame, width=40)
        self.message_entry.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))

        tk.Button(self.chat_frame, text='Отправить', command=self.send_message).pack(side=tk.LEFT, padx=10, pady=(0, 10))

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning('Внимание', 'Пожалуйста, заполните все поля')
            return
        try:
            response = requests.post(f'{SERVER_URL}/login', json={'username': username, 'password': password})
            if response.status_code == 200:
                self.user_id = response.json()['user_id']
                self.login_frame.pack_forget()
                self.chat_frame.pack()
                self.connect_socket()
            else:
                messagebox.showerror('Ошибка', response.json()['message'])
        except requests.ConnectionError:
            messagebox.showerror('Ошибка', 'Не удалось подключиться к серверу')

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning('Внимание', 'Пожалуйста, заполните все поля')
            return
        try:
            response = requests.post(f'{SERVER_URL}/register', json={'username': username, 'password': password})
            if response.status_code == 201:
                messagebox.showinfo('Успех', 'Регистрация прошла успешно')
            else:
                messagebox.showerror('Ошибка', response.json()['message'])
        except requests.ConnectionError:
            messagebox.showerror('Ошибка', 'Не удалось подключиться к серверу')

    def send_message(self):
        message = self.message_entry.get()
        if message:
            self.sio.emit('send_message', {'user_id': self.user_id, 'message': message})
            self.message_entry.delete(0, tk.END)

    def connect_socket(self):
        try:
            self.sio.connect(SERVER_URL)
            self.sio.emit('request_history')
        except socketio.exceptions.ConnectionError:
            messagebox.showerror('Ошибка', 'Не удалось установить соединение WebSocket')

    def register_socket_events(self):
        @self.sio.event
        def connect():
            print('Соединение установлено')

        @self.sio.event
        def disconnect():
            print('Соединение разорвано')

        @self.sio.on('receive_message')
        def on_receive_message(data):
            username = data['username']
            message = data['message']
            timestamp = data['timestamp']
            self.display_message(username, message, timestamp)

        @self.sio.on('message_history')
        def on_message_history(messages):
            self.messages_text.config(state='normal')
            self.messages_text.delete(1.0, tk.END)
            for msg in messages:
                self.display_message(msg['username'], msg['message'], msg['timestamp'])
            self.messages_text.config(state='disabled')

    def display_message(self, username, message, timestamp):
        self.messages_text.config(state='normal')
        self.messages_text.insert(tk.END, f"[{timestamp}] {username}: {message}\n")
        self.messages_text.config(state='disabled')
        self.messages_text.see(tk.END)

    def on_closing(self):
        self.sio.disconnect()
        self.master.destroy()

if __name__ == '__main__':
    host = os.getenv("CLIENT_TARGET_HOST", "server")
    port = os.getenv("CLIENT_TARGET_PORT", 5000)
    url = f"http://{host}:{port}"
    SERVER_URL = url
    root = tk.Tk()
    app = MessengerClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()