import streamlit as st
import requests

st.set_page_config(
    page_title="붓꽃 분류기 (Iris Classifier)",
    page_icon="🌸",
    layout="centered"
)

st.title("🌸 붓꽃 품종 분류기 (Iris Classifier)")
st.markdown("GCP Cloud VM에서 구동 중인 FastAPI 서빙 컨테이너와 통신하는 프론트엔드 앱입니다.")

# 1. 서버 설정 사이드바
st.sidebar.header("⚙️ 클라우드 서버 설정")
vm_ip = st.sidebar.text_input(
    "GCP VM 외부 IP",
    value="35.255.177.177",
    help="본인의 GCP Compute Engine VM 외부 IP 주소를 입력하세요."
)
port = st.sidebar.text_input(
    "포트 번호",
    value="80",
    help="GCP에서 열어둔 포트 번호 (기본: 80)"
)

# API 엔드포인트 생성
API_URL = f"http://{vm_ip.strip()}:{port.strip()}/predict"
st.sidebar.markdown(f"**엔드포인트:** `{API_URL}`")

# 2. 피처 입력 슬라이더
st.subheader("📊 꽃의 특징(Feature) 입력")
st.write("슬라이더를 조정하여 붓꽃의 수치를 입력해주세요.")

col1, col2 = st.columns(2)

with col1:
    s_l = st.slider("꽃받침 길이 (Sepal Length, cm)", min_value=4.0, max_value=8.0, value=5.1, step=0.1)
    s_w = st.slider("꽃받침 너비 (Sepal Width, cm)", min_value=2.0, max_value=4.5, value=3.5, step=0.1)

with col2:
    p_l = st.slider("꽃잎 길이 (Petal Length, cm)", min_value=1.0, max_value=7.0, value=1.4, step=0.1)
    p_w = st.slider("꽃잎 너비 (Petal Width, cm)", min_value=0.1, max_value=2.5, value=0.2, step=0.1)

species_info = {
    0: {"name": "Setosa (세토사)", "desc": "꽃잎이 작고 둥근 형태가 특징인 품종입니다."},
    1: {"name": "Versicolor (버시컬러)", "desc": "중간 크기의 꽃잎과 꽃받침을 가진 품종입니다."},
    2: {"name": "Virginica (버진카)", "desc": "꽃잎과 꽃받침이 가장 큰 대형 품종입니다."}
}

st.divider()

# 3. 예측 요청 버튼
if st.button("🌸 품종 예측하기", type="primary", use_container_width=True):
    payload = {
        "data": [float(s_l), float(s_w), float(p_l), float(p_w)]
    }
    
    try:
        with st.spinner("GCP 서버로 예측 요청 중..."):
            response = requests.post(API_URL, json=payload, timeout=5)
            
        if response.status_code == 200:
            result = response.json()
            class_idx = result.get("class_index", 0)
            info = species_info.get(class_idx, {"name": f"클래스 {class_idx}", "desc": ""})
            
            st.success(f"### 🎉 예측 결과: **{info['name']}** (Class {class_idx})")
            if info["desc"]:
                st.info(info["desc"])
        else:
            st.error(f"서버 응답 오류 (HTTP Status: {response.status_code})")
            st.json(response.text)
            
    except requests.exceptions.Timeout:
        st.error("⏳ 요청 시간 초과: GCP VM 서버가 응답하지 않습니다. IP 및 포트(80) 방화벽을 확인하세요.")
    except requests.exceptions.ConnectionError:
        st.error("❌ 연결 실패: API 서버에 접속할 수 없습니다. VM 인스턴스가 켜져 있는지와 외부 IP를 확인하세요!")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
