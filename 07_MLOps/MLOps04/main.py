from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np

app = FastAPI(
    title="Iris Classifier API",
    description="MLOps Serving API using FastAPI and Scikit-Learn",
    version="1.0.0"
)

# 1. 모델 로드
model = joblib.load("model.joblib")

# 2. 요청 바디 스키마 정의
class IrisInput(BaseModel):
    data: list[float]  # [sepal_length, sepal_width, petal_length, petal_width]

@app.get("/")
def read_root():
    return {"message": "Iris Classifier API is running!"}

@app.post("/predict")
def predict(input_data: IrisInput):
    # 2D 배열로 변환 (shape: (1, 4))
    features = np.array(input_data.data).reshape(1, -1)
    
    # 예측 수행
    prediction = model.predict(features)
    class_index = int(prediction[0])
    
    target_names = ["setosa", "versicolor", "virginica"]
    class_name = target_names[class_index] if class_index < len(target_names) else "unknown"
    
    return {
        "class_index": class_index,
        "class_name": class_name
    }
