import streamlit as st
import pandas as pd
import numpy as np
import openpyxl

# ---------------------------------------------------------
# 1. UI 디자인 (Breaking Bad Theme) 🧪
# ---------------------------------------------------------
st.set_page_config(page_title="Bakery Analytics V3", layout="wide", page_icon="💎")

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
    """엑셀 파일을 통째로 읽어서 시트 이름들을 반환"""
    try:
        # 엑셀 파일인 경우 모든 시트를 읽음
        if uploaded_file.name.endswith('.xlsx'):
            # sheet_name=None이면 모든 시트를 딕셔너리로 가져옴
            all_sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None, engine='openpyxl')
            return all_sheets, None
        elif uploaded_file.name.endswith('.csv'):
            # CSV는 시트 개념이 없으므로 단일 딕셔너리로 처리
            df = pd.read_csv(uploaded_file, header=None)
            return {'Default': df}, None
    except Exception as e:
        return None, str(e)

def analyze_sheet(df, sheet_name):
    """특정 시트(Month)의 데이터를 분석"""
    try:
        # 1. 요일 행 찾기 (병합된 셀 고려하여 '월' 또는 'Mon' 찾기)
        weekdays_row_idx = -1
        # 보통 상단 10줄 이내에 요일 헤더가 있음
        for i in range(10): 
            row_values = df.iloc[i, :].astype(str).values
            # 행에 '월'과 '화'가 동시에 있거나 'Mon'이 포함되어 있다면 요일 행으로 간주
            if ('월' in row_values and '화' in row_values) or 'Mon' in row_values:
                weekdays_row_idx = i
                break
        
        if weekdays_row_idx == -1:
            return None, f"'{sheet_name}' 시트에서 요일 행(월, 화...)을 찾을 수 없습니다."

        # 2. 요일 데이터 정제 (★핵심: 병합된 셀 처리 Forward Fill)
        # 해당 행 전체를 가져옴
        raw_days_row = df.iloc[weekdays_row_idx, :]
        
        # 앞의 값으로 채우기 (Merge Cell 대응)
        # 주의: 엑셀 읽을 때 header=None이므로 인덱스로 접근
        # 데이터는 보통 C열(2) 또는 D열(3)부터 시작. 
        # 안전하게 전체 행을 ffill() 한 뒤 슬라이싱
        filled_days_row = raw_days_row.ffill()
        
        # 데이터 시작 열 찾기 (요일이 시작되는 첫 번째 열)
        # 보통 '생산'/'폐기' 데이터는 숫자 데이터이므로 요일이 있는 열부터 시작
        # 여기서는 기존 로직대로 C열(2)부터 시작한다고 가정하되, 검증 필요
        # 데이터 범위: C열(2) ~ BK열(63) (기존 파일 기준)
        
        weekdays_clean = filled_days_row.iloc[2:64].astype(str).values
        weekdays_clean = [w.strip() for w in weekdays_clean]

        # 주간/주말 마스크 생성
        is_weekday = np.array([w in ['월', '화', '수', '목', '금'] for w in weekdays_clean])
        is_weekend = np.array([w in ['토', '일'] for w in weekdays_clean])

        # 3. 메뉴 데이터 분석
        results = []
        # 데이터는 요일 행 2칸 밑에서부터 시작한다고 가정 (요일행 -> 날짜행 -> 헤더행 -> 데이터)
        # 혹은 "생산리스트" 또는 제품명이 나오는 곳을 찾아야 함.
        # 안전하게 요일행 + 2 부터 시작
        start_row = weekdays_row_idx + 2
        
        for i in range(start_row, len(df)):
            row = df.iloc[i]
            
            # A열(0)을 메뉴명으로 인식
            menu_name = str(row[0]).strip()
            
            # 유효성 검사
            # 'nan', '입력한 사람', '생산리스트' 등 제외
            # ★ '합계'는 포함하되, 리스트에서 식별 가능하게
            if pd.isna(row[0]) or menu_name in ['nan', '입력한 사람', '생산리스트', '전체 폐기율', '메뉴별 폐기 합계', 'None']:
                continue
                
            # 메뉴명이 너무 짧거나(1글자 이하) 숫자로만 된 경우 건너뛰기 (날짜 행 등 방지)
            if len(menu_name) < 1: 
                continue

            # 데이터 추출 (생산: 짝수 인덱스, 폐기: 홀수 인덱스) relative to start column (2)
            # C열(2) 부터 BK열(63)까지
            subset = row.iloc[2:64]
            
            # 2칸 간격으로 슬라이싱
            prod_vals = pd.to_numeric(subset.iloc[0::2], errors='coerce').fillna(0).values
            waste_vals = pd.to_numeric(subset.iloc[1::2], errors='coerce').fillna(0).values
            
            # 길이 검증 (마스크와 데이터 길이가 같아야 함)
            if len(prod_vals) != len(is_weekday):
                # 데이터 길이가 안 맞으면 해당 행 스킵 (혹은 길이에 맞게 자름)
                min_len = min(len(prod_vals), len(is_weekday))
                prod_vals = prod_vals[:min_len]
                waste_vals = waste_vals[:min_len]
                current_is_weekday = is_weekday[:min_len]
                current_is_weekend = is_weekend[:min_len]
            else:
                current_is_weekday = is_weekday
                current_is_weekend = is_weekend

            sales_vals = prod_vals - waste_vals
            
            # 주간 통계
            w_prod = prod_vals[current_is_weekday].sum()
            w_waste = waste_vals[current_is_weekday].sum()
            w_sales = sales_vals[current_is_weekday].sum()
            w_rate = (w_waste / w_prod * 100) if w_prod > 0 else 0
            
            # 주말 통계
            e_prod = prod_vals[current_is_weekend].sum()
            e_waste = waste_vals[current_is_weekend].sum()
            e_sales = sales_vals[current_is_weekend].sum()
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
    <h1><span class="highlight-green">Ba</span>kery <span class="highlight-green">Da</span>ta Analytics <span style="font-size:0.5em; color:#666;">v3.0</span></h1>
""", unsafe_allow_html=True)

st.divider()

# 사이드바 설정
with st.sidebar:
    st.header("🎛️ Control Panel")
    uploaded_file = st.file_uploader("엑셀 파일 투입 (.xlsx)", type=['xlsx', 'csv'])
    
    selected_sheet = None
    
    if uploaded_file is not None:
        sheets_dict, load_err = load_excel_file(uploaded_file)
        
        if load_err:
            st.error(f"파일 로드 실패: {load_err}")
        else:
            # 시트 선택 기능 추가
            sheet_names = list(sheets_dict.keys())
            st.markdown("---")
            st.subheader("📅 월 선택 (Select Month)")
            selected_sheet_name = st.selectbox("분석할 시트를 선택하세요", sheet_names)
            
            selected_sheet = sheets_dict[selected_sheet_name]

    st.markdown("---")
    st.subheader("🔍 정렬 기준")
    sort_criterion = st.radio(
        "Sort By:",
        ('판매량 높은 순', '폐기율 높은 순', '폐기율 낮은 순', '이름 순')
    )

# 메인 화면 분석 결과 표시
if uploaded_file is not None and selected_sheet is not None:
    st.markdown(f"### 🧪 Analysis Result: {selected_sheet_name}")
    
    df_result, analyze_err = analyze_sheet(selected_sheet, selected_sheet_name)
    
    if analyze_err:
        st.error(f"분석 오류: {analyze_err}")
    elif df_result is not None and not df_result.empty:
        
        # 1. 정렬
        if '판매량' in sort_criterion:
            df_result['전체_판매'] = df_result['주간_판매'] + df_result['주말_판매']
            df_sorted = df_result.sort_values(by='전체_판매', ascending=False).drop(columns=['전체_판매'])
        elif '폐기율 높은' in sort_criterion:
            df_sorted = df_result.sort_values(by='주간_폐기율(%)', ascending=False)
        elif '폐기율 낮은' in sort_criterion:
            df_sorted = df_result.sort_values(by='주간_폐기율(%)', ascending=True)
        else:
            df_sorted = df_result.sort_values(by='메뉴명')

        # 2. 합계 행 맨 위로
        total_row = df_sorted[df_sorted['메뉴명'].str.contains('합계')]
        menu_rows = df_sorted[~df_sorted['메뉴명'].str.contains('합계')]
        final_df = pd.concat([total_row, menu_rows])
        
        # 3. 결과 표시
        st.dataframe(
            final_df,
            column_config={
                "메뉴명": st.column_config.TextColumn("메뉴명", width="medium"),
                "주간_폐기율(%)": st.column_config.ProgressColumn(
                    "주간 폐기율", format="%.1f%%", min_value=0, max_value=100
                ),
                "주말_폐기율(%)": st.column_config.ProgressColumn(
                    "주말 폐기율", format="%.1f%%", min_value=0, max_value=100
                ),
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )
    else:
        st.warning("해당 시트에서 유효한 데이터를 찾지 못했습니다. 데이터 구조를 확인해주세요.")

elif uploaded_file is None:
    st.info("👈 왼쪽에서 엑셀 파일을 업로드하면 분석이 시작됩니다.")