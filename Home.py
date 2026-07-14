import streamlit as st

st.set_page_config(
    page_title="核电重大设备智能监测预警系统",
    page_icon="☢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 将系统导航固定在左侧栏。页面滚动时导航不会覆盖主标题或曲线图。
st.markdown(
    """
    <style>
    section[data-testid="stSidebarNav"] {
        padding-top: 0.25rem !important;
        padding-bottom: 0.20rem !important;
        margin-bottom: 0.15rem !important;
    }
    section[data-testid="stSidebarNav"] ul {
        gap: 0.10rem !important;
    }
    section[data-testid="stSidebarNav"] a {
        min-height: 2.15rem !important;
        padding-top: 0.30rem !important;
        padding-bottom: 0.30rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

detection_page = st.Page(
    "pages/app_detection.py",
    title="智能监测",
    icon="📊",
    default=True,
)

simulation_page = st.Page(
    "pages/app_simulation.py",
    title="工况仿真",
    icon="🎛️",
)

current_page = st.navigation(
    [detection_page, simulation_page],
    position="sidebar",
)

current_page.run()
