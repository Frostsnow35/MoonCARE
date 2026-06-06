import requests
import time
import json

BASE_URL = "http://159.75.13.158/api/v1"
EMAIL = f"test_{int(time.time())}@example.com"

print(f"Registering {EMAIL}...")
# In debug mode or if email verification is not strictly enforced, we might need a workaround.
# But wait, looking at the code, register requires email_code.
# Let's see if there's a test user we can use, or if we can get the code.
# Actually, the user must have logged in successfully on the frontend, otherwise they would get a 401, not a 500.
# So the 500 is specifically for the chat endpoint.
