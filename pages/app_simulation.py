import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os
import re
import hashlib
import sys
import os
st.set_page_config(page_title="核电参数仿真输入系统", page_icon="🎛️", layout="wide")

# 页面顶部与侧边栏标题对齐：右上角工具栏保留悬浮，左侧标题上移到与主标题同一视觉高度。
st.markdown("""
<style>
.block-container {
    padding-top: 1.15rem !important;
    padding-bottom: 1rem !important;
}
[data-testid="stHeader"] {
    height: 0rem !important;
    background: transparent !important;
}
[data-testid="stToolbar"] {
    right: 0.75rem !important;
    top: 0.25rem !important;
}
section[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebarContent"] {
    padding-top: 0rem !important;
}
/* 侧边栏标题与右侧主标题做像素级视觉对齐：上一版上移过多，这里下调约 8px。 */
.sidebar-main-title {
    margin-top: -1.85rem !important;
    margin-bottom: 0.85rem !important;
    padding: 0 !important;
    font-size: 1.62rem !important;
    line-height: 1.20 !important;
    font-weight: 800 !important;
    color: #1f2a44 !important;
    white-space: nowrap !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    margin-top: 0.15rem !important;
}
</style>
""", unsafe_allow_html=True)



def get_resource_path(relative_path):
    """
    获取资源的绝对路径。
    无论是直接运行 Python 脚本，还是被 PyInstaller 打包成 .exe 运行，都能动态找到文件。
    """
    if hasattr(sys, '_MEIPASS'):
        # 如果是被 PyInstaller 打包后的 .exe 运行，文件会被解压到 sys._MEIPASS 临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    # 如果是开发环境下直接运行，返回当前工作目录下的相对路径
    return os.path.join(os.path.abspath("."), relative_path)

# 使用兼容函数获取真实的文件路径
CONFIG_FILE = get_resource_path("active_points_config.csv")
DATA_FILE = get_resource_path("live_data.csv")

# ==========================================
# 实时演示时间轴配置
# ==========================================
# 旧版仿真曲线以 2026-06-05 00:00 为最终时刻。新版将这个最终时刻平移到当前真实时间，
# 并向前展示 5 天窗口；曲线形状、幅值和异常相对最终时刻的位置保持不变。
SIM_BASE_START = pd.Timestamp("2026-06-01 00:00:00")
SIM_BASE_END = pd.Timestamp("2026-06-05 00:00:00")
SIM_FREQ = "10min"
REALTIME_WINDOW_DAYS = 5


def get_realtime_end():
    """当前实时检测终点，按分钟取整，避免演示时间比真实时间慢一截。
    采样间隔仍保持 10 分钟，只是整条时间轴的终点贴近当前真实时间。
    """
    return pd.Timestamp.now().floor("min")


def build_realtime_time_axes():
    """
    返回：
    - real_index：展示/写入 live_data.csv 的真实时间轴，范围为当前时刻往前 5 天；
    - sim_eval_index：用于保持旧曲线形状的内部计算时间轴。

    例如旧曲线 2026-06-03 00:00 的异常距离旧终点 2026-06-05 00:00 为 2 天，
    平移后仍会出现在“当前实时终点 - 2 天”。
    由于展示窗口是 5 天，而旧模板有效形状为 4 天，最前面额外 1 天会保持旧模板起点附近的稳定工况。
    """
    real_end = get_realtime_end()
    real_start = real_end - pd.Timedelta(days=REALTIME_WINDOW_DAYS)
    real_index = pd.date_range(start=real_start, end=real_end, freq=SIM_FREQ)
    shift = real_end - SIM_BASE_END
    sim_eval_index = real_index - shift
    sim_eval_index = pd.DatetimeIndex([max(t, SIM_BASE_START) for t in sim_eval_index])
    return real_index, sim_eval_index, real_end, shift


def format_trigger_time(start_idx, n, time_index=None):
    """将场景计划中的触发时刻显示为真实时间轴上的时间。"""
    if time_index is not None and len(time_index) > 0:
        idx = min(max(int(start_idx), 0), len(time_index) - 1)
        return pd.to_datetime(time_index[idx]).strftime('%Y-%m-%d %H:%M:%S')
    idx = min(max(int(start_idx), 0), n - 1)
    return pd.date_range(start=SIM_BASE_START, periods=n, freq=SIM_FREQ)[idx].strftime('%Y-%m-%d %H:%M:%S')

# ==========================================
# 0. 核心状态初始化
# ==========================================
BUILT_IN_SYSTEMS = ["RHR反应堆余热排出系统", "RCV化学容积控制系统"]

CORE_SYSTEM_COLUMNS = ['系统', '编码', '测点名称', '基准值', '正常范围', '低2报', '低报', '高报', '高2报', '高3报', '单位']
CORE_SYSTEM_DATA = [
        # RHR 反应堆余热排出系统
        ['RHR反应堆余热排出系统', 'RHR004MP', 'RHR001PO泵出口管道压力', 0.6, '0.3-1.2', None, 0.3, 1.2, 3.0, 3.8,
         'MPa'],
        ['RHR反应堆余热排出系统', 'RHR005MP', 'RHR002PO泵出口管道压力', 0.6, '0.3-1.2', None, 0.3, 1.2, 3.0, 3.8,
         'MPa'],
        ['RHR反应堆余热排出系统', 'RHR006MD', 'A列RHR出口流量', 550.0, '400-670', 350.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR032MD', 'A列RHR出口流量', 550.0, '400-670', 350.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR008MD', 'B列RHR出口流量', 550.0, '400-670', 351.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR033MD', 'B列RHR出口流量', 550.0, '400-670', 351.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR016MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR118MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR018MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR120MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR017MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR119MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR019MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR121MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', '3RHR027MT', '3RHR002PO机械密封出口水温度', 32.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR026MT', '3RHR001PO机械密封出口水温度', 24.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR025MT', '3RHR002PO泵推力轴承温度（轴承外侧）', 33.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR024MT', '3RHR001PO泵推力轴承温度（轴承外侧）', 24.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR023MT', '3RHR002PO泵推力轴承温度（轴承内侧）', 33.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR022MT', '3RHR001PO泵推力轴承温度（轴承内侧）', 24.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR021MT', '3RHR002PO电机定子线圈绕组温度（W相）', 30.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR020MT', '3RHR001PO电机定子线圈绕组温度（W相）', 24.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR019MT', '3RHR002PO电机定子线圈绕组温度（V相）', 30.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR018MT', '3RHR001PO电机定子线圈绕组温度（V相）', 24.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR017MT', '3RHR002PO电机定子线圈绕组温度（U相）', 30.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR016MT', '3RHR001PO电机定子线圈绕组温度（U相）', 24.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR015MT', '3RHR002PO电机轴承温度（非轴伸端）', 31.5, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR014MT', '3RHR001PO电机轴承温度（非轴伸端）', 24.0, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR013MT', '3RHR002PO电机轴承温度（轴伸端）', 32.5, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR012MT', '3RHR001PO电机轴承温度（轴伸端）', 24.0, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR011MT', '3RHR002PO径向轴承温度（非驱动端）', 34.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR010MT', '3RHR001PO径向轴承温度（非驱动端）', 24.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        # RCV 化学容积控制系统
        ['RCV化学容积控制系统', 'RCV100MT', '上充泵电机驱动端轴承温度', 72.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV200MT', '上充泵电机驱动端轴承温度', 72.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV101MT', '上充泵电机非驱动端轴承温度', 68.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV201MT', '上充泵电机非驱动端轴承温度', 68.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV126MT', '上充泵油冷却器进口温度', 52.0, '0-65', None, None, 65.0, 70.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV226MT', '上充泵油冷却器进口温度', 52.0, '0-65', None, None, 65.0, 70.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV018MD', '上充管线流量', 16.0, '6.8-28.5', None, 6.8, 28.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV005MD', '下泄管线流量', 20.0, '0-33', None, None, 33.0, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV123MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV124MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV223MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV224MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV121MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV122MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV221MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV222MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV002MT', 'RCV换热器下游温度', 45.0, '0-57', None, None, 57.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV003MT', 'RCV换热器下游温度', 45.0, '0-57', None, None, 57.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV105MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV106MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV205MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV206MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV110MT', '上充泵径向轴承温度', 69.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV210MT', '上充泵径向轴承温度', 69.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV102MT', '上充泵电机绕组温度(U相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV103MT', '上充泵电机绕组温度(V相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV104MT', '上充泵电机绕组温度(W相)', 107.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV202MT', '上充泵电机绕组温度(U相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV203MT', '上充泵电机绕组温度(V相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV204MT', '上充泵电机绕组温度(W相)', 107.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV021MD', '密封注入水流量A', 2.1, '1.8-2.5', None, 1.32, 2.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV022MD', '密封注入水流量B', 2.1, '1.8-2.5', None, 1.32, 2.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV023MD', '密封注入水流量C', 2.1, '1.8-2.5', None, 1.32, 2.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV046VP', '上充流量调节阀', 50.0, '0-100', None, None, None, None, None, '%'],
        ['RCV化学容积控制系统', 'RCV064MT', '主泵轴封注入水温度', 48.0, '0-65', None, None, 65.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV011MN', '容控箱水位', 1.5, '1.12-1.95', None, 1.09, 1.95, None, None, 'm'],
        ['RCV化学容积控制系统', 'RCV012MN', '容控箱水位', 1.5, '1.12-1.95', None, 1.09, 1.95, None, None, 'm']
    ]


def get_core_systems_df():
    """返回 RHR/RCV 两套基础系统的标准测点库。"""
    return pd.DataFrame(CORE_SYSTEM_DATA, columns=CORE_SYSTEM_COLUMNS)


def ensure_core_systems_in_config(base_df, config_file=CONFIG_FILE):
    """自动恢复被误删的 RHR/RCV 基础系统，并补齐缺失的基础测点。"""
    core_df = get_core_systems_df()

    if base_df is None or base_df.empty:
        restored_df = core_df.copy()
        restored_df.to_csv(config_file, index=False)
        return restored_df, BUILT_IN_SYSTEMS.copy()

    # 对齐列，兼容外部导入系统带来的新增字段。
    for col in core_df.columns:
        if col not in base_df.columns:
            base_df[col] = np.nan
    for col in base_df.columns:
        if col not in core_df.columns:
            core_df[col] = np.nan
    core_df = core_df[base_df.columns]

    current_keys = set((base_df['系统'].astype(str).str.strip() + '::' + base_df['编码'].astype(str).str.strip()).tolist())
    core_keys = core_df['系统'].astype(str).str.strip() + '::' + core_df['编码'].astype(str).str.strip()
    missing_core_df = core_df[~core_keys.isin(current_keys)].copy()

    restored_systems = []
    if not missing_core_df.empty:
        restored_systems = missing_core_df['系统'].dropna().unique().tolist()
        base_df = pd.concat([base_df, missing_core_df], ignore_index=True)
        base_df = base_df.drop_duplicates(subset=['系统', '编码'], keep='first')
        base_df.to_csv(config_file, index=False)

    return base_df, restored_systems


if 'p_matrix' not in st.session_state:
    st.session_state.p_matrix = {}
if 'random_baselines' not in st.session_state:
    st.session_state.random_baselines = {}
if 'simulation_plans' not in st.session_state:
    st.session_state.simulation_plans = {}

# ==========================================
# 1. 自动化全量标准数据库初始化引擎 (1:1 复刻您的全部测点数据)
# ==========================================
if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
    base_data = [
        # RHR 反应堆余热排出系统
        ['RHR反应堆余热排出系统', 'RHR004MP', 'RHR001PO泵出口管道压力', 0.6, '0.3-1.2', None, 0.3, 1.2, 3.0, 3.8,
         'MPa'],
        ['RHR反应堆余热排出系统', 'RHR005MP', 'RHR002PO泵出口管道压力', 0.6, '0.3-1.2', None, 0.3, 1.2, 3.0, 3.8,
         'MPa'],
        ['RHR反应堆余热排出系统', 'RHR006MD', 'A列RHR出口流量', 550.0, '400-670', 350.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR032MD', 'A列RHR出口流量', 550.0, '400-670', 350.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR008MD', 'B列RHR出口流量', 550.0, '400-670', 351.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR033MD', 'B列RHR出口流量', 550.0, '400-670', 351.0, 400.0, 670.0, None, None,
         'm³/h'],
        ['RHR反应堆余热排出系统', 'RHR016MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR118MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR018MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR120MM', 'A列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR017MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR119MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR019MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', 'RHR121MM', 'B列卸压保护阀阀位位移', 2.0, '0.5-4', None, 0.5, 4.0, None, None, 'mm'],
        ['RHR反应堆余热排出系统', '3RHR027MT', '3RHR002PO机械密封出口水温度', 32.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR026MT', '3RHR001PO机械密封出口水温度', 24.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR025MT', '3RHR002PO泵推力轴承温度（轴承外侧）', 33.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR024MT', '3RHR001PO泵推力轴承温度（轴承外侧）', 24.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR023MT', '3RHR002PO泵推力轴承温度（轴承内侧）', 33.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR022MT', '3RHR001PO泵推力轴承温度（轴承内侧）', 24.0, '0-80', None, None, 80.0,
         90.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR021MT', '3RHR002PO电机定子线圈绕组温度（W相）', 30.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR020MT', '3RHR001PO电机定子线圈绕组温度（W相）', 24.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR019MT', '3RHR002PO电机定子线圈绕组温度（V相）', 30.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR018MT', '3RHR001PO电机定子线圈绕组温度（V相）', 24.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR017MT', '3RHR002PO电机定子线圈绕组温度（U相）', 30.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR016MT', '3RHR001PO电机定子线圈绕组温度（U相）', 24.0, '0-130', None, None, 130.0,
         140.0, None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR015MT', '3RHR002PO电机轴承温度（非轴伸端）', 31.5, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR014MT', '3RHR001PO电机轴承温度（非轴伸端）', 24.0, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR013MT', '3RHR002PO电机轴承温度（轴伸端）', 32.5, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR012MT', '3RHR001PO电机轴承温度（轴伸端）', 24.0, '0-90', None, None, 90.0, 95.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR011MT', '3RHR002PO径向轴承温度（非驱动端）', 34.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        ['RHR反应堆余热排出系统', '3RHR010MT', '3RHR001PO径向轴承温度（非驱动端）', 24.0, '0-80', None, None, 80.0, 90.0,
         None, '℃'],
        # RCV 化学容积控制系统
        ['RCV化学容积控制系统', 'RCV100MT', '上充泵电机驱动端轴承温度', 72.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV200MT', '上充泵电机驱动端轴承温度', 72.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV101MT', '上充泵电机非驱动端轴承温度', 68.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV201MT', '上充泵电机非驱动端轴承温度', 68.0, '0-90', None, None, 90.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV126MT', '上充泵油冷却器进口温度', 52.0, '0-65', None, None, 65.0, 70.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV226MT', '上充泵油冷却器进口温度', 52.0, '0-65', None, None, 65.0, 70.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV018MD', '上充管线流量', 16.0, '6.8-28.5', None, 6.8, 28.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV005MD', '下泄管线流量', 20.0, '0-33', None, None, 33.0, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV123MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV124MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV223MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV224MT', '上充泵齿轮箱低速侧温度', 66.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV121MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV122MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV221MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV222MT', '上充泵齿轮箱高速侧温度', 63.0, '0-85', None, None, 85.0, 95.0, None, '℃'],
        ['RCV化学容积控制系统', 'RCV002MT', 'RCV换热器下游温度', 45.0, '0-57', None, None, 57.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV003MT', 'RCV换热器下游温度', 45.0, '0-57', None, None, 57.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV105MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV106MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV205MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV206MT', '上充泵推力轴承温度', 70.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV110MT', '上充泵径向轴承温度', 69.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV210MT', '上充泵径向轴承温度', 69.0, '0-90', None, None, 90.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV102MT', '上充泵电机绕组温度(U相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV103MT', '上充泵电机绕组温度(V相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV104MT', '上充泵电机绕组温度(W相)', 107.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV202MT', '上充泵电机绕组温度(U相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV203MT', '上充泵电机绕组温度(V相)', 95.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV204MT', '上充泵电机绕组温度(W相)', 107.0, '0-140', None, None, 140.0, None, None,
         '℃'],
        ['RCV化学容积控制系统', 'RCV021MD', '密封注入水流量A', 2.1, '1.8-2.5', None, 1.32, 2.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV022MD', '密封注入水流量B', 2.1, '1.8-2.5', None, 1.32, 2.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV023MD', '密封注入水流量C', 2.1, '1.8-2.5', None, 1.32, 2.5, None, None, 'm³/h'],
        ['RCV化学容积控制系统', 'RCV046VP', '上充流量调节阀', 50.0, '0-100', None, None, None, None, None, '%'],
        ['RCV化学容积控制系统', 'RCV064MT', '主泵轴封注入水温度', 48.0, '0-65', None, None, 65.0, None, None, '℃'],
        ['RCV化学容积控制系统', 'RCV011MN', '容控箱水位', 1.5, '1.12-1.95', None, 1.09, 1.95, None, None, 'm'],
        ['RCV化学容积控制系统', 'RCV012MN', '容控箱水位', 1.5, '1.12-1.95', None, 1.09, 1.95, None, None, 'm']
    ]
    df_init = pd.DataFrame(base_data,
                           columns=['系统', '编码', '测点名称', '基准值', '正常范围', '低2报', '低报', '高报', '高2报',
                                    '高3报', '单位'])
    df_init.to_csv(CONFIG_FILE, index=False)

base_system_df = pd.read_csv(CONFIG_FILE)
base_system_df, _restored_core_systems = ensure_core_systems_in_config(base_system_df)
if _restored_core_systems:
    st.sidebar.success("🔒 已自动恢复基础系统：" + "、".join(_restored_core_systems))


# ==========================================
# 1.1 工业仿真通用工具：报警边界、微量噪声、工程特性曲线
# ==========================================
ALARM_COLUMNS = ['低4报', '低3报', '低2报', '低报', '高报', '高2报', '高3报', '高4报']
LOW_ALARM_COLUMNS = ['低4报', '低3报', '低2报', '低报']
HIGH_ALARM_COLUMNS = ['高报', '高2报', '高3报', '高4报']


def make_state_key(system_name, code):
    """仿真状态的唯一键：必须同时绑定系统名和测点编码，避免不同系统同编码串流。"""
    return f"{str(system_name).strip()}::{str(code).strip()}"


def make_stream_prefix(system_name, code):
    """live_data.csv 的列名前缀。内置系统保持旧列名，新导入系统使用系统哈希隔离。"""
    code = str(code).strip()
    sys_name = str(system_name).strip()
    if sys_name in BUILT_IN_SYSTEMS:
        return code
    safe_code = re.sub(r'[^0-9A-Za-z_]+', '_', code)
    sys_hash = hashlib.md5(sys_name.encode('utf-8')).hexdigest()[:8]
    return f"SYS{sys_hash}_{safe_code}"


def stream_baseline_col(system_name, code):
    return f"{make_stream_prefix(system_name, code)}_Baseline"


def stream_actual_col(system_name, code):
    return f"{make_stream_prefix(system_name, code)}_Actual"


def legacy_code_key(code):
    """兼容旧版本遗留 session_state，启动/停止时同步清理，避免旧键继续污染新系统。"""
    return str(code).strip()

for _col in ALARM_COLUMNS:
    if _col not in base_system_df.columns:
        base_system_df[_col] = np.nan
    base_system_df[_col] = pd.to_numeric(base_system_df[_col], errors='coerce')


def safe_float(value):
    try:
        if pd.isna(value) or str(value).strip() == '':
            return None
        return float(value)
    except Exception:
        return None


def parse_normal_range(range_text):
    """从 0-90、0~90、1.12-1.95 这类文本中解析正常范围。"""
    if range_text is None or pd.isna(range_text):
        return None, None
    text = str(range_text)
    text = text.replace('～', '~').replace('—', '-').replace('－', '-')
    # 把两个数字之间的短横线视为范围分隔符，避免把右侧数字误识别为负数。
    text = re.sub(r'(?<=\d)\s*-\s*(?=\d)', '~', text)
    nums = re.findall(r'[-+]?\d+(?:\.\d+)?', text)
    if len(nums) >= 2:
        a, b = float(nums[0]), float(nums[1])
        return (min(a, b), max(a, b))
    return None, None


def get_valid_alarms(row):
    valid = {}
    for col in ALARM_COLUMNS:
        val = safe_float(row.get(col))
        if val is not None:
            valid[col] = val
    return valid


def get_normal_bounds(row, valid_alarms=None):
    """优先使用低1/高1报警线作为正常区间；缺失时回退到正常范围文本和基准值。"""
    if valid_alarms is None:
        valid_alarms = get_valid_alarms(row)
    range_low, range_high = parse_normal_range(row.get('正常范围'))
    low1 = safe_float(row.get('低报'))
    high1 = safe_float(row.get('高报'))

    low_bound = low1 if low1 is not None else range_low
    high_bound = high1 if high1 is not None else range_high

    base = safe_float(row.get('基准值'))
    if low_bound is None and high_bound is None:
        if base is not None:
            low_bound, high_bound = base * 0.8, base * 1.2
            if low_bound == high_bound:
                low_bound, high_bound = base - 1.0, base + 1.0
        else:
            low_bound, high_bound = 0.0, 100.0
    elif low_bound is None:
        # 只有高报警/上限时，以下限 0 或文本下限作为稳定区间下界。
        if high_bound is not None and high_bound > 0:
            low_bound = 0.0
        else:
            low_bound = high_bound - max(abs(high_bound) * 0.5, 1.0)
    elif high_bound is None:
        high_bound = low_bound + max(abs(low_bound) * 0.5, 1.0)

    if low_bound >= high_bound:
        span = max(abs(low_bound) * 0.2, 1.0)
        low_bound, high_bound = low_bound - span, low_bound + span
    return float(low_bound), float(high_bound)


def choose_stable_value(row, low_bound, high_bound):
    """稳定值放在正常区间的 1/3、1/2、2/3 附近，避免贴近报警线。"""
    fraction = random.choice([1 / 3, 1 / 2, 2 / 3])
    base_val = low_bound + (high_bound - low_bound) * fraction
    base_from_file = safe_float(row.get('基准值'))
    if base_from_file is not None and low_bound < base_from_file < high_bound:
        # 有可信基准值时，70% 概率沿用基准值，更符合工艺点真实额定工况。
        if random.random() < 0.7:
            base_val = base_from_file
    return float(base_val)


def get_signal_profile(code, name, unit):
    code_u = str(code).upper()
    name = str(name)
    unit = str(unit)
    if 'MT' in code_u or '温度' in name or unit in ['℃', '°C']:
        if any(k in name for k in ['绕组', '线圈', '电机']):
            return 'thermal_winding'
        if any(k in name for k in ['轴承', '齿轮箱', '密封']):
            return 'thermal_bearing'
        return 'thermal'
    if 'MN' in code_u or '液位' in name or unit == 'm':
        return 'level'
    if 'MD' in code_u or '流量' in name or 'm³/h' in unit or 'm3/h' in unit:
        return 'flow'
    if 'MP' in code_u or '压力' in name or unit == 'MPa':
        return 'pressure'
    if 'VP' in code_u or '阀' in name or '位移' in name or unit in ['%', 'mm']:
        return 'position'
    return 'generic'


def bounded_micro_noise(base_val, length, normal_span):
    """生成不超过稳定值 2% 的微量噪声；实际默认控制在 1.2% 内。"""
    scale = max(abs(base_val), abs(normal_span) * 0.05, 1e-6)
    hard_limit = scale * 0.02
    jitter = np.random.uniform(-hard_limit * 0.35, hard_limit * 0.35, length)
    drift = np.sin(np.linspace(0, random.uniform(1.0, 2.5) * np.pi, length) + random.random() * np.pi) * hard_limit * 0.25
    noise = jitter + drift
    return np.clip(noise, -hard_limit, hard_limit)


def build_stable_curve(base_val, length, low_bound, high_bound, profile='generic'):
    """正常工况曲线：稳定基准 + 柔和工况起伏 + 有界微量噪声。

    关键约束：
    1. 微量噪声始终限制在稳定值约 2% 以内；
    2. 柔和起伏属于真实工况缓慢变化，不是噪声，幅值受安全边界限制；
    3. 正常曲线不会越过低1/高1报警线，也不会制造突变。
    """
    span = max(high_bound - low_bound, abs(base_val) * 0.2, 1e-6)
    vals = np.full(length, base_val, dtype=float)

    # 安全边界：正常曲线与报警线保持至少 2% 量程距离，避免微小漂移误报警。
    guard = max(span * 0.02, abs(base_val) * 0.005, 1e-6)
    safe_low, safe_high = low_bound + guard, high_bound - guard
    if safe_low >= safe_high:
        safe_low, safe_high = low_bound, high_bound

    # 约 65% 的正常测点带有柔和工况起伏，其余测点保持近似水平直线。
    if random.random() < 0.65 and length > 20:
        # 不同测点类型的正常工况变化幅度：均低于报警/突变判据，且变化足够慢。
        factor_map = {
            'thermal': (0.012, 0.030),
            'thermal_bearing': (0.010, 0.026),
            'thermal_winding': (0.012, 0.032),
            'level': (0.010, 0.030),
            'flow': (0.018, 0.040),
            'pressure': (0.012, 0.035),
            'position': (0.015, 0.040),
            'generic': (0.010, 0.030),
        }
        lo_f, hi_f = factor_map.get(profile, factor_map['generic'])
        requested_amp = span * random.uniform(lo_f, hi_f)
        boundary_amp = max(min(abs(base_val - safe_low), abs(safe_high - base_val)) * 0.55, 0.0)
        amp = min(requested_amp, boundary_amp)

        if amp > 0:
            x = np.linspace(0, 1, length)
            phase = random.uniform(0, 2 * np.pi)
            if profile in ['thermal', 'thermal_bearing', 'thermal_winding', 'level']:
                # 温度/液位：热惯性或补排水导致的慢漂移，不做频繁抖动。
                center = random.uniform(0.35, 0.70)
                width = random.uniform(0.18, 0.35)
                bump = np.exp(-0.5 * ((x - center) / width) ** 2)
                bump = (bump - bump.min()) / max(bump.max() - bump.min(), 1e-6)
                sign = random.choice([-1, 1])
                vals += sign * amp * bump
            else:
                # 流量/压力/阀位：允许缓慢负荷摆动，但周期长、斜率小，不形成突变。
                cycles = random.uniform(0.45, 1.25)
                wave = np.sin(2 * np.pi * cycles * x + phase)
                vals += amp * wave

    # 传感器底噪：严格有界，控制在稳定值约 2% 以内。
    vals += bounded_micro_noise(base_val, length, span)
    return np.clip(vals, safe_low, safe_high)


def pick_alarm_target(valid_alarms):
    """从该测点真实存在的报警线中随机挑一个，支持低1/低2/低3/低4和高1/高2/高3/高4。"""
    items = [(k, v) for k, v in valid_alarms.items() if k in ALARM_COLUMNS]
    if not items:
        return None, None
    return random.choice(items)


def apply_engineering_anomaly(vals, base_val, target_name, target_val, profile, low_bound, high_bound, time_index=None):
    """按测点工程特性注入异常：温度/液位慢变，流量/压力/阀位快变或阶跃。"""
    n = len(vals)
    if n < 20 or target_name is None:
        return vals, None

    span = max(high_bound - low_bound, abs(base_val) * 0.2, abs(target_val) * 0.1, 1e-6)
    is_high = '高' in target_name
    margin = max(span * 0.04, abs(target_val) * 0.015, 1e-6)
    end_val = target_val + margin if is_high else target_val - margin

    if profile in ['thermal', 'thermal_bearing']:
        ramp_len = random.randint(18, 42)      # 3~7小时缓慢升温/降温
        hold_len = random.randint(6, 18)
        recover_len = random.randint(12, 30)
        shape = '缓慢热惯性越限'
    elif profile == 'thermal_winding':
        ramp_len = random.randint(6, 18)       # 绕组热响应比轴承快
        hold_len = random.randint(4, 12)
        recover_len = random.randint(8, 20)
        shape = '电机绕组较快热冲击'
    elif profile == 'level':
        ramp_len = random.randint(12, 36)      # 液位随补排水慢漂移
        hold_len = random.randint(6, 18)
        recover_len = random.randint(12, 30)
        shape = '液位缓慢漂移越限'
    elif profile == 'flow':
        ramp_len = random.randint(1, 3)        # 流量阀门扰动响应快
        hold_len = random.randint(3, 10)
        recover_len = random.randint(2, 6)
        shape = '流量快速阶跃/脉冲'
    elif profile == 'pressure':
        ramp_len = random.randint(2, 6)        # 压力建立快但有一定管路惯性
        hold_len = random.randint(4, 12)
        recover_len = random.randint(4, 10)
        shape = '压力快速爬升/跌落'
    elif profile == 'position':
        ramp_len = random.randint(1, 2)        # 阀位/位移近似阶跃
        hold_len = random.randint(3, 8)
        recover_len = random.randint(1, 4)
        shape = '阀位/位移突变'
    else:
        ramp_len = random.randint(4, 12)
        hold_len = random.randint(4, 12)
        recover_len = random.randint(4, 12)
        shape = '中速过程扰动'

    total_len = ramp_len + hold_len + recover_len
    start_min = int(n * 0.20)
    start_max = max(start_min + 1, n - total_len - 2)
    if start_max <= start_min:
        start_idx = max(1, int(n * 0.35))
    else:
        start_idx = random.randint(start_min, min(int(n * 0.78), start_max))

    ramp = np.linspace(base_val, end_val, ramp_len)
    hold = np.full(hold_len, end_val)
    # 多数情况下恢复到正常；少数情况下保持异常，便于验证持续报警。
    recover_target = base_val if random.random() < 0.75 else (target_val + margin * 0.7 if is_high else target_val - margin * 0.7)
    recover = np.linspace(end_val, recover_target, recover_len)
    event = np.concatenate([ramp, hold, recover])
    event += bounded_micro_noise(end_val, len(event), span) * 0.6

    # 保证越过被选中的报警线，不被噪声拉回阈值内。
    if is_high:
        event[ramp_len:ramp_len + hold_len] = np.maximum(event[ramp_len:ramp_len + hold_len], target_val + margin * 0.5)
    else:
        event[ramp_len:ramp_len + hold_len] = np.minimum(event[ramp_len:ramp_len + hold_len], target_val - margin * 0.5)

    end_idx = min(n, start_idx + len(event))
    vals[start_idx:end_idx] = event[:end_idx - start_idx]
    alarm_note = {
        '报警线': target_name,
        '报警值': round(float(target_val), 4),
        '触发时间': format_trigger_time(start_idx, n, time_index),
        '模拟形态': shape,
        '目标峰值': round(float(end_val), 4)
    }
    return vals, alarm_note


def pick_near_alarm_target(valid_alarms):
    """临近报警只选择最先触发的低/高侧报警线，避免靠近 H2/L2 时已经越过 H/L。"""
    high_items = [(k, v) for k, v in valid_alarms.items() if k in HIGH_ALARM_COLUMNS]
    low_items = [(k, v) for k, v in valid_alarms.items() if k in LOW_ALARM_COLUMNS]
    candidates = []
    if high_items:
        candidates.append(min(high_items, key=lambda kv: kv[1]))  # 最低高报线，最先触发
    if low_items:
        candidates.append(max(low_items, key=lambda kv: kv[1]))   # 最高低报线，最先触发
    return random.choice(candidates) if candidates else (None, None)


def apply_near_alarm_condition(vals, base_val, target_name, target_val, profile, low_bound, high_bound, time_index=None):
    """模拟临近报警：靠近但不越过最先触发的报警线。"""
    n = len(vals)
    if n < 20 or target_name is None:
        return vals, None
    span = max(high_bound - low_bound, abs(base_val) * 0.2, abs(target_val) * 0.1, 1e-6)
    is_high = '高' in target_name
    guard = max(span * random.uniform(0.015, 0.035), abs(target_val) * 0.005, 1e-6)
    if is_high:
        near_val = min(target_val - guard, high_bound - guard)
        near_val = max(near_val, low_bound + span * 0.05)
        shape = '临近高报但未越限'
    else:
        near_val = max(target_val + guard, low_bound + guard)
        near_val = min(near_val, high_bound - span * 0.05)
        shape = '临近低报但未越限'

    if profile in ['thermal', 'thermal_bearing', 'thermal_winding', 'level']:
        ramp_len, hold_len, recover_len = random.randint(18, 36), random.randint(8, 18), random.randint(12, 28)
    else:
        ramp_len, hold_len, recover_len = random.randint(4, 10), random.randint(6, 14), random.randint(4, 10)
    total_len = ramp_len + hold_len + recover_len
    start_max = max(int(n * 0.25) + 1, n - total_len - 2)
    start_idx = random.randint(int(n * 0.18), min(int(n * 0.75), start_max)) if start_max > int(n * 0.18) else int(n * 0.35)

    event = np.concatenate([
        np.linspace(base_val, near_val, ramp_len),
        np.full(hold_len, near_val),
        np.linspace(near_val, base_val, recover_len),
    ])
    event += bounded_micro_noise(near_val, len(event), span) * 0.35
    # 强制约束：临近但不跨越报警线。
    safe_low = low_bound + max(span * 0.005, 1e-6)
    safe_high = high_bound - max(span * 0.005, 1e-6)
    if is_high:
        event = np.minimum(event, target_val - guard * 0.5)
    else:
        event = np.maximum(event, target_val + guard * 0.5)
    event = np.clip(event, safe_low, safe_high)

    end_idx = min(n, start_idx + len(event))
    vals[start_idx:end_idx] = event[:end_idx - start_idx]
    alarm_note = {
        '报警线': f'临近{target_name}',
        '报警值': round(float(target_val), 4),
        '触发时间': format_trigger_time(start_idx, n, time_index),
        '模拟形态': shape,
        '目标峰值': round(float(near_val), 4)
    }
    return vals, alarm_note


def apply_jump_condition(vals, base_val, profile, low_bound, high_bound, time_index=None):
    """模拟安全区间内的快速参数突变：不越限、不临近报警，但变化斜率明显。"""
    n = len(vals)
    if n < 20:
        return vals, None
    span = max(high_bound - low_bound, abs(base_val) * 0.2, 1e-6)
    guard = max(span * 0.08, abs(base_val) * 0.01, 1e-6)
    safe_low, safe_high = low_bound + guard, high_bound - guard
    if safe_low >= safe_high:
        safe_low, safe_high = low_bound, high_bound

    # 目标幅度足够大，便于检测端识别为突变，但仍严格限制在正常区间内。
    max_up = safe_high - base_val
    max_down = base_val - safe_low
    directions = []
    if max_up > span * 0.12:
        directions.append('+')
    if max_down > span * 0.12:
        directions.append('-')
    direction = random.choice(directions) if directions else random.choice(['+', '-'])
    raw_amp = span * random.uniform(0.14, 0.24)
    if direction == '+':
        target_val = min(base_val + raw_amp, safe_high)
    else:
        target_val = max(base_val - raw_amp, safe_low)

    if profile in ['thermal', 'thermal_bearing']:
        ramp_len = random.randint(5, 10)       # 热参数可出现较快梯度变化，不做一秒级阶跃
        hold_len = random.randint(6, 14)
        recover_len = random.randint(5, 12)
        shape = '安全区间内快速梯度变化'
    elif profile == 'thermal_winding':
        ramp_len = random.randint(3, 7)
        hold_len = random.randint(5, 12)
        recover_len = random.randint(4, 10)
        shape = '绕组负荷扰动导致快速变化'
    elif profile in ['flow', 'pressure', 'position']:
        ramp_len = random.randint(1, 3)
        hold_len = random.randint(4, 10)
        recover_len = random.randint(2, 6)
        shape = '安全区间内阶跃/脉冲突变'
    else:
        ramp_len = random.randint(3, 8)
        hold_len = random.randint(4, 10)
        recover_len = random.randint(3, 8)
        shape = '安全区间内参数突变'

    total_len = ramp_len + hold_len + recover_len
    start_max = max(int(n * 0.25) + 1, n - total_len - 2)
    start_idx = random.randint(int(n * 0.18), min(int(n * 0.75), start_max)) if start_max > int(n * 0.18) else int(n * 0.35)
    event = np.concatenate([
        np.linspace(base_val, target_val, ramp_len),
        np.full(hold_len, target_val),
        np.linspace(target_val, base_val, recover_len),
    ])
    event += bounded_micro_noise(target_val, len(event), span) * 0.30
    event = np.clip(event, safe_low, safe_high)

    end_idx = min(n, start_idx + len(event))
    vals[start_idx:end_idx] = event[:end_idx - start_idx]
    alarm_note = {
        '报警线': '参数突变',
        '报警值': '正常区间内',
        '触发时间': format_trigger_time(start_idx, n, time_index),
        '模拟形态': shape,
        '目标峰值': round(float(target_val), 4)
    }
    return vals, alarm_note


def pick_near_high_alarm_target(valid_alarms):
    """临近高报：选择最先触发的高侧报警线，也就是所有高报线中的最低值。"""
    high_items = [(k, v) for k, v in valid_alarms.items() if k in HIGH_ALARM_COLUMNS]
    return min(high_items, key=lambda kv: kv[1]) if high_items else (None, None)


def pick_near_low_alarm_target(valid_alarms):
    """临近低报：选择最先触发的低侧报警线，也就是所有低报线中的最高值。"""
    low_items = [(k, v) for k, v in valid_alarms.items() if k in LOW_ALARM_COLUMNS]
    return max(low_items, key=lambda kv: kv[1]) if low_items else (None, None)


SCENARIO_ICONS = {
    '正常稳定工况': '🟢',
    '越限高报': '🔴',
    '越限低报': '🔵',
    '临近高报': '🟠',
    '临近低报': '🟡',
    '参数突变': '⚡',
}
SCENARIO_ORDER = ['正常稳定工况', '越限高报', '越限低报', '临近高报', '临近低报', '参数突变']


def scenario_display_name(scenario):
    scenario = str(scenario or '正常稳定工况')
    return f"{SCENARIO_ICONS.get(scenario, '•')} {scenario}"


def pick_high_alarm_target(valid_alarms):
    """越限高报：从该测点真实存在的高侧报警线中随机挑一个。"""
    high_items = [(k, v) for k, v in valid_alarms.items() if k in HIGH_ALARM_COLUMNS]
    return random.choice(high_items) if high_items else (None, None)


def pick_low_alarm_target(valid_alarms):
    """越限低报：从该测点真实存在的低侧报警线中随机挑一个。"""
    low_items = [(k, v) for k, v in valid_alarms.items() if k in LOW_ALARM_COLUMNS]
    return random.choice(low_items) if low_items else (None, None)


def choose_required_scenario_map(eligible_codes, row_map, all_sys_codes):
    """
    每次启动尽量覆盖完整工况：
    - 正常稳定工况：至少保留一部分测点不注入异常；
    - 越限高报：系统存在高侧报警线时至少 1 个；
    - 越限低报：系统存在低侧报警线时至少 1 个；
    - 临近高报：系统存在高侧报警线时至少 1 个；
    - 临近低报：系统存在低侧报警线时至少 1 个；
    - 参数突变：至少 1 个。

    后续会再随机追加若干测点到各类场景中，因此不会总是每类刚好 1 个。
    如果系统缺少对应高/低报警线，则自动跳过该类，不硬造不存在的报警逻辑。
    """
    scenario_map = {}
    used = set()
    eligible_codes = [str(c).strip() for c in eligible_codes]
    all_sys_codes = [str(c).strip() for c in all_sys_codes]

    high_candidates = [
        c for c in eligible_codes
        if pick_high_alarm_target(get_valid_alarms(row_map[c]))[0] is not None
    ]
    low_candidates = [
        c for c in eligible_codes
        if pick_low_alarm_target(get_valid_alarms(row_map[c]))[0] is not None
    ]
    any_candidates = list(eligible_codes)

    scenario_candidates = {
        '越限高报': high_candidates,
        '越限低报': low_candidates,
        '临近高报': high_candidates,
        '临近低报': low_candidates,
        '参数突变': any_candidates,
    }

    # 至少保留一部分正常测点。系统测点越多，保留的正常测点越多。
    if len(all_sys_codes) >= 10:
        min_normal_count = max(2, int(len(all_sys_codes) * 0.35))
    elif len(all_sys_codes) >= 5:
        min_normal_count = 1
    else:
        min_normal_count = 0
    max_victims = max(0, min(len(eligible_codes), len(all_sys_codes) - min_normal_count))

    def choose_one(candidates):
        candidates = [c for c in candidates if c not in used]
        if not candidates or len(scenario_map) >= max_victims:
            return None
        random.shuffle(candidates)
        return candidates[0]

    # 先保证关键场景各至少一个：高越限、低越限、临近高、临近低、突变。
    required_order = ['越限高报', '越限低报', '临近高报', '临近低报', '参数突变']
    for scenario in required_order:
        chosen = choose_one(scenario_candidates.get(scenario, []))
        if chosen is not None:
            scenario_map[chosen] = scenario
            used.add(chosen)

    if len(scenario_map) >= max_victims:
        return scenario_map

    # 再随机追加若干异常/预警测点，让每次工况更丰富，避免每类刚好 1 个。
    remaining = [c for c in eligible_codes if c not in used]
    if not remaining:
        return scenario_map

    # 目标异常数量：在“必选数量”基础上追加 15%~30% 的系统测点，但仍保留正常测点。
    extra_upper = max(len(scenario_map), min(max_victims, len(scenario_map) + max(1, int(len(all_sys_codes) * 0.25))))
    # 只要有余量，就至少额外追加 1 个场景测点，避免每个特殊场景永远刚好 1 个。
    if remaining and extra_upper > len(scenario_map):
        target_victims = random.randint(len(scenario_map) + 1, extra_upper)
    else:
        target_victims = len(scenario_map)

    extra_scenarios = ['越限高报', '越限低报', '临近高报', '临近低报', '参数突变']
    while len(scenario_map) < target_victims and remaining:
        random.shuffle(extra_scenarios)
        assigned = False
        for scenario in extra_scenarios:
            candidates = [c for c in scenario_candidates.get(scenario, []) if c not in used]
            if not candidates:
                continue
            chosen = random.choice(candidates)
            scenario_map[chosen] = scenario
            used.add(chosen)
            remaining = [c for c in remaining if c != chosen]
            assigned = True
            break
        if not assigned:
            break

    return scenario_map

# ==========================================
# 2. 侧边栏：增删系统双向同步
# ==========================================
st.sidebar.markdown('<div class="sidebar-main-title">🎛️ 仿真推流中心</div>', unsafe_allow_html=True)

with st.sidebar.expander("🗑️ 系统接入管理", expanded=False):
    system_options = base_system_df['系统'].dropna().unique().tolist()

    def format_delete_option(sys_name: str) -> str:
        # 下拉框只显示系统原名，避免图标和长后缀导致名称显示不完整。
        return str(sys_name)

    if not system_options:
        st.info("当前暂无已接入系统。")
    else:
        sys_to_delete = st.selectbox(
            "选择操作系统",
            system_options,
            key="sim_del_sys_all_visible",
            format_func=format_delete_option
        )
        is_core_system = sys_to_delete in BUILT_IN_SYSTEMS
        st.caption(f"当前选中：{sys_to_delete}")
        if is_core_system:
            st.markdown(
                "<div style='color:#888; background:#f1f3f5; border:1px solid #ddd; "
                "border-radius:6px; padding:8px;'>🔒 当前选中的是基础系统，仅展示，不允许卸载。</div>",
                unsafe_allow_html=True
            )

        if st.button(
            "🗑️ 卸载该工艺系统",
            use_container_width=True,
            disabled=is_core_system,
            help="RHR/RCV 基础系统受保护，不能卸载。" if is_core_system else None
        ):
            if sys_to_delete in BUILT_IN_SYSTEMS:
                st.sidebar.error("基础系统受保护，不能删除。")
            elif sys_to_delete:
                base_system_df = base_system_df[base_system_df['系统'] != sys_to_delete]
                base_system_df.to_csv(CONFIG_FILE, index=False)
                st.sidebar.success(f"已同步卸载系统: {sys_to_delete}，监测端映射已同步！")
                st.rerun()

with st.sidebar.expander("📥 导入定值规范 (同步入库)", expanded=False):
    new_sys_name = st.text_input("为新接入工艺系统命名", placeholder="如：3RBM反应堆补给系统")
    uploaded_file = st.file_uploader("上传定值文件", type=['csv', 'xlsx', 'xls', 'docx'], key="sim_upload")
    if uploaded_file and new_sys_name:
        if st.button("➕ 添加系统至全局标准库", use_container_width=True):
            st.info("💡 提示：请统一在『智能监测预警系统』端执行定值手册的解析与导入。")


# ==========================================
# 3. 完美结合双引擎的全局时序生成模块
# ==========================================
def generate_timeseries_unified(df_meta, random_baselines_dict):
    time_index, sim_eval_index, realtime_end, time_shift = build_realtime_time_axes()
    df_ts = pd.DataFrame({'Time': time_index})

    t0, t1, t2 = pd.to_datetime("2026-06-01 00:00:00"), pd.to_datetime("2026-06-01 02:00:00"), pd.to_datetime(
        "2026-06-03 12:00:00")
    t3, t4, t5 = pd.to_datetime("2026-06-03 15:00:00"), pd.to_datetime("2026-06-03 16:00:00"), pd.to_datetime(
        "2026-06-03 17:00:00")
    t_0602_0400 = pd.to_datetime("2026-06-02 04:00:00")
    t_0602_0410 = pd.to_datetime("2026-06-02 04:10:00")
    t_0602_0412 = pd.to_datetime("2026-06-02 04:12:00")
    t_0602_1000 = pd.to_datetime("2026-06-02 10:00:00")
    t_0602_1750 = pd.to_datetime("2026-06-02 17:50:00")
    t_0603_0600 = pd.to_datetime("2026-06-03 06:00:00")
    t_0603_0900 = pd.to_datetime("2026-06-03 09:00:00")
    t_0603_1000 = pd.to_datetime("2026-06-03 10:00:00")
    t_0603_1110 = pd.to_datetime("2026-06-03 11:10:00")
    t_0603_1230 = pd.to_datetime("2026-06-03 12:30:00")
    t_0603_1400 = pd.to_datetime("2026-06-03 14:00:00")
    t_0603_1420 = pd.to_datetime("2026-06-03 14:20:00")
    t_0603_1500 = pd.to_datetime("2026-06-03 15:00:00")
    t_0603_1600 = pd.to_datetime("2026-06-03 16:00:00")
    t_0603_1800 = pd.to_datetime("2026-06-03 18:00:00")
    t_0604_0800 = pd.to_datetime("2026-06-04 08:00:00")
    t_0604_1000 = pd.to_datetime("2026-06-04 10:00:00")
    t_0604_1340 = pd.to_datetime("2026-06-04 13:40:00")
    t_0604_1400 = pd.to_datetime("2026-06-04 14:00:00")
    t_0604_1700 = pd.to_datetime("2026-06-04 17:00:00")
    t_0604_1800 = pd.to_datetime("2026-06-04 18:00:00")
    t_0604_1802 = pd.to_datetime("2026-06-04 18:02:00")

    for _, r_meta in df_meta.iterrows():
        code = str(r_meta['编码']).strip()
        sys_name = r_meta['系统']
        unit = r_meta['单位']

        # 启动工况模拟后，所有系统都优先使用按 系统名+编码 隔离的随机仿真曲线。
        # 内置 RHR/RCV 若没有随机仿真曲线，则继续回退到下方标准预设模型；新上传系统未启动前保持静默。
        s_key = make_state_key(sys_name, code)
        if s_key in random_baselines_dict:
            curve = np.asarray(random_baselines_dict[s_key], dtype=float)
            if len(curve) != len(time_index):
                # 兼容旧缓存：时间轴从固定 2026-06-01~06-05 切换为实时 5 天窗口后，
                # 已缓存曲线长度可能不一致。这里仅按索引平滑重采样，保持原曲线形态。
                if len(curve) > 1:
                    old_x = np.linspace(0, 1, len(curve))
                    new_x = np.linspace(0, 1, len(time_index))
                    curve = np.interp(new_x, old_x, curve)
                elif len(curve) == 1:
                    curve = np.full(len(time_index), curve[0])
                else:
                    curve = np.full(len(time_index), np.nan)
            df_ts[stream_baseline_col(sys_name, code)] = curve
            continue

        if sys_name not in BUILT_IN_SYSTEMS:
            continue

        # 老系统专属物理参数
        if 'RCV' in sys_name:
            noise_std = 0.001 if unit == "MPa" else (
                0.1 if unit == "m³/h" else (0.001 if unit in ["mm", "m"] else (0.05 if unit == "%" else 0.01)))
        else:
            noise_std = 0.002 if unit == "MPa" else (0.5 if unit == "m³/h" else (0.005 if unit == "mm" else 0.05))
        if code in ["RCV021MD", "RCV022MD", "RCV023MD"]:
            noise_std = 0.015
        vals = []
        for t in sim_eval_index:
            if code == "RHR004MP":
                val = 0.2 if t < t3 else (0.2 + (0.8 - 0.2) * ((t - t3).total_seconds() / 3600) if t < t4 else 0.8)
            elif code == "RHR005MP":
                val = 0.0 + (0.81 - 0.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (0.81 if t < t2 else (
                    0.81 + (1.1 - 0.81) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        1.1 - (1.1 - 0.2) * ((t - t3).total_seconds() / 7200) if t < t5 else 0.2)))
            elif code in ["RHR006MD", "RHR032MD", "RHR008MD", "RHR033MD"]:
                val = 550.0
            elif "MM" in code:
                val = 2.0
            elif code == "3RHR027MT":
                val = 24.0 + (32.0 - 24.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (32.0 if t < t2 else (
                    32.0 + (85.0 - 32.0) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        85.0 - (85.0 - 24.0) * ((t - t3).total_seconds() / 7200) if t < t5 else 24.0)))
            elif code == "3RHR026MT":
                val = 24.0 if t < t3 else (24.0 + (32.0 - 24.0) * ((t - t3).total_seconds() / 3600) if t < t4 else 32.0)
            elif code == "3RHR025MT":
                val = 24.0 + (32.0 - 24.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (33.0 if t < t2 else (
                    33.0 + (84.0 - 33.0) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        84.0 - (84.0 - 24.0) * ((t - t3).total_seconds() / 7200) if t < t5 else 24.0)))
            elif code == "3RHR024MT":
                val = 24.0 if t < t3 else (24.0 + (33.0 - 24.0) * ((t - t3).total_seconds() / 3600) if t < t4 else 33.0)
            elif code == "3RHR023MT":
                val = 24.0 + (36.0 - 24.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (33.0 if t < t2 else (
                    33.0 + (84.0 - 33.0) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        84.0 - (84.0 - 24.0) * ((t - t3).total_seconds() / 7200) if t < t5 else 24.0)))
            elif code == "3RHR022MT":
                val = 24.0 if t < t3 else (24.0 + (33.0 - 24.0) * ((t - t3).total_seconds() / 3600) if t < t4 else 33.0)
            elif code in ["3RHR021MT", "3RHR019MT", "3RHR017MT"]:
                val = 24.0 + (30.0 - 24.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (30.0 if t < t2 else (
                    30.0 + (50.0 - 30.0) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        50.0 - (50.0 - 24.0) * ((t - t3).total_seconds() / 7200) if t < t5 else 24.0)))
            elif code in ["3RHR020MT", "3RHR018MT", "3RHR016MT"]:
                val = 24.0 if t < t3 else (24.0 + (30.0 - 24.0) * ((t - t3).total_seconds() / 3600) if t < t4 else 30.0)
            elif code == "3RHR015MT":
                val = 24.0 + (31.5 - 24.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (31.5 if t < t2 else (
                    31.5 + (45.0 - 31.5) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        45.0 - (45.0 - 24.0) * ((t - t3).total_seconds() / 7200) if t < t5 else 24.0)))
            elif code == "3RHR014MT":
                val = 24.0 if t < t3 else (24.0 + (31.5 - 24.0) * ((t - t3).total_seconds() / 3600) if t < t4 else 31.5)
            elif code == "3RHR013MT":
                val = 24.0 + (32.5 - 24.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (32.5 if t < t2 else (
                    32.5 + (51.0 - 32.5) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        51.0 - (51.0 - 24.0) * ((t - t3).total_seconds() / 7200) if t < t5 else 24.0)))
            elif code == "3RHR012MT":
                val = 24.0 if t < t3 else (24.0 + (32.5 - 24.0) * ((t - t3).total_seconds() / 3600) if t < t4 else 32.5)
            elif code == "3RHR011MT":
                val = 24.0 + (34.0 - 24.0) * ((t - t0).total_seconds() / 7200) if t < t1 else (34.0 if t < t2 else (
                    34.0 + (49.0 - 34.0) * ((t - t2).total_seconds() / 10800) if t < t3 else (
                        49.0 - (49.0 - 24.0) * ((t - t3).total_seconds() / 7200) if t < t5 else 24.0)))
            elif code == "3RHR010MT":
                val = 24.0 if t < t3 else (24.0 + (34.0 - 24.0) * ((t - t3).total_seconds() / 3600) if t < t4 else 34.0)

            elif code in ["RCV100MT", "RCV200MT"]:
                val = 72.0 if t < t_0602_1750 else (72.0 + (83.0 - 72.0) * (
                            (t - t_0602_1750).total_seconds() / 10800) if t < t_0602_1750 + pd.Timedelta(hours=3) else (
                    83.0 if t < t_0602_1750 + pd.Timedelta(hours=6) else (83.0 - (83.0 - 72.0) * ((t - (
                                t_0602_1750 + pd.Timedelta(
                            hours=6))).total_seconds() / 10800) if t < t_0602_1750 + pd.Timedelta(hours=9) else 72.0)))
            elif code in ["RCV101MT", "RCV201MT"]:
                val = 68.0 if t < t_0602_0400 else (68.0 + (81.0 - 68.0) * (
                            (t - t_0602_0400).total_seconds() / 10800) if t < t_0602_0400 + pd.Timedelta(hours=3) else (
                    81.0 - (81.0 - 68.0) * ((t - (t_0602_0400 + pd.Timedelta(
                        hours=3))).total_seconds() / 7200) if t < t_0602_0400 + pd.Timedelta(hours=5) else 68.0))
            elif code in ["RCV126MT", "RCV226MT"]:
                val = 52.0 if t < t_0603_0900 else (
                    52.0 + (65.0 - 52.0) * ((t - t_0603_0900).total_seconds() / 7800) if t < t_0603_1110 else (
                        65.0 + (71.0 - 65.0) * ((t - t_0603_1110).total_seconds() / 11400) if t < t_0603_1420 else (
                            71.0 if t < t_0603_1600 else (71.0 - (71.0 - 52.0) * (
                                        (t - t_0603_1600).total_seconds() / 7200) if t < t_0603_1800 else 52.0))))
            elif code == "RCV018MD":
                val = 6.2 if t_0602_0410 <= t <= t_0602_0412 else (
                    12.0 if t_0604_1000 <= t <= t_0604_1000 + pd.Timedelta(minutes=30) else 16.0)
            elif code == "RCV005MD":
                val = 26.0 if t_0602_1000 <= t <= t_0602_1000 + pd.Timedelta(minutes=20) else (
                    24.5 if t_0604_1400 <= t <= t_0604_1400 + pd.Timedelta(minutes=20) else 20.0)
            elif code in ["RCV123MT", "RCV124MT", "RCV223MT", "RCV224MT"]:
                val = 66.0 if t < t_0604_1000 else (
                    66.0 + (86.0 - 66.0) * ((t - t_0604_1000).total_seconds() / 13200) if t < t_0604_1340 else (
                        86.0 if t < t_0604_1700 else (86.0 - (86.0 - 66.0) * (
                                    (t - t_0604_1700).total_seconds() / 7200) if t < t_0604_1700 + pd.Timedelta(
                            hours=2) else 66.0)))
            elif code in ["RCV121MT", "RCV122MT", "RCV221MT", "RCV222MT"]:
                val = 63.0 + 17.0 * (1 - abs((t - (t_0603_1000 + pd.Timedelta(
                    hours=3))).total_seconds()) / 10800) if t_0603_1000 <= t <= t_0603_1000 + pd.Timedelta(
                    hours=6) else 63.0
            elif code in ["RCV002MT", "RCV003MT"]:
                val = 45.0 + 7.0 * (1 - abs((t - (t_0602_0400 + pd.Timedelta(
                    hours=2.5))).total_seconds()) / 9000) if t_0602_0400 <= t < t_0602_0400 + pd.Timedelta(
                    hours=5) else (45.0 + 5.0 * (1 - abs((t - (t_0604_1000 + pd.Timedelta(
                    hours=1.5))).total_seconds()) / 5400) if t_0604_1000 <= t < t_0604_1000 + pd.Timedelta(
                    hours=3) else 45.0)
            elif code in ["RCV105MT", "RCV106MT", "RCV205MT", "RCV206MT"]:
                val = 70.0 + 8.0 * (1 - abs((t - (t_0603_1400 + pd.Timedelta(
                    hours=2))).total_seconds()) / 7200) if t_0603_1400 <= t <= t_0603_1400 + pd.Timedelta(
                    hours=4) else 70.0
            elif code in ["RCV110MT", "RCV210MT"]:
                val = 69.0 + 9.0 * (1 - abs((t - (t_0604_0800 + pd.Timedelta(
                    hours=2))).total_seconds()) / 7200) if t_0604_0800 <= t <= t_0604_0800 + pd.Timedelta(
                    hours=4) else 69.0
            elif code in ["RCV102MT", "RCV103MT", "RCV104MT", "RCV202MT", "RCV203MT", "RCV204MT"]:
                base = 107.0 if "104" in code or "204" in code else 95.0
                val = base + 10.0 if (t.day in [3, 4] and 14 <= t.hour < 15 and t.minute < 10 and (
                            "104" in code or "103" in code)) else base
            elif code in ["RCV021MD", "RCV022MD", "RCV023MD"]:
                # 6月4日 18:00 到 18:30，发生异常突升至 2.7
                if t_0604_1800 <= t <= t_0604_1800 + pd.Timedelta(minutes=30):
                    val = 2.7
                # 每天的 15:10 到 15:30，发生例行突降至 1.6
                elif t.hour == 15 and 10 <= t.minute <= 30:
                    val = 1.6
                # 平时 99% 的时间，稳如老狗保持在 2.1
                else:
                    val = 2.1
            elif code == "RCV046VP":
                val = 20.0 if t_0602_0410 <= t <= t_0602_0412 else 50.0
            elif code == "RCV064MT":
                val = 48.0 + 11.0 * (1 - abs((t - (t_0602_0400 + pd.Timedelta(
                    hours=3))).total_seconds()) / 10800) if t_0602_0400 <= t < t_0602_0400 + pd.Timedelta(
                    hours=6) else 48.0
            elif code in ["RCV011MN", "RCV012MN"]:
                val = 1.5 if t < t_0603_0600 else (
                    1.5 - (1.5 - 1.08) * ((t - t_0603_0600).total_seconds() / 23400) if t < t_0603_1230 else (
                        1.08 if t < t_0603_1500 else (1.08 + (1.5 - 1.08) * (
                                    (t - t_0603_1500).total_seconds() / 14400) if t < t_0603_1500 + pd.Timedelta(
                            hours=4) else 1.5)))
            else:
                val = r_meta['基准值'] if pd.notna(r_meta['基准值']) else 50.0

            vals.append(val + np.random.normal(0, noise_std))

        df_ts[stream_baseline_col(sys_name, code)] = vals
    return df_ts


df_ts_full = generate_timeseries_unified(base_system_df, st.session_state.random_baselines)

# ==========================================
# 4. 动态滤波运算与总线广播
# ==========================================
# 侧边栏“选择仿真目标系统”已删除。页面中唯一的“指定工况控制系统”
# 将同时驱动启动/停止、清单显示和人工异动注入。
for _, r in base_system_df.iterrows():
    c_code = str(r['编码']).strip()
    sys_name_for_row = str(r['系统']).strip()
    base_col = stream_baseline_col(sys_name_for_row, c_code)
    actual_col = stream_actual_col(sys_name_for_row, c_code)
    state_key = make_state_key(sys_name_for_row, c_code)

    if base_col not in df_ts_full.columns:
        continue

    if state_key not in st.session_state.p_matrix:
        st.session_state.p_matrix[state_key] = np.zeros(len(df_ts_full))

    raw_arr = np.asarray(st.session_state.p_matrix[state_key], dtype=float)
    if len(raw_arr) != len(df_ts_full):
        # 兼容旧会话缓存：实时 5 天窗口长度变化后，人工扰动数组长度需要同步。
        raw_arr = np.zeros(len(df_ts_full))
        st.session_state.p_matrix[state_key] = raw_arr
    filter_arr = np.zeros(len(df_ts_full))
    if np.any(raw_arr != 0):
        tgt = 0.0
        u = r['单位']
        alpha = 0.35 if u == "℃" else (0.85 if u in ["MPa", "m³/h"] else (0.65 if u == "mm" else 0.50))
        for i in range(len(df_ts_full)):
            if raw_arr[i] != 0: tgt = raw_arr[i]
            filter_arr[i] = tgt if i == 0 else filter_arr[i - 1] + alpha * (tgt - filter_arr[i - 1])
    else:
        filter_arr = raw_arr

    df_ts_full[actual_col] = df_ts_full[base_col] + filter_arr

# 绝对只写入 df_ts_full 中真实存在的列，杜绝错乱
df_ts_full.to_csv(DATA_FILE, index=False)

# ==========================================
# 5. 【微噪稳定版】系统工况推演控制台
# ==========================================
st.markdown("### 🌊 工业级仿真推流控制台")
realtime_end_for_ui = get_realtime_end()

system_manage_options = base_system_df['系统'].dropna().unique().tolist()
if 'sim_selected_system' not in st.session_state or st.session_state['sim_selected_system'] not in system_manage_options:
    st.session_state['sim_selected_system'] = system_manage_options[0] if system_manage_options else None
sys_to_manage = st.selectbox(
    "🎯 指定工况控制系统：",
    system_manage_options,
    key="sim_selected_system"
)
st.markdown(
    f"当前仿真目标系统：**{sys_to_manage}** &nbsp;&nbsp;|&nbsp;&nbsp; "
    f"🕒 实时演示时间轴：**{(realtime_end_for_ui - pd.Timedelta(days=REALTIME_WINDOW_DAYS)).strftime('%Y-%m-%d %H:%M')} → {realtime_end_for_ui.strftime('%Y-%m-%d %H:%M')}**",
    unsafe_allow_html=True
)
sys_active_df = base_system_df[base_system_df['系统'] == sys_to_manage].reset_index(drop=True)
# 保持下方清单与人工异动注入区域和上方选择完全一致。
selected_system = sys_to_manage
active_system_df = sys_active_df

is_generated = any(make_state_key(sys_to_manage, code) in st.session_state.random_baselines for code in sys_active_df['编码'].tolist())
if is_generated:
    st.success(f"🟢 **系统状态**：该系统已有随机模拟输入（正常/越限高报/越限低报/临近高报/临近低报/参数突变完整混合场景）。")
elif sys_to_manage in BUILT_IN_SYSTEMS:
    st.info(f"⚙️ **系统状态**：该基础系统当前使用内置标准模拟输入模型。")
else:
    st.warning(f"⚪ **系统状态**：该系统当前无模拟输入。")

if sys_to_manage in st.session_state.simulation_plans:
    plan_df = pd.DataFrame(st.session_state.simulation_plans[sys_to_manage])
    if not plan_df.empty:
        with st.expander("📌 本轮完整工况场景计划", expanded=False):
            st.caption("本轮尽量覆盖：正常稳定、越限高报、越限低报、临近高报、临近低报、参数突变；若系统缺少对应高/低报警线，则自动跳过该类。")
            if '场景类型' in plan_df.columns:
                scenario_counts = plan_df['场景类型'].fillna('正常稳定工况').value_counts().to_dict()
                card_html = "<div style='display:flex; flex-wrap:wrap; gap:10px; margin:8px 0 14px 0;'>"
                for scenario in SCENARIO_ORDER:
                    if scenario not in scenario_counts:
                        continue
                    count = int(scenario_counts.get(scenario, 0))
                    card_html += (
                        "<div style='min-width:145px; flex:0 0 auto; padding:10px 12px; "
                        "border:1px solid #e6e8ef; border-radius:10px; background:#fbfcff;'>"
                        f"<div style='font-size:14px; font-weight:700; color:#1f2937;'>{scenario_display_name(scenario)}</div>"
                        f"<div style='font-size:22px; font-weight:800; margin-top:4px;'>{count}</div>"
                        "</div>"
                    )
                card_html += "</div>"
                st.markdown(card_html, unsafe_allow_html=True)
                plan_view_df = plan_df.copy()
                plan_view_df.insert(0, '场景', plan_view_df['场景类型'].map(scenario_display_name))
                plan_view_df = plan_view_df.drop(columns=['场景类型'])
                st.dataframe(
                    plan_view_df,
                    use_container_width=True,
                    hide_index=True,
                    height=360,
                    column_config={
                        '场景': st.column_config.TextColumn(width='small'),
                        '编码': st.column_config.TextColumn(width='small'),
                        '测点名称': st.column_config.TextColumn(width='medium'),
                        '工程类型': st.column_config.TextColumn(width='small'),
                        '报警线': st.column_config.TextColumn(width='small'),
                        '报警值': st.column_config.TextColumn(width='small'),
                        '触发时间': st.column_config.TextColumn(width='medium'),
                        '模拟形态': st.column_config.TextColumn(width='large'),
                        '目标峰值': st.column_config.TextColumn(width='small'),
                    }
                )
            else:
                st.dataframe(plan_df, use_container_width=True, hide_index=True, height=360)

c1, c2, c3 = st.columns([1, 1, 2])

with c2:
    if st.button(f"⏹️ 停止模拟 (清空工况状态)", type="secondary", use_container_width=True):
        for raw_code in sys_active_df['编码'].tolist():
            code = str(raw_code).strip()
            s_key = make_state_key(sys_to_manage, code)
            st.session_state.random_baselines.pop(s_key, None)
            st.session_state.random_baselines.pop(legacy_code_key(code), None)
            if s_key in st.session_state.p_matrix:
                st.session_state.p_matrix[s_key] = np.zeros(len(df_ts_full))
            st.session_state.p_matrix.pop(legacy_code_key(code), None)
        st.session_state.simulation_plans.pop(sys_to_manage, None)
        if sys_to_manage in BUILT_IN_SYSTEMS:
            st.success(f"已清除【{sys_to_manage}】随机模拟场景，恢复基础内置标准输入。")
        else:
            st.success(f"成功停止推流，【{sys_to_manage}】已重置为空白静默状态！")
        st.rerun()

with c1:
    if st.button(f"🚀 启动工况模拟", type="primary", use_container_width=True):
        with st.spinner(f"正在依据工业物理特性严格演算 {sys_to_manage} 工况数据..."):
            time_steps = len(df_ts_full)
            sys_codes = [str(c).strip() for c in sys_active_df['编码'].tolist()]

            # 清除当前系统旧缓存，且同步清理旧版本按 code 存储的遗留键，避免污染其他系统。
            for c in sys_codes:
                s_key = make_state_key(sys_to_manage, c)
                st.session_state.random_baselines.pop(s_key, None)
                st.session_state.random_baselines.pop(legacy_code_key(c), None)
                if s_key in st.session_state.p_matrix:
                    st.session_state.p_matrix[s_key] = np.zeros(time_steps)
                st.session_state.p_matrix.pop(legacy_code_key(c), None)

            eligible_codes = []
            row_map = {}
            for _, row in sys_active_df.iterrows():
                code = str(row['编码']).strip()
                row_map[code] = row
                if get_valid_alarms(row):
                    eligible_codes.append(code)

            # 每次启动尽量强制覆盖：正常稳定、越限、临近高报、临近低报、参数突变。
            scenario_map = choose_required_scenario_map(eligible_codes, row_map, sys_codes)
            all_victims = set(scenario_map.keys())
            plan_records = []
            time_axis_for_plan = df_ts_full['Time'].reset_index(drop=True)

            for _, row in sys_active_df.iterrows():
                code = str(row['编码']).strip()
                name = str(row['测点名称'])
                unit = row.get('单位', '')
                valid_alarms = get_valid_alarms(row)
                low_bound, high_bound = get_normal_bounds(row, valid_alarms)
                base_val = choose_stable_value(row, low_bound, high_bound)
                profile = get_signal_profile(code, name, unit)

                # 正常工况：近似水平直线 + 被严格限制在稳定值2%以内的微量噪声。
                actual_vals = build_stable_curve(base_val, time_steps, low_bound, high_bound, profile)

                if code in all_victims and valid_alarms:
                    scenario = scenario_map.get(code, '越限报警')
                    if scenario == '临近高报':
                        target_alarm_name, target_alarm_val = pick_near_high_alarm_target(valid_alarms)
                        actual_vals, alarm_note = apply_near_alarm_condition(
                            actual_vals, base_val, target_alarm_name, target_alarm_val,
                            profile, low_bound, high_bound, time_axis_for_plan
                        )
                    elif scenario == '临近低报':
                        target_alarm_name, target_alarm_val = pick_near_low_alarm_target(valid_alarms)
                        actual_vals, alarm_note = apply_near_alarm_condition(
                            actual_vals, base_val, target_alarm_name, target_alarm_val,
                            profile, low_bound, high_bound, time_axis_for_plan
                        )
                    elif scenario == '参数突变':
                        actual_vals, alarm_note = apply_jump_condition(
                            actual_vals, base_val, profile, low_bound, high_bound, time_axis_for_plan
                        )
                    elif scenario == '越限高报':
                        target_alarm_name, target_alarm_val = pick_high_alarm_target(valid_alarms)
                        actual_vals, alarm_note = apply_engineering_anomaly(
                            actual_vals, base_val, target_alarm_name, target_alarm_val,
                            profile, low_bound, high_bound, time_axis_for_plan
                        )
                    elif scenario == '越限低报':
                        target_alarm_name, target_alarm_val = pick_low_alarm_target(valid_alarms)
                        actual_vals, alarm_note = apply_engineering_anomaly(
                            actual_vals, base_val, target_alarm_name, target_alarm_val,
                            profile, low_bound, high_bound, time_axis_for_plan
                        )
                    else:
                        target_alarm_name, target_alarm_val = pick_alarm_target(valid_alarms)
                        actual_vals, alarm_note = apply_engineering_anomaly(
                            actual_vals, base_val, target_alarm_name, target_alarm_val,
                            profile, low_bound, high_bound, time_axis_for_plan
                        )
                    if alarm_note:
                        alarm_note['场景类型'] = scenario
                        plan_records.append({
                            '编码': code,
                            '测点名称': name,
                            '工程类型': profile,
                            **alarm_note
                        })
                else:
                    plan_records.append({
                        '编码': code,
                        '测点名称': name,
                        '工程类型': profile,
                        '报警线': '无',
                        '报警值': '-',
                        '触发时间': '-',
                        '模拟形态': '正常稳定运行：近似水平线/柔和工况起伏 + ≤2%微量噪声',
                        '目标峰值': '-',
                        '场景类型': '正常稳定工况'
                    })

                # 关键修复：按 系统名+编码 写入，避免不同系统相同编码时同时启动/停止。
                st.session_state.random_baselines[make_state_key(sys_to_manage, code)] = np.asarray(actual_vals, dtype=float).tolist()

            st.session_state.simulation_plans[sys_to_manage] = plan_records

            st.success(f"🎉 演算完成！当前对【{sys_to_manage}】生成 {len(sys_codes)} 条测点曲线，其中 {len(all_victims)} 个测点触发越限高报/越限低报/临近高报/临近低报/参数突变场景，其他测点保持正常稳定工况。")
            st.rerun()

st.markdown("---")

# ==========================================
# 6. 左下角：全量测点监控清单
# ==========================================
# 演示版隐藏右侧人工扰动面板，清单占满主区域。
col_l = st.container()

with col_l:
    st.markdown(f"### 📋 {selected_system} - 仿真侧过程监控清单")

    display_df = pd.DataFrame()
    display_df['编码'] = active_system_df['编码']
    display_df['测点名称'] = active_system_df['测点名称']

    status_list, cursor_list, limit_list = [], [], []
    try:
        latest_row = df_ts_full.iloc[-1]
    except:
        latest_row = None

    for _, row in active_system_df.iterrows():
        c_code = str(row['编码']).strip()
        sys_name = row['系统']

        lim_str = []
        for k_name, k_col in [
            ('L4', '低4报'), ('L3', '低3报'), ('L2', '低2报'), ('L', '低报'),
            ('H', '高报'), ('H2', '高2报'), ('H3', '高3报'), ('H4', '高4报')
        ]:
            if k_col in row and pd.notna(row.get(k_col)) and str(row.get(k_col)).strip() != '':
                try:
                    lim_str.append(f"{k_name}: {float(row[k_col]):g}")
                except Exception:
                    lim_str.append(f"{k_name}: {row[k_col]}")
        limit_list.append(" | ".join(lim_str) if lim_str else "None")

        state_key = make_state_key(sys_name, c_code)
        actual_col = stream_actual_col(sys_name, c_code)
        if sys_name in BUILT_IN_SYSTEMS or state_key in st.session_state.random_baselines:
            if latest_row is not None and actual_col in latest_row:
                val = latest_row[actual_col]
                cursor_list.append(f"{val:.2f}")
                status_list.append("🟢 已加载工况")
            else:
                status_list.append("🟡 已启动，等待总线刷新")
                cursor_list.append("-")
        else:
            status_list.append("⚪ 无模拟输入")
            cursor_list.append("-")

    display_df['检测结果'] = status_list
    display_df['最新实测值'] = cursor_list
    display_df['报警限值(合)'] = limit_list
    display_df['正常范围'] = active_system_df['正常范围']
    display_df['单位'] = active_system_df['单位']

    # 按列内容设置更合理的宽度：短字段收窄，长字段放宽，避免报警限值被截断。
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            "编码": st.column_config.TextColumn("编码", width=115),
            "测点名称": st.column_config.TextColumn("测点名称", width=220),
            "检测结果": st.column_config.TextColumn("检测结果", width=115),
            "最新实测值": st.column_config.TextColumn("最新实测值", width=90),
            "报警限值(合)": st.column_config.TextColumn("报警限值(合)", width=380),
            "正常范围": st.column_config.TextColumn("正常范围", width=140),
            "单位": st.column_config.TextColumn("单位", width=75),
        }
    )

# ==========================================
# 7. 人工异动注入模块
# ==========================================
# 演示版已完全隐藏人工异动注入功能，避免页面展示冗余控件。
# 如需恢复，请从历史版本 app_simulation_realtime_axis_ui_opt.py 中复制该模块。
