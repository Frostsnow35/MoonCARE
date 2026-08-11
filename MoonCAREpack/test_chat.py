import httpx

r = httpx.post('http://127.0.0.1:8000/api/v1/auth/login', json={'email': '', 'password': ''})
token = r.json()['access_token']

headers = {'Authorization': f'Bearer {token}'}

r = httpx.post('http://127.0.0.1:8000/api/v1/chat/session', headers=headers)
session_id = r.json()['session_id']

payload = {'message': '你是谁', 'session_id': session_id}
r = httpx.post('http://127.0.0.1:8000/api/v1/chat/message', headers=headers, data=payload)
print(r.status_code, r.text)
