"""
Day 5 v2 - 고급 주택 가격 예측 FastAPI 서버
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from app.housing_advanced_schemas import (
    HousingItem, HousingSingleResponse,
    HousingBatchRequest, HousingBatchResponse,
    HousingExplainResponse
)
from app.housing_advanced_model import HousingAdvancedPredictor
from app.logger_config import setup_logger
from app.error_handlers import register_error_handlers
from app.middleware import RequestLoggingMiddleware

logger = setup_logger("housing_advanced_api")
predictor: HousingAdvancedPredictor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    logger.info("🚀 [Lifespan] LightGBM 고급 주택 가격 모델 파이프라인 로드 중...")
    predictor = HousingAdvancedPredictor()
    logger.info("✅ [Lifespan] 모델 로드 완료")
    yield
    logger.info("🛑 [Lifespan] 서버 종료")

app = FastAPI(
    title="California Housing Price Prediction API (v2 Advanced)",
    description="LightGBM GBDT 파이프라인 기반 고성능 주택 가격 예측 & XAI API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(RequestLoggingMiddleware)
register_error_handlers(app)


@app.get("/health", tags=["System"])
async def health_check():
    """서버 및 모델 헬스체크"""
    return {
        "status": "healthy" if predictor is not None else "loading",
        "model_type": "LightGBM TransformedTargetRegressor Pipeline",
        "version": "2.0.0"
    }


@app.post("/predict", response_model=HousingSingleResponse, tags=["Prediction"])
async def predict_single(request: HousingItem):
    """단건 주택 가격 예측"""
    if predictor is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")

    data_dict = request.model_dump()
    result = predictor.predict(data_dict)

    return HousingSingleResponse(
        success=True,
        predicted_price=result["predicted_price"],
        predicted_price_usd=result["predicted_price_usd"],
        input_features=data_dict
    )


@app.post("/predict/batch", response_model=HousingBatchResponse, tags=["Prediction"])
async def predict_batch(request: HousingBatchRequest):
    """대량(배치) 주택 가격 예측"""
    if predictor is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")

    items = [item.model_dump() for item in request.items]
    predictions = predictor.predict_batch(items)

    return HousingBatchResponse(
        success=True,
        total_count=len(predictions),
        predictions=predictions
    )


@app.post("/explain", response_model=HousingExplainResponse, tags=["Explainability"])
async def explain_prediction(request: HousingItem):
    """피처별 가격 기여도(XAI) 분석"""
    if predictor is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")

    data_dict = request.model_dump()
    explanation = predictor.explain(data_dict)

    return HousingExplainResponse(
        success=True,
        predicted_price_usd=explanation["predicted_price_usd"],
        feature_contributions_usd=explanation["feature_contributions_usd"]
    )
