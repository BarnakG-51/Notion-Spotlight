import requests
try:
    r = requests.get('https://api.notion.com/v1', timeout=10)
    print('status', r.status_code)
    print(r.text[:1000])
except Exception as e:
    print('error', e)
