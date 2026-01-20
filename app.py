import streamlit as st
import pandas as pd
import numpy as np
import openpyxl

# ---------------------------------------------------------
# 1. UI 디자인 (Breaking Bad Theme) 🧪
# ---------------------------------------------------------
st.set_page_config(page_title="Bakery Analytics V4", layout="wide", page_icon="💎")

breaking_bad_css = """
<style>
    .stApp { background-color: #0e1117; color: #e6e6e6; }
    h1 { font-family: 'Courier New', monospace; font-weight: 800; color: #ffffff; }
    .highlight-green {
        color: #4CAF50; background-color: #1a2e1a;
        padding: 0px 5px; border: 2px solid #4CAF50; display: inline-block;
    }
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #1a2e1a; color: #4CAF50; font-weight: bold;
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
def load_excel_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.xlsx'):
            return pd.read_excel(uploaded_file, sheet_name=None, header=None, engine='openpyxl'), None
        elif uploaded_file.name.endswith('.csv'):
            return {'Default': pd.read_csv(uploaded_file, header=None)}, None
    except Exception as e:
        return None, str(e)

def analyze_sheet(df, sheet_name):
    try:
        # -----------------------------------------------------
        # STEP 1: 헤더 처리 (사장님 지시사항: 1행=요일, 2행=날짜)
        # -----------------------------------------------------
        # 파이썬은 0부터 시작하므로 1행은 index 0 입니다.
        
        # 1행(요일) 가져오기 & 병합된 셀 채우기 (ffill)
        # A열(0)은 비어있거나 헤더일 테니 제외하고 B열(1)부터 끝까지
        raw_days = df.iloc[0, 1:] 
        filled_days = raw_days.ffill() # 월, Nan -> 월, 월 (빈칸 채우기)
        
        days_list = filled_days.astype(str).values
        days_clean = [d.strip() for d in days_list]

        # 주간/주말 판별 마스크 생성 (생산/폐기 2열씩 짝이 맞아야 함)
        # B열부터 시작하므로 데이터 열 개수만큼 마스크 생성
        is_weekday = np.array([d in ['월', '화', '수', '목', '금', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'] for d in days_clean])
        is_weekend = np.array([d in ['토', '일', 'Sat', 'Sun'] for d in days_clean])

        # -----------------------------------------------------
        # STEP 2: 데이터 처리 (사장님 지시사항: A3 밑인 4행부터 데이터)
        # -----------------------------------------------------
        results = []
        total_row_data = None # 합계 행 저장용
        
        # 4행 (Index 3) 부터 끝까지 반복
        start_row = 3 
        
        for i in range(start_row, len(df)):
            row = df.iloc[i]
            
            # A열: 제품 이름
            menu_name = str(row[0]).strip()
            
            # 건너뛰기 조건 (빈 값, 헤더 등)
            if pd.isna(row[0]) or menu_name in ['nan', '생산리스트', '입력한 사람', '전체 폐기율', '메뉴별 폐기 합계']:
                continue
            
            # 데이터 추출: B열(1) 부터 끝까지
            # 데이터 순서: [생산, 폐기, 생산, 폐기 ...] (요일별 2열씩)
            row_data = pd.to_numeric(row[1:], errors='coerce').fillna(0).values
            
            # 데이터 길이 맞추기 (헤더 길이와 데이터 길이가 다를 경우 방지)
            min_len = min(len(row_data), len(is_weekday))
            current_data = row_data[:min_len]
            current_weekday = is_weekday[:min_len]
            current_weekend = is_weekend[:min_len]
            
            # 생산량(짝수 인덱스), 폐기량(홀수 인덱스) 분리
            # current_data는 [생산1, 폐기1, 생산2, 폐기2 ...] 형태
            prod_all = current_data[0::2]
            waste_all = current_data[1::2]
            
            # 마스크도 2칸씩 건너뛰며 적용 (요일 당 1개의 True/False가 필요하므로)
            # is_weekday는 [월, 월, 화, 화...] 형태이므로 짝수 인덱스만 가져오면 [월, 화...] 가 됨
            mask_weekday = current_weekday[0::2]
            mask_weekend = current_weekend[0::2]
            
            # 길이 재검증 (생산량 배열과 마스크 배열 길이가 같아야 함)
            calc_len = min(len(prod_all), len(mask_weekday))
            prod_all = prod_all[:calc_len]
            waste_all = waste_all[:calc_len]
            mask_weekday = mask_weekday[:calc_len]
            mask_weekend = mask_weekend[:calc_len]
            
            sales_all = prod_all - waste_all

            # --- 통계 계산 ---
            # 1. 주간 (Weekday)
            w_prod = prod_all[mask_weekday].sum()
            w_waste = waste_all[mask_weekday].sum()
            w_sales = sales_all[mask_weekday].sum()
            w_rate = (w_waste / w_prod * 100) if w_prod > 0 else 0
            
            # 2. 주말 (Weekend)
            e_prod = prod_all[mask_weekend].sum()
            e_waste = waste_all[mask_weekend].sum()
            e_sales = sales_all[mask_weekend].sum()
            e_rate = (e_waste / e_prod * 100) if e_prod > 0 else 0
            
            data_dict = {
                '메뉴명': menu_name,
                '주간_생산': int(w_prod),
                '주간_판매': int(w_sales),
                '주간_폐기율(%)': round(w_rate, 1),
                '주말_생산': int(e_prod),
                '주말_판매': int(e_sales),
                '주말_폐기율(%)': round(e_rate, 1)
            }
            
            # '합계' 행이면 따로 저장, 아니면 결과 리스트에 추가
            if '합계' in menu_name:
                total_row_data = data_dict
            else:
                results.append(data_dict)
            
        return pd.DataFrame(results), total_row_data, None

    except Exception as e:
        return None, None, str(e)

# ---------------------------------------------------------
# 3. 앱 화면 구성 (Layout) 📺
# ---------------------------------------------------------
st.markdown("""
    <h1><span class="highlight-green">Ba</span>kery <span class="highlight-green">Da</span>ta Analytics <span style="font-size:0.5em; color:#666;">v4.0</span></h1>
""", unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.header("🎛️ Control Panel")
    uploaded_file = st.file_uploader("엑셀 파일 투입 (.xlsx)", type=['xlsx', 'csv'])
    
    selected_sheet = None
    if uploaded_file:
        sheets_dict, load_err = load_excel_file(uploaded_file)
        if load_err:
            st.error(f"Error: {load_err}")
        else:
            sheet_names = list(sheets_dict.keys())
            st.markdown("---")
            selected_sheet_name = st.selectbox("📅 월 선택 (Select Sheet)", sheet_names)
            selected_sheet = sheets_dict[selected_sheet_name]

    st.markdown("---")
    st.subheader("🔍 정렬 기준")
    sort_criterion = st.radio("Sort By:", ('판매량 높은 순', '폐기율 높은 순', '폐기율 낮은 순', '이름 순'))

if uploaded_file and selected_sheet is not None:
    st.markdown(f"### 🧪 Analysis Result: {selected_sheet_name}")
    
    # 분석 실행
    df_result, total_data, analyze_err = analyze_sheet(selected_sheet, selected_sheet_name)
    
    if analyze_err:
        st.error(f"분석 오류: {analyze_err}")
    elif df_result is not None and not df_result.empty:
        
        # 1. 정렬 로직
        if '판매량' in sort_criterion:
            df_result['총판매'] = df_result['주간_판매'] + df_result['주말_판매']
            df_sorted = df_result.sort_values(by='총판매', ascending=False).drop(columns=['총판매'])
        elif '폐기율 높은' in sort_criterion:
            df_sorted = df_result.sort_values(by='주간_폐기율(%)', ascending=False)
        elif '폐기율 낮은' in sort_criterion:
            df_sorted = df_result.sort_values(by='주간_폐기율(%)', ascending=True)
        else:
            df_sorted = df_result.sort_values(by='메뉴명')

        # 2. 합계 행 처리 (맨 아래로 붙이기)
        if total_data:
            total_df = pd.DataFrame([total_data])
            # 합계 행 시각적 구분을 위해 이름 변경
            total_df['메뉴명'] = "📊 전체 합계 (Total)"
            final_df = pd.concat([df_sorted, total_df], ignore_index=True)
        else:
            final_df = df_sorted

        # 3. 테이블 출력
        st.dataframe(
            final_df,
            column_config={
                "메뉴명": st.column_config.TextColumn("메뉴명", width="medium"),
                # 순서: 생산 -> 판매 -> 폐기율
                "주간_생산": st.column_config.NumberColumn("주간 생산", format="%d개"),
                "주간_판매": st.column_config.NumberColumn("주간 판매", format="%d개"),
                "주간_폐기율(%)": st.column_config.ProgressColumn("주간 폐기율", format="%.1f%%", min_value=0, max_value=100),
                "주말_생산": st.column_config.NumberColumn("주말 생산", format="%d개"),
                "주말_판매": st.column_config.NumberColumn("주말 판매", format="%d개"),
                "주말_폐기율(%)": st.column_config.ProgressColumn("주말 폐기율", format="%.1f%%", min_value=0, max_value=100),
            },
            hide_index=True,
            use_container_width=True,
            height=800
        )
    else:
        st.warning("데이터를 분석할 수 없습니다. 1행(요일), 4행(데이터 시작) 형식이 맞는지 확인해주세요.")
elif not uploaded_file:
    st.info("👈 엑셀 파일을 업로드해주세요.")