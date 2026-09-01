# [Day 06 Quest] PyTorch BERT 파인튜닝, TorchServe 모델 서빙 & Vertex AI

---

## 1. 퀘스트 개요 (Quest Overview)

* **퀘스트 주제**: 자연어 처리(NLP) BERT 모델 파인튜닝, TorchServe 전후처리 핸들러 기반 `.mar` 아카이빙 패키징, 5000번 포트 실시간 추론 서버 배포 및 Google Cloud Vertex AI 엔터프라이즈 MLOps 아키텍처 분석
* **관련 교안**: 「모두를 위한 MLOps」 17강 ~ 18강
* **관련 실습 파일**: 
  * [3_PyTorch_model_serving.ipynb](./3_PyTorch_model_serving.ipynb)
  * [README.md](./README.md)
* **핵심 목표**:
  1. 사전학습된 **BERT** 모델을 AG News 4분류 데이터셋으로 파인튜닝하고, 손실 곡선, 테스트셋 정확도(85%+), 혼동 행렬(Confusion Matrix)로 다각도 평가한다.
  2. 순수 가중치(`.pth`)의 서빙 한계를 이해하고, **TorchServe 4단계 생명주기(`initialize` -> `preprocess` -> `inference` -> `postprocess`)**를 구현한 `model_handler.py`를 작성한다.
  3. `torch-model-archiver` 도구로 가중치, 아키텍처, 핸들러, 설정을 단일 압축 파일인 **`.mar` (Model Archive)**로 패키징한다.
  4. TorchServe 추론 서버를 5000번 포트로 백그라운드 기동하고 `/ping` 헬스체크 및 `/predictions/bert_news_classification` 실시간 예측 REST API를 검증한다.
  5. 노트북 수동 파이프라인의 한계를 진단하고, **Google Cloud Vertex AI**의 5대 핵심 MLOps 컴포넌트 구조를 체계적으로 분석한다.

---

## 2. 퀘스트 평가 루브릭 (Assessment Rubric)

| 번호 | 평가 항목 (Rubric Items) | 달성 기준 |
| :---: | :--- | :--- |
| **1** | **BERT 4분류 모델 파인튜닝 및 평가** | AG News 데이터셋으로 T4 GPU 환경에서 3 Epochs 학습을 완료하고, 손실 감소 추이와 85% 안팎의 정확도를 달성하였는가? |
| **2** | **TorchServe 커스텀 핸들러 작성** | `BaseHandler`를 상속하여 모델 초기화, JSON 텍스트 추출/토큰화, Logits 연산, Softmax 확률 반환 4단계를 구현하였는가? |
| **3** | **배포용 `.mar` 아카이브 패키징** | `torch-model-archiver` 명령어를 통해 `.pth` 가중치와 핸들러, 설정 파일을 묶은 `bert_news_classification.mar`을 생성하였는가? |
| **4** | **TorchServe 추론 서버 기동 및 API 검증** | 5000번 포트로 서버를 기동하고 `/ping` (Healthy) 및 3종 기사 JSON에 대해 올바른 카테고리 레이블과 확률을 반환받았는가? |
| **5** | **Vertex AI 엔터프라이즈 플랫폼 분석** | 수동 파이프라인의 5대 한계와 Vertex AI의 Training, Model Registry, Prediction, Feature Store, Pipeline 대응 구조를 정립하였는가? |

---

## 3. 세부 퀘스트 수행 내용 (Quest Details)

### [미션 1] BERT 파인튜닝 & 다각도 모델 평가

* **AG News 4분류 문제 정의**:
  * `0: World (시사/세계)`, `1: Sports (스포츠)`, `2: Business (경제)`, `3: Sci/Tech (기술·과학)`
* **사전학습 BERT 아키텍처**:
  * `BertTokenizer (bert-base-uncased)`: 영문 텍스트를 의미론적 최소 단위(Subword)로 분절하고 정수 `input_ids` 및 `attention_mask` 생성
  * `BertForSequenceClassification`: 사전학습된 Transformer 인코더 가중치를 재사용하고 4-way Linear Classification Head를 새로 얹어 파인튜닝
  * `AdamW (lr=5e-5)` 및 `CrossEntropyLoss` 적용
* **학습 및 평가 결과**:
  * **손실 곡선 (Loss Curve)**: 에폭 1 (0.63) -> 에폭 2 (0.29) -> 에폭 3 (0.15) 로 안정적 수렴 확인
  * **테스트셋 정확도**: 1,200건의 짧은 학습만으로도 **85.25%**의 높은 정확도 달성
  * **단건 기사 추론 검증**: 축구 감독 사임 기사에 대해 `Logits` -> `Softmax` -> `Argmax`를 거쳐 `1: Sports` 정확 분류
  * **혼동 행렬 (Confusion Matrix)**: 대각선(정답) 칸의 예측 빈도가 가장 높음을 히트맵으로 시각화 검증

---

### [미션 2] 왜 `.pth` 파일만으로는 서빙할 수 없는가? (모델 아카이빙)

* **`.pth` 가중치 파일의 한계**:
  * `model.state_dict()`는 수치 파라미터만 담고 있어, 모델의 아키텍처 형태나 텍스트를 토큰화하고 결과를 가공하는 전후처리 로직이 전혀 들어있지 않습니다.
* **`.mar` (Model Archive) 패키지**:
  * **[가중치(`.pth`) + 모델 아키텍처 + 전후처리 파이썬 핸들러(`model_handler.py`) + 설정 파일(`config.properties`) + 부속 토큰 사전(`vocab.txt`)]**을 하나로 압축 묶음한 최종 배포 형상입니다.

```text
[TorchServe 핸들러 4단계 생명주기 (model_handler.py)]

  1. initialize()   : 서버 기동 시 1회 호출 -> 토크나이저 로드, 가중치 주입, GPU 할당, eval() 전환
        │
        ▼
  2. preprocess()   : HTTP POST 요청마다 -> JSON 본문 텍스트 추출, BERT 토크나이징, GPU 텐서 변환
        │
        ▼
  3. inference()    : 추론 실행 -> with torch.no_grad() 환경에서 모델 순전파 및 Logits 계산
        │
        ▼
  4. postprocess()  : 후처리 -> Softmax 확률 변환 후 최고 확률 레이블 번호와 확률값 JSON 반환
```

---

### [미션 3] TorchServe 핸들러 및 `.mar` 패키징 코드

```python
# model_handler.py 소스코드 (요약)
import json
import torch
from ts.context import Context
from ts.torch_handler.base_handler import BaseHandler
from transformers import BertTokenizer, BertForSequenceClassification

class ModelHandler(BaseHandler):
    def __init__(self):
        self.initialized = False
        self.tokenizer = None
        self.model = None

    def initialize(self, context: Context):
        self.initialized = True
        self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        self.model = BertForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=4)
        self.model.load_state_dict(torch.load("bert_news_classification_model.pth", map_location="cpu"))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    def preprocess(self, data: list[dict]):
        model_input_texts = []
        for item in data:
            body = item.get("data") or item.get("body")
            if isinstance(body, (bytes, bytearray)):
                body = body.decode("utf-8")
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except:
                    pass
            if isinstance(body, dict) and "data" in body:
                model_input_texts.extend(body["data"])
            elif isinstance(body, list):
                model_input_texts.extend(body)
            elif isinstance(body, str):
                model_input_texts.append(body)

        inputs = self.tokenizer(model_input_texts, truncation=True, padding=True, max_length=512, return_tensors="pt")
        return inputs.to(self.device)

    def inference(self, input_batch):
        with torch.no_grad():
            outputs = self.model(**input_batch)
        return outputs.logits

    def postprocess(self, inference_output):
        probabilities = torch.nn.functional.softmax(inference_output, dim=1)
        results = []
        for prob in probabilities:
            label_idx = int(torch.argmax(prob))
            results.append({
                "label": label_idx,
                "probability": float(prob.max().item())
            })
        return results
```

```bash
# .mar 파일 패키징 CLI 명령어
torch-model-archiver \
  --model-name bert_news_classification \
  --version 1.0 \
  --serialized-file bert_news_classification_model.pth \
  --handler ./model_handler.py \
  --extra-files "bert-base-uncased-vocab.txt" \
  --export-path model-store \
  -f
```

---

### [미션 4] TorchServe 추론 서버 기동 및 실시간 REST API 검증

```bash
# 1. 포트 설정 파일 (config.properties)
# inference_address=http://0.0.0.0:5000 (추론)
# management_address=http://0.0.0.0:5001 (관리)
# metrics_address=http://0.0.0.0:5002 (메트릭)

# 2. 서버 백그라운드 기동
torchserve --start --ncs \
  --ts-config config.properties \
  --model-store model-store \
  --models bert_news_classification=bert_news_classification.mar \
  --disable-token-auth

# 3. 헬스체크 엔드포인트 호출
curl -X GET http://localhost:5000/ping
# 응답: {"status": "Healthy"}
```

```text
[실시간 뉴스 분류 API 호출 검증 결과]

1. 스포츠 기사 요청:
   Request: {"data": ["Bleary-eyed from 16 hours on a Greyhound bus, he strolled into the baseball stadium..."]}
   Response: [{"label": 1, "probability": 0.9878}] -> [Sports: 1] 정답 판정

2. 비즈니스 기사 요청:
   Request: {"data": ["DETROIT — Automotive stocks surged as Wall Street reported record quarterly profits..."]}
   Response: [{"label": 2, "probability": 0.8747}] -> [Business: 2] 정답 판정

3. 기술 기사 요청:
   Request: {"data": ["OpenVoice comprises two AI models for text-to-speech conversion and voice tone cloning..."]}
   Response: [{"label": 3, "probability": 0.9444}] -> [Sci/Tech: 3] 정답 판정
```

---

### [미션 5] Google Cloud Vertex AI 엔터프라이즈 MLOps 플랫폼 총정리 (18강)

```text
[노트북 수동 파이프라인의 5대 한계]      ───>    [Google Cloud Vertex AI 솔루션]
1. 개인 로컬 GPU 장비에 묶임                     -> Vertex AI Custom Training (온디맨드 클라우드 GPU)
2. 모델 파일이 로컬에 산재 (버전/메트릭 분실)   -> Vertex AI Model Registry (버전/성능 지표 중앙화)
3. 서빙 서버 프로세스 수동 관리                 -> Vertex AI Online Prediction (서버리스 오토스케일링)
4. 피처 데이터 분산 및 드리프트 미감지           -> Vertex AI Feature Store & Model Monitoring
5. 학습부터 배포까지 셀 단위 수동 실행          -> Vertex AI Pipelines (전 구간 자동 오케스트레이션)
```

| 수동 파이프라인의 한계 | Vertex AI 대응 컴포넌트 | 엔터프라이즈 MLOps 효과 |
| :--- | :--- | :--- |
| **학습이 개인 장비에 묶임** | **Vertex AI Training** | 필요할 때만 고성능 GPU를 동적 할당받아 학습하고 끝나면 즉시 반환 (비용 최적화) |
| **가중치 파일 버전 관리 부재** | **Model Registry** | 모델 버전별 아티팩트와 평가 성능 지표를 중앙 저장소에서 추적하고 손쉬운 롤백 지원 |
| **서빙 서버 수동 관리** | **Online Prediction** | 모델 등록 시 엔드포인트 URL이 자동 발급되며 트래픽에 따른 자동 스케일링 지원 |
| **피처 데이터 분산/드리프트** | **Feature Store / Monitoring** | 실시간 피처를 중앙에서 일관 관리하고 배포 후 데이터 분포 변화(Drift)를 조기 감지 |
| **학습~배포 수동 실행** | **Vertex AI Pipelines** | 데이터 수집 -> 가공 -> 학습 -> 평가 -> 배포 전 과정을 하나의 자동화 파이프라인 코드로 오케스트레이션 |

---

## 4. 퀘스트 결론 및 핵심 요약 (Summary)

* 자연어 처리(NLP) 분야의 사전학습 모델인 BERT를 파인튜닝하여 뉴스 기사를 고정밀도로 자동 분류하는 모델을 완성했습니다.
* 순수 가중치 파일(`.pth`)의 한계를 극복하고, 전후처리 핸들러의 4단계 생명주기와 설정을 결합한 `.mar` 아카이브 패키징을 통해 프로덕션 배포 표준을 확립했습니다.
* TorchServe 기반의 고성능 실시간 추론 REST API 서버를 5000번 포트로 구동하고 실제 HTTP POST 요청을 통해 3종 뉴스에 대한 실시간 분류를 성공적으로 검증했습니다.
* 개별 노트북 기반 수동 파이프라인의 한계를 분석하고, 이를 엔터프라이즈 규모로 확장 관리할 수 있는 Google Cloud Vertex AI의 통합 아키텍처를 정립했습니다.
