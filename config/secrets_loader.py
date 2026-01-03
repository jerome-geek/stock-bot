# config/secrets_loader.py
import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_gcp_credentials():
    """
    GCP 서비스 계정 인증 정보를 가져옵니다.
    1. 로컬의 'service_account.json' 파일 확인
    2. 환경 변수 'GCP_SERVICE_ACCOUNT' 확인 (GitHub Actions용)
    """
    file_path = "service_account.json"
    
    # 1. 로컬 파일 확인
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    
    # 2. 환경 변수 확인
    env_creds = os.getenv("GCP_SERVICE_ACCOUNT")
    if env_creds:
        return json.loads(env_creds)
    
    return None
