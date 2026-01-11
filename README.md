# Notion Agent with OAuth

A FastAPI-based Notion assistant that supports OAuth authentication for multiple users, with a GUI launcher for easy authentication.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Fill in your Notion OAuth credentials and API keys

3. **Launch the application:**
   ```bash
   python launch.py
   # or
   ./launch.py
   ```

   This will open a GUI window for authentication. Follow the on-screen instructions to log in with Notion.

## GUI Authentication Flow

When you run `python launch.py`:

1. **Server Startup**: The application starts the FastAPI server in the background
2. **Authentication Window**: A popup window appears with a "Login with Notion" button
3. **Browser Redirect**: Clicking the button opens your default browser to Notion's OAuth page
4. **Authorization**: Log in to Notion and authorize the application
5. **Success**: The GUI shows your user ID and a "Continue" button
6. **Agent Access**: Clicking "Continue" opens the CLI interface for interacting with your Notion databases

## Alternative Usage

### CLI Only
If you prefer the command-line interface without the GUI:

```bash
cd notion-spotlight-mvp/backend
python cli.py
```

The CLI will automatically load your saved authentication if available, or prompt for a user ID.

### Direct API Access
For developers or advanced users, you can interact directly with the API:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Notion OAuth:**
   - Go to [Notion Developers](https://developers.notion.com/)
   - Create a new integration
   - Set the integration type to "Public" (not Internal)
   - Add a redirect URI: `http://localhost:8001/oauth/callback`
   - Copy the Client ID and Client Secret
   - Note: For production, use `https://yourdomain.com/oauth/callback`

3. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Fill in:
     - `GROQ_API_KEY`: Your Groq API key
     - `NOTION_CLIENT_ID`: From your Notion integration
     - `NOTION_CLIENT_SECRET`: From your Notion integration
     - `NOTION_REDIRECT_URI`: Should match what you set in Notion
     - `HABIT_DB_ID` and `TODO_DB_ID`: Your Notion database IDs

4. **Database Setup:**
   - Create Habit Tracker and Todo databases in Notion
   - Share them with your integration (click "Share" → "Invite" → your integration)
   - Get the database IDs from the URL: `https://notion.so/your-db-id`
   - Add these IDs to your `.env` file

## User Authentication

Each user needs to authenticate with Notion OAuth:

1. **Get Authorization URL:**
   ```bash
   curl http://localhost:8001/oauth/authorize
   ```
   This returns an `auth_url` and `state` parameter.

2. **User Authorization:**
   - Direct users to the `auth_url`
   - They log in to Notion and authorize your app
   - Notion redirects back with an authorization code

3. **Complete Authentication:**
   - The callback endpoint stores the user's access token
   - Returns a `user_id` for that user
   - Store this `user_id` for future API calls

## API Usage

All API calls now require a `user_id`:

```bash
curl -X POST "http://localhost:8001/prompt" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Mark water habit done",
    "user_id": "your-user-id-here"
  }'
```

## OAuth Flow

- `/oauth/authorize`: Returns the Notion authorization URL
- `/oauth/callback`: Handles the OAuth callback and stores user tokens
- `/prompt`: Processes user requests with their authenticated Notion access

## Security Notes

- User tokens are stored locally in `user_tokens.json`
- In production, use a proper database and secure token storage
- The `state` parameter provides CSRF protection during OAuth flow