# [Day 04 Quest] GitHub Actions 기반 CI/CD 완전 자동화 파이프라인 구축

---

## 1. 퀘스트 개요 (Quest Overview)

* **퀘스트 주제**: GitHub Actions 워크플로우를 활용한 CI(지속적 통합: 도커 자동 빌드/푸시) 및 CD(지속적 배포: GCP VM SSH 무중단 자동 배포) 완전 자동화 파이프라인 구축
* **관련 실습 파일**: 
  * [fsdl_day3.ipynb](./fsdl_day3.ipynb)
  * [.github/workflows/main.yml](./.github/workflows/main.yml)
  * [Dockerfile](./Dockerfile)
  * [main.py](./main.py)
  * [train.py](./train.py)
  * [model.joblib](./model.joblib)
  * [requirements.txt](./requirements.txt)
  * [실습 인증 캡처 보관함](./images/)
* **핵심 목표**:
  1. GitHub Actions 워크플로우 파일(`main.yml`)을 작성하여 `main` 브랜치 push 이벤트 기반의 트리거를 구성한다.
  2. Docker Hub 및 GCP VM 원격 접속에 필요한 5대 보안 변수를 **GitHub Repository Secrets**에 등록한다.
  3. GCP VM에서 SSH 배포 키를 생성 및 등록하고, 도커 비권한 실행(`sudo usermod -aG docker $USER`)을 설정한다.
  4. 로컬에서 `git push` 실행 시 **[CI: 이미지 빌드 및 Docker Hub 푸시] -> [CD: GCP VM SSH 접속 후 컨테이너 무중단 교체 배포]**가 1분 안에 자동 완료되는 엔드투엔드 파이프라인을 검증한다.
  5. 5종의 필수 실습 인증 캡처를 확보하고 정리한다.

---

## 2. 퀘스트 평가 루브릭 (Assessment Rubric)

| 번호 | 평가 항목 (Rubric Items) | 달성 기준 |
| :---: | :--- | :--- |
| **1** | **GitHub Actions CI/CD 워크플로우 작성** | `build-and-push` 작업과 `deploy` 작업의 의존성(`needs`)이 연결된 `main.yml` 파일을 올바르게 작성하였는가? |
| **2** | **GitHub Secrets 보안 변수 등록** | Docker Hub 인증(2개) 및 GCP VM SSH 접속(3개) 총 5개 Secret을 레포지토리에 안전하게 등록하였는가? |
| **3** | **GCP VM 자동 배포 환경 구성** | RSA PEM 형식 배포 키 생성, `authorized_keys` 등록, 도커 권한 부여를 완료하여 SSH 접속을 허용하였는가? |
| **4** | **CI/CD 완전 자동화 파이프라인 검증** | `git push` 후 GitHub Actions 탭에서 두 단계 모두 초록색 체크(Success)로 완료되고 GCP에 최신 서버가 기동되었는가? |
| **5** | **실습 인증 캡처 5종 확보** | Actions 성공, Secrets 목록, Docker Hub 푸시, `docker ps`, Swagger UI 5종 이미지를 체계적으로 정리하였는가? |

---

## 3. 세부 퀘스트 수행 내용 (Quest Details)

### [미션 1] CI/CD 자동화 워크플로우 작성 (`.github/workflows/main.yml`)

```yaml
# .github/workflows/main.yml 소스코드
name: Build, Push and Deploy

on:
  push:
    branches:
      - main

jobs:
  # [1단계] CI 작업: Docker 이미지 빌드 및 Docker Hub 자동 푸시
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Log in to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and Push Docker Image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./Dockerfile
          push: true
          tags: ${{ secrets.DOCKERHUB_USERNAME }}/my-ml-app:latest

  # [2단계] CD 작업: GCP VM SSH 원격 접속 및 무중단 재배포
  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: SSH and Deploy to GCP VM
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.GCP_VM_HOST }}
          username: ${{ secrets.GCP_VM_USERNAME }}
          key: ${{ secrets.GCP_SSH_KEY }}
          port: 22
          script: |
            # 1. Docker 로그인
            echo "${{ secrets.DOCKERHUB_TOKEN }}" | docker login -u "${{ secrets.DOCKERHUB_USERNAME }}" --password-stdin

            # 2. 기존 컨테이너 중지 및 삭제
            docker stop my-app-container || true
            docker rm my-app-container || true

            # 3. 최신 이미지 다운로드
            docker pull ${{ secrets.DOCKERHUB_USERNAME }}/my-ml-app:latest

            # 4. 새 컨테이너 실행 (외부 80 포트 -> 내부 8000 포트)
            docker run -d \
              --name my-app-container \
              -p 80:8000 \
              ${{ secrets.DOCKERHUB_USERNAME }}/my-ml-app:latest

            # 5. 미사용 구버전 이미지 정리 (디스크 용량 최적화)
            docker image prune -f
```

---

### [미션 2] GitHub Repository Secrets 5대 보안 변수 등록

소스코드에 개인 비밀번호나 SSH 비공개 키가 평문으로 노출되는 것을 방지하기 위해, 레포지토리의 **Settings -> Secrets and variables -> Actions** 메뉴에 아래 5개 암호화 변수를 등록했습니다:

| Secret 이름 | 용도 | 등록 값 형식 |
| :--- | :--- | :--- |
| **`DOCKERHUB_USERNAME`** | Docker Hub 로그인 아이디 | `1003pro` |
| **`DOCKERHUB_TOKEN`** | Docker Hub Personal Access Token | `dckr_pat_...` |
| **`GCP_VM_HOST`** | GCP VM 외부 IP 주소 | `104.198.243.70` (또는 `35.xxx`) |
| **`GCP_VM_USERNAME`** | GCP VM 로그인 계정명 | `g1003pro_official` |
| **`GCP_SSH_KEY`** | GCP VM 접속용 RSA 비공개 키 | `-----BEGIN RSA PRIVATE KEY----- ...` |

---

### [미션 3] GCP VM 원격 SSH 자동 배포 환경 구성

GCP VM 내부에서 GitHub Actions 러너가 비밀번호 없이 SSH 접속하여 도커 명령어를 실행할 수 있도록 터미널에서 설정을 완료했습니다:

```bash
# 1. SSH 디렉터리 권한 정비
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 2. OpenSSH / appleboy 호환 PEM 형식 RSA 4096비트 키 발급
ssh-keygen -t rsa -b 4096 -m PEM -N "" -f ~/.ssh/gcp_deploy_key

# 3. 공개키를 authorized_keys에 등록 및 권한 설정
cat ~/.ssh/gcp_deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 4. 도커 그룹에 사용자 추가 (sudo 없이 docker 명령 실행 권한 부여)
sudo usermod -aG docker $USER

# 5. 자체 SSH 접속 검증 테스트
ssh -o StrictHostKeyChecking=no -i ~/.ssh/gcp_deploy_key $(whoami)@localhost "echo 'OK_SUCCESS'"
```

---

### [미션 4] CI/CD 파이프라인 동작 시퀀스 다이어그램

```text
[개발자 PC] ─── 1. git push origin main ───> [GitHub Repository]
                                                    │
                                                    ▼
                                            [GitHub Actions Runner]
                                                    │
                                       [Job 1: build-and-push (CI)]
                                       - Checkout 소스코드
                                       - Docker 로그인
                                       - Dockerfile 빌드
                                       - docker push ─────────────> [Docker Hub 레지스트리]
                                                    │                               │
                                       [Job 2: deploy (CD)]                         │
                                       - appleboy/ssh-action 원격 접속              │
                                                    │                               │
                                                    ▼ (SSH Port 22)                 │
                                            [GCP VM: mlops-server]                  │
                                            - docker pull <─────────────────────────┘
                                            - docker stop & rm my-app-container
                                            - docker run -d -p 80:8000
                                            - docker image prune -f
                                                    │
                                                    ▼ (무중단 배포 완료)
[외부 사용자] <──── HTTP GET /docs ───────── [http://[VM-IP]/docs]
```

---

### [미션 5] 4일차 실습 인증 캡처 5종 매핑 (`./images/`)

| 번호 | 캡처 파일명 | 인증 내용 및 검증 포인트 |
| :---: | :--- | :--- |
| **01** | [01_github_actions_success.png](./images/01_github_actions_success.png) | GitHub Actions에서 `build-and-push` (50s) -> `deploy` (16s)가 초록색 체크(Success)로 연쇄 실행 완료된 파이프라인 그래프 |
| **02** | [02_github_secrets.png](./images/02_github_secrets.png) | `DOCKERHUB_TOKEN`, `DOCKERHUB_USERNAME`, `GCP_SSH_KEY`, `GCP_VM_HOST`, `GCP_VM_USERNAME` 5개 Secret 등록 목록 |
| **03** | [03_docker_hub_pushed.png](./images/03_docker_hub_pushed.png) | Docker Hub의 `1003pro/my-ml-app` 저장소에 `latest` 태그 이미지가 Actions에 의해 자동 푸시된 내역 |
| **04** | [04_gcp_docker_ps.png](./images/04_gcp_docker_ps.png) | GCP VM 터미널에서 `docker ps` 실행 시 `my-app-container`가 80번 포트로 정상 Up 상태 구동 중인 화면 |
| **05** | [05_fastapi_swagger_docs.png](./images/05_fastapi_swagger_docs.png) | 웹 브라우저에서 GCP 외부 IP 주소로 접속한 FastAPI Swagger UI 대화형 API 문서 정상 출력 화면 |

---

## 4. 퀘스트 결론 및 핵심 요약 (Summary)

* 소스코드 수정 후 `git push` 명령어 단 한 번으로, 클라우드 환경에서 도커 이미지가 자동 빌드되어 레지스트리에 푸시되고(CI), GCP 운영 서버에 무중단으로 교체 배포되는(CD) 완전 자동화 MLOps 파이프라인을 완성했습니다.
* GitHub Repository Secrets를 통해 인프라 접속 키와 계정 인증 정보를 암호화 관리하여 기업용 프로덕션 수준의 보안성을 확보했습니다.
* 5종의 필수 실습 인증 캡처를 체계적으로 확보하여, 개발-통합-배포-운영 전 단계의 정상 동작을 성공적으로 검증했습니다.
