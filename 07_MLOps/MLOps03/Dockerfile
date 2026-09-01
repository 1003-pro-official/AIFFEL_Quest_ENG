# 1. 베이스 이미지 설정 (가벼운 파이썬 버전)
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /root/mlops_serving

# 3. 필수 라이브러리 설치
RUN pip install --no-cache-dir fastapi uvicorn scikit-learn joblib python-multipart numpy

# 4. 모델 파일과 API 코드를 컨테이너 안으로 복사
COPY main.py .
COPY model.joblib .

# 5. 서버 실행 명령 (8000 포트)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
