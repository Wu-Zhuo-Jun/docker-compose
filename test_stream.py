import requests

resp = requests.post(
    "http://localhost:8000/chat/qa/stream?user_id=1",
    json={"query": "hello", "session_id": None},
    timeout=5,
    stream=True
)
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('content-type')}")

# Read stream
for line in resp.iter_lines():
    if line:
        print(f"Event: {line.decode('utf-8')}")
