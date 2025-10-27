# 임시 확인 코드
import requests
from datetime import datetime

API_KEY = "cb5adb1eb4720ef153d4f8e1583925e2"
headers = {'X-ELS-APIKey': API_KEY, 'Accept': 'application/json'}

response = requests.get(
    "https://api.elsevier.com/content/search/sciencedirect", 
    headers=headers, 
    params={'query': 'test', 'count': 1}
)

print(f"남은 요청: {response.headers.get('X-RateLimit-Remaining')}")
print(f"총 한도: {response.headers.get('X-RateLimit-Limit')}")

reset_time = int(response.headers.get('X-RateLimit-Reset'))
reset_readable = datetime.fromtimestamp(reset_time)
print(f"리셋 시간: {reset_readable}")

hours_left = (reset_readable - datetime.now()).total_seconds() / 3600
print(f"리셋까지: {hours_left:.1f}시간")