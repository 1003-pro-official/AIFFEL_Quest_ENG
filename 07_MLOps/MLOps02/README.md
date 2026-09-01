# Day 02: Docker 컨테이너 환경 구축 & FastAPI 로컬 모델 서빙

> **2일차 목표**: Docker를 이용해 로컬 개발 환경과 완전히 격리된 독립 컨테이너를 만들고 볼륨 마운트로 코드를 공유하며, Scikit-learn 머신러닝 모델을 학습·직렬화한 뒤 FastAPI를 이용해 로컬 REST API로 서빙합니다.

---

## 📌 2일차 실습 자료 및 파일 매핑
* 📓 **실습 주피터 노트북**: [`fsdl_day1.ipynb`](./fsdl_day1.ipynb)
* 📄 **모델 학습 스크립트**: [`train.py`](./train.py)
* 📄 **FastAPI 서빙 API**: [`main.py`](./main.py)
* 📦 **직렬화된 모델 파일**: [`model.joblib`](./model.joblib)

---

## 💡 1. WHY Docker인가? (도커를 쓰는 이유)

* **독립 환경 생성 편의성**: `conda`나 `venv` 같은 파이썬 가상환경은 파이썬 패키지만 격리할 뿐 OS 수준의 C 라이브러리, 시스템 환경변수, 런타임 버전까지 격리하지 못합니다. Docker는 OS 수준에서 완전히 독립된 환경을 제공하는 **가상환경의 완벽한 상위 호환**입니다.
* **환경 공유의 편의성**: "내 컴퓨터에서는 잘 돌아가는데 다른 컴퓨터나 서버에서는 에러가 나요"라는 고질적인 환경 불일치 문제를 해결합니다.
* 🎥 [참고 영상: 개발바닥을 완전히 바꿔버린 도커 (YouTube)](https://www.youtube.com/watch?v=e0koWWAmXSk)

---

## 🛠️ 2. 도커 설치 및 기본 동작 확인

터미널(VSCode 터미널 또는 WSL)에서 도커가 정상 동작하는지 확인합니다.

```bash
# 1. 도커 설치 확인
docker help
docker ps -a

# 2. 기본 이미지 다운로드 및 실행 테스트
docker run hello-world
docker ps -a
```

* `docker run hello-world` 실행 시 `Hello from Docker!` 메시지가 출력되면 도커 엔진이 정상 작동하는 것입니다.
* 이름을 지정하지 않으면 Docker가 임의로 형용사_이름 형태(예: `elastic_johnson`)의 컨테이너 이름을 자동 생성합니다.

---

## 🚀 3. 실습 컨테이너 생성 및 로컬 볼륨 마운트

로컬 작업 폴더와 컨테이너 내부를 연결(**볼륨 마운트**)하여, 로컬에서 코드를 수정해도 컨테이너 내부에 즉시 반영되도록 환경을 구성합니다.

```bash
# 1. 작업 폴더 생성 및 이동
mkdir -p mlops_serving
cd mlops_serving

# 2. 도커 컨테이너 생성 및 인터랙티브 bash 진입
docker run -it --name my_test_space \
  -v "$(pwd):/root/mlops_serving" \
  -w /root/mlops_serving \
  -p 8000:8000 \
  python:3.13-slim /bin/bash
```

### 🔍 옵션 상세 분석

| 옵션 | 설명 |
| :--- | :--- |
| **`-it`** | Interactive(`-i`) + TTY(`-t`): 컨테이너 표준 입출력을 유지하여 내부 bash 터미널을 직접 조작 |
| **`--name my_test_space`** | 생성할 컨테이너의 이름을 `my_test_space`로 지정 |
| **`-v "$(pwd):/root/mlops_serving"`** | **볼륨 마운트**: 내 로컬 현재 경로(`$(pwd)`)와 컨테이너 내부 경로를 실시간 동기화 |
| **`-w /root/mlops_serving`** | 컨테이너 시작 시 기본 작업 디렉토리(Working Directory) 설정 |
| **`-p 8000:8000`** | **포트 포워딩**: 로컬 컴퓨터의 `8000`번 포트 요청을 컨테이너 내부 `8000`번 포트로 전달 |
| **`python:3.13-slim`** | 베이스로 사용할 경량 파이썬 공식 도커 이미지 |
| **`/bin/bash`** | 컨테이너 진입 시 실행할 기본 셸 |

> 💡 **VSCode 확장 팁**: VSCode에서 `Dev Containers` 또는 `Remote - Containers` 확장을 설치하면 컨테이너 내부 환경에 VSCode 에디터를 직접 연결하여 작업할 수 있습니다.

---

## 📦 4. 컨테이너 내부 필수 라이브러리 설치

컨테이너 내부 bash 터미널(`root@...:/root/mlops_serving#`)에서 다음 명령어를 실행합니다:

```bash
pip install --upgrade pip
pip install fastapi uvicorn scikit-learn joblib python-multipart
```

* **`scikit-learn`**: 붓꽃 품종 분류 모델 학습
* **`joblib`**: 학습된 모델 객체를 디스크 파일(`model.joblib`)로 직렬화/역직렬화
* **`fastapi`**: 고성능 비동기 REST API 프레임워크
* **`uvicorn`**: FastAPI 애플리케이션을 구동하는 경량 ASGI 웹 서버
* **`python-multipart`**: 폼 데이터 및 멀티파트 요청 처리 지원

---

## 🌲 5. 모델 학습 및 직렬화 (`train.py` / `test.ipynb`)

RandomForestClassifier 알고리즘을 사용하여 붓꽃(Iris) 데이터셋을 학습하고 `model.joblib` 파일로 저장합니다.

```python
import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier

# 1. 데이터셋 로드
iris = load_iris()
X, y = iris.data, iris.target

# 2. 랜덤 포레스트 분류기 학습
model = RandomForestClassifier(n_estimators=10, random_state=42)
model.fit(X, y)

# 3. 모델 파일로 직렬화 저장
joblib.dump(model, 'model.joblib')
print("Model saved successfully to model.joblib!")
```

실행:
```bash
python train.py
```
* 로컬 폴더와 컨테이너 내부 모두에 `model.joblib` 파일이 생성됩니다.

---

## 🌐 6. FastAPI 서빙 API 구현 (`main.py`)

저장된 모델을 메모리에 로드하고, 클라이언트가 HTTP POST 요청으로 꽃의 수치를 보냈을 때 예측 결과를 반환하는 API 서버를 작성합니다.

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import joblib

app = FastAPI(
    title="Iris Model Serving API",
    description="2일차 로컬 모델 서빙 FastAPI 서버",
    version="1.0.0"
)

# 1. 직렬화된 모델 로드
model = joblib.load('model.joblib')

# 2. 요청 바디 데이터 검증 스키마 정의 (Pydantic)
class PredictRequest(BaseModel):
    data: List[float]  # [sepal_length, sepal_width, petal_length, petal_width]

@app.get("/")
def root():
    return {"message": "Iris Serving API is running!"}

@app.post("/predict")
def predict(request: PredictRequest):
    # 2D 배열 형태로 변환 후 예측 수행
    prediction = model.predict([request.data])
    class_index = int(prediction[0])
    
    target_names = ["setosa", "versicolor", "virginica"]
    class_name = target_names[class_index] if class_index < len(target_names) else "unknown"
    
    return {
        "class_index": class_index,
        "class_name": class_name
    }
```

---

## 🧪 7. 로컬 서버 구동 및 Swagger UI 테스트

컨테이너 내부 터미널에서 Uvicorn 서버를 실행합니다:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 🌐 브라우저에서 확인
1. 로컬 컴퓨터 브라우저에서 **`http://127.0.0.1:8000/docs`** (또는 `http://localhost:8000/docs`) 접속
2. **`POST /predict`** 클릭 ➔ **[Try it out]** 클릭
3. 요청 바디에 아래 JSON 입력 후 **[Execute]** 클릭:
   ```json
   {
     "data": [5.1, 3.5, 1.4, 0.2]
   }
   ```
4. **Server response (200)** 에 `class_index: 0`, `class_name: "setosa"` 응답이 오는지 확인합니다.

---

## 🧹 부록: 실습 컨테이너 및 이미지 정리 명령어

실습이 끝난 후 컨테이너를 정리하고 초기화하고 싶을 때 사용합니다:

```bash
# 1. 실행 중인 모든 컨테이너 목록 확인
docker ps -a

# 2. 생성했던 컨테이너 강제 삭제 (-f: 실행 중이어도 강제 삭제)
docker rm -f my_test_space

# 3. 도커 이미지 목록 확인 및 삭제
docker images
docker rmi python:3.13-slim
```
