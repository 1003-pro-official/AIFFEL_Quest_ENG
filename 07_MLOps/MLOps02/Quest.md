# [Day 02 Quest] Docker 환경 격리, 모델 직렬화 & FastAPI 로컬 서빙

---

## 1. 퀘스트 개요 (Quest Overview)

* **퀘스트 주제**: Docker 컨테이너 기반 개발 환경 격리, 붓꽃(Iris) 모델 학습/직렬화 및 FastAPI 로컬 서빙 구축
* **관련 실습 파일**: 
  * [fsdl_day1.ipynb](./fsdl_day1.ipynb)
  * [train.py](./train.py)
  * [main.py](./main.py)
  * [model.joblib](./model.joblib)
* **핵심 목표**:
  1. Docker 볼륨 마운트(`-v`)를 활용하여 로컬 파일 시스템과 실시간 동기화되는 독립 개발 컨테이너(`my_test_space`)를 구축한다.
  2. Scikit-learn으로 붓꽃(Iris) 3개 품종 분류 모델(`RandomForestClassifier`)을 학습시키고 `joblib`으로 직렬화 파일(`model.joblib`)을 생성한다.
  3. `FastAPI` 프레임워크와 Pydantic 데이터 검증 모델을 기반으로 예측 엔드포인트(`POST /predict`)를 개발한다.
  4. `uvicorn` 웹 서버를 8000번 포트로 기동하고 Swagger UI(`/docs`)를 통해 실시간 서빙 동작을 검증한다.

---

## 2. 퀘스트 평가 루브릭 (Assessment Rubric)

| 번호 | 평가 항목 (Rubric Items) | 달성 기준 |
| :---: | :--- | :--- |
| **1** | **Docker 볼륨 마운트 격리 환경 구축** | `-v` 옵션을 활용하여 로컬 소스코드가 컨테이너 내부(`/root/mlops_serving`)에 안전하게 마운트된 개발 환경을 생성하였는가? |
| **2** | **모델 학습 및 바이너리 직렬화** | 붓꽃 데이터셋을 분할 학습하고, `joblib.dump()`를 통해 모델 가중치를 `model.joblib` 파일로 올바르게 저장하였는가? |
| **3** | **FastAPI 서빙 API 엔드포인트 개발** | Pydantic 스키마(`PredictRequest`)로 입력을 검증하고 모델 추론 결과를 JSON으로 반환하는 API 코드를 작성하였는가? |
| **4** | **로컬 서빙 검증 및 Swagger UI 테스트** | `uvicorn` 서버 기동 후 `http://localhost:8000/docs`에서 실제 입력값에 대한 예측 품종(Setosa, Versicolour, Virginica)을 정상 수신하였는가? |

---

## 3. 세부 퀘스트 수행 내용 (Quest Details)

### [미션 1] Docker 컨테이너 볼륨 마운트 개발 환경 구축

* **볼륨 마운트(Volume Mount)의 필요성**:
  * 컨테이너는 기본적으로 종료 시 내부 데이터가 사라지는 휘발성(Stateless) 특성을 가집니다.
  * `-v` (Volume) 옵션을 통해 로컬 호스트의 작업 폴더를 컨테이너 내부 디렉터리에 연결하면, 로컬에서 편집한 코드가 컨테이너 내부에 즉시 반영되고 컨테이너에서 생성된 모델 파일도 로컬에 영구 보존됩니다.

```bash
# 1. Docker 실행 및 로컬 작업 폴더 볼륨 마운트
docker run -it \
  --name my_test_space \
  -v "$(pwd):/root/mlops_serving" \
  -w /root/mlops_serving \
  python:3.11-slim \
  bash

# 2. 필수 의존성 패키지 설치
pip install scikit-learn fastapi uvicorn pydantic joblib
```

---

### [미션 2] 머신러닝 모델 학습 및 파일 직렬화 (`train.py`)

* **붓꽃(Iris) 데이터셋 구조**:
  * 4개 입력 피처: `sepal length (꽃받침 길이)`, `sepal width (꽃받침 너비)`, `petal length (꽃잎 길이)`, `petal width (꽃잎 너비)`
  * 3개 출력 타깃: `0: Setosa`, `1: Versicolour`, `2: Virginica`
* **직렬화(Serialization)**:
  * 메모리 상에 존재하는 학습된 모델 객체를 영구 파일 형태(`model.joblib`)로 변환하여 디스크에 저장합니다.

```python
# train.py 소스코드
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

# 1. 데이터셋 로드 및 분할
iris = load_iris()
X, y = iris.data, iris.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 2. RandomForestClassifier 모델 학습
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 3. 모델 평가
preds = model.predict(X_test)
acc = accuracy_score(y_test, preds)
print(f"Model Accuracy: {acc * 100:.2f}%")

# 4. 모델 직렬화 저장
joblib.dump(model, "model.joblib")
print("Model serialized to model.joblib successfully!")
```

---

### [미션 3] FastAPI 기반 REST API 서빙 엔드포인트 구현 (`main.py`)

* **FastAPI 프레임워크 선정 이유**:
  * 비동기 처리(ASGI) 지원으로 초당 처리량(Throughput)이 매우 높음
  * Pydantic 기반의 자동 데이터 유효성 검사 및 타입 힌트 제공
  * 코드 작성만으로 OpenAPI 기반의 대화형 Swagger 문서(`/docs`) 자동 생성

```python
# main.py 소스코드
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np

# 1. FastAPI 인스턴스 초기화
app = FastAPI(
    title="Iris Classifier API",
    description="MLOps Serving API using FastAPI and Scikit-Learn",
    version="1.0.0"
)

# 2. 직렬화된 모델 파일 로드
try:
    model = joblib.load("model.joblib")
    target_names = ["setosa", "versicolor", "virginica"]
except Exception as e:
    model = None

# 3. Pydantic 입력 스키마 정의
class IrisInput(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# 4. 엔드포인트 정의
@app.get("/")
def read_root():
    return {"message": "Iris Classification Serving API is running!"}

@app.post("/predict")
def predict(data: IrisInput):
    if model is None:
        raise HTTPException(status_code=500, detail="Model is not loaded.")
    
    # 2차원 배열 형태로 변환 후 추론
    features = np.array([[data.sepal_length, data.sepal_width, data.petal_length, data.petal_width]])
    prediction = int(model.predict(features)[0])
    probabilities = model.predict_proba(features)[0].tolist()
    
    return {
        "prediction_index": prediction,
        "prediction_label": target_names[prediction],
        "probabilities": probabilities
    }
```

---

### [미션 4] Uvicorn 서버 기동 및 Swagger UI 테스트

```text
[클라이언트 / Swagger UI] ──── HTTP POST /predict ────> [Uvicorn ASGI Server]
                                                            │
                                                            ▼
                                                     [FastAPI / Pydantic]
                                                     (입력 데이터 유효성 검증)
                                                            │
                                                            ▼
                                                     [model.joblib 로드]
                                                     (RandomForest 추론 수행)
                                                            │
                                                            ▼
[예측 결과 JSON 응답]   <─── {"prediction_label": "setosa"} ─┘
```

1. **Uvicorn 서버 실행**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Swagger UI 접속**: 브라우저에서 `http://localhost:8000/docs` 열기
3. **추론 요청 테스트**:
   * **Request Body**:
     ```json
     {
       "sepal_length": 5.1,
       "sepal_width": 3.5,
       "petal_length": 1.4,
       "petal_width": 0.2
     }
     ```
   * **Response Body (200 OK)**:
     ```json
     {
       "prediction_index": 0,
       "prediction_label": "setosa",
       "probabilities": [1.0, 0.0, 0.0]
     }
     ```

---

## 4. 퀘스트 결론 및 핵심 요약 (Summary)

* Docker 볼륨 마운트(`-v`)를 통해 컨테이너의 격리성(Isolation)과 로컬 파일 수정의 편리성(Flexibility)을 동시에 확보한 MLOps 개발 환경을 정립했습니다.
* 학습된 머신러닝 모델을 파일(`model.joblib`)로 직렬화하여, 학습 파이프라인과 서빙 파이프라인을 완전히 분리할 수 있는 아키텍처 기반을 마련했습니다.
* FastAPI와 Uvicorn을 활용하여 경량화되고 안전한 실시간 머신러닝 추론 REST API 서버를 로컬 환경에 성공적으로 구축 및 검증했습니다.
