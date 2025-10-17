import requests
import json

LAMBDA_URL = "https://9wyawpmjib.execute-api.us-east-1.amazonaws.com/default/reddit-mcp-bot"

payload = {"action": "engage"}

try:
    response = requests.post(
        LAMBDA_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=25   # Timeout set just below Lambda default, adjust as needed
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
