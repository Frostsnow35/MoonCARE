import requests

BASE_URL = "http://159.75.13.158/api/v1"

# Since debug empty login works in the local environment, let's see if we can trigger it remotely
resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "",
    "password": ""
})
if resp.status_code != 200:
    print("Login failed, status:", resp.status_code, resp.text)
else:
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
