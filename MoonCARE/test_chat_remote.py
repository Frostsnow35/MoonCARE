import requests

BASE_URL = "http://159.75.13.158/api/v1"

# 1. Register or Login
resp = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "test2@example.com",
    "password": "password123",
    "nickname": "test"
})
if resp.status_code == 400: # might already exist
    pass

resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "test2@example.com",
    "password": "password123"
})
token = resp.json().get("access_token")
print("Token:", token)

# 2. Chat stream
resp = requests.post(
    f"{BASE_URL}/chat/stream",
    headers={"Authorization": f"Bearer {token}"},
    data={"message": "hello"}
)
print("Status:", resp.status_code)
print("Body:", resp.text)
