import streamlit as st
import pandas as pd
import numpy as np
import openpyxl

# ---------------------------------------------------------
# 1. UI 디자인 (Breaking Bad Theme) 🧪
# ---------------------------------------------------------
st.set_page_config(page_title="Bakery Analytics V2", layout="wide", page_icon="💎")

breaking_bad_css = """
<style>
    .stApp { background-color: #0e1117; color: #e6e6e6; }
    h1 { font-family: 'Courier New', monospace; font-weight: 800; color: #ffffff; }
    .highlight-green {
        color: #4CAF50; background-color: #1a2e1a;
        padding: 0px 5px; border: 2px solid #4CAF50; display: inline-block;
    }
    /* 테이블 헤더 색상 변경 */
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #1a2e1a;
        color: #4CAF50;
        font-weight: bold;
    }
    div[data-testid="stMetric"] {
        background-color: #262730; border-left: 5px solid #F7D358;
        padding: 15px; border-radius: 5px;
    }
    div[data-testid="stMetricLabel"] { color: #F7D358 !important; font-weight: bold; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
</style>
"""
st.markdown(breaking_bad_css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 데이터 분석 엔진 (Logic) ⚗️
# ---------------------------------------------------------
@st.cache_data
def process_bakery_data(uploaded_file):
    try:
        # 파일 읽기
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None)
        else:
            df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')
        
        # 1. 요일 행 찾기 (월, 화, 수... 가 있는 행)
        # 보통 3행~5행 사이에 있음. 반복문으로 찾음
        weekdays_row_idx = -1
        for i in range(2, 6):
            row_values = df.iloc[i, :].astype(str).values
            if '월' in row_values or 'Mon' in row_values:
                weekdays_row_idx = i
                break
        
        if weekdays_row_idx == -1:
            return None, "요일 정보(월, 화...)를 찾을 수 없습니다."

        # 요일 데이터 정제
        weekdays_raw = df.iloc[weekdays_row_idx, 2:64].values[::2] # C열부터 2칸씩
        weekdays_clean = [str(w).strip() for w in weekdays_raw]
        
        # 주간/주말 구분 마스크
        is_weekday = np.array([w in ['월', '화', '수', '목', '금'] for w in weekdays_clean])
        is_weekend = np.array([w in ['토', '일'] for w in weekdays_clean])
        
        results = []
        
        # 2. 데이터 순회 (요일 행 다음 다음 행부터 데이터 시작으로 가정)
        start_row = weekdays_row_idx + 2 
        
        for i in range(start_row, len(df)):
            row = df.iloc[i]
            
            # ★ 수정사항: A열(인덱스 0)을 제품 이름으로 인식
            menu_name = str(row[0]).strip() 
            
            # 유효성 검사 (빈 값, '입력한 사람' 등 제외. ★ '합계'는 포함!)
            if pd.isna(row[0]) or menu_name in ['nan', '입력한 사람', '생산리스트', '전체 폐기율', '메뉴별 폐기 합계']:
                continue
            
            # 이름이 없으면 건너뜀
            if not menu_name:
                continue

            # 데이터 추출 (C열=2 부터 BK열=63 까지 2칸 간격)
            prod_vals = pd.to_numeric(row[2:64:2], errors='coerce').fillna(0).values
            waste_vals = pd.to_numeric(row[3:65:2], errors='coerce').fillna(0).values
            sales_vals = prod_vals - waste_vals
            
            # 주간 통계
            w_prod = prod_vals[is_weekday].sum()
            w_sales = sales_vals[is_weekday].sum()
            w_waste = waste_vals[is_weekday].sum()
            w_rate = (w_waste / w_prod * 100) if w_prod > 0 else 0
            
            # 주말 통계
            e_prod = prod_vals[is_weekend].sum()
            e_sales = sales_vals[is_weekend].sum()
            e_waste = waste_vals[is_weekend].sum()
            e_rate = (e_waste / e_prod * 100) if e_prod > 0 else 0
            
            results.append({
                '메뉴명': menu_name,
                '주간_판매': int(w_sales),
                '주간_생산': int(w_prod),
                '주간_폐기율(%)': round(w_rate, 1),
                '주말_판매': int(e_sales),
                '주말_생산': int(e_prod),
                '주말_폐기율(%)': round(e_rate, 1)
            })
            
        return pd.DataFrame(results), None
        
    except Exception as e:
        return None, str(e)

# ---------------------------------------------------------
# 3. 앱 화면 구성 (Layout) 📺
# ---------------------------------------------------------
st.markdown("""
    <h1><span class="highlight-green">Ba</span>kery <span class="highlight-green">Da</span>ta Analytics <span style="font-size:0.5em; color:#666;">v2.0</span></h1>
""", unsafe_allow_html=True)

st.divider()

# 사이드바: 파일 업로드 및 필터
with st.sidebar:
    st.header("🎛️ Control Panel")
    uploaded_file = st.file_uploader("파일 업로드 (Excel/CSV)", type=['xlsx', 'csv'])
    
    st.markdown("---")
    st.subheader("🔍 정렬 필터 (Sort By)")
    sort_criterion = st.radio(
        "무엇을 기준으로 정렬할까요?",
        ('판매량 높은 순 (Best Seller)', '폐기율 높은 순 (High Waste)', '폐기율 낮은 순 (Low Waste)', '이름 순 (A-Z)')
    )

if uploaded_file is not None:
    df_result, error_msg = process_bakery_data(uploaded_file)

    if error_msg:
        st.error(f"오류 발생: {error_msg}")
    elif df_result is not None and not df_result.empty:
        
        # 1. 정렬 로직 적용
        if '판매량' in sort_criterion:
            # 주말 + 주간 합쳐서 전체 판매량 기준으로 정렬
            df_result['전체_판매'] = df_result['주간_판매'] + df_result['주말_판매']
            df_sorted = df_result.sort_values(by='전체_판매', ascending=False).drop(columns=['전체_판매'])
        elif '폐기율 높은' in sort_criterion:
            # 주간 폐기율 기준 내림차순
            df_sorted = df_result.sort_values(by='주간_폐기율(%)', ascending=False)
        elif '폐기율 낮은' in sort_criterion:
            # 주간 폐기율 기준 오름차순
            df_sorted = df_result.sort_values(by='주간_폐기율(%)', ascending=True)
        else:
            df_sorted = df_result.sort_values(by='메뉴명')

        # 2. '합계' 행은 맨 위로 올리기 (데이터프레임 분리)
        total_row = df_sorted[df_sorted['메뉴명'].str.contains('합계')]
        menu_rows = df_sorted[~df_sorted['메뉴명'].str.contains('합계')]
        
        # 합계가 있으면 맨 위에 붙이기
        final_df = pd.concat([total_row, menu_rows])

        st.success(f"분석 완료! 총 {len(final_df)}개의 항목을 분석했습니다.")

        # 3. 데이터 표시
        st.dataframe(
            final_df,
            column_config={
                "메뉴명": st.column_config.TextColumn("메뉴명", help="제품 이름 (A열)"),
                "주간_폐기율(%)": st.column_config.ProgressColumn(
                    "주간 폐기율", format="%.1f%%", min_value=0, max_value=100
                ),
                "주말_폐기율(%)": st.column_config.ProgressColumn(
                    "주말 폐기율", format="%.1f%%", min_value=0, max_value=100
                ),
            },
            hide_index=True,
            use_container_width=True,
            height=600 # 표 높이 조절
        )
        
    else:
        st.warning("데이터를 분석할 수 없습니다. 엑셀 형식을 확인해주세요.")

else:
    st.info("👈 왼쪽 사이드바에서 엑셀 파일을 업로드해주세요.")