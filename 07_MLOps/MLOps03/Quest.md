# [Day 03 Quest] Docker Hub 푸시, GCP VM 클라우드 배포 & Streamlit 연동

---

## 1. 퀘스트 개요 (Quest Overview)

* **퀘스트 주제**: Dockerfile 이미지 패키징, Docker Hub 원격 푸시, GCP Compute Engine VM 클라우드 배포 및 Streamlit 프론트엔드 연동
* **관련 실습 파일**: 
  * [fsdl_day2.ipynb](./fsdl_day2.ipynb)
  * [Dockerfile](./Dockerfile)
  * [main.py](./main.py)
  * [train.py](./train.py)
  * [model.joblib](./model.joblib)
  * [requirements.txt](./requirements.txt)
  * [app_streamlit.py](./app_streamlit.py)
* **핵심 목표**:
  1. 배포용 경량 베이스 이미지(`python:3.11-slim`) 기반의 `Dockerfile`을 작성하고 이미지를 빌드한다.
  2. 공용 원격 컨테이너 레지스트리인 **Docker Hub**에 로그인하고 이미지를 원격 푸시(`docker push`)한다.
  3. Google Cloud Platform(GCP) Compute Engine에서 무료 가상머신(`e2-micro`, 방화벽 HTTP 80 허용)을 생성한다.
  4. GCP VM에 도커를 설치하고 원격 이미지를 pull 받아 80번 포트로 컨테이너를 실행하여 외부 IP로 Swagger 문서를 검증한다.
  5. 파이썬 웹 프론트엔드인 `Streamlit` 대시보드를 실행하여 GCP 클라우드 API와 실시간 추론 통신을 연동한다.

---

## 2. 퀘스트 평가 루브릭 (Assessment Rubric)

| 번호 | 평가 항목 (Rubric Items) | 달성 기준 |
| :---: | :--- | :--- |
| **1** | **배포용 Dockerfile 작성 및 빌드** | `python:3.11-slim` 기반으로 코드, 모델, 의존성을 패키징하고 `uvicorn` 기동 명령어가 포함된 이미지를 정상 빌드하였는가? |
| **2** | **Docker Hub 원격 이미지 푸시** | Docker Hub 계정으로 로그인하고 태그를 부여하여 원격 저장소(`1003pro/my-ml-app:latest`)에 이미지를 푸시하였는가? |
| **3** | **GCP Compute Engine VM 인스턴스 구축** | `us-central1` 리전, `e2-micro` 사양, 방화벽 HTTP 80 포트 개방, 스냅샷 미설정 조건으로 무료 인스턴스를 생성하였는가? |
| **4** | **클라우드 컨테이너 서빙 배포** | GCP VM 내부에서 `docker run -d -p 80:8000`으로 컨테이너를 구동하고 외부 IP(`http://[VM-IP]/docs`)로 접속을 확인하였는가? |
| **5** | **Streamlit 프론트엔드 연동** | `app_streamlit.py` 대시보드에서 슬라이더 입력을 받아 GCP 외부 IP의 `/predict` API와 정상 통신하여 품종을 시각화하였는가? |

---

## 3. 세부 퀘스트 수행 내용 (Quest Details)

### [미션 1] 배포용 Dockerfile 및 의존성 패키징

```dockerfile
# Dockerfile 소스코드
FROM python:3.11-slim

# 작업 디렉터리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 및 학습된 모델 파일 복사
COPY main.py .
COPY model.joblib .

# FastAPI 기본 포트 노출
EXPOSE 8000

# 컨테이너 시작 명령어 (Uvicorn 기동)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```text
# requirements.txt
fastapi==0.115.6
uvicorn==0.34.0
scikit-learn==1.6.0
joblib==1.4.2
pydantic==2.10.4
numpy==2.2.1
```

---

### [미션 2] 로컬 이미지 빌드 및 Docker Hub 원격 푸시

```bash
# 1. 로컬에서 Docker 이미지 빌드
docker build -t 1003pro/my-ml-app:latest .

# 2. Docker Hub 로그인 (CLI 인증)
docker login -u 1003pro

# 3. 원격 레지스트리로 이미지 푸시
docker push 1003pro/my-ml-app:latest
```

* **확인**: [Docker Hub (hub.docker.com)](https://hub.docker.com/) 웹사이트에서 `1003pro/my-ml-app` 저장소에 `latest` 태그 이미지가 정상 업로드되었음을 확인했습니다.

---

### [미션 3] GCP Compute Engine VM 인스턴스 구축

```text
+-----------------------------------------------------------------------------------+
| [GCP Compute Engine VM 설정 명세]                                                 |
|                                                                                   |
|  * 인스턴스 이름: mlops-server                                                    |
|  * 리전(Region): us-central1 (아이오와 - GCP 평생 무료 티어)                      |
|  * 머신 유형: E2 -> e2-micro (2 vCPU, 1GB RAM)                                    |
|  * 부팅 디스크: Ubuntu 22.04 LTS (x86/64), 표준 영구 디스크 10GB                  |
|  * 방화벽: HTTP 트래픽 허용 (80 포트 인바운드 개방)                               |
|  * 데이터 보호: 스냅샷 일정 없음 (과금 방지)                                      |
+-----------------------------------------------------------------------------------+
```

---

### [미션 4] GCP VM 내부 컨테이너 배포 및 Swagger 문서 검증

1. **GCP VM 터미널 SSH 접속 후 도커 설치**:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io
   sudo systemctl start docker
   sudo systemctl enable docker
   ```
2. **Docker Hub 최신 이미지 다운로드 및 컨테이너 실행**:
   ```bash
   # 외부 80 포트를 컨테이너 내부 8000 포트로 포트 포워딩
   docker run -d \
     --name my-app-container \
     -p 80:8000 \
     1003pro/my-ml-app:latest
   ```
3. **배포 검증**:
   * 브라우저에서 `http://[GCP-VM-외부-IP]/docs` 로 접속하여 **FastAPI Swagger 대화형 API 문서**가 전 세계 어디서나 정상 열림을 확인했습니다.

---

### [미션 5] Streamlit 웹 대시보드 프론트엔드 연동 (`app_streamlit.py`)

```python
# app_streamlit.py 소스코드 (요약)
import streamlit as st
import requests

st.set_page_config(page_title="Iris MLOps Classifier", layout="centered")
st.title("Iris Species Classification Dashboard")
st.write("GCP Cloud VM Serving API와 실시간으로 통신하는 프론트엔드 대시보드입니다.")

# 1. 사이드바에서 GCP 외부 IP 입력 (기본값 설정)
api_host = st.sidebar.text_input("GCP VM Public IP", value="35.255.177.177")
api_url = f"http://{api_host}/predict"

# 2. 사용자 피처 입력 슬라이더
st.subheader("Input Flower Features")
col1, col2 = st.columns(2)
with col1:
    sepal_len = st.slider("Sepal Length (cm)", 4.0, 8.0, 5.1, 0.1)
    petal_len = st.slider("Petal Length (cm)", 1.0, 7.0, 1.4, 0.1)
with col2:
    sepal_width = st.slider("Sepal Width (cm)", 2.0, 5.0, 3.5, 0.1)
    petal_width = st.slider("Petal Width (cm)", 0.1, 3.0, 0.2, 0.1)

# 3. 예측 요청 버튼
if st.button("Predict Species"):
    payload = {
        "sepal_length": sepal_len,
        "sepal_width": sepal_width,
        "petal_length": petal_len,
        "petal_width": petal_width
    }
    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            st.success(f"Predicted Species: {res_data['prediction_label'].upper()}")
            st.write("Prediction Probabilities:", res_data["probabilities"])
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Connection Failed: {e}")
```

```bash
# 로컬에서 Streamlit 실행
streamlit run app_streamlit.py
```

* **동작 검증**: `http://localhost:8501`에서 슬라이더를 움직여 `Predict Species`를 클릭했을 때, GCP VM에 배포된 백엔드 서버로부터 `SETOSA` 분류 결과와 확률 벡터를 정상적으로 수신하여 화면에 렌더링함을 확인했습니다.

---

## 4. 전체 엔드투엔드 서빙 아키텍처 다이어그램

```text
[개발자 로컬 환경]
  1. Dockerfile 작성
  2. docker build -t 1003pro/my-ml-app:latest
  3. docker push ───────────────────────────────────> [Docker Hub 레지스트리]
                                                               │
[GCP 클라우드 서버 (mlops-server)]                             │
  4. SSH 접속 & docker pull <─────────────────────────────────┘
  5. docker run -d -p 80:8000 (FastAPI Uvicorn 컨테이너 기동)
       │
       ▼ (외부 80 포트 개방)
  6. http://[GCP-VM-IP]/docs (퍼블릭 Swagger API 서빙)
       ▲
       │ HTTP POST /predict (실시간 요청)
       │
[사용자 프론트엔드 대시보드]
  7. Streamlit App (http://localhost:8501)
```

---

## 5. 퀘스트 결론 및 핵심 요약 (Summary)

* 로컬 환경에 갇혀 있던 머신러닝 모델을 `Dockerfile`로 독립 패키징하고 `Docker Hub`에 배포함으로써 전 세계 어디서든 배포 가능한 표준 이미지를 확보했습니다.
* Google Cloud Platform의 무료 `e2-micro` 인스턴스를 프로비저닝하고 80번 포트로 컨테이너를 구동하여, 실제 상용 웹 서비스처럼 동작하는 퍼블릭 서빙 인프라를 완성했습니다.
* `Streamlit` 프론트엔드와 `FastAPI` 클라우드 백엔드를 RESTful 통신으로 연동하여, 사용자가 브라우저에서 실시간으로 머신러닝 예측을 수행할 수 있는 엔드투엔드 MLOps 파이프라인을 성공적으로 구축했습니다.
