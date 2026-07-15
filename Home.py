import streamlit as st
from pathlib import Path
import shutil
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_FILE = ROOT_DIR / "default_live_data.csv"
LIVE_DATA_FILE = ROOT_DIR / "live_data.csv"


@st.cache_resource
def initialize_runtime_data_bus() -> bool:
    """
    每次云端进程启动时执行一次：
    用内置默认曲线初始化运行数据。
    普通页面切换和控件操作不会反复覆盖。
    """
    if not DEFAULT_DATA_FILE.exists():
        raise FileNotFoundError(
            f"未找到默认数据文件：{DEFAULT_DATA_FILE}"
        )

    shutil.copy2(DEFAULT_DATA_FILE, LIVE_DATA_FILE)
    return True


initialize_runtime_data_bus()

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
