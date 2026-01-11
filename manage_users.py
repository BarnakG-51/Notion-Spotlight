#!/usr/bin/env python3
"""
Helper script to logout and manage users
"""
import requests
import json
import webbrowser

BASE_URL = "http://localhost:8001"

def list_users():
    """List all logged in users"""
    response = requests.get(f"{BASE_URL}/users")
    if response.status_code == 200:
        data = response.json()
        users = data.get('users', [])
        if users:
            print("\n👥 Logged in users:\n")
            for idx, user in enumerate(users, 1):
                print(f"{idx}. {user['workspace_name']}")
                print(f"   User ID: {user['user_id']}")
                print(f"   Databases: {user['database_count']}")
                print()
            return users
        else:
            print("\n📭 No users logged in.\n")
            return []
    else:
        print(f"❌ Error: {response.status_code}")
        return []

def logout_user(user_id):
    """Logout a specific user"""
    response = requests.delete(f"{BASE_URL}/user/{user_id}/logout")
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ {data['message']}\n")
        return True
    else:
        print(f"\n❌ Error: {response.status_code} - {response.text}\n")
        return False

def start_oauth():
    """Start OAuth login flow"""
    response = requests.get(f"{BASE_URL}/oauth/authorize")
    if response.status_code == 200:
        data = response.json()
        auth_url = data['auth_url']
        print(f"\n🔐 Opening Notion login in your browser...\n")
        print(f"If it doesn't open automatically, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)
        print("After logging in, you'll be redirected back to the app.")
        print("The server will handle the callback automatically.\n")
    else:
        print(f"❌ Error: {response.status_code}")

def main():
    print("=" * 60)
    print("  Notion Agent - User Management")
    print("=" * 60)
    
    while True:
        print("\nWhat would you like to do?")
        print("1. List logged in users")
        print("2. Logout a user")
        print("3. Login (OAuth)")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            list_users()
        
        elif choice == "2":
            users = list_users()
            if users:
                try:
                    idx = int(input("Enter user number to logout: ")) - 1
                    if 0 <= idx < len(users):
                        logout_user(users[idx]['user_id'])
                    else:
                        print("❌ Invalid user number")
                except ValueError:
                    print("❌ Invalid input")
        
        elif choice == "3":
            start_oauth()
        
        elif choice == "4":
            print("\n👋 Goodbye!\n")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
