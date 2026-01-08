from fastapi import FastAPI
from notion_client import Client
from groq import Groq
import os
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Initialize clients (will fail gracefully if keys not set)
notion = None
groq_client = None

try:
    if os.getenv("NOTION_API_KEY"):
        notion = Client(auth=os.getenv("NOTION_API_KEY"))
    if os.getenv("GROQ_API_KEY"):
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    print(f"Warning: Could not initialize API clients: {e}")

class Prompt(BaseModel):
    text: str

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

def mark_habit_done(habit_name: str):
    """Mark a habit as done in Notion Habit Tracker database"""
    if not notion:
        return "❌ Notion client not initialized"

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

def create_reminder(task: str, time: str):
    """Create a reminder task in Notion"""
    if not notion:
        return "❌ Notion client not initialized"

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

def show_reminders():
    """Show recent reminders from Notion"""
    if not notion:
        return "❌ Notion client not initialized"

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
    if not groq_client or not notion:
        return {"status": "error", "message": "API keys not configured. Please set NOTION_API_KEY and GROQ_API_KEY in .env file"}

    try:
        # Call Groq with tool calling
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
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
                result = mark_habit_done(arguments["habit_name"])
            elif function_name == "create_reminder":
                result = create_reminder(arguments["task"], arguments["time"])
            elif function_name == "show_reminders":
                result = show_reminders()
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
