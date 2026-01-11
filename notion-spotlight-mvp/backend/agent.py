from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from notion_client import Client
from groq import Groq
import os
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import requests
import uuid
from typing import Optional

# Load environment variables
load_dotenv()

app = FastAPI()

# OAuth Configuration
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI", "http://localhost:8001/oauth/callback")
TOKEN_STORAGE_FILE = "user_tokens.json"
DEBUG_LOG_FILE = "oauth_debug.log"

# Initialize Groq client
groq_client = None
try:
    if os.getenv("GROQ_API_KEY"):
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    print(f"Warning: Could not initialize Groq client: {e}")

# Token storage functions
def load_tokens():
    """Load user tokens from file"""
    try:
        with open(TOKEN_STORAGE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def debug_log(event: str, payload: Optional[dict] = None, response: Optional[object] = None):
    """Append a masked debug line to the debug log file. Best-effort only."""
    try:
        entry = {"time": datetime.now().isoformat(), "event": event}
        if payload is not None:
            p = dict(payload)
            # Mask sensitive fields
            if 'client_secret' in p:
                p['client_secret'] = '***REDACTED***'
            entry['payload'] = p
        if response is not None:
            try:
                entry['response'] = response.json()
            except Exception:
                try:
                    entry['response_text'] = response.text
                except Exception:
                    entry['response_text'] = '<unavailable>'
            try:
                entry['status_code'] = response.status_code
            except Exception:
                entry['status_code'] = None

        with open(DEBUG_LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        # Do not raise logging errors
        try:
            with open(DEBUG_LOG_FILE, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - debug_log failure\n")
        except Exception:
            pass

def save_tokens(tokens):
    """Save user tokens to file"""
    with open(TOKEN_STORAGE_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

def get_notion_client(user_id: str):
    """Get Notion client for a specific user"""
    tokens = load_tokens()
    if user_id not in tokens:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    user_tokens = tokens[user_id]
    if datetime.fromisoformat(user_tokens['expires_at']) < datetime.now():
        # Token expired, refresh it
        refresh_tokens(user_id)
        tokens = load_tokens()
        user_tokens = tokens[user_id]
    
    return Client(auth=user_tokens['access_token'])

def refresh_tokens(user_id: str):
    """Refresh expired access token"""
    tokens = load_tokens()
    if user_id not in tokens:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    refresh_token = tokens[user_id]['refresh_token']
    
    url = 'https://api.notion.com/v1/oauth/token'
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': NOTION_CLIENT_ID,
        'client_secret': NOTION_CLIENT_SECRET,
    }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    # Log outgoing request (masking secret)
    debug_log('refresh_request', payload=payload)
    response = requests.post(url, json=payload, headers=headers)
    debug_log('refresh_response', payload=None, response=response)

    # Helpful debugging output if the exchange fails
    if response.status_code != 200:
        detail = None
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(status_code=401, detail=f"Failed to refresh token: {detail}")

    data = response.json()
    tokens[user_id] = {
        'access_token': data['access_token'],
        'refresh_token': data.get('refresh_token', refresh_token),
        'expires_at': (datetime.now() + timedelta(seconds=data['expires_in'])).isoformat(),
        'workspace_id': data.get('workspace_id'),
        'workspace_name': data.get('workspace_name'),
    }
    save_tokens(tokens)

# OAuth endpoints
@app.get("/oauth/authorize")
async def authorize():
    """Start OAuth flow"""
    if not NOTION_CLIENT_ID:
        raise HTTPException(status_code=500, detail="NOTION_CLIENT_ID not configured")
    
    state = str(uuid.uuid4())  # Generate a unique state for security
    
    auth_url = (
        "https://api.notion.com/v1/oauth/authorize?"
        f"client_id={NOTION_CLIENT_ID}&"
        f"response_type=code&"
        f"owner=user&"
        f"redirect_uri={NOTION_REDIRECT_URI}&"
        f"state={state}"
    )
    
    return {"auth_url": auth_url, "state": state}

@app.get("/oauth/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """Handle OAuth callback"""
    if not NOTION_CLIENT_ID or not NOTION_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="OAuth credentials not configured")
    
    # Exchange code for tokens
    url = 'https://api.notion.com/v1/oauth/token'
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': NOTION_REDIRECT_URI,
        'client_id': NOTION_CLIENT_ID,
        'client_secret': NOTION_CLIENT_SECRET,
    }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    # Log outgoing request (masking secret)
    debug_log('token_request', payload=payload)
    response = requests.post(url, json=payload, headers=headers)
    debug_log('token_response', payload=None, response=response)

    if response.status_code != 200:
        # Include the remote response body to help debug (Notion returns JSON error)
        detail = None
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(status_code=400, detail=f"Failed to exchange code for tokens: {detail}")

    data = response.json()
    
    # Generate user ID and store tokens
    user_id = str(uuid.uuid4())
    tokens = load_tokens()
    tokens[user_id] = {
        'access_token': data['access_token'],
        'refresh_token': data.get('refresh_token'),
        'expires_at': (datetime.now() + timedelta(seconds=data['expires_in'])).isoformat(),
        'workspace_id': data.get('workspace_id'),
        'workspace_name': data.get('workspace_name'),
    }
    save_tokens(tokens)
    
    return {
        "message": "Authentication successful!",
        "user_id": user_id,
        "workspace_name": data.get('workspace_name', 'Unknown Workspace')
    }

class Prompt(BaseModel):
    text: str
    user_id: str

# Tool definitions for Groq
tools = [
    {
        "type": "function",
        "function": {
            "name": "mark_habit_done",
            "description": "Mark a habit as completed in the Notion Habit Tracker database",
            "parameters": {
                "type": "object",
                "properties": {
                    "habit_name": {
                        "type": "string",
                        "description": "The name of the habit to mark as done"
                    }
                },
                "required": ["habit_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a reminder task in Notion with a specific date/time",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The reminder task description"
                    },
                    "time": {
                        "type": "string",
                        "description": "When to be reminded (e.g., 'tomorrow', 'next week', '2024-01-15')"
                    }
                },
                "required": ["task", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_reminders",
            "description": "Show recent reminder tasks from Notion",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def mark_habit_done(user_id: str, habit_name: str):
    """Mark a habit as done in Notion Habit Tracker database"""
    try:
        notion = get_notion_client(user_id)
    except HTTPException:
        return "❌ User not authenticated"

    # You'll need to replace these with your actual database IDs
    habit_db_id = os.getenv("HABIT_DB_ID")  # Your Habit Tracker database ID

    if not habit_db_id:
        return "❌ HABIT_DB_ID not set in environment variables"

    try:
        response = notion.databases.query(
            database_id=habit_db_id,
            filter={
                "property": "Name",
                "title": {
                    "equals": habit_name
                }
            }
        )

        if response["results"]:
            page_id = response["results"][0]["id"]
            # Toggle the checkbox
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Done": {
                        "checkbox": True
                    }
                }
            )
            return f"✅ Marked '{habit_name}' as done!"
        else:
            return f"❌ Habit '{habit_name}' not found in database"
    except Exception as e:
        return f"❌ Error updating habit: {str(e)}"

def create_reminder(user_id: str, task: str, time: str):
    """Create a reminder task in Notion"""
    try:
        notion = get_notion_client(user_id)
    except HTTPException:
        return "❌ User not authenticated"

    todo_db_id = os.getenv("TODO_DB_ID")  # Your To-Do database ID

    if not todo_db_id:
        return "❌ TODO_DB_ID not set in environment variables"

    # Parse time (simple implementation - you can enhance this)
    reminder_date = None
    if time.lower() == "tomorrow":
        reminder_date = datetime.now() + timedelta(days=1)
    elif time.lower() == "next week":
        reminder_date = datetime.now() + timedelta(weeks=1)
    else:
        # Try to parse as date
        try:
            reminder_date = datetime.strptime(time, "%Y-%m-%d")
        except:
            reminder_date = datetime.now() + timedelta(days=1)  # Default to tomorrow

    try:
        # Create the page
        notion.pages.create(
            parent={"database_id": todo_db_id},
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": task
                            }
                        }
                    ]
                },
                "Date": {
                    "date": {
                        "start": reminder_date.strftime("%Y-%m-%d")
                    }
                },
                "Tags": {
                    "multi_select": [
                        {
                            "name": "Reminder"
                        }
                    ]
                }
            }
        )

        return f"✅ Created reminder: '{task}' for {reminder_date.strftime('%Y-%m-%d')}"
    except Exception as e:
        return f"❌ Error creating reminder: {str(e)}"

def show_reminders(user_id: str):
    """Show recent reminders from Notion"""
    try:
        notion = get_notion_client(user_id)
    except HTTPException:
        return "❌ User not authenticated"

    todo_db_id = os.getenv("TODO_DB_ID")

    if not todo_db_id:
        return "❌ TODO_DB_ID not set in environment variables"

    try:
        # Query recent pages
        response = notion.databases.query(
            database_id=todo_db_id,
            filter={
                "property": "Tags",
                "multi_select": {
                    "contains": "Reminder"
                }
            },
            sorts=[
                {
                    "property": "Date",
                    "direction": "descending"
                }
            ],
            page_size=5
        )

        reminders = []
        for page in response["results"]:
            title = page["properties"]["Name"]["title"][0]["text"]["content"]
            date = page["properties"]["Date"]["date"]["start"] if page["properties"]["Date"]["date"] else "No date"
            reminders.append(f"• {title} ({date})")

        if reminders:
            return "📝 Recent Reminders:\n" + "\n".join(reminders)
        else:
            return "📝 No recent reminders found"
    except Exception as e:
        return f"❌ Error fetching reminders: {str(e)}"

@app.post("/prompt")
async def process_prompt(prompt: Prompt):
    if not groq_client:
        return {"status": "error", "message": "GROQ_API_KEY not configured"}

    try:
        # Call Groq with tool calling
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Notion assistant. Use the available tools to help users manage their habits, reminders, and tasks. Be concise and helpful."
                },
                {
                    "role": "user",
                    "content": prompt.text
                }
            ],
            tools=tools,
            tool_choice="auto"
        )

        # Check if tool was called
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            # Execute the appropriate function
            if function_name == "mark_habit_done":
                result = mark_habit_done(prompt.user_id, arguments["habit_name"])
            elif function_name == "create_reminder":
                result = create_reminder(prompt.user_id, arguments["task"], arguments["time"])
            elif function_name == "show_reminders":
                result = show_reminders(prompt.user_id)
            else:
                result = "❌ Unknown action"

            return {"status": "success", "message": result}
        else:
            return {"status": "success", "message": "I didn't understand that command. Try: 'Mark water habit done', 'Remind me to call mom tomorrow', or 'Show reminders'"}

    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
