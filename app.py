import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# 1. UI 디자인 (Breaking Bad Theme) 🧪
# ---------------------------------------------------------
st.set_page_config(page_title="Bakery Analytics", layout="wide", page_icon="💎")

breaking_bad_css = """
<style>
    .stApp { background-color: #0e1117; color: #e6e6e6; }
    h1 { font-family: 'Courier New', monospace; font-weight: 800; color: #ffffff; }
    .highlight-green {
        color: #4CAF50; background-color: #1a2e1a;
        padding: 0px 5px; border: 2px solid #4CAF50; display: inline-block;
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
@st.cache_data  # 서버 속도를 위해 계산 결과를 기억해둠
def process_bakery_data(uploaded_file):
    try:
        # 파일 확장자에 따라 읽는 방식 구분
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None)
        else:
            # 엑셀 파일일 경우 openpyxl 엔진 사용
            df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')
        
        # 요일 행 찾기 (4행 또는 5행)
        weekdays_raw = df.iloc[3, 2:64].values[::2]
        if pd.isna(weekdays_raw).all() or '월' not in str(weekdays_raw):
            weekdays_raw = df.iloc[4, 2:64].values[::2]
            
        weekdays_clean = [str(w).strip() for w in weekdays_raw]
        
        # 주간/주말 구분
        is_weekday = np.array([w in ['월', '화', '수', '목', '금'] for w in weekdays_clean])
        is_weekend = np.array([w in ['토', '일'] for w in weekdays_clean])
        
        results = []
        
        # 데이터 순회 (6행부터 시작 가정)
        for i in range(6, len(df)):
            row = df.iloc[i]
            menu_name = str(row[1]).strip()
            
            if pd.isna(row[1]) or menu_name in ['합계', '입력한 사람', '생산리스트', 'nan', '전체 폐기율']:
                continue
                
            # 데이터 추출
            prod_vals = pd.to_numeric(row[2:64:2], errors='coerce').fillna(0).values
            waste_vals = pd.to_numeric(row[3:65:2], errors='coerce').fillna(0).values
            sales_vals = prod_vals - waste_vals
            
            # 주간 계산
            w_prod = prod_vals[is_weekday].sum()
            w_waste = waste_vals[is_weekday].sum()
            w_sales = sales_vals[is_weekday].sum()
            w_rate = (w_waste / w_prod * 100) if w_prod > 0 else 0
            
            # 주말 계산
            e_prod = prod_vals[is_weekend].sum()
            e_waste = waste_vals[is_weekend].sum()
            e_sales = sales_vals[is_weekend].sum()
            e_rate = (e_waste / e_prod * 100) if e_prod > 0 else 0
            
            results.append({
                '메뉴명': menu_name,
                '주간_생산': int(w_prod), '주간_판매': int(w_sales), '주간_폐기율(%)': round(w_rate, 1),
                '주말_생산': int(e_prod), '주말_판매': int(e_sales), '주말_폐기율(%)': round(e_rate, 1)
            })
            
        return pd.DataFrame(results)
        
    except Exception as e:
        return None

# ---------------------------------------------------------
# 3. 앱 화면 구성 (Layout) 📺
# ---------------------------------------------------------
st.markdown("""
    <h1><span class="highlight-green">Ba</span>kery <span class="highlight-green">Da</span>ta Analysis</h1>
""", unsafe_allow_html=True)

st.divider()

uploaded_file = st.file_uploader("파일을 투입구에 넣으세요 (CSV 또는 Excel)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    df_result = process_bakery_data(uploaded_file)

    if df_result is not None and not df_result.empty:
        st.success("Analysis Complete: 99.1% Pure")
        
        sort_option = st.selectbox("정렬 기준 (Sort By)", ['주말_판매', '주간_판매', '주간_폐기율(%)', '주말_폐기율(%)'])
        df_sorted = df_result.sort_values(by=sort_option, ascending=False)
        
        st.dataframe(
            df_sorted,
            column_config={
                "주간_폐기율(%)": st.column_config.ProgressColumn("주간 폐기율", format="%.1f%%", min_value=0, max_value=100),
                "주말_폐기율(%)": st.column_config.ProgressColumn("주말 폐기율", format="%.1f%%", min_value=0, max_value=100),
            },
            hide_index=True, use_container_width=True
        )
        
        st.divider()
        
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_menu = st.radio("상세 분석할 메뉴 선택", df_sorted['메뉴명'].head(10))
        
        with col2:
            if selected_menu:
                menu_row = df_sorted[df_sorted['메뉴명'] == selected_menu].iloc[0]
                st.markdown(f"### 🔬 {selected_menu} 분석 결과")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("평일(주간) 판매량", f"{menu_row['주간_판매']}개")
                    st.metric("평일 폐기율", f"{menu_row['주간_폐기율(%)']}%")
                with c2:
                    st.metric("주말 판매량", f"{menu_row['주말_판매']}개", delta=int(menu_row['주말_판매'] - menu_row['주간_판매']))
                    st.metric("주말 폐기율", f"{menu_row['주말_폐기율(%)']}%")
    else:
        st.error("데이터를 읽을 수 없습니다. 파일 형식을 확인해주세요.")