#!/usr/bin/env python3
"""
Quick script to refresh databases for existing users
"""
import requests
import json

def refresh_databases():
    # Read user tokens
    try:
        with open('notion-spotlight-mvp/backend/user_tokens.json', 'r') as f:
            tokens = json.load(f)
    except FileNotFoundError:
        print("❌ No user tokens found. Please login first.")
        return
    
    if not tokens:
        print("❌ No users found. Please login first.")
        return
    
    print(f"Found {len(tokens)} user(s)")
    
    for user_id in tokens.keys():
        print(f"\n🔄 Refreshing databases for user: {user_id}")
        
        response = requests.post(f"http://localhost:8001/user/{user_id}/databases/refresh")
        
        if response.status_code == 200:
            data = response.json()
            databases = data.get('databases', [])
            print(f"✅ {data['message']}")
            print(f"\n📊 Found {len(databases)} database(s):\n")
            for db in databases:
                print(f"  • {db['title']}")
                print(f"    ID: {db['id']}")
                print()
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    print("=" * 60)
    print("  Refreshing Notion Databases")
    print("=" * 60)
    print("\nMake sure the server is running (python launch.py)\n")
    
    try:
        refresh_databases()
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server.")
        print("Please make sure the server is running on port 8001")
