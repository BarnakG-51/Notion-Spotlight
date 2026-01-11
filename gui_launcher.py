#!/usr/bin/env python3
"""
GUI Launcher for Notion Agent with OAuth Authentication
"""
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import requests
import threading
import time
import subprocess
import sys
import os
from urllib.parse import urlparse, parse_qs
import json

class NotionAuthGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Notion Agent - Authentication")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Center the window
        self.root.eval('tk::PlaceWindow . center')

        self.server_process = None
        self.auth_url = None
        self.state = None
        self.user_id = None

        self.setup_ui()
        self.start_server()

    def setup_ui(self):
        """Setup the GUI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(main_frame, text="🤖 Notion Agent",
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Status label
        self.status_label = ttk.Label(main_frame, text="Starting server...",
                                    font=("Arial", 10))
        self.status_label.grid(row=1, column=0, pady=(0, 20))

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        self.progress.start()

        # Auth button (initially disabled)
        self.auth_button = ttk.Button(main_frame, text="🔐 Login with Notion",
                                    command=self.start_auth, state='disabled')
        self.auth_button.grid(row=3, column=0, pady=(0, 10))

        # User ID display (initially hidden)
        self.user_id_frame = ttk.Frame(main_frame)
        ttk.Label(self.user_id_frame, text="✅ Authentication successful!",
                 font=("Arial", 12, "bold")).grid(row=0, column=0, pady=(0, 5))
        ttk.Label(self.user_id_frame, text="Your User ID:").grid(row=1, column=0)
        self.user_id_label = ttk.Label(self.user_id_frame, text="", font=("Courier", 10))
        self.user_id_label.grid(row=2, column=0, pady=(0, 10))

        # Continue button (initially hidden)
        self.continue_button = ttk.Button(self.user_id_frame, text="🚀 Continue to Agent",
                                        command=self.open_agent)
        self.continue_button.grid(row=3, column=0, pady=(10, 0))

        # Instructions
        instructions = ttk.Label(main_frame,
            text="Click 'Login with Notion' to authenticate and access your databases.\n"
                 "A browser window will open for you to authorize the application.",
            wraplength=400, justify="center")
        instructions.grid(row=4, column=0, pady=(20, 0))

    def start_server(self):
        """Start the FastAPI server in background"""
        def run_server():
            try:
                # Change to backend directory
                backend_dir = os.path.join(os.path.dirname(__file__), 'notion-spotlight-mvp', 'backend')
                os.chdir(backend_dir)

                # Start server
                self.server_process = subprocess.Popen(
                    [sys.executable, 'agent.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                # Wait for server to be ready
                for _ in range(30):  # Try for 30 seconds
                    try:
                        response = requests.get('http://127.0.0.1:8001/docs', timeout=1)
                        if response.status_code == 200:
                            self.root.after(0, self.server_ready)
                            return
                    except:
                        pass
                    time.sleep(1)

                self.root.after(0, lambda: self.show_error("Failed to start server"))

            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Server error: {str(e)}"))

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

    def server_ready(self):
        """Called when server is ready"""
        self.progress.stop()
        self.progress.grid_remove()
        self.status_label.config(text="✅ Server started successfully!")
        self.auth_button.config(state='normal')

    def start_auth(self):
        """Start the OAuth authentication process"""
        try:
            response = requests.get('http://127.0.0.1:8001/oauth/authorize', timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.auth_url = data['auth_url']
                self.state = data['state']

                # Open browser
                webbrowser.open(self.auth_url)

                # Update UI
                self.auth_button.config(state='disabled', text="🔄 Complete authentication in browser...")
                self.status_label.config(text="Complete authentication in your browser")

                # Start polling for completion
                self.poll_auth_completion()

            else:
                self.show_error("Failed to get authorization URL")

        except Exception as e:
            self.show_error(f"Authentication error: {str(e)}")

    def poll_auth_completion(self):
        """Poll for authentication completion by checking for user tokens"""
        def check_auth():
            try:
                # Check if user_tokens.json has been created/updated
                tokens_file = os.path.join(os.path.dirname(__file__),
                                         'notion-spotlight-mvp', 'backend', 'user_tokens.json')

                if os.path.exists(tokens_file):
                    with open(tokens_file, 'r') as f:
                        tokens = json.load(f)

                    if tokens:  # If there are any tokens
                        # Get the most recent user_id
                        user_ids = list(tokens.keys())
                        if user_ids:
                            self.user_id = user_ids[-1]  # Get last authenticated user
                            self.root.after(0, self.auth_success)

                # Continue polling
                self.root.after(2000, check_auth)  # Check every 2 seconds

            except Exception as e:
                print(f"Polling error: {e}")
                self.root.after(2000, check_auth)

        check_auth()

    def auth_success(self):
        """Called when authentication is successful"""
        self.status_label.grid_remove()
        self.auth_button.grid_remove()

        # Show user ID frame
        self.user_id_frame.grid(row=1, column=0, pady=(20, 0))
        self.user_id_label.config(text=self.user_id)

        # Save user_id to a config file for the CLI
        self.save_user_config()

    def save_user_config(self):
        """Save user_id to a config file"""
        config_dir = os.path.join(os.path.dirname(__file__), 'config')
        os.makedirs(config_dir, exist_ok=True)

        config_file = os.path.join(config_dir, 'user_config.json')
        with open(config_file, 'w') as f:
            json.dump({'user_id': self.user_id}, f)

    def open_agent(self):
        """Open the agent interface"""
        # Start CLI in new terminal or window
        try:
            backend_dir = os.path.join(os.path.dirname(__file__), 'notion-spotlight-mvp', 'backend')
            subprocess.Popen(['xterm', '-e', f'cd {backend_dir} && python3 cli.py'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            # Fallback: try gnome-terminal
            try:
                backend_dir = os.path.join(os.path.dirname(__file__), 'notion-spotlight-mvp', 'backend')
                subprocess.Popen(['gnome-terminal', '--', 'bash', '-c',
                                f'cd {backend_dir} && python3 cli.py; read -p "Press Enter to exit"'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                # Last resort: just run in background
                backend_dir = os.path.join(os.path.dirname(__file__), 'notion-spotlight-mvp', 'backend')
                subprocess.Popen([sys.executable, os.path.join(backend_dir, 'cli.py')],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.root.quit()

    def show_error(self, message):
        """Show error message"""
        self.progress.stop()
        self.status_label.config(text=f"❌ {message}")
        messagebox.showerror("Error", message)

    def run(self):
        """Run the GUI"""
        self.root.mainloop()

        # Cleanup
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()

def main():
    app = NotionAuthGUI()
    app.run()

if __name__ == "__main__":
    main()