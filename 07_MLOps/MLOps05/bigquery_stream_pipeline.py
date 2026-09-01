import time
import uuid
import random
import string
from google.cloud import bigquery

# 1. 설정 정보 (본인의 GCP 프로젝트 ID)
PROJECT_ID = "project-115ad59e-fee8-4a5c-a0d"
DATASET_ID = "example"
TABLE_ID = "stream"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

def generate_random_text(length: int = 50) -> str:
    """랜덤 영문+숫자 더미 텍스트 생성 헬퍼 함수"""
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for _ in range(length))

def main():
    print(f"🚀 BigQuery 클라이언트 초기화 중... (프로젝트: {PROJECT_ID})")
    client = bigquery.Client(PROJECT_ID)

    # 2. 데이터 세트 생성 (멱등 생성: 이미 있어도 에러 안 남)
    print(f"📦 데이터 세트 '{DATASET_ID}' 확인 및 생성...")
    client.create_dataset(DATASET_ID, exists_ok=True)

    # 3. 테이블 및 스키마 정의 (없을 때만 생성)
    try:
        client.get_table(FULL_TABLE_ID)
        print(f"ℹ️ 테이블 '{FULL_TABLE_ID}' 가 이미 존재합니다.")
    except Exception:
        schema = [
            bigquery.SchemaField(name="log_id", field_type="STRING"),
            bigquery.SchemaField(name="text", field_type="STRING"),
            bigquery.SchemaField(name="date", field_type="INTEGER"),
        ]
        table = bigquery.Table(FULL_TABLE_ID, schema=schema)
        client.create_table(table)
        print(f"✅ 새 테이블 '{FULL_TABLE_ID}' 생성 완료!")

    # 4. 1건씩 스트리밍 삽입하는 함수
    def insert_new_line():
        rows_to_insert = [
            {
                "log_id": str(uuid.uuid4()),
                "text": generate_random_text(50),
                "date": int(time.time()),
            }
        ]
        errors = client.insert_rows_json(FULL_TABLE_ID, rows_to_insert)
        if errors:
            print(f"❌ 삽입 에러: {errors}")

    # 5. 실시간 스트리밍 적재 시작 (총 1,000건)
    total_count = 1000
    print(f"\n⚡ BigQuery 실시간 스트리밍 적재 시작 (총 {total_count}건)...")
    print("💡 이 스크립트가 실행되는 동안 BigQuery Studio에서 실시간으로 COUNT(*) 쿼리를 날려보세요!\n")

    for i in range(1, total_count + 1):
        insert_new_line()
        if i % 100 == 0 or i == 1:
            print(f"  ➔ [{i}/{total_count}건] BigQuery로 실시간 전송 완료...")
        time.sleep(0.05)  # 잦은 주기로 데이터 전송 시뮬레이션

    print("\n🎉 총 1,000건의 로그 스트리밍 적재가 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()
