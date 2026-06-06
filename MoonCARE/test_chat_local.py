import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. Register or Login
resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "",
    "password": ""
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
