import httpx
token = ''
headers = {'Authorization': f'Bearer {token}'}
payload = {'content': 'ÄãÊÇË­', 'role': 'user'}
r = httpx.post('http://127.0.0.1:8000/api/v1/chat/message', headers=headers, json=payload)
print(r.status_code, r.text)
