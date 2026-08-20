"""
Day 5 v2 - 캘리포니아 주택 가격 최적화 추론 및 피처 엔지니어링 모듈
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# 캘리포니아 주요 5대 거점 경제권 도시 좌표 (위도, 경도)
SF_COORD = (37.7749, -122.4194)   # San Francisco (샌프란시스코)
SJ_COORD = (37.3382, -121.8863)   # San Jose (실리콘밸리 중심 산호세)
LA_COORD = (34.0522, -118.2437)   # Los Angeles (로스앤젤레스)
SD_COORD = (32.7157, -117.1611)   # San Diego (샌디에이고)
SAC_COORD = (38.5816, -121.4944)  # Sacramento (캘리포니아 주도 새크라멘토)


class HousingFeatureEngineer(BaseEstimator, TransformerMixin):
    """부동산 도메인 파생 변수 생성기 (학습 & 직렬화 & 서빙 공용)"""
    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_out = X.copy()
        if isinstance(X_out, np.ndarray):
            cols = ["MedInc", "HouseAge", "AveRooms", "AveBedrms", "Population", "AveOccup", "Latitude", "Longitude"]
            X_out = pd.DataFrame(X_out, columns=cols[:X_out.shape[1]])

        # 1. 방 대비 침실 비율 & 1인당 방 수
        X_out["BedroomsPerRoom"] = X_out["AveBedrms"] / (X_out["AveRooms"] + 1e-6)
        X_out["RoomsPerPerson"] = X_out["AveRooms"] / (X_out["AveOccup"] + 1e-6)
        X_out["MedIncPerPerson"] = X_out["MedInc"] / (X_out["AveOccup"] + 1e-6)

        # 2. 5대 주요 경제 거점 도시와의 유클리드 거리 (Spatial Proximity)
        X_out["DistToSF"] = np.sqrt((X_out["Latitude"] - SF_COORD[0])**2 + (X_out["Longitude"] - SF_COORD[1])**2)
        X_out["DistToSJ"] = np.sqrt((X_out["Latitude"] - SJ_COORD[0])**2 + (X_out["Longitude"] - SJ_COORD[1])**2)
        X_out["DistToLA"] = np.sqrt((X_out["Latitude"] - LA_COORD[0])**2 + (X_out["Longitude"] - LA_COORD[1])**2)
        X_out["DistToSD"] = np.sqrt((X_out["Latitude"] - SD_COORD[0])**2 + (X_out["Longitude"] - SD_COORD[1])**2)
        X_out["DistToSAC"] = np.sqrt((X_out["Latitude"] - SAC_COORD[0])**2 + (X_out["Longitude"] - SAC_COORD[1])**2)

        # 3. 가장 가까운 대도시까지의 거리
        X_out["DistToMinCity"] = X_out[["DistToSF", "DistToSJ", "DistToLA", "DistToSD", "DistToSAC"]].min(axis=1)

        return X_out


class HousingAdvancedPredictor:
    """통합 Scikit-Learn 파이프라인 기반 추론 및 설명 모듈"""

    def __init__(self, model_path: str = "models/housing_advanced_pipeline.joblib"):
        self.pipeline = joblib.load(model_path)
        self.feature_names = [
            "MedInc", "HouseAge", "AveRooms", "AveBedrms",
            "Population", "AveOccup", "Latitude", "Longitude"
        ]

    def predict(self, features: dict) -> dict:
        """단건 예측"""
        df_input = pd.DataFrame([features])[self.feature_names]
        pred_val = float(self.pipeline.predict(df_input)[0])
        pred_val = max(0.0, pred_val)

        return {
            "predicted_price": round(pred_val, 4),
            "predicted_price_usd": int(pred_val * 100000),
        }

    def predict_batch(self, items: list[dict]) -> list[dict]:
        """다건(배치) 예측"""
        df_input = pd.DataFrame(items)[self.feature_names]
        preds = self.pipeline.predict(df_input)
        preds = np.clip(preds, 0.0, None)

        results = []
        for p in preds:
            val = float(p)
            results.append({
                "predicted_price": round(val, 4),
                "predicted_price_usd": int(val * 100000)
            })
        return results

    def explain(self, features: dict) -> dict:
        """피처별 가격 기여도 간이 분석 (Base 대비 증감분 $)"""
        df_input = pd.DataFrame([features])[self.feature_names]
        base_pred = float(self.pipeline.predict(df_input)[0])

        baseline = {
            "MedInc": 3.87, "HouseAge": 28.6, "AveRooms": 5.43, "AveBedrms": 1.10,
            "Population": 1425.0, "AveOccup": 3.07, "Latitude": 35.63, "Longitude": -119.57
        }

        contributions = {}
        for col in self.feature_names:
            df_temp = df_input.copy()
            df_temp[col] = baseline[col]
            pred_without = float(self.pipeline.predict(df_temp)[0])
            diff_usd = int((base_pred - pred_without) * 100000)
            contributions[col] = diff_usd

        return {
            "predicted_price_usd": int(base_pred * 100000),
            "feature_contributions_usd": contributions
        }
