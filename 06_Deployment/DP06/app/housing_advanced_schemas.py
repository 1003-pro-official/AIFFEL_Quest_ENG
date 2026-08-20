"""
Day 5 v2 - Pydantic V2 데이터 검증 스키마 (교차 필드 검증 적용)
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class HousingItem(BaseModel):
    """단일 주택 정보"""
    MedInc: float = Field(..., gt=0, description="중위 소득 (10,000 USD 단위)")
    HouseAge: float = Field(..., ge=0, le=100, description="주택 연식 (0~100년)")
    AveRooms: float = Field(..., gt=0, le=100, description="평균 방 수")
    AveBedrms: float = Field(..., gt=0, le=50, description="평균 침실 수")
    Population: float = Field(..., gt=0, le=100000, description="구역 인구 수")
    AveOccup: float = Field(..., gt=0, le=100, description="가구당 평균 거주 인원")
    Latitude: float = Field(..., ge=32.5, le=42.5, description="위도 (캘리포니아 영역)")
    Longitude: float = Field(..., ge=-125.0, le=-114.0, description="경도 (캘리포니아 영역)")

    @model_validator(mode="after")
    def validate_cross_fields(self):
        # 1. 침실 수가 전체 방 수보다 많을 수 없음
        if self.AveBedrms > self.AveRooms:
            raise ValueError(f"평균 침실 수(AveBedrms={self.AveBedrms})는 평균 방 수(AveRooms={self.AveRooms})보다 클 수 없습니다.")

        # 2. 인구 수와 거주 인원의 모순 체크
        if self.Population < self.AveOccup:
            raise ValueError(f"구역 총 인구(Population={self.Population})가 가구당 인원(AveOccup={self.AveOccup})보다 작을 수 없습니다.")

        return self


class HousingSingleResponse(BaseModel):
    """단건 예측 응답"""
    success: bool
    predicted_price: float
    predicted_price_usd: int
    input_features: Dict[str, Any]


class HousingBatchRequest(BaseModel):
    """배치 예측 요청"""
    items: List[HousingItem] = Field(..., max_length=1000, description="최대 1000건의 주택 목록")


class HousingBatchResponse(BaseModel):
    """배치 예측 응답"""
    success: bool
    total_count: int
    predictions: List[Dict[str, Any]]


class HousingExplainResponse(BaseModel):
    """피처 기여도 설명 응답"""
    success: bool
    predicted_price_usd: int
    feature_contributions_usd: Dict[str, int]
