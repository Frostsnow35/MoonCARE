import httpx

r = httpx.post('http://127.0.0.1:8000/api/v1/auth/login', json={'email': '', 'password': ''})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

payload = {'message': '你是谁', 'session_id': '', 'agent_mode': 'auto', 'client_context': '[]'}
r = httpx.post('http://127.0.0.1:8000/api/v1/chat/stream', headers=headers, data=payload)
print(r.status_code, r.text)
