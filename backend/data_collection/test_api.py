# backend/data_collection/test_api.py
# NTIS API 연결 테스트 스크립트
# 기능: API 키 유효성, 응답 포맷 확인

import warnings
import requests
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# .env 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
API_KEY = os.getenv("NTIS_API_KEY")

if not API_KEY:
    print("❌ NTIS_API_KEY가 .env에 없습니다!")
    print(f"   .env 경로: {env_path}")
    exit(1)

print(f"✓ API 키: {API_KEY[:10]}...")

BASE_URL = "https://www.ntis.go.kr/rndopen/openApi/totalRstSearch"

params = {
    "apprvKey": API_KEY,
    "query": "AI",
    "userId": "",
    "collection": "project",
    "searchField": "",
    "startPosition": 1,
    "displayCount": 5,
    "naviCount": 10,
    "sortby": "",
    "boostquery": "",
    "addQuery": "",
}

print("\n🔍 NTIS API 테스트...")
print(f"   URL: {BASE_URL}")
print(f"   Keyword: AI, Year: 2024-2025\n")

try:
    response = requests.get(BASE_URL, params=params, timeout=20, verify=False)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")

    # 응답 확인
    if "<!doctype html>" in response.text.lower() or "<html>" in response.text.lower():
        print("\n❌ 오류: HTML 응답이 반환되었습니다 (인증 실패)")
        print("   가능한 원인:")
        print("   1. API 키가 유효하지 않음")
        print("   2. API 사용 승인이 필요함")
        print("   3. IP 제한 설정이 있음")
        print("\n   -> NTIS 사이트에서 API 키 확인: https://www.ntis.go.kr/")

    elif response.text.startswith("<?xml"):
        print("\n✓ XML 응답 성공!")
        print(f"   응답 크기: {len(response.text)} bytes")
        print(f"\n   첫 300자:")
        print("   " + response.text[:300])
    else:
        print(f"\n⚠️  예상치 못한 응답 형식")
        print(f"   응답 (처음 300자): {response.text[:300]}")

except requests.exceptions.Timeout:
    print("❌ 타임아웃: NTIS 서버 응답 없음")
except requests.exceptions.ConnectionError:
    print("❌ 연결 오류: 네트워크 확인")
except Exception as e:
    print(f"❌ 오류: {e}")
