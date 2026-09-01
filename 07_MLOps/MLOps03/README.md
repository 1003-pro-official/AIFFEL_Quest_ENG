# Day 03: Docker 컨테이너화 & GCP 클라우드 배포 & Streamlit 연동

## 📌 3일차 실습 자료
* 📓 실습 주피터 노트북: [`fsdl_day2.ipynb`](./fsdl_day2.ipynb)
* 📄 도커 빌드 파일: [`Dockerfile`](./Dockerfile)
* 📄 모델 학습 스크립트: [`train.py`](./train.py)
* 📄 FastAPI 서빙 API: [`main.py`](./main.py)
* 📦 모델 직렬화 파일: [`model.joblib`](./model.joblib)
* 📄 Streamlit 대시보드: [`app_streamlit.py`](./app_streamlit.py)
* 📄 라이브러리 목록: [`requirements.txt`](./requirements.txt)

---

## 🎯 3일차 핵심 목표
어제(2일차) 만들었던 내부망 로컬 서빙 코드를 **Docker Hub에 이미지로 패키징**하여 올리고, **GCP(Google Cloud Platform) 무료 가상머신(e2-micro)**을 대여하여 전 세계 누구나 접속 가능한 퍼블릭 API로 배포한 뒤, **Streamlit 프론트엔드 웹 앱**과 연동합니다.

---

## 🚀 1. Dockerfile 작성

```dockerfile
# 1. 베이스 이미지 설정 (가벼운 파이썬 버전)
FROM python:3.13-slim

# 2. 작업 디렉토리 설정
WORKDIR /root/mlops_serving

# 3. 필수 라이브러리 설치
RUN pip install --no-cache-dir fastapi uvicorn scikit-learn joblib python-multipart

# 4. 모델 파일과 API 코드를 컨테이너 안으로 복사
COPY main.py .
COPY model.joblib .

# 5. 서버 실행 명령 (8000 포트)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🐳 2. 로컬에서 Docker Hub 빌드 & 푸시

```bash
# 1. 도커 허브 로그인
docker login

# 2. 도커 이미지 빌드 (마침표 . 포함)
docker build -t 1003pro/iris-classifier:v1 .

# (Mac 실리콘 M1/M2/M3의 경우 GCP 호환 빌드)
# docker build --platform linux/amd64 -t 1003pro/iris-classifier:v1 .

# 3. 도커 허브로 이미지 푸시
docker push 1003pro/iris-classifier:v1
```

---

## ☁️ 3. GCP Compute Engine VM 인스턴스 생성

1. [GCP 콘솔](https://console.cloud.google.com/) 접속 ➔ **Compute Engine ➔ VM 인스턴스 ➔ 인스턴스 만들기**
2. **권장 무료 티어 설정**:
   * **리전**: `us-central1 (아이오와)` (무료 사용 지원)
   * **머신 구성**: `E2` ➔ `e2-micro` (2 vCPU, 1GB 메모리)
   * **OS & 디스크**: Ubuntu 22.04 LTS (x86_64), 표준 영구 디스크 10GB
   * **방화벽**: **`HTTP 트래픽 허용 (80 포트)` 체크 ✅**
   * ⚠️ **스냅샷 일정**: `백업 없음` (과금 방지)
3. **만들기** 클릭

---

## 💻 4. GCP VM (SSH) 접속 및 컨테이너 실행

GCP VM 목록에서 **SSH** 버튼을 눌러 브라우저 터미널 창을 엽니다.

```bash
# 1. 도커 설치
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# 2. 도커 허브에서 이미지 pull
sudo docker pull 1003pro/iris-classifier:v1

# 3. 컨테이너 백그라운드 실행 (외부 80 포트 -> 내부 8000 포트)
sudo docker run -d -p 80:8000 --name iris-api 1003pro/iris-classifier:v1

# 4. 실행 상태 확인
sudo docker ps
```

---

## 🌐 5. 배포 확인 및 Streamlit 프론트엔드 연동

1. **Swagger UI 확인**:
   * 브라우저에서 `http://[본인-VM-외부-IP]/docs` 접속 (예: `http://35.255.177.177/docs`)
   * ⚠️ 반드시 `http://`로 접속 (`https://` 아님)

2. **Streamlit 대시보드 실행 (로컬 터미널)**:
   ```bash
   streamlit run app_streamlit.py
   ```
   * 사이드바에 본인의 **GCP VM 외부 IP**를 입력하고 꽃받침/꽃잎 수치를 조절하여 예측 결과를 실시간으로 확인합니다.

---

## ⚠️ 6. 실습 종료 후 과금 방지 체크리스트
* 실습을 마치면 GCP 콘솔에서 VM 인스턴스를 **[중지(Stop)]** 또는 **[삭제(Delete)]** 합니다.
* **Compute Engine ➔ 스냅샷 ➔ 스냅샷 일정** 메뉴에서 등록된 백업 일정이 있다면 삭제합니다.
