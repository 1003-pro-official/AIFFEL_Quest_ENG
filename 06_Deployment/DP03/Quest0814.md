# Day 3 — 비동기 처리와 에러 핸들링 (DP03 제출)

## 제출 미션
1. 각 섹션 실행 내역 및 결과 기록
2. 각 섹션 체크포인트 및 최종 체크포인트 답변

---

## 1. 각 섹션 실행 내역 및 출력 결과

### [섹션 2] async/await의 기본 원리

#### 2.2 동기 vs 비동기 실행 시간 비교

* **동기 순차 실행 (`sync_task` + `time.sleep`)**:
  - 코드 내용:
    ```python
    def sync_task(name, seconds):
        print(f"  [{name}] 시작")
        time.sleep(seconds)
        print(f"  [{name}] 완료 ({seconds}초)")

    start = time.time()
    sync_task("작업A", 2)
    sync_task("작업B", 2)
    sync_task("작업C", 2)
    print(f"\n총 소요 시간: {round(time.time() - start, 1)}초")
    ```
  - 실행 출력:
    ```text
    ===== 동기 실행 =====
      [작업A] 시작
      [작업A] 완료 (2초)
      [작업B] 시작
      [작업B] 완료 (2초)
      [작업C] 시작
      [작업C] 완료 (2초)

    총 소요 시간: 6.0초
    ```

* **비동기 동시 실행 (`async_task` + `await asyncio.sleep`)**:
  - 코드 내용:
    ```python
    async def async_task(name, seconds):
        print(f"  [{name}] 시작")
        await asyncio.sleep(seconds)
        print(f"  [{name}] 완료 ({seconds}초)")

    start = time.time()
    await asyncio.gather(
        async_task("작업A", 2),
        async_task("작업B", 2),
        async_task("작업C", 2),
    )
    print(f"\n총 소요 시간: {round(time.time() - start, 1)}초")
    ```
  - 실행 출력:
    ```text
    ===== 비동기 실행 =====
      [작업A] 시작
      [작업B] 시작
      [작업C] 시작
      [작업A] 완료 (2초)
      [작업B] 완료 (2초)
      [작업C] 완료 (2초)

    총 소요 시간: 2.0초
    ```

---

### [섹션 3] 문제 시연: 동기 추론이 서버를 멈추는 순간

#### 3.1 `app/main_sync_problem.py` 생성 및 서버 실행
* **코드 내용**: `%%writefile app/main_sync_problem.py`
  - `/predict/blocking`: `async def` + `time.sleep(3)` (이벤트 루프 차단 시뮬레이션)
  - `/predict/threadpool`: 일반 `def` + `time.sleep(3)` (FastAPI 자동 스레드풀)
  - `/health`: `async def` 헬스체크 엔드포인트
* **실행 출력**:
  ```text
  Writing app/main_sync_problem.py
  서버 실행됨: http://127.0.0.1:8000
  ```

#### 3.2 실험 1: blocking 엔드포인트 동시 요청 테스트
* **코드 내용**: `concurrent_test("http://localhost:8000/predict/blocking", n_requests=3)`
* **실행 출력**:
  ```text
  =======================================================
    3개 동시 요청 → http://localhost:8000/predict/blocking
  =======================================================
    요청 #1: 9.0초
    요청 #2: 3.0초
    요청 #3: 6.0초

    전체 소요 시간: 9.0초
  ```

#### 3.3 실험 2: threadpool 엔드포인트 동시 요청 테스트
* **코드 내용**: `concurrent_test("http://localhost:8000/predict/threadpool", n_requests=3)`
* **실행 출력**:
  ```text
  =======================================================
    3개 동시 요청 → http://localhost:8000/predict/threadpool
  =======================================================
    요청 #1: 5.1초
    요청 #2: 5.1초
    요청 #3: 5.1초

    전체 소요 시간: 5.1초
  ```

#### 3.4 실험 3: blocking이 헬스체크(`/health`)까지 막는 현상
* **코드 내용**: 추론 요청 실행 중 백그라운드 스레드에서 `/health` 헬스체크 호출
* **실행 출력**:
  ```text
  ===== /predict/blocking 중 헬스체크 =====
    추론 응답: 5.0초
    헬스체크 응답: 4.5초    ← 단순 상태 확인인데 2.5초 대기!

  ===== /predict/threadpool 중 헬스체크 =====
    추론 응답: 5.0초
    헬스체크 응답: 2.1초    ← 즉시 응답!
  ```

---

### [섹션 4] 해결 패턴: run_in_executor로 블로킹 방지하기

#### 4.2 세 가지 동시 처리 방식 비교
* **`app/main_async_solution.py` 생성 및 서버 실행 후 3개 동시 요청 비교**:
* **버전 1: `async def + time.sleep` (blocking)**
  ```text
  ==================================================
  버전 1: async def + time.sleep (blocking)
  ==================================================
    요청 #1: 5.0초
    요청 #2: 8.0초
    요청 #3: 11.0초
    전체: 11.0초
  ```
* **버전 2: 일반 `def` (FastAPI 자동 스레드풀)**
  ```text
  ==================================================
  버전 2: 일반 def (FastAPI 자동 스레드풀)
  ==================================================
    요청 #1: 5.0초
    요청 #2: 5.0초
    요청 #3: 5.0초
    전체: 5.0초
  ```
* **버전 3: `async def + run_in_executor` (권장 패턴)**
  ```text
  ==================================================
  버전 3: async def + run_in_executor (권장)
  ==================================================
    요청 #1: 5.1초
    요청 #2: 5.1초
    요청 #3: 5.1초
    전체: 5.1초
  ```

#### 4.4 `app/main_v2.py` 생성
* **코드 내용**: `%%writefile app/main_v2.py` (Day 2의 MNIST API에 `run_in_executor` 적용)
* **실행 출력**:
  ```text
  Writing app/main_v2.py
  ```

#### 4.5 CPU 코어 수 및 권장 스레드풀 크기 확인
* **코드 내용**: `os.cpu_count()`
* **실행 출력**:
  ```text
  CPU 코어 수: 12
  권장 max_workers (CPU 추론): 12
  권장 max_workers (GPU 추론): 1~2
  ```

---

### [섹션 5] 에러 핸들링과 로깅

#### 5.2 글로벌 Exception Handler 파일 생성
* **코드 내용**: `%%writefile app/error_handlers.py`
  - `HTTPException`, `RequestValidationError`, `Exception` 전역 핸들러 정의
* **실행 출력**:
  ```text
  Writing app/error_handlers.py
  ```

#### 5.3 로깅 설정 및 테스트
* **코드 내용**: `%%writefile app/logger_config.py` 및 로거 테스트
* **실행 출력**:
  ```text
  Writing app/logger_config.py
  2026-08-14 12:26:37 INFO     [ml_api] 서버가 시작되었습니다.
  2026-08-14 12:26:37 WARNING  [ml_api] GPU 메모리가 80%를 초과했습니다.
  2026-08-14 12:26:37 ERROR    [ml_api] 모델 추론 중 에러가 발생했습니다.
  ```

#### 5.4 요청/응답 로깅 미들웨어 생성
* **코드 내용**: `%%writefile app/middleware.py` (`BaseHTTPMiddleware` 기반 소요 시간 및 상태 코드 로깅)
* **실행 출력**:
  ```text
  Writing app/middleware.py
  ```

---

### [섹션 6] 실습: 최종 서버 + 동시 요청 테스트

#### 6.0 사전 준비: 의존 파일 검증
* **실행 출력**:
  ```text
  ⚠️ app/model_utils.py 없음 → 생성합니다.
    ✅ app/model_utils.py 생성 완료
  ⚠️ app/schemas.py 없음 → 생성합니다.
    ✅ app/schemas.py 생성 완료
  ⚠️ app/error_handlers.py 없음 → 생성합니다.
    ✅ app/error_handlers.py 생성 완료
  ⚠️ app/logger_config.py 없음 → 생성합니다.
    ✅ app/logger_config.py 생성 완료
  ⚠️ app/middleware.py 없음 → 생성합니다.
    ✅ app/middleware.py 생성 완료
  ✅ models/mnist_state_dict.pth 있음
  
  🎉 모든 의존 파일이 준비되었습니다. 다음 셀로 진행하세요.
  ```

#### 6.1 최종 서버 코드 생성 (`app/main_final.py`)
* **코드 내용**: `%%writefile app/main_final.py` (비동기 `run_in_executor` + 글로벌 에러 핸들러 + 미들웨어 + 로거 통합)
* **실행 출력**:
  ```text
  Overwriting app/main_final.py
  ```

#### 6.2 최종 서버 실행
* **코드 내용**: `serve_in_thread("app.main_final:app", port=8000)`
* **실행 출력**:
  ```text
  2026-08-14 14:16:19 INFO     [ml_api] 모델 로드 중: models/mnist_state_dict.pth
  2026-08-14 14:16:19 INFO     [ml_api] 모델 로드 완료
  서버 실행됨: http://127.0.0.1:8000
  ```

#### 6.2 동시 요청 부하 테스트 (1, 2, 4, 8개 동시 요청)
* **실행 출력**:
  ```text
  ==================================================
    1개 동시 요청 (실제 추론)
  ==================================================
  2026-08-14 14:16:25 INFO     [ml_api] POST /predict/pixels -> 200 (0.048s)
    요청 #1: 2.11초 (HTTP 200)
    전체: 2.13초

  ==================================================
    2개 동시 요청 (실제 추론)
  ==================================================
  2026-08-14 14:16:28 INFO     [ml_api] POST /predict/pixels -> 200 (0.007s)
  2026-08-14 14:16:28 INFO     [ml_api] POST /predict/pixels -> 200 (0.009s)
    요청 #1: 2.03초 (HTTP 200)
    요청 #2: 2.04초 (HTTP 200)
    전체: 2.04초

  ==================================================
    4개 동시 요청 (실제 추론)
  ==================================================
  2026-08-14 14:16:31 INFO     [ml_api] POST /predict/pixels -> 200 (0.006s)
  2026-08-14 14:16:31 INFO     [ml_api] POST /predict/pixels -> 200 (0.007s)
  2026-08-14 14:16:31 INFO     [ml_api] POST /predict/pixels -> 200 (0.01s)
  2026-08-14 14:16:31 INFO     [ml_api] POST /predict/pixels -> 200 (0.011s)
    요청 #1: 2.06초 (HTTP 200)
    요청 #2: 2.06초 (HTTP 200)
    요청 #3: 2.05초 (HTTP 200)
    요청 #4: 2.06초 (HTTP 200)
    전체: 2.06초

  ==================================================
    8개 동시 요청 (실제 추론)
  ==================================================
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.011s)
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.012s)
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.014s)
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.015s)
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.019s)
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.019s)
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.02s)
  2026-08-14 14:16:34 INFO     [ml_api] POST /predict/pixels -> 200 (0.022s)
    요청 #1: 2.05초 (HTTP 200)
    요청 #2: 2.04초 (HTTP 200)
    요청 #3: 2.05초 (HTTP 200)
    요청 #4: 2.05초 (HTTP 200)
    요청 #5: 2.04초 (HTTP 200)
    요청 #6: 2.03초 (HTTP 200)
    요청 #7: 2.04초 (HTTP 200)
    요청 #8: 2.03초 (HTTP 200)
    전체: 2.05초
  ```

#### 6.3 에러 핸들링 및 상태 코드 동작 확인
* **실행 출력**:
  ```text
  ==================================================
    에러 핸들링 테스트
  ==================================================
  2026-08-14 14:16:41 INFO     [ml_api] POST /predict/pixels -> 200 (0.005s)

  [정상 요청] 상태: 200, 예측: 7
  2026-08-14 14:16:43 WARNING  [ml_api] POST /predict/pixels -> 422 (0.005s)
  [잘못된 크기] 상태: 422
  2026-08-14 14:16:46 WARNING  [ml_api] POST /predict/image -> 400 (0.18s)
  [잘못된 Base64] 상태: 400, 에러: 이미지 처리 실패: cannot identify image file <_io.BytesIO object at 0x000002311E7C22F0>
  2026-08-14 14:16:48 INFO     [ml_api] GET /health -> 200 (0.0s)
  [헬스체크] 상태: 200, 응답: {'status': 'healthy', 'model_loaded': True}
  ```

---

## 2. 각 섹션 체크포인트 답변

### [섹션 2 체크포인트]

#### Q1. `time.sleep(3)`과 `await asyncio.sleep(3)`의 핵심 차이는 무엇입니까?
* **답변**:
  - **`time.sleep(3)` (동기 블로킹)**: 실행 중인 Python 프로세스/스레드 전체를 멈추게 합니다. 비동기 이벤트 루프(Event Loop) 안에서 이를 호출하면 이벤트 루프 자체가 3초간 완전히 멈추어, 그 시간 동안 다른 어떤 비동기 작업이나 들어오는 HTTP 요청도 처리하지 못하고 블로킹됩니다.
  - **`await asyncio.sleep(3)` (비동기 논블로킹)**: 현재 코루틴(coroutine)의 실행 권한을 이벤트 루프에 양보(yield)하고 백그라운드 타이머만 등록합니다. 이벤트 루프는 3초 동안 다른 작업이나 HTTP 요청을 멈춤 없이 계속 처리할 수 있으며, 3초가 지난 뒤 해당 위치로 돌아와 다음 작업을 재개합니다.

#### Q2. 모델 추론처럼 CPU를 계속 사용하는 작업에서 `async/await`만으로 동시 처리가 안 되는 이유는 무엇입니까?
* **답변**:
  - `async/await`는 I/O 대기 시간(네트워크 통신, DB 쿼리, 디스크 입출력 등) 동안 CPU 제어권을 다른 태스크로 넘겨주는 협력적 멀티태스킹(Cooperative Multitasking) 방식입니다.
  - 모델 추론(행렬 연산, 텐서 계산)은 대기 시간이 없는 **CPU-bound(연산 집중형) 작업**입니다.
  - 연산 중에는 이벤트 루프에 제어권을 넘겨주는 `await` 지점이 없으므로, 메인 이벤트 루프 스레드에서 직접 추론을 돌리면 연산이 끝날 때까지 단일 스레드를 100% 독점하여 다른 요청을 처리할 수 없게 됩니다.

---

### [섹션 3 체크포인트]

#### Q1. `async def` 안에서 `time.sleep(3)`을 호출하면 왜 다른 요청까지 지연됩니까?
* **답변**:
  - FastAPI에서 `async def` 엔드포인트는 메인 이벤트 루프 스레드에서 직접 실행됩니다.
  - `time.sleep(3)`을 호출하면 메인 이벤트 루프 자체가 멈추므로, 뒤이어 도착하는 다른 모든 클라이언트의 요청이 처리되지 못하고 큐에 대기하게 됩니다.
  - 그 결과 3명이 동시에 요청하면 3초, 6초, 9초로 순차적 누적 지연이 발생합니다.

#### Q2. 일반 `def`로 선언된 엔드포인트는 FastAPI가 내부적으로 어떻게 처리합니까?
* **답변**:
  - FastAPI는 `def`(동기 함수) 엔드포인트를 감지하면, 메인 이벤트 루프를 막지 않도록 **FastAPI 내부의 별도 외부 스레드풀(ThreadPoolExecutor)** 에 작업을 위임하여 실행합니다.
  - 동기 블로킹 코드가 있더라도 별도의 스레드에서 동작하므로 메인 이벤트 루프는 차단되지 않고 계속해서 다른 요청을 수신할 수 있습니다.

#### Q3. blocking 추론 중 헬스체크까지 막히면 실무에서 어떤 문제가 발생할 수 있습니까?
* **답변**:
  - 쿠버네티스(Kubernetes)나 AWS ALB/로드밸런서는 주기적으로 `/health` (Liveness / Readiness Probe) 엔드포인트를 호출하여 서버 상태를 체크합니다.
  - 긴 추론 연산으로 인해 이벤트 루프가 멈춰 헬스체크 응답 타임아웃이 발생하면:
    1. 로드밸런서가 해당 인스턴스를 비정상(Unhealthy)으로 판단하여 트래픽 전송에서 제외시키고,
    2. 쿠버네티스가 정상적으로 추론 중이던 파드(Pod)를 다운된 것으로 오판하여 강제로 재시작(Restart)시켜 버려, 사용자 요청이 유실되고 서비스 장애가 연쇄적으로 확산됩니다.

---

### [섹션 4 체크포인트]

#### Q1. `run_in_executor`가 이벤트 루프 블로킹을 방지하는 원리는 무엇입니까?
* **답변**:
  - `loop.run_in_executor(executor, func, *args)`는 무거운 동기 연산 작업(추론 함수)을 메인 이벤트 루프 스레드가 아닌 **별도의 백그라운드 스레드풀(ThreadPoolExecutor)** 로 전달하여 실행합니다.
  - 메인 이벤트 루프는 스레드가 결과를 낼 때까지 `await`로 비동기 대기하면서 다른 HTTP 요청을 자유롭게 처리할 수 있으며, 스레드 작업이 완료되면 Future 결과를 반환받아 응답을 생성합니다.

#### Q2. `run_in_executor`의 첫 번째 인자에 `None`을 넣으면 어떤 스레드풀이 사용됩니까?
* **답변**:
  - `None`을 전달하면 파이썬 `asyncio` 이벤트 루프의 **기본(Default) ThreadPoolExecutor** 가 사용됩니다.

#### Q3. 일반 `def`와 `async def + run_in_executor`의 핵심 차이는 무엇입니까?
* **답변**:
  - **일반 `def`**: 엔드포인트 전체 함수가 FastAPI 공용 스레드풀의 스레드 하나를 완전히 점유합니다. 요청마다 스레드가 소모되며, 스레드풀 크기를 모델별/작업별로 정밀하게 제어하기 어렵습니다.
  - **`async def + run_in_executor`**: 엔드포인트 진입과 데이터 검증, 전/후처리는 가벼운 비동기로 이벤트 루프에서 처리하고, **오직 순수하게 무거운 모델 추론 단계만 전용 ThreadPoolExecutor로 위임**합니다. 또한 스레드풀 크기(`max_workers`)를 CPU 코어 수나 GPU 자원에 맞춰 독립적이고 세밀하게 제어할 수 있습니다.

#### Q4. GPU 추론 시 스레드풀 크기를 1~2로 제한하는 이유는 무엇입니까?
* **답변**:
  - GPU는 고도의 병렬 연산 장치이지만, 여러 스레드가 동시에 GPU 커널을 호출하면 **CUDA 컨텍스트 스위칭 오버헤드, 자원 경합(Contention), GPU 메모리 부족(CUDA Out of Memory: OOM)** 현상이 발생하여 서버가 다운되거나 처리 속도가 급격히 저하됩니다.
  - 따라서 GPU 서빙 시에는 스레드풀 크기를 1~2로 엄격히 제한(또는 큐를 통한 배치 처리)하여 안정적인 VRAM 관리와 일정한 처리 성능을 보장해야 합니다.

---

### [섹션 5 체크포인트]

#### Q1. 글로벌 Exception Handler를 사용하면 어떤 반복을 줄일 수 있습니까?
* **답변**:
  - 모든 엔드포인트마다 개별적으로 작성해야 했던 `try-except` 예외 처리 블록과 에러 로깅 코드의 중복을 제거할 수 있습니다.
  - 서버 전역에서 발생하는 예외를 한곳에서 가로채 **일관된 표준 에러 응답 포맷(Standardized JSON Error Format)** 으로 클라이언트에게 반환할 수 있습니다.

#### Q2. 클라이언트에게 스택 트레이스를 노출하면 안 되는 이유는 무엇입니까?
* **답변**:
  - **보안 위험 (정보 유출)**: 스택 트레이스에는 서버의 내부 파일 경로, 운영체제 계정 정보, 라이브러리 및 정확한 버전, 데이터베이스 테이블 구조 등 민감한 정보가 노출되어 공격자에게 취약점 공격의 단서를 제공합니다.
  - **사용자 경험(UX)**: 클라이언트나 프론트엔드가 해석할 수 없는 복잡한 내부 로그 대신, 알기 쉬운 메시지와 명확한 HTTP 상태 코드(400, 404, 500 등)를 전달해야 합니다.

#### Q3. `logging` 모듈이 `print()`보다 나은 점은 무엇입니까?
* **답변**:
  - **로그 레벨(Level) 제어**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` 등 심각도별로 로그를 분류하고, 실행 환경에 따라 출력 레벨을 동적으로 조정할 수 있습니다.
  - **구조화된 메타데이터**: 타임스탬프, 모듈명, 프로세스/스레드 ID, 함수명, 라인 번호 등의 디버깅 정보를 자동으로 일관되게 기록할 수 있습니다.
  - **다양한 출력 대상(Handler)**: 콘솔 출력뿐만 아니라 파일 저장, 날짜/용량별 로그 로테이션(Rotating), 중앙 집중식 로그 수집 시스템(ELK, CloudWatch 등)으로 유연하게 전송할 수 있습니다.

---

### [Day 3 최종 체크포인트]

```
Q1. 동기 서버에서 3초 걸리는 추론을 3명이 동시에 요청하면 총 몇 초 걸립니까?
Q2. time.sleep(3)과 await asyncio.sleep(3)의 핵심 차이는?
Q3. async def 안에서 동기 블로킹 코드를 실행하면 왜 헬스체크까지 영향받습니까?
Q4. run_in_executor가 이벤트 루프 블로킹을 방지하는 원리는?
Q5. 글로벌 Exception Handler를 사용하는 이유는?
Q6. 클라이언트에게 스택 트레이스를 노출하면 안 되는 이유는?
```

* **Q1 답변**: 약 **9초** (3초 × 3명 = 9초). 동기 단일 스레드 서버에서는 요청을 순차적으로 1개씩 처리하므로 첫 번째 요청 3초, 두 번째 요청 6초, 세 번째 요청 9초가 소요되어 전체 9초가 걸립니다.
* **Q2 답변**: `time.sleep(3)`은 스레드와 이벤트 루프 전체를 멈추는 **동기 블로킹** 방식이고, `await asyncio.sleep(3)`은 이벤트 루프에 제어권을 양보하여 다른 작업을 처리할 수 있게 하는 **비동기 논블로킹** 방식입니다.
* **Q3 답변**: `async def`는 메인 이벤트 루프 스레드에서 직접 실행되므로, 동기 블로킹 코드가 이벤트 루프 자체를 멈춰버려 `/health` 같은 다른 엔드포인트 요청이 들어와도 이벤트 루프가 깨어날 때까지 대기 큐에 갇히게 되기 때문입니다.
* **Q4 답변**: 무거운 동기 연산 작업을 메인 이벤트 루프가 아닌 **별도의 백그라운드 ThreadPoolExecutor에 위임**하고 `await`로 비동기 대기함으로써, 메인 이벤트 루프는 다른 HTTP 요청을 논블로킹으로 계속 처리할 수 있도록 분리하기 때문입니다.
* **Q5 답변**: 엔드포인트마다 중복되는 `try-except` 코드를 제거하고, 시스템 전역에서 발생하는 예외를 한곳에서 가로채 **일관된 표준 에러 응답 포맷을 제공**하며, **중앙 집중식 로깅**과 **보안 정보 유출 방지**를 달성하기 위함입니다.
* **Q6 답변**: 내부 파일 경로, 코드 구조, 모듈 버전, DB 구조 등 시스템의 민감한 내부 아키텍처가 노출되어 **보안 취약점 공격(Reconnaissance)의 빌미**를 제공하기 때문입니다.

---

## 3. 프로젝트 구조 및 파일 명세

```
AIFFEL_Quest_ENG/06_Deployment/DP03/
├── 📁 app/
│   ├── __init__.py
│   ├── error_handlers.py          ← 글로벌 에러 핸들러 (HTTPException, ValidationError, 전역 Exception)
│   ├── logger_config.py           ← 구조화된 로깅 설정 (ml_api)
│   ├── main_async_solution.py     ← 3가지 비동기/동기 패턴 비교 서버
│   ├── main_final.py              ← 최종 서버 (비동기 run_in_executor + 에러핸들러 + 로깅 미들웨어)
│   ├── main_sync_problem.py       ← 동기 블로킹 문제 재현 서버
│   ├── main_v2.py                 ← MNIST API에 run_in_executor 적용 서버
│   ├── middleware.py              ← 요청/응답 자동 로깅 미들웨어
│   ├── model_utils.py             ← SimpleClassifier 모델 및 추론/전처리 유틸리티
│   └── schemas.py                 ← Pydantic V2 Request/Response 스키마
├── 📁 models/
│   └── mnist_state_dict.pth       ← 학습된 MNIST 모델 가중치
├── 📁 data/                       ← MNIST 테스트 데이터셋
├── 📓 모델배포개론03.ipynb           ← Day 3 실습 및 실행 노트북
├── 📄 Quest0814.md                ← 제출용 퀘스트 결과 문서 (본 파일)
└── 📄 README.md                   ← Peer Review 템플릿
```
