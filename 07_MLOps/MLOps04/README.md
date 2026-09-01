# Day 04: GitHub Actions 기반 CI/CD 파이프라인 자동화

## 📌 4일차 실습 자료
* 📓 실습 주피터 노트북: [`fsdl_day3.ipynb`](./fsdl_day3.ipynb)
* ⚙️ CI/CD 워크플로우: [`.github/workflows/main.yml`](./.github/workflows/main.yml)
* 📄 Dockerfile: [`Dockerfile`](./Dockerfile)
* 📄 모델 학습 스크립트: [`train.py`](./train.py)
* 📄 FastAPI 서빙 API: [`main.py`](./main.py)
* 📦 모델 직렬화 파일: [`model.joblib`](./model.joblib)

---

## 🎯 4일차 핵심 목표: "딸깍 한 번으로 빌드부터 클라우드 배포까지"
모델 코드를 수정하고 GitHub에 `git push`만 하면, **GitHub Actions가 자동으로 Docker 이미지를 빌드해 Docker Hub에 올리고(CI), GCP VM에 접속하여 컨테이너를 최신 버전으로 재배포(CD)**하는 완전 자동화 파이프라인을 구축합니다.

```mermaid
flowchart LR
    A["로컬 코드 수정<br/>(git push)"] --> B["GitHub Actions<br/>(CI 시작)"]
    B --> C["Docker Hub<br/>(Image Push)"]
    C --> D["GCP VM SSH 접속<br/>(CD 시작)"]
    D --> E["최신 컨테이너<br/>(Pull & Run)"]
    E --> F["배포 완료 🎉"]
```

---

## 🚀 Step 1. 깃허브 레포지토리 생성 및 로컬 연동

```bash
# 4일차 폴더로 이동
cd day04_pipeline_cicd

# Git 초기화 및 커밋
git init -b main
git add .
git commit -m "feat: Add FastAPI model serving with CI/CD"

# GitHub CLI를 사용하는 경우
gh repo create mlops-serving --public --source=. --remote=origin --push
```

---

## 🔑 Step 2. GitHub Secrets 5개 등록 (핵심 보안 설정)

GitHub 레포지토리 ➔ **Settings ➔ Secrets and variables ➔ Actions ➔ [New repository secret]**

| Secret 이름 | 설명 | 가져오는 방법 |
| :--- | :--- | :--- |
| **`DOCKERHUB_USERNAME`** | Docker Hub 아이디 | 본인 Docker 계정명 (예: `1003pro`) |
| **`DOCKERHUB_TOKEN`** | Docker Hub 액세스 토큰 | Docker Hub ➔ Account Settings ➔ Security ➔ New Access Token |
| **`GCP_VM_HOST`** | GCP VM의 외부 IP | GCP Compute Engine 콘솔의 **외부 IP** (예: `35.255.177.177`) |
| **`GCP_VM_USERNAME`** | GCP VM 접속 계정명 | GCP VM SSH 터미널에서 `whoami` 실행 결과 |
| **`GCP_SSH_KEY`** | GCP SSH Private Key | GCP VM에서 `ssh-keygen`으로 생성한 **비공개 키** |

---

## 🛠️ Step 3. GCP VM에서 SSH Key 발급 & 도커 권한 설정

GCP VM **SSH 터미널**에서 아래 명령어를 순서대로 실행합니다:

### 1) SSH Key 생성
```bash
ssh-keygen -t rsa -b 4096 -f ./gcp_deploy_key
```
*(passphrase는 그냥 엔터 2번 치기)*

### 2) 공개키(Public Key)를 VM 인증 목록에 추가
```bash
cat gcp_deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3) 비밀키(Private Key) 확인 및 GitHub에 복사
```bash
cat gcp_deploy_key
```
* `-----BEGIN OPENSSH PRIVATE KEY-----` (또는 RSA) 부터 `-----END ... KEY-----` 까지 **전체 복사**하여 GitHub의 **`GCP_SSH_KEY`** Secret에 등록!

### 4) Docker sudo 권한 없이 실행 가능하도록 설정 (필수!)
```bash
sudo usermod -aG docker $USER
```

---

## ⚡ Step 4. CI/CD 자동화 테스트 (코드 푸시)

로컬에서 코드를 수정하거나 빈 커밋을 푸시하여 Actions 동작을 확인합니다:

```bash
# 빈 커밋으로 GitHub Actions 트리거
git commit --allow-empty -m "test: trigger CI/CD pipeline"
git push origin main
```

* **GitHub ➔ Actions 탭**에서 `build-and-push`와 `deploy` 두 단계가 초록색 체크(✅)로 통과하는지 확인합니다.
* 완료 후 브라우저에서 `http://[VM-외부-IP]/docs` 로 접속하여 최신 서버가 잘 돌아가는지 확인합니다!

---

## 📸 4일차 실습 인증 캡처 보관함 (`./images/`)

4일차 실습 성공을 증명하는 캡처 이미지들을 `images/` 폴더에 아래와 같이 정리하여 보관합니다:

1. **[01_github_actions_success.png](./images/01_github_actions_success.png)** : GitHub Actions `build-and-push` ➔ `deploy` 전체 성공 파이프라인
2. **[02_github_secrets.png](./images/02_github_secrets.png)** : GitHub Repository Secrets 5개 등록 완료 화면
3. **[03_docker_hub_pushed.png](./images/03_docker_hub_pushed.png)** : Docker Hub `1003pro/my-ml-app:latest` 자동 푸시 내역
4. **[04_gcp_docker_ps.png](./images/04_gcp_docker_ps.png)** : GCP VM에서 `docker ps` 실행 (새 컨테이너 `my-app-container` 구동)
5. **[05_fastapi_swagger_docs.png](./images/05_fastapi_swagger_docs.png)** : GCP 외부 IP를 통한 FastAPI Swagger UI 문서 (`/docs`) 접속 확인

