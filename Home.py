import streamlit as st

st.set_page_config(
    page_title="核电重大设备智能监测预警系统",
    page_icon="☢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 使用显式导航替代 pages/ 自动生成的“Home / 应用检测 / 应用模拟”。
# 导航放到页面顶部，释放左侧工具栏的纵向空间。
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
    position="top",
)

current_page.run()
