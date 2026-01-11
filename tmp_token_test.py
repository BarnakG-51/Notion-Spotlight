import json, requests, re

def load_env(path='.env'):
    env = {}
    with open(path) as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k,v=line.split('=',1)
                env[k.strip()]=v.strip()
    return env

env = load_env()
client_id = env.get('NOTION_CLIENT_ID')
client_secret = env.get('NOTION_CLIENT_SECRET')
redirect = env.get('NOTION_REDIRECT_URI')

print('Using redirect_uri:', redirect)

url='https://api.notion.com/v1/oauth/token'
payload={
    'grant_type':'authorization_code',
    'code':'invalid-or-used-code',
    'redirect_uri': redirect,
    'client_id': client_id,
    'client_secret': client_secret
}
headers={'Content-Type':'application/json','Accept':'application/json'}

try:
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    print('status', r.status_code)
    try:
        print('body', json.dumps(r.json()))
    except Exception:
        print('body non-json:', r.text)
except Exception as e:
    print('error', e)
