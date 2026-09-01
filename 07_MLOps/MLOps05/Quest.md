# [Day 05 Quest] GCP BigQuery 데이터 웨어하우스 & 실시간 데이터 파이프라인

---

## 1. 퀘스트 개요 (Quest Overview)

* **퀘스트 주제**: Google Cloud Platform(GCP) 인프라 이해, BigQuery 기반 대규모 분산 데이터 집계 및 실시간 스트리밍 적재 파이프라인 구축
* **관련 교안**: 「모두를 위한 MLOps」 14강 ~ 16강
* **관련 실습 파일**: 
  * [bigquery_stream_pipeline.py](./bigquery_stream_pipeline.py)
  * [README.md](./README.md)
* **핵심 목표**:
  1. AI/ML 인프라에서 GCP의 장점과 **프로젝트(`PROJECT_ID`) 단위 격리 관리** 및 과금 방지 체계를 이해한다.
  2. **OLTP(서비스 트랜잭션 중심)**와 **OLAP(대규모 분산 집계 중심)**의 아키텍처 및 성능 차이를 비교 분석한다.
  3. 머신러닝 피처 보존 관점에서 **ETL(Extract-Transform-Load)**과 **ELT(Extract-Load-Transform)**의 차이점 및 레이크하우스(Lakehouse) 트렌드를 정립한다.
  4. Google Colab에서 Python SDK(`google-cloud-bigquery`)를 연동하여 대규모 공개 데이터셋을 분산 집계하고 DataFrame으로 변환한다.
  5. `insert_rows_json`을 활용한 실시간 스트리밍 적재 메커니즘을 파악하고, 머신러닝의 **콜드 스타트(Cold Start)** 해결 전략과 **데이터 플라이휠(Data Flywheel)** 루프를 설계한다.

---

## 2. 퀘스트 평가 루브릭 (Assessment Rubric)

| 번호 | 평가 항목 (Rubric Items) | 달성 기준 |
| :---: | :--- | :--- |
| **1** | **GCP 프로젝트 및 DW 개념 이해** | 프로젝트 단위 자원 격리 구조와 대규모 데이터 집계를 위한 데이터 웨어하우스의 역할을 설명할 수 있는가? |
| **2** | **OLTP vs OLAP 비교 분석** | 원자성/트랜잭션 보장 여부, 데이터 규모, 처리 속도 관점에서 MySQL과 BigQuery의 차이를 구분할 수 있는가? |
| **3** | **ETL vs ELT와 ML 피처 보존** | 적재 전 변환(ETL)으로 인한 데이터 소실 문제와 원본 보존 후 변환(ELT)의 MLOps적 이점을 서술할 수 있는가? |
| **4** | **Python SDK 기반 BigQuery 연동** | Colab에서 계정 인증을 수행하고 `google-cloud-bigquery` 클라이언트로 복합 쿼리를 실행하여 결과를 수신하였는가? |
| **5** | **스트리밍 적재 및 데이터 플라이휠** | 실시간 행 단위 적재의 비차단(Non-blocking) 특성과 콜드 스타트 극복 및 지속적 학습(CT) 순환 구조를 정립하였는가? |

---

## 3. 세부 퀘스트 수행 내용 (Quest Details)

### [미션 1] AI/ML 인프라에서 GCP와 프로젝트(Project) 관리 체계

* **왜 MLOps에서 GCP인가?**:
  * 구글은 대규모 데이터 분산 처리 엔진인 **BigQuery**와 통합 머신러닝 플랫폼인 **Vertex AI** 등 강력한 AI/빅데이터 도구를 기본 제공하여 MLOps 파이프라인 구축에 최적화되어 있습니다.
* **프로젝트(Project) 기반 자원 격리**:
  * AWS가 계정 단위로 자원을 관리하는 것과 달리, GCP는 모든 가상머신, 데이터셋, 모델이 **'프로젝트'**라는 논리적 단위로 묶입니다.
  * 학습용 프로젝트를 생성하여 실습한 뒤 프로젝트를 삭제하면 내부 모든 자원이 일괄 정리되어 **예상치 못한 과금을 원천 차단**할 수 있습니다.
  * 식별자: 시스템 내부에서 식별자로 쓰이는 고유값은 **`PROJECT_ID (예: project-115ad59e-fee8-4a5c-a0d)`**입니다.

---

### [미션 2] OLTP vs OLAP 아키텍처 및 성능 비교

```text
[1. OLTP: 서비스 트랜잭션 DB (MySQL / PostgreSQL)]
  - 목적: 단건 사용자 결제/회원가입의 원자성(Atomicity)과 데이터 무결성 보장
  - 한계: 2억 건 전체 스캔 및 그룹 집계 시 락(Lock) 발생으로 수 시간 소요

[2. OLAP: 데이터 웨어하우스 (Google BigQuery)]
  - 목적: 수억~수조 건의 대규모 로그 분석 및 ML 피처 가공
  - 원리: 쿼리 요청 시 수백~수천 대 CPU 슬롯이 동적으로 붙어 분할 정복(Divide & Conquer) 수행
  - 속도: 2억 건의 복합 그룹 집계도 단 15초 이내에 초고속 응답
```

| 비교 항목 | OLTP (Online Transaction Processing) | OLAP (Online Analytical Processing) |
| :--- | :--- | :--- |
| **주 용도** | 서비스 운영 데이터베이스 (회원, 주문, 결제) | 데이터 웨어하우스, 대규모 데이터 집계/분석, ML 피처 가공 |
| **트랜잭션** | ACID(원자성, 일관성, 고립성, 지속성) 보장, 실패 시 롤백 | 트랜잭션 미지원 (대신 초고속 분산 처리) |
| **적합한 데이터** | 정확도가 최우선인 서비스 정형 데이터 | 대용량 로그 데이터, 이벤트 스트림, 제품 데이터 |
| **과금 방식** | 할당된 인스턴스 스펙(vCPU/RAM) 고정 비용 | **서버리스: 쿼리가 스캔한 데이터 용량만큼 온디맨드 과금** |
| **대표 제품** | MySQL, MariaDB, PostgreSQL | **Google BigQuery**, Amazon Redshift, Snowflake |

---

### [미션 3] ETL vs ELT (머신러닝 피처 보존 관점)

```text
[전통적 ETL 방식]
  데이터 소스 ───> [추출: Extract] ───> [변환: Transform] ───> [적재: Load] (DW)
                                         (세부 정보 소실 발생)     (정형화된 데이터만 보관)
  * 문제점: 나이 소수점, 상세 OS 핑거프린트 등 사소한 로그를 버리고 적재하므로,
           추후 ML 모델에 새로운 피처가 필요해졌을 때 과거 데이터 복구 불가.

[최신 ELT 방식 (Data Lake / Lakehouse)]
  데이터 소스 ───> [추출: Extract] ───> [적재: Load] (Lake) ───> [변환: Transform] (필요 시)
                                         (원본 100% 보존)          (ML 피처 엔지니어링 수행)
  * 장점: 일단 모든 원천 데이터를 무손실 적재하므로, 미래의 어떤 머신러닝 요구사항에도 유연하게 대응 가능.
```

---

### [미션 4] Python SDK 기반 BigQuery 대규모 공개 데이터 조회

Google Colab에서 `google-cloud-bigquery` 라이브러리를 통해 키 파일 없이 구글 계정 인증(`auth.authenticate_user()`)만으로 수백만 건의 GitHub 공개 데이터셋을 집계했습니다:

```python
# Colab 실습 코드
from google.cloud import bigquery
from google.colab import auth

# 1. 구글 계정 인증 및 클라이언트 생성
auth.authenticate_user()
PROJECT_ID = "project-115ad59e-fee8-4a5c-a0d"
client = bigquery.Client(PROJECT_ID)

# 2. 복합 집계 쿼리 실행 (ARRAY_AGG 복합 타입 활용)
query = """
SELECT
    repository.language,
    AVG(repository.size) AS average_size,
    SUM(repository.forks) AS total_forks,
    COUNT(*) AS total_repositories,
    ARRAY_AGG(DISTINCT repository.owner LIMIT 5) AS sample_owners
FROM
    `bigquery-public-data.samples.github_nested`
WHERE
    repository.language IS NOT NULL
GROUP BY
    repository.language
HAVING
    total_forks > 100
ORDER BY
    total_forks DESC
LIMIT 10;
"""

df = client.query(query).to_dataframe(create_bqstorage_client=False)
print(df.head())
```

* **복합 데이터 타입(`complex data type`)의 이점**:
  * BigQuery는 `ARRAY`, `RECORD`, `ARRAY_AGG`를 지원하여, RDBMS처럼 표준 SQL을 사용하면서도 JSON/NoSQL처럼 한 셀 안에 여러 값을 배열로 담는 유연한 데이터 처리가 가능합니다.

---

### [미션 5] 실시간 스트리밍 적재 & MLOps 데이터 플라이휠

* **스트리밍 적재 (`insert_rows_json`)**:
  * 파일 단위로 묶어 올리는 배치(Batch) 적재와 달리, 발생하는 즉시 1건씩 행 단위로 밀어 넣는 실시간 인터페이스입니다.
  * 쓰기(파이썬 스크립트)와 읽기(BigQuery Studio SQL)가 서로 락(Lock)을 걸지 않고 독립적으로 동시 수행됩니다.

```text
[MLOps 콜드 스타트(Cold Start) 해결 3단계]
  1단계: [룰 베이스 출시]  학습 데이터가 없으므로 전통적 규칙 기반 코드로 서비스 선출시
  2단계: [데이터 축적]     서빙 API에서 발생하는 사용자 로그를 BigQuery 스트리밍으로 지속 축적
  3단계: [모델 전환]       충분히 쌓인 로그 데이터를 학습 파이프라인에 태워 머신러닝 모델로 전환
```

```text
[데이터 플라이휠 (Data Flywheel) 선순환 루프]
  좋은 제품 출시 ───> 사용자 유입 증가 ───> 서버 로그 데이터 축적
         ▲                                         │
         │                                         ▼
  제품 품질 향상 <─── 더 똑똑한 모델 학습 <─── BigQuery 스트리밍 적재
```

* **지속적 학습 (Continuous Training, CT)**:
  * 실시간으로 유입되는 서빙 로그를 기반으로 시간 경과에 따른 **모델 드리프트(Model Drift)**를 조기에 감지하고, 최신 트렌드를 반영하는 재학습 파이프라인을 자동 순환시킵니다.

---

## 4. 퀘스트 결론 및 핵심 요약 (Summary)

* 머신러닝 시스템의 성패는 모델 알고리즘 자체보다, 모델이 지속적으로 먹고 자라는 **데이터 인프라의 확장성(Scalability)**에 달려 있음을 확인했습니다.
* BigQuery는 서버리스 기반의 가변 CPU 할당과 분할 정복 아키텍처를 통해 수억 건의 데이터도 수 초 만에 집계하는 강력한 OLAP 성능을 제공합니다.
* 머신러닝 피처 손실을 방지하는 ELT 패러다임과 실시간 스트리밍 적재(`insert_rows_json`)를 활용하여, 콜드 스타트를 극복하고 데이터 플라이휠을 구동하는 현대적 MLOps 데이터 파이프라인의 기반을 확립했습니다.
