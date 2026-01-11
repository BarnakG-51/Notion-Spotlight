#!/usr/bin/env python3
"""
CLI for interacting with the Notion Agent via the FastAPI backend
"""
import subprocess
import time
import requests
import sys
import os
import json

def load_user_config():
    """Load user configuration from file"""
    config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'user_config.json')
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def start_server():
    """Start the FastAPI server in the background"""
    # Change to the backend directory
    os.chdir(os.path.dirname(__file__))
    
    # Start the server
    process = subprocess.Popen([sys.executable, 'agent.py'], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
    return process

def wait_for_server():
    """Wait for the server to be ready"""
    for _ in range(10):  # Try for 10 seconds
        try:
            response = requests.get('http://127.0.0.1:8001/docs', timeout=1)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def main():
    print("🤖 Starting Notion Agent server...")
    
    # Start the server
    server_process = start_server()
    
    # Wait for it to be ready
    if not wait_for_server():
        print("❌ Failed to start server")
        server_process.terminate()
        return
    
    print("✅ Server started successfully!")
    print("🤖 Notion Agent CLI")
    print()
    
    # Try to load user config
    user_config = load_user_config()
    if user_config and 'user_id' in user_config:
        user_id = user_config['user_id']
        print(f"✅ Loaded user authentication: {user_id}")
    else:
        # Get user authentication
        print("🔐 Authentication required")
        print("1. If you have a user_id from OAuth, enter it")
        print("2. Or run 'python gui_launcher.py' for GUI authentication")
        print()
        
        user_id = input("Enter your user_id (or press Enter to exit): ").strip()
        if not user_id:
            print("❌ User ID is required. Run GUI launcher for authentication.")
            server_process.terminate()
            return
    
    print(f"✅ Using user_id: {user_id}")
    print("Type your commands or 'quit' to exit")
    print()
    
    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            try:
                response = requests.post('http://127.0.0.1:8001/prompt', 
                                       json={"text": user_input, "user_id": user_id}, 
                                       timeout=30)
                result = response.json()
                
                if result["status"] == "success":
                    print(f"Agent: {result['message']}")
                else:
                    print(f"Error: {result['message']}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Connection error: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                
            print()
            
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("Goodbye!")

if __name__ == "__main__":
    main()