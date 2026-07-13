import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
import plotly
from datetime import datetime, timedelta
import requests
import json
import base64
import copy
import re
import hashlib
import html

st.set_page_config(
    page_title="核电重大设备智能预警",
    page_icon="☢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 页面顶部与侧边栏标题对齐：右上角工具栏保留悬浮，左侧标题上移到与主标题同一视觉高度。
st.markdown("""
<style>
/* =========================
   全局主区域：只做自然流式布局，禁止负边距互相覆盖
   ========================= */
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] main .block-container {
    padding-top: 1.05rem !important;
    padding-bottom: 1.5rem !important;
}
[data-testid="stHeader"] {
    height: 0 !important;
    background: transparent !important;
}
[data-testid="stToolbar"] {
    right: 0.75rem !important;
    top: 0.25rem !important;
}

/* =========================
   左侧栏：恢复控件默认高度，避免下拉框、时间滑块和文字叠在一起
   ========================= */
section[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebarContent"] {
    padding-top: 0rem !important;
    padding-bottom: 0.55rem !important;
}
/* 只压缩侧边栏最外层纵向间距，展开后的表单内部仍保留正常可读间距。 */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.sidebar-main-title) {
    gap: 0.42rem !important;
}
.sidebar-main-title {
    margin: -0.42rem 0 0.42rem 0 !important;
    padding: 0 !important;
    font-size: 1.62rem !important;
    line-height: 1.25 !important;
    font-weight: 800 !important;
    color: #1f2a44 !important;
    white-space: nowrap !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    margin-top: 0 !important;
    margin-bottom: 0.08rem !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] details > summary {
    min-height: 2.45rem !important;
    padding-top: 0.32rem !important;
    padding-bottom: 0.32rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] {
    margin-top: 0 !important;
    margin-bottom: 0.10rem !important;
}
/* 云端多页面模式下不再显示占空间的侧栏横线。 */
section[data-testid="stSidebar"] hr {
    display: none !important;
}

/* 系统切换标题与刷新按钮 */
.sys-switch-label {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.25 !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.sys-switch-label) {
    align-items: center !important;
    margin-bottom: 0.25rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.sys-switch-label) div[data-testid="stButton"] {
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
    margin: 0 !important;
    padding: 0 !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.sys-switch-label) div[data-testid="stButton"] > button {
    min-width: 1.72rem !important;
    width: 1.72rem !important;
    max-width: 1.72rem !important;
    min-height: 1.72rem !important;
    height: 1.72rem !important;
    max-height: 1.72rem !important;
    padding: 0 !important;
    border-radius: 0.5rem !important;
    line-height: 1 !important;
    font-size: 1rem !important;
    font-family: Arial, sans-serif !important;
    border: 1px solid #d0d5dd !important;
    background: #ffffff !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.sys-switch-label) div[data-testid="stButton"] > button p {
    font-size: 1rem !important;
    line-height: 1 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* =========================
   图例：独立于 Plotly 画布，允许自动换行，永不裁切
   ========================= */
.alarm-legend-wrap {
    width: 100%;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    flex-wrap: wrap;
    column-gap: 0.9rem;
    row-gap: 0.35rem;
    box-sizing: border-box;
    padding: 0.08rem 0.15rem 0.20rem 0.15rem;
    margin: 0.02rem 0 0 0;
    font-size: 0.76rem;
    line-height: 1.2;
    color: #344054;
}
.alarm-legend-title {
    font-weight: 700;
    color: #475467;
    white-space: nowrap;
}
.alarm-legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    white-space: nowrap;
}
.alarm-legend-line {
    display: inline-block;
    width: 1.75rem;
    height: 0;
    flex: 0 0 auto;
}

/* Plotly 图表保持正常文档流，不再使用负边距压缩 */
section[data-testid="stMain"] div[data-testid="stPlotlyChart"],
[data-testid="stAppViewContainer"] main div[data-testid="stPlotlyChart"] {
    margin: 0 !important;
    overflow: visible !important;
}

/* =========================
   主图游标：云端稳健版
   1. 同时兼容带 key 容器和 Streamlit Cloud 的 main DOM；
   2. 用背景遮罩彻底覆盖原生红色轨道；
   3. 只保留可拖动的蓝绿色小三角，不影响侧边栏时间窗滑块。
   ========================= */
.st-key-cursor_slider_box {
    min-height: 1.05rem !important;
    height: 1.05rem !important;
    margin-top: -1.18rem !important;
    margin-bottom: 0.12rem !important;
    position: relative !important;
    z-index: 20 !important;
    overflow: visible !important;
    isolation: isolate !important;
}
/* 覆盖云端主题重新绘制出来的红色轨道和圆点底座。 */
.st-key-cursor_slider_box::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    top: -0.28rem;
    height: 1.45rem;
    background: var(--background-color, #ffffff);
    z-index: 40;
    pointer-events: none;
}

.st-key-cursor_slider_box div[data-testid="stSlider"],
[data-testid="stAppViewContainer"] main .st-key-cursor_slider_box div[data-testid="stSlider"],
section[data-testid="stMain"] .st-key-cursor_slider_box div[data-testid="stSlider"] {
    min-height: 1.05rem !important;
    height: 1.05rem !important;
    margin: 0 !important;
    padding: 0 28px !important;
    position: relative !important;
    z-index: 50 !important;
    overflow: visible !important;
    box-sizing: border-box !important;
}

.st-key-cursor_slider_box div[data-testid="stSlider"] p,
.st-key-cursor_slider_box div[data-testid="stSlider"] [data-testid="stThumbValue"] {
    display: none !important;
}

.st-key-cursor_slider_box div[data-testid="stSlider"] [data-baseweb="slider"] {
    min-height: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    position: relative !important;
    z-index: 60 !important;
    overflow: visible !important;
    background: transparent !important;
    background-image: none !important;
    border: 0 !important;
    box-shadow: none !important;
}

/* 所有包含 thumb 的祖先保留布局，但清空背景；其余轨道/进度条节点直接隐藏。 */
.st-key-cursor_slider_box div[data-testid="stSlider"] [data-baseweb="slider"] * {
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    border-color: transparent !important;
    box-shadow: none !important;
    outline: none !important;
}
.st-key-cursor_slider_box div[data-testid="stSlider"] [data-baseweb="slider"] *:not([role="slider"]):not(:has([role="slider"])) {
    visibility: hidden !important;
    opacity: 0 !important;
}
.st-key-cursor_slider_box div[data-testid="stSlider"] [data-baseweb="slider"] input {
    opacity: 0 !important;
}
.st-key-cursor_slider_box div[data-testid="stSlider"] [data-baseweb="slider"]::before,
.st-key-cursor_slider_box div[data-testid="stSlider"] [data-baseweb="slider"]::after,
.st-key-cursor_slider_box div[data-testid="stSlider"] [role="slider"]::before,
.st-key-cursor_slider_box div[data-testid="stSlider"] [role="slider"]::after {
    content: none !important;
    display: none !important;
}

/* 蓝绿色可拖动小三角。 */
.st-key-cursor_slider_box div[data-testid="stSlider"] [role="slider"],
[data-testid="stAppViewContainer"] main .st-key-cursor_slider_box [role="slider"],
section[data-testid="stMain"] .st-key-cursor_slider_box [role="slider"] {
    visibility: visible !important;
    opacity: 1 !important;
    display: block !important;
    position: relative !important;
    z-index: 100 !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    padding: 0 !important;
    border-left: 7px solid transparent !important;
    border-right: 7px solid transparent !important;
    border-top: 0 !important;
    border-bottom: 13px solid #00bcd4 !important;
    border-radius: 0 !important;
    background: transparent !important;
    background-image: none !important;
    box-shadow: none !important;
    outline: none !important;
    margin-top: -7px !important;
    cursor: grab !important;
}
.st-key-cursor_slider_box div[data-testid="stSlider"] [role="slider"]:active {
    cursor: grabbing !important;
}

/* AI 区域始终位于曲线图和游标之后 */
.ai-section-title {
    margin: 0.12rem 0 0.40rem 0 !important;
    padding: 0 !important;
    line-height: 1.25 !important;
}

/* 测点清单前置勾选框放大，提升点击切换体验 */
section[data-testid="stMain"] div[data-testid="stDataFrame"] [role="checkbox"],
[data-testid="stAppViewContainer"] main div[data-testid="stDataFrame"] [role="checkbox"] {
    transform: scale(1.28) !important;
    transform-origin: center center !important;
}
section[data-testid="stMain"] div[data-testid="stDataFrame"] [role="gridcell"]:first-child,
section[data-testid="stMain"] div[data-testid="stDataFrame"] [role="columnheader"]:first-child,
[data-testid="stAppViewContainer"] main div[data-testid="stDataFrame"] [role="gridcell"]:first-child,
[data-testid="stAppViewContainer"] main div[data-testid="stDataFrame"] [role="columnheader"]:first-child {
    min-width: 2.35rem !important;
    width: 2.35rem !important;
    justify-content: center !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 核心凭证配置与【多级无损聚合】解析舱
# ==========================================
DIFY_API_KEY = "app-KgNfeANAf2qp1cMr3Wdq8Rkp"
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"

CONFIG_FILE = "active_points_config.csv"
DATA_FILE = "live_data.csv"
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



def make_stream_prefix(system_name, code):
    """与仿真端一致的总线列名前缀。新导入系统使用系统哈希隔离，避免同编码串流。"""
    code = str(code).strip()
    sys_name = str(system_name).strip()
    if sys_name in BUILT_IN_SYSTEMS:
        return code
    safe_code = re.sub(r'[^0-9A-Za-z_]+', '_', code)
    sys_hash = hashlib.md5(sys_name.encode('utf-8')).hexdigest()[:8]
    return f"SYS{sys_hash}_{safe_code}"


def resolve_actual_col(df, system_name, code):
    """优先读取系统隔离列；若是旧版总线或内置系统，再回退到 code_Actual。"""
    isolated_col = f"{make_stream_prefix(system_name, code)}_Actual"
    legacy_col = f"{str(code).strip()}_Actual"
    if isolated_col in df.columns:
        return isolated_col
    if legacy_col in df.columns:
        return legacy_col
    return None

if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
    get_core_systems_df().to_csv(CONFIG_FILE, index=False)
    st.warning("🔒 未找到静态配置库，已自动创建 RHR/RCV 基础系统配置。")

base_system_df = pd.read_csv(CONFIG_FILE)
base_system_df, _restored_core_systems = ensure_core_systems_in_config(base_system_df)
if _restored_core_systems:
    st.sidebar.success("🔒 已自动恢复基础系统：" + "、".join(_restored_core_systems))
# 补齐所有可能的多级报警字段
for col in ['低4报', '低3报', '低2报', '低报', '高报', '高2报', '高3报', '高4报']:
    if col not in base_system_df.columns:
        base_system_df[col] = np.nan

st.sidebar.markdown('<div class="sidebar-main-title">⚙️ 智能监测预警中心</div>', unsafe_allow_html=True)

# 管理/删除已接入系统
with st.sidebar.expander("🗑️ 管理/删除已接入系统", expanded=False):
    system_options = base_system_df['系统'].dropna().unique().tolist()

    def format_delete_option(sys_name: str) -> str:
        # 下拉框只显示系统原名，避免前缀图标和长后缀挤占宽度。
        return str(sys_name)

    if not system_options:
        st.info("当前暂无已接入系统。")
    else:
        sys_to_delete = st.selectbox(
            "选择要删除的系统",
            system_options,
            key="del_sys_all_visible",
            format_func=format_delete_option
        )
        is_core_system = sys_to_delete in BUILT_IN_SYSTEMS
        st.caption(f"当前选中：{sys_to_delete}")
        if is_core_system:
            st.markdown(
                "<div style='color:#888; background:#f1f3f5; border:1px solid #ddd; "
                "border-radius:6px; padding:8px;'>🔒 当前选中的是基础系统，仅展示，不允许删除。</div>",
                unsafe_allow_html=True
            )

        if st.button(
            "🗑️ 确认永久删除该系统",
            use_container_width=True,
            disabled=is_core_system,
            help="RHR/RCV 基础系统受保护，不能删除。" if is_core_system else None
        ):
            if sys_to_delete in BUILT_IN_SYSTEMS:
                st.sidebar.error("基础系统受保护，不能删除。")
            elif sys_to_delete:
                base_system_df = base_system_df[base_system_df['系统'] != sys_to_delete]
                base_system_df.to_csv(CONFIG_FILE, index=False)
                st.sidebar.success(f"已成功删除系统: {sys_to_delete}")
                st.rerun()

with st.sidebar.expander("📥 智能导入外部定值手册", expanded=False):
    new_sys_name = st.text_input("为新接入工艺系统命名", placeholder="如：3RBM反应堆补给系统")
    uploaded_file = st.file_uploader("上传定值文件", type=['csv', 'xlsx', 'xls', 'docx'])

    if uploaded_file and new_sys_name:
        if st.button("➕ 添加新系统", use_container_width=True):
            try:
                raw_data = []
                if uploaded_file.name.endswith('.docx'):
                    import docx

                    doc = docx.Document(uploaded_file)
                    for table in doc.tables:
                        for row in table.rows:
                            raw_data.append([cell.text.replace('\n', '').strip() for cell in row.cells])
                elif uploaded_file.name.endswith('.csv'):
                    raw_data = pd.read_csv(uploaded_file, header=None).fillna("").values.tolist()
                else:
                    raw_data = pd.read_excel(uploaded_file, header=None).fillna("").values.tolist()

                def _norm_txt(x):
                    """统一清洗 Word 表格中常见的空格、换行和单位写法。"""
                    s = "" if x is None else str(x)
                    s = s.replace('\n', '').replace('\r', '').replace(' ', '').replace('\u3000', '')
                    s = s.replace('m³', 'm³').replace('m3', 'm³').replace('m³', 'm³')
                    s = s.replace('Mpa', 'MPa').replace('Mpa.g', 'MPa.g').replace('PPM', 'ppm')
                    return s.strip()

                def _safe_cell(row, idx, default=''):
                    try:
                        if idx is None or idx < 0 or idx >= len(row):
                            return default
                        return row[idx]
                    except Exception:
                        return default

                def _parse_num_unit(text):
                    """从 '12.78m' / '0.3m³/h' / '-0.02MPa.g' 中提取数值和单位。"""
                    s = _norm_txt(text)
                    if not s or s.upper() in ['NA', 'NAN']:
                        return None, ''
                    m = re.search(r"([-+]?\d+(?:\.\d+)?)", s)
                    if not m:
                        return None, ''
                    val = float(m.group(1))
                    unit = s[m.end():]
                    unit = re.sub(r"^[0-9.]+", "", unit).strip()
                    return val, unit

                def _parse_range_text(range_text):
                    """提取整定范围的展示文本、上下界和单位。整定范围只用于展示/基准估计，不直接当报警值。"""
                    s = _norm_txt(range_text)
                    if not s or s.upper() in ['NA', 'NAN']:
                        return '', None, None, ''
                    unit = ''
                    # 匹配 0-13.1m、-0.100-0.150MPa.g、0~150℃
                    m = re.search(r"^([-+]?\d+(?:\.\d+)?)(?:~|～|至|\-)([-+]?\d+(?:\.\d+)?)(.*)$", s)
                    if m:
                        lo, hi = float(m.group(1)), float(m.group(2))
                        unit = m.group(3).strip()
                        return s, lo, hi, unit
                    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", s)
                    if len(nums) >= 2:
                        tail = re.sub(r"[-+]?\d+(?:\.\d+)?", "", s).replace('-', '').replace('~', '').replace('～', '').strip()
                        return s, float(nums[0]), float(nums[1]), tail
                    return s, None, None, ''

                def _is_special_logic_name(set_name):
                    """过滤非普通模拟量报警：比较表达式、差值/偏差、设定值、控制器/滤波器等。"""
                    s = _norm_txt(set_name)
                    if not s or s.upper() in ['NA', 'NAN']:
                        return True
                    # CBA<2000ppm、CBM-CBA>200ppm、硼酸累积量-设定值、补水流量>10%定值
                    if re.search(r"[<>＜＞≤≥=＝]|[-－—–]", s):
                        return True
                    bad_keywords = ['偏差', '设定值', '定值', '累积', '控制器', '滤波器', '手动设定', 'IIC', 'SP', '%', '％', 'K/(', '1/(']
                    return any(k in s for k in bad_keywords)

                def _normal_bounds_from_record(record):
                    """正常区间：所有低报警阈值中的最高值 ~ 所有高报警阈值中的最低值。"""
                    low_vals = []
                    high_vals = []
                    for col in ['低4报', '低3报', '低2报', '低报']:
                        val = record.get(col)
                        if pd.notna(val):
                            try:
                                low_vals.append(float(val))
                            except Exception:
                                pass
                    for col in ['高报', '高2报', '高3报', '高4报']:
                        val = record.get(col)
                        if pd.notna(val):
                            try:
                                high_vals.append(float(val))
                            except Exception:
                                pass
                    low_safe = max(low_vals) if low_vals else None
                    high_safe = min(high_vals) if high_vals else None
                    return low_safe, high_safe

                def _infer_baseline(record):
                    """为仿真端提供一个合理初始值；检测端实际状态仍由 live_data.csv 驱动。"""
                    low_safe, high_safe = _normal_bounds_from_record(record)
                    r_lo, r_hi = record.get('_range_low'), record.get('_range_high')
                    if low_safe is not None and high_safe is not None and low_safe < high_safe:
                        return (low_safe + high_safe) / 2
                    if r_lo is not None and r_hi is not None and r_lo < r_hi:
                        return (r_lo + r_hi) / 2
                    if high_safe is not None:
                        return high_safe * 0.7 if high_safe != 0 else 1.0
                    if low_safe is not None:
                        return low_safe * 1.3 if low_safe != 0 else 1.0
                    return 0.0

                # 只保留仪控定值中的普通模拟量分级报警。
                # 不采集机械/电气，不采集 NA/SP/K/T/D 等非报警参数。
                # L/L1/L2/L3/L4 与 H/H1/H2/H3/H4 全部属于模拟量分级报警，全部纳入清单。
                allowed_alarm_params = {'L', 'L1', 'L2', 'L3', 'L4', 'H', 'H1', 'H2', 'H3', 'H4'}
                param_to_col = {
                    'L': '低报', 'L1': '低报', 'L2': '低2报', 'L3': '低3报', 'L4': '低4报',
                    'H': '高报', 'H1': '高报', 'H2': '高2报', 'H3': '高3报', 'H4': '高4报'
                }

                in_ic_section = False
                header_idx = {}
                parsed_records_dict = {}
                skipped_special_logic = 0
                skipped_param = 0
                skipped_bad_value = 0

                for row in raw_data:
                    row_str = _norm_txt("".join([str(x) for x in row]))
                    if "仪控定值" in row_str:
                        in_ic_section = True
                        continue
                    if "机械定值" in row_str or "电气定值" in row_str:
                        in_ic_section = False
                        continue
                    if not in_ic_section:
                        continue

                    if "设备编码" in row_str and "参数代码" in row_str and "过程定值" in row_str:
                        header_idx = {}
                        for i, col in enumerate(row):
                            val = _norm_txt(col)
                            # 注意：母设备编码也包含“设备编码”，因此用完全匹配优先，避免取错列。
                            if val == "设备编码":
                                header_idx['code'] = i
                            elif val == "设备名称":
                                header_idx['name'] = i
                            elif val == "定值名称":
                                header_idx['set_name'] = i
                            elif val == "参数代码":
                                header_idx['param'] = i
                            elif val == "过程定值":
                                header_idx['value'] = i
                            elif val == "整定范围":
                                header_idx['range'] = i
                        continue

                    if not header_idx:
                        continue

                    code = _norm_txt(_safe_cell(row, header_idx.get('code')))
                    name = str(_safe_cell(row, header_idx.get('name'))).replace('\n', '').strip()
                    set_name = str(_safe_cell(row, header_idx.get('set_name'))).replace('\n', '').strip()
                    param = _norm_txt(_safe_cell(row, header_idx.get('param'))).upper()
                    val_str = _norm_txt(_safe_cell(row, header_idx.get('value')))
                    range_str = _norm_txt(_safe_cell(row, header_idx.get('range')))

                    if not code or code.upper() in ['NA', 'NAN']:
                        continue
                    if '开关量' in name or '开关量' in set_name:
                        skipped_special_logic += 1
                        continue
                    if param not in allowed_alarm_params:
                        skipped_param += 1
                        continue
                    if _is_special_logic_name(set_name):
                        skipped_special_logic += 1
                        continue

                    num_val, unit = _parse_num_unit(val_str)
                    range_display, range_low, range_high, range_unit = _parse_range_text(range_str)
                    if num_val is None:
                        skipped_bad_value += 1
                        continue
                    if not unit and range_unit:
                        unit = range_unit

                    if code not in parsed_records_dict:
                        parsed_records_dict[code] = {
                            '系统': new_sys_name,
                            '编码': code,
                            '测点名称': name if name else set_name,
                            '基准值': 0.0,
                            '正常范围': range_display if range_display else '',
                            '低4报': np.nan,
                            '低3报': np.nan,
                            '低2报': np.nan,
                            '低报': np.nan,
                            '高报': np.nan,
                            '高2报': np.nan,
                            '高3报': np.nan,
                            '高4报': np.nan,
                            '单位': unit,
                            '_range_low': range_low,
                            '_range_high': range_high,
                            '_range_display': range_display,
                        }

                    rec = parsed_records_dict[code]
                    if not rec['单位'] and unit:
                        rec['单位'] = unit
                    if not rec.get('_range_display') and range_display:
                        rec['_range_display'] = range_display
                        rec['_range_low'] = range_low
                        rec['_range_high'] = range_high

                    rec[param_to_col[param]] = num_val

                for k, v in parsed_records_dict.items():
                    unit = v.get('单位', '')
                    low_safe, high_safe = _normal_bounds_from_record(v)

                    # 正常范围 = 所有低报警值中的最高值 到 所有高报警值中的最低值。
                    # 这才是不触发任何低/高分级报警的安全区间。
                    if low_safe is not None and high_safe is not None and low_safe < high_safe:
                        v['正常范围'] = f"{low_safe:g}~{high_safe:g}"
                    elif high_safe is not None:
                        v['正常范围'] = f"≤{high_safe:g}{unit}"
                    elif low_safe is not None:
                        v['正常范围'] = f"≥{low_safe:g}{unit}"
                    elif v.get('_range_display'):
                        v['正常范围'] = v['_range_display']
                    else:
                        v['正常范围'] = "未定"

                    v['基准值'] = _infer_baseline(v)
                    v.pop('_range_low', None)
                    v.pop('_range_high', None)
                    v.pop('_range_display', None)

                if skipped_special_logic or skipped_param or skipped_bad_value:
                    st.info(
                        f"导入过滤统计：已跳过特殊逻辑/设定值/偏差类 {skipped_special_logic} 条，"
                        f"跳过非 L/L1/L2/L3/L4/H/H1/H2/H3/H4 参数 {skipped_param} 条，"
                        f"跳过无有效数值 {skipped_bad_value} 条。"
                    )

                new_df = pd.DataFrame(list(parsed_records_dict.values()))
                if new_df.empty:
                    st.warning("⚠️ 未提取到符合规范的仪控模拟量测点。")
                else:
                    # 关键修复：同名系统重新导入时，先整体替换旧记录。
                    # 否则旧版本解析留下的“只含 L/H 的残缺测点”会和新记录并存，
                    # 页面上仍可能显示旧记录，造成 H2/L2/L4 等报警值看起来没有提取出来。
                    clean_sys_name = str(new_sys_name).strip()
                    new_df['系统'] = clean_sys_name
                    existing_mask = base_system_df['系统'].astype(str).str.strip().str.casefold() != clean_sys_name.casefold()
                    merged_df = pd.concat([base_system_df.loc[existing_mask], new_df], ignore_index=True)
                    merged_df.to_csv(CONFIG_FILE, index=False)
                    st.success(f"🎉 提取成功！已替换/接入【{clean_sys_name}】共 {len(new_df)} 个模拟量分级报警测点。")
                    st.rerun()
            except Exception as e:
                st.error(f"解析失败: {e}")

# ==========================================
# 2. 系统调度与高联动双向时间窗
# ==========================================
system_options = base_system_df['系统'].dropna().unique().tolist()
# 刷新按钮必须保持当前系统，不允许刷新后跳回列表第一个系统。
if st.session_state.get("refresh_target_system") in system_options:
    st.session_state["selected_monitor_system"] = st.session_state.pop("refresh_target_system")
if st.session_state.get("selected_monitor_system") not in system_options:
    st.session_state["selected_monitor_system"] = system_options[0] if system_options else None
label_col, refresh_col = st.sidebar.columns([0.90, 0.10], gap="small")
with label_col:
    st.markdown('<div class="sys-switch-label">📂 <b>切换监测工艺系统</b></div>', unsafe_allow_html=True)
with refresh_col:
    if st.button("↻", key="refresh_monitor_system", help="刷新当前系统数据/重新读取模拟输入"):
        # 模拟端启动或停止后，点击此按钮只刷新当前系统数据，不改变当前选择。
        cur_sys = st.session_state.get("selected_monitor_system")
        if cur_sys in system_options:
            st.session_state["refresh_target_system"] = cur_sys
            st.session_state["selected_monitor_system"] = cur_sys
        st.session_state.pop('last_ai_response', None)
        st.session_state['data_range_key'] = None
        st.rerun()
selected_system = st.sidebar.selectbox(
    "切换监测工艺系统",
    system_options,
    key="selected_monitor_system",
    label_visibility="collapsed"
)
active_system_df = base_system_df[base_system_df['系统'] == selected_system].reset_index(drop=True)

try:
    df_ts_full = pd.read_csv(DATA_FILE)
    df_ts_full['Time'] = pd.to_datetime(df_ts_full['Time'])
except FileNotFoundError:
    st.error("🚨 基础数据总线未接通。请优先运行 app_simulation.py 发射工况。")
    st.stop()

if df_ts_full.empty:
    abs_start = datetime.now() - timedelta(days=1)
    abs_end = datetime.now()
else:
    abs_start, abs_end = df_ts_full['Time'].min().to_pydatetime(), df_ts_full['Time'].max().to_pydatetime()

current_data_range_key = (abs_start.strftime('%Y-%m-%d %H:%M:%S'), abs_end.strftime('%Y-%m-%d %H:%M:%S'))
# 当仿真端把时间轴平移到新的实时窗口后，自动把分析窗重置到最新数据范围，
# 避免浏览器会话里残留旧的 2026-06-01~06-05 时间窗导致看不到数据。
if st.session_state.get('data_range_key') != current_data_range_key:
    st.session_state['data_range_key'] = current_data_range_key
    st.session_state['ts_start'] = abs_start
    st.session_state['ts_end'] = abs_end
if 'ts_start' not in st.session_state:
    st.session_state['ts_start'] = abs_start
if 'ts_end' not in st.session_state:
    st.session_state['ts_end'] = abs_end
# 防止手动输入或旧会话状态超出当前实时数据范围。
st.session_state['ts_start'] = max(abs_start, min(st.session_state['ts_start'], abs_end))
st.session_state['ts_end'] = max(abs_start, min(st.session_state['ts_end'], abs_end))
if st.session_state['ts_start'] >= st.session_state['ts_end']:
    st.session_state['ts_start'], st.session_state['ts_end'] = abs_start, abs_end


def on_slider_change():
    st.session_state['ts_start'], st.session_state['ts_end'] = st.session_state['main_slider']
    st.session_state['txt_start_key'] = st.session_state['ts_start'].strftime('%Y-%m-%d %H:%M')
    st.session_state['txt_end_key'] = st.session_state['ts_end'].strftime('%Y-%m-%d %H:%M')


def on_confirm_click():
    try:
        ps, pe = pd.to_datetime(st.session_state['txt_start_key']).to_pydatetime(), pd.to_datetime(
            st.session_state['txt_end_key']).to_pydatetime()
        if ps >= pe:
            st.sidebar.error("⚠️ 开始时间需小于截止时间！")
        else:
            st.session_state.update({'ts_start': ps, 'ts_end': pe, 'main_slider': (ps, pe)})
    except Exception:
        st.sidebar.error("⚠️ 格式非法")


st.sidebar.slider("⏳ 设定智能分析时间窗", min_value=abs_start, max_value=abs_end,
                  value=(st.session_state['ts_start'], st.session_state['ts_end']), format="MM/DD HH:mm",
                  step=timedelta(minutes=10), key="main_slider", on_change=on_slider_change)
st.sidebar.markdown("✍️ **手动精确调整时间窗**")
st.sidebar.text_input("开始时间：", value=st.session_state['ts_start'].strftime('%Y-%m-%d %H:%M'), key="txt_start_key")
st.sidebar.text_input("截止时间：", value=st.session_state['ts_end'].strftime('%Y-%m-%d %H:%M'), key="txt_end_key")
st.sidebar.button("✅ 确定应用新时间", type="primary", use_container_width=True, on_click=on_confirm_click)

if not df_ts_full.empty:
    df_ts = df_ts_full.loc[(df_ts_full['Time'] >= st.session_state['ts_start']) & (
                df_ts_full['Time'] <= st.session_state['ts_end'])].reset_index(drop=True)
else:
    df_ts = pd.DataFrame(columns=['Time'])

# ==========================================
# 3. 动态核心图表绘制舱 (状态看门狗与标题微调)
# ==========================================
if 'active_point_codes' not in st.session_state: st.session_state['active_point_codes'] = [
    active_system_df['编码'].iloc[0]]
if not set(st.session_state['active_point_codes']).issubset(active_system_df['编码'].values): st.session_state[
    'active_point_codes'] = [active_system_df['编码'].iloc[0]]

primary_code = st.session_state['active_point_codes'][0]
point_info = active_system_df[active_system_df['编码'] == primary_code].iloc[0]
point_name, unit = point_info['测点名称'], point_info.get('单位', '')

valid_codes = [c for c in st.session_state['active_point_codes'] if
               active_system_df[active_system_df['编码'] == c].iloc[0].get('单位', '') == unit]

# ──── 【核心修复 1：增设状态监视哨，阻断AI结论跨点跨系统污染】 ────
current_tracking_key = f"{selected_system}_{primary_code}"
if "last_processed_key" not in st.session_state:
    st.session_state["last_processed_key"] = current_tracking_key

if st.session_state["last_processed_key"] != current_tracking_key:
    if 'last_ai_response' in st.session_state:
        del st.session_state['last_ai_response']  # 强制抹除上一靶点的分析痕迹
    st.session_state["last_processed_key"] = current_tracking_key

st.markdown("## 📊 重大设备状态智能监测预警系统")

# ──── 【核心修复 2：冒号后方动态数值内容加粗，前缀标签保持常规字体】 ────
st.markdown(
    f"系统名称：**{selected_system}** &nbsp;|&nbsp; 设备编码：**{primary_code}** &nbsp;|&nbsp; 监测对象：**{point_name}** &nbsp;|&nbsp; 正常范围标准：**{point_info['正常范围']} {unit}**")

# 游标截面时刻：先从 session_state 读取游标值用于绘图；
# 滑块控件放到主图下方，更像时间轴下的小游标，不抢占主图上方空间。
if not df_ts.empty:
    cursor_min = df_ts['Time'].min().to_pydatetime()
    cursor_max = df_ts['Time'].max().to_pydatetime()
    cursor_key = f"cursor_time_slider_{selected_system}"
    cur_saved = st.session_state.get(cursor_key)
    if cur_saved is None or cur_saved < cursor_min or cur_saved > cursor_max:
        st.session_state[cursor_key] = cursor_max
    cursor_time = st.session_state[cursor_key]
else:
    cursor_min = cursor_max = st.session_state['ts_end']
    cursor_key = f"cursor_time_slider_{selected_system}"
    cursor_time = st.session_state['ts_end']

has_curve_stream = False
theme_colors = ['#00ffcc', '#ff00ff', '#00aaff', '#ffff00', '#ff9900', '#00ff00']
fig = go.Figure()
alarm_legend_items = []
curve_legend_items = []

for i, code in enumerate(valid_codes):
    actual_col = resolve_actual_col(df_ts, selected_system, code)
    if actual_col is not None and not df_ts[actual_col].isna().all():
        has_curve_stream = True
        break

if not df_ts.empty:
    x_vals = df_ts['Time'].tolist()
else:
    x_vals = pd.date_range(start=st.session_state['ts_start'], end=st.session_state['ts_end'], periods=10).tolist()

for limit_key, color, dash in [('高4报', '#550000', 'dash'), ('高3报', '#8B0000', 'dash'), ('高2报', '#FF4500', 'dash'),
                               ('高报', '#FFD700', 'dash'), ('低报', '#1E90FF', 'dashdot'),
                               ('低2报', '#0000CD', 'dashdot'),
                               ('低3报', '#800080', 'dashdot'), ('低4报', '#4B0082', 'dashdot')]:
    if limit_key in point_info and pd.notna(point_info[limit_key]):
        l_val = float(point_info[limit_key])
        alarm_label = f'{limit_key} ({l_val:g})'
        alarm_legend_items.append((alarm_label, color, 'dashed'))
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=[l_val] * len(x_vals),
            mode='lines',
            name=alarm_label,
            line=dict(color=color, width=1.5, dash=dash),
            hoverinfo='skip',
            showlegend=False
        ))

if has_curve_stream:
    for i, code in enumerate(valid_codes):
        actual_col = resolve_actual_col(df_ts, selected_system, code)
        if actual_col is not None:
            y_actual = df_ts[actual_col].tolist()
            c_meta_name = active_system_df[active_system_df['编码'] == code].iloc[0]['测点名称']
            curve_color = theme_colors[i % len(theme_colors)]
            curve_legend_items.append((str(c_meta_name), curve_color, 'solid'))
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_actual, mode='lines', name=f'{c_meta_name}',
                line=dict(color=curve_color, width=2.5 if i == 0 else 2.0),
                hovertemplate=f"%{{x|%Y-%m-%d %H:%M}}<br>{c_meta_name}: %{{y:.4g}}{unit}<extra></extra>",
                showlegend=False
            ))

fig.add_vline(x=cursor_time.strftime('%Y-%m-%d %H:%M:%S'), line_width=2, line_dash="dash", line_color="cyan")
x_axis_range = [st.session_state['ts_start'], st.session_state['ts_end']]
fig.update_xaxes(
    tickformat="%Y-%m-%d\n%H:%M",
    hoverformat="%Y-%m-%d %H:%M:%S",
    range=x_axis_range,
    fixedrange=True
)
fig.update_yaxes(rangemode="tozero", fixedrange=True)
fig.update_layout(
    template="plotly_dark",
    height=286,
    margin=dict(l=28, r=28, t=4, b=54),
    hovermode="closest",
    hoverlabel=dict(
        bgcolor="rgba(255,255,255,0.68)",
        bordercolor="rgba(0,0,0,0.15)",
        font_size=11,
        align="left"
    ),
    dragmode=False,
    showlegend=False
)

legend_parts = []
for label, color, line_style in alarm_legend_items + curve_legend_items:
    safe_label = html.escape(str(label))
    safe_color = html.escape(str(color), quote=True)
    border_style = "solid" if line_style == "solid" else "dashed"
    legend_parts.append(
        f'<span class="alarm-legend-item">'
        f'<span class="alarm-legend-line" style="border-top:2px {border_style} {safe_color};"></span>'
        f'<span>{safe_label}</span></span>'
    )

if legend_parts:
    st.markdown(
        '<div class="alarm-legend-wrap">'
        '<span class="alarm-legend-title">测点曲线及各级报警线：</span>'
        + ''.join(legend_parts)
        + '</div>',
        unsafe_allow_html=True
    )

if not has_curve_stream:
    st.warning(f"⚠️ 核心提示：系统已录入【{primary_code}】的定值规范坐标轴架，但当前总线尚未接收到外部模拟曲线数据。")

# 先保留主图位置；异常检测完成后再把关键点标注写入图中并统一渲染。
chart_placeholder = st.empty()

# 轻量游标：隐藏文字，仅保留可拖动小三角；清单读取该截面值。
if not df_ts.empty:
    with st.container(key="cursor_slider_box"):
        st.slider(
            "游标截面时刻",
            min_value=cursor_min,
            max_value=cursor_max,
            value=st.session_state[cursor_key],
            step=timedelta(minutes=10),
            format="MM/DD HH:mm",
            key=cursor_key,
            label_visibility="collapsed",
            help="拖动时间轴附近的小三角，清单『📍游标时刻值』会读取对应截面。"
        )

# ==========================================
# 4. 全景多维预警及大模型综合分析推理模块
# ==========================================
global_has_anomaly, global_is_severe = False, False
all_fault_descs = []
p_max, p_min = 0.0, 0.0

# 工况曲线关键点：仅异常情况下记录极值点，正常曲线不添加任何标注。
curve_key_points = {}
_key_point_priority = {
    'low_extreme': 1,
    'high_extreme': 1,
}


def _register_curve_key_point(code, point_time, point_value, title, kind, ax=0, ay=-42):
    """登记异常极值点；同一波峰/波谷附近只保留一个最极端的点。"""
    try:
        ts = pd.to_datetime(point_time)
        value = float(point_value)
    except Exception:
        return
    if pd.isna(ts) or not np.isfinite(value):
        return

    code = str(code)
    merge_window = pd.Timedelta(minutes=120)

    # 同一测点、同一方向且时间相近的候选点，视为同一个波峰或波谷。
    # 高侧只保留数值最大的点，低侧只保留数值最小的点，避免多个圆点挤在一起。
    for current in curve_key_points.values():
        if current.get('code') != code or current.get('kind') != kind:
            continue
        if abs(ts - current.get('time')) > merge_window:
            continue

        if str(title) not in current['titles']:
            current['titles'].append(str(title))

        is_more_extreme = (
            (kind == 'high_extreme' and value > current.get('value', value))
            or (kind == 'low_extreme' and value < current.get('value', value))
        )
        if is_more_extreme:
            current.update({
                'time': ts,
                'value': value,
                'ax': ax,
                'ay': ay,
            })
        return

    key = (code, int(ts.value), round(value, 8))
    curve_key_points[key] = {
        'code': code,
        'time': ts,
        'value': value,
        'titles': [str(title)],
        'kind': kind,
        'priority': _key_point_priority.get(kind, 0),
        'ax': ax,
        'ay': ay,
    }


def get_limit(val):
    try:
        return float(val) if pd.notna(val) and str(val).strip() != '' else None
    except:
        return None


def get_alarm_ranges(mask, time_series):
    # 兼容 NaN 布尔掩码，避免部分空值导致连续区间切分异常
    mask = pd.Series(mask, index=time_series.index).fillna(False).astype(bool)
    if not mask.any():
        return ""
    diff = mask.ne(mask.shift())
    groups = diff.cumsum()
    ranges = []
    for _, group in time_series[mask].groupby(groups[mask]):
        start_t = group.min().strftime('%Y-%m-%d %H:%M')
        end_t = group.max().strftime('%H:%M')
        if group.min().strftime('%m-%d') != group.max().strftime('%m-%d'):
            end_t = group.max().strftime('%Y-%m-%d %H:%M')
        ranges.append(f"[{start_t} 至 {end_t}]")
    return "、".join(ranges[:3]) + (f" 等共计 {len(ranges)} 个时段" if len(ranges) > 3 else "")


def _robust_data_scale(series):
    """返回用于突变阈值的工程尺度。只用于识别突变，不用于生成“安全区间趋势偏移”报警。"""
    s = pd.to_numeric(series, errors='coerce').dropna()
    if len(s) == 0:
        return 1.0
    median_abs = abs(float(s.median()))
    if len(s) >= 5:
        q95, q05 = np.nanpercentile(s, [95, 5])
        span = abs(float(q95 - q05))
    else:
        span = abs(float(s.max() - s.min()))
    return max(span, median_abs * 0.10, 1e-6)


def _noise_sigma(series):
    """用一阶差分的 MAD 估计仪表微噪，避免把正常抖动识别成突变。"""
    s = pd.to_numeric(series, errors='coerce').dropna()
    if len(s) < 3:
        return 0.0
    diff_valid = s.diff().dropna()
    if len(diff_valid) == 0:
        return 0.0
    diff_median = float(diff_valid.median())
    return float(1.4826 * np.median(np.abs(diff_valid - diff_median)))


def _engineering_span(series, safe_low, safe_high):
    """
    仅在同时存在低报警与高报警时，使用正常区间宽度作为工程尺度。
    单侧报警测点不强行拼量程，改用历史数据自身尺度判断突变。
    """
    if safe_low is not None and safe_high is not None and safe_high > safe_low:
        return float(safe_high - safe_low)
    return _robust_data_scale(series)


def _near_margin(series, threshold_value, span=None):
    """
    临近报警线的缓冲带：双侧报警优先用正常带宽的 5%；单侧报警使用报警值/当前值的小比例。
    """
    if span is not None and span > 0:
        return max(span * 0.05, _noise_sigma(series) * 5, 1e-6)
    s = pd.to_numeric(series, errors='coerce').dropna()
    ref = abs(float(threshold_value)) if threshold_value not in [None, 0] else 0.0
    if len(s) > 0:
        ref = max(ref, abs(float(s.median())))
    return max(ref * 0.03, _noise_sigma(series) * 5, 1e-6)


@st.cache_data(show_spinner=False, max_entries=512)
def _detect_jump_events(series, time_series, span):
    """
    混合型突变检测：覆盖瞬时尖峰/下探、短时快速变化、持续爬坡和平台跃迁。

    与上一版相比，本版重点修正事件起止时间：
    1. 触发阈值仍用于确认“这是一次突变”，但事件开始时间会向前回溯到
       曲线首次持续脱离原稳态的位置，而不是把首次达到 7% 阈值的时间当作开始时间；
    2. 回归稳定或进入新稳态时，记录稳定区间的第一个采样点，避免结束时间额外延迟；
    3. 主体候选计算保持 NumPy 向量化，仅对少量候选事件做局部回溯，保证切换测点速度。
    """
    raw_values = pd.to_numeric(series, errors='coerce')
    raw_times = pd.to_datetime(time_series, errors='coerce')
    work = pd.DataFrame({'time': raw_times, 'value': raw_values}).dropna()
    work = work.sort_values('time').drop_duplicates(subset='time', keep='last').reset_index(drop=True)
    if len(work) < 6:
        return []

    times = work['time']
    values = work['value'].to_numpy(dtype=float)
    time_minutes = times.astype('int64').to_numpy(dtype=np.float64) / 60_000_000_000.0
    dt_minutes = np.diff(time_minutes, prepend=np.nan)
    valid_dt = dt_minutes[np.isfinite(dt_minutes) & (dt_minutes > 0)]
    sample_minutes = float(np.median(valid_dt)) if len(valid_dt) else 10.0
    sample_minutes = max(sample_minutes, 1e-3)

    noise = max(float(_noise_sigma(pd.Series(values))), 0.0)
    robust_scale = max(float(_robust_data_scale(pd.Series(values))), 1e-6)
    try:
        engineering_span = abs(float(span)) if span is not None and np.isfinite(float(span)) else 0.0
    except Exception:
        engineering_span = 0.0

    # 轻度中值平滑用于识别爬坡；瞬时尖峰仍使用原始值判断。
    smooth_points = max(3, int(round(20.0 / sample_minutes)))
    if smooth_points % 2 == 0:
        smooth_points += 1
    smooth_points = min(smooth_points, 7)
    smooth_values = (
        pd.Series(values)
        .rolling(window=smooth_points, center=True, min_periods=1)
        .median()
        .to_numpy(dtype=float)
    )

    time_index = pd.DatetimeIndex(times)
    indexed_raw = pd.Series(values, index=time_index)
    indexed_smooth = pd.Series(smooth_values, index=time_index)

    # 快速变化基准：当前点之前 1 小时均值。
    fast_roll = indexed_raw.rolling('60min', closed='left')
    fast_baseline = fast_roll.mean().to_numpy(dtype=float)
    fast_count = fast_roll.count().to_numpy(dtype=float)

    # 爬坡基准：当前点之前 6 小时中位数，避免爬坡过程污染基准。
    slow_roll = indexed_smooth.rolling('6h', closed='left')
    slow_baseline = slow_roll.median().to_numpy(dtype=float)
    slow_count = slow_roll.count().to_numpy(dtype=float)

    min_fast_points = max(3, int(np.ceil(20.0 / sample_minutes)))
    min_slow_points = max(min_fast_points, int(np.ceil(60.0 / sample_minutes)))
    fast_valid_base = (fast_count >= min_fast_points) & np.isfinite(fast_baseline)
    slow_valid_base = (slow_count >= min_slow_points) & np.isfinite(slow_baseline)

    baseline = np.where(slow_valid_base, slow_baseline, fast_baseline)
    baseline_valid = np.where(slow_valid_base, True, fast_valid_base) & np.isfinite(baseline)

    fallback_scale = max(
        robust_scale * 0.25,
        engineering_span * 0.05,
        noise * 10.0,
        1e-6
    )
    ref_scale = np.abs(baseline)
    ref_scale = np.where(
        np.isfinite(ref_scale) & (ref_scale > max(noise * 6.0, 1e-6)),
        ref_scale,
        fallback_scale
    )
    ref_scale = np.maximum(ref_scale, 1e-6)
    absolute_gate = np.maximum(noise * 6.0, ref_scale * 0.015)

    # A. 瞬时/快速突变：相邻点相对变化 + 单位时间相对斜率。
    step_delta = np.diff(values, prepend=np.nan)
    safe_dt = np.where(np.isfinite(dt_minutes) & (dt_minutes > 0), dt_minutes, np.nan)
    fast_ref = np.abs(fast_baseline)
    fast_ref = np.where(
        np.isfinite(fast_ref) & (fast_ref > max(noise * 6.0, 1e-6)),
        fast_ref,
        fallback_scale
    )
    fast_ref = np.maximum(fast_ref, 1e-6)
    step_rel_change = np.abs(step_delta) / fast_ref
    step_rel_slope = np.divide(
        step_rel_change,
        safe_dt,
        out=np.zeros_like(step_rel_change),
        where=np.isfinite(safe_dt) & (safe_dt > 0)
    )
    fast_mask = (
        fast_valid_base
        & np.isfinite(step_delta)
        & (step_rel_change >= 0.05)
        & (step_rel_slope >= 0.003)
        & (np.abs(step_delta) >= np.maximum(noise * 6.0, fast_ref * 0.012))
    )

    # B. 爬坡/平台突变：相对于长期稳态基准的累计偏离。
    deviation = smooth_values - baseline
    rel_deviation = np.abs(deviation) / ref_scale

    max_window_rel_change = np.zeros(len(values), dtype=float)
    max_window_rel_slope = np.zeros(len(values), dtype=float)
    all_indices = np.arange(len(values))
    for horizon_minutes in (30.0, 60.0, 120.0, 180.0, 360.0):
        start_indices = np.searchsorted(time_minutes, time_minutes - horizon_minutes, side='left')
        elapsed = time_minutes - time_minutes[start_indices]
        delta = smooth_values - smooth_values[start_indices]
        rel_change = np.abs(delta) / ref_scale
        rel_slope = np.divide(
            rel_change,
            elapsed,
            out=np.zeros_like(rel_change),
            where=elapsed > 0
        )
        valid_window = (
            (start_indices < all_indices)
            & (elapsed >= min(20.0, horizon_minutes * 0.45))
            & (elapsed <= horizon_minutes + sample_minutes * 1.5)
        )
        max_window_rel_change = np.maximum(
            max_window_rel_change,
            np.where(valid_window, rel_change, 0.0)
        )
        max_window_rel_slope = np.maximum(
            max_window_rel_slope,
            np.where(valid_window, rel_slope, 0.0)
        )

    ramp_mask = (
        baseline_valid
        & (rel_deviation >= 0.07)
        & (np.abs(deviation) >= absolute_gate)
        & (max_window_rel_change >= 0.05)
        & (max_window_rel_slope >= 0.00012)
    )

    candidate_mask = fast_mask | ramp_mask
    if not candidate_mask.any():
        return []

    candidate_starts = np.flatnonzero(candidate_mask & ~np.r_[False, candidate_mask[:-1]])
    events = []
    covered_until = -1
    stable_points_required = max(2, int(np.ceil(30.0 / sample_minutes)))
    plateau_points_required = max(stable_points_required, int(np.ceil(60.0 / sample_minutes)))
    onset_confirm_points = max(2, int(np.ceil(20.0 / sample_minutes)))
    max_event_minutes = 12.0 * 60.0

    for trigger_idx in candidate_starts:
        trigger_idx = int(trigger_idx)
        if trigger_idx <= covered_until:
            continue

        is_fast_trigger = bool(fast_mask[trigger_idx])
        if is_fast_trigger:
            base_value = float(fast_baseline[trigger_idx])
            trigger_delta = float(values[trigger_idx] - base_value)
        else:
            base_value = float(baseline[trigger_idx])
            trigger_delta = float(smooth_values[trigger_idx] - base_value)

        if not np.isfinite(base_value) or trigger_delta == 0:
            continue
        direction = 1 if trigger_delta > 0 else -1

        scale = abs(base_value)
        if scale <= max(noise * 6.0, 1e-6):
            scale = fallback_scale
        scale = max(scale, 1e-6)

        # 回溯真正的突变起点：阈值触发点只负责确认异常，开始时间取曲线首次
        # 持续脱离稳态的点。0.4% 的低门槛用于找起点，不用于确认是否报警。
        search_begin = int(np.searchsorted(time_minutes, time_minutes[trigger_idx] - 360.0, side='left'))
        prior_segment = smooth_values[search_begin:trigger_idx + 1]
        directional_dev = direction * (prior_segment - base_value)
        directional_steps = direction * np.diff(prior_segment, prepend=prior_segment[0])
        onset_deviation_gate = max(scale * 0.004, noise * 2.5, 1e-6)
        onset_step_gate = max(scale * 0.0008, noise * 1.2, 1e-6)
        small_reverse_tolerance = max(scale * 0.0004, noise * 0.8, 1e-6)

        start_local = None
        for local_idx in range(1, len(prior_segment)):
            confirm_end = min(len(prior_segment), local_idx + onset_confirm_points)
            if confirm_end <= local_idx:
                continue
            confirm_steps = directional_steps[local_idx:confirm_end]
            net_move = direction * (
                prior_segment[confirm_end - 1] - prior_segment[max(0, local_idx - 1)]
            )
            forward_fraction = float(np.mean(confirm_steps >= -small_reverse_tolerance)) if len(confirm_steps) else 0.0
            onset_signal = (
                directional_dev[local_idx] >= onset_deviation_gate
                or directional_steps[local_idx] >= onset_step_gate
            )
            if (
                onset_signal
                and net_move >= onset_deviation_gate * 0.8
                and forward_fraction >= 0.65
            ):
                start_local = local_idx
                break

        if start_local is not None:
            start_idx = search_begin + int(start_local)
        else:
            # 极短尖峰可能没有可持续回溯段，起点取发生明显跳变的当前点。
            start_idx = trigger_idx

        start_idx = max(search_begin, min(start_idx, trigger_idx))

        # 用起点之前 1 小时重新计算稳态值，报告基准不受突变过程污染。
        prior_mask = (
            (time_minutes < time_minutes[start_idx])
            & (time_minutes >= time_minutes[start_idx] - 60.0)
        )
        if int(prior_mask.sum()) >= min_fast_points:
            base_value = float(np.mean(values[prior_mask]))
            scale = abs(base_value)
            if scale <= max(noise * 6.0, 1e-6):
                scale = fallback_scale
            scale = max(scale, 1e-6)

        # 回归原稳态采用更窄的 1.8% 带宽，避免曲线仍明显偏离稳态时就提前结束事件。
        recovery_band = max(scale * 0.018, noise * 6.0, 1e-6)
        # 新平台必须连续稳定约 1 小时，防止把峰值后的缓慢回落误判成新稳态。
        plateau_range_gate = max(scale * 0.012, noise * 7.0, 1e-6)
        plateau_deviation_gate = max(scale * 0.065, noise * 7.0, 1e-6)

        extreme_idx = trigger_idx
        event_end_idx = trigger_idx
        end_reason = 'data_end'
        recovery_count = 0
        plateau_count = 0

        for k in range(trigger_idx + 1, len(values)):
            if time_minutes[k] - time_minutes[start_idx] > max_event_minutes:
                event_end_idx = k
                end_reason = 'timeout'
                break

            if direction > 0 and values[k] >= values[extreme_idx]:
                extreme_idx = k
            elif direction < 0 and values[k] <= values[extreme_idx]:
                extreme_idx = k

            event_end_idx = k

            if k > extreme_idx and abs(values[k] - base_value) <= recovery_band:
                recovery_count += 1
            else:
                recovery_count = 0

            recent_start = max(start_idx, k - plateau_points_required + 1)
            recent_values = values[recent_start:k + 1]
            if len(recent_values) >= plateau_points_required:
                recent_range = float(np.nanmax(recent_values) - np.nanmin(recent_values))
                recent_mean = float(np.nanmean(recent_values))
                if (
                    k > extreme_idx
                    and recent_range <= plateau_range_gate
                    and abs(recent_mean - base_value) >= plateau_deviation_gate
                ):
                    plateau_count += 1
                else:
                    plateau_count = 0

            if recovery_count >= 2:
                # 记录回归稳定区间的第一个点，而不是第二个确认点。
                event_end_idx = max(extreme_idx, k - recovery_count + 1)
                end_reason = 'recovered'
                break
            if plateau_count >= 2:
                # 记录新稳态区间的起点，避免结束时间额外延迟。
                event_end_idx = max(extreme_idx, k - plateau_points_required + 1)
                end_reason = 'new_plateau'
                break

        segment = values[start_idx:event_end_idx + 1]
        if len(segment) < 2:
            continue
        if direction > 0:
            extreme_idx = start_idx + int(np.nanargmax(segment))
        else:
            extreme_idx = start_idx + int(np.nanargmin(segment))

        signed_change = float(values[extreme_idx] - base_value)
        if signed_change == 0 or (signed_change > 0) != (direction > 0):
            continue

        total_change = abs(signed_change)
        relative_change = total_change / scale
        minutes_to_extreme = max(time_minutes[extreme_idx] - time_minutes[start_idx], sample_minutes)
        average_relative_slope = relative_change / minutes_to_extreme

        # 瞬时尖峰的事件起点就是异常采样点，但斜率仍需与前一个稳态采样点比较。
        slope_calc_start = max(0, start_idx - 1)
        local_steps = np.diff(values[slope_calc_start:extreme_idx + 1])
        local_dt = np.diff(time_minutes[slope_calc_start:extreme_idx + 1])
        if len(local_steps):
            local_step_rel_change = np.abs(local_steps) / scale
            local_step_slope = np.divide(
                local_step_rel_change,
                local_dt,
                out=np.zeros_like(local_step_rel_change),
                where=local_dt > 0
            )
            peak_relative_slope = float(np.nanmax(local_step_slope))
            peak_step_change = float(np.nanmax(local_step_rel_change))
        else:
            peak_relative_slope = 0.0
            peak_step_change = 0.0

        absolute_event_gate = max(noise * 6.0, scale * 0.015, 1e-6)
        fast_valid = (
            peak_step_change >= 0.05
            and peak_relative_slope >= 0.003
            and total_change >= absolute_event_gate
        )
        ramp_valid = (
            relative_change >= 0.07
            and average_relative_slope >= 0.00012
            and total_change >= absolute_event_gate
            and minutes_to_extreme <= 360.0 + sample_minutes * 2
        )
        broad_ramp_valid = (
            relative_change >= 0.10
            and total_change >= absolute_event_gate
            and minutes_to_extreme <= 720.0
        )
        if not (fast_valid or ramp_valid or broad_ramp_valid):
            continue

        event_type = (
            '瞬时突变'
            if fast_valid and minutes_to_extreme <= max(30.0, sample_minutes * 3)
            else '爬坡突变'
        )
        display_slope = peak_relative_slope if event_type == '瞬时突变' else average_relative_slope

        events.append({
            'start_time': times.iloc[start_idx].strftime('%Y-%m-%d %H:%M'),
            'end_time': times.iloc[event_end_idx].strftime('%Y-%m-%d %H:%M'),
            'extreme_time': times.iloc[extreme_idx].strftime('%Y-%m-%d %H:%M'),
            'start_timestamp': times.iloc[start_idx],
            'end_timestamp': times.iloc[event_end_idx],
            'extreme_timestamp': times.iloc[extreme_idx],
            'dir': '+' if signed_change > 0 else '-',
            'event_type': event_type,
            'end_reason': end_reason,
            'total_change': total_change,
            'signed_change': signed_change,
            'start_value': base_value,
            'start_point_value': float(values[start_idx]),
            'baseline_value': base_value,
            'end_value': float(values[extreme_idx]),
            'extreme_value': float(values[extreme_idx]),
            'recovery_value': float(values[event_end_idx]),
            'relative_change_pct': relative_change * 100.0,
            'relative_slope_per_min': display_slope * 100.0,
            'average_relative_slope_per_min': average_relative_slope * 100.0,
            'peak_relative_slope_per_min': peak_relative_slope * 100.0,
            'duration_minutes': max(time_minutes[event_end_idx] - time_minutes[start_idx], 0.0),
            'duration_steps': max(1, event_end_idx - start_idx),
            'threshold': 0.00012 if event_type == '爬坡突变' else 0.003,
        })

        covered_until = event_end_idx
        while covered_until + 1 < len(values) and candidate_mask[covered_until + 1]:
            covered_until += 1

    return events


def _format_jump_event(je, unit):
    """格式化突变区间；只保留稳态基准、极值及极值时间等关键内容。"""
    event_type = je.get('event_type', '瞬时突变')
    if event_type == '爬坡突变':
        direction_word = '持续爬坡上升' if je.get('dir') == '+' else '持续爬坡下降'
    else:
        direction_word = '快速上升' if je.get('dir') == '+' else '快速下降'

    signed = '+' if je.get('dir') == '+' else '-'
    start_t = je.get('start_time') or je.get('time')
    end_t = je.get('end_time') or start_t
    extreme_t = je.get('extreme_time')
    total = float(je.get('total_change', je.get('amp', 0.0)))
    baseline_value = je.get('baseline_value', je.get('start_value'))
    extreme_value = je.get('extreme_value', je.get('end_value'))

    detail_parts = []
    if baseline_value is not None and extreme_value is not None:
        detail_parts.append(f"前1小时稳态均值{float(baseline_value):.2f}{unit}→极值{float(extreme_value):.2f}{unit}")
    if extreme_t:
        detail_parts.append(f"极值时刻{extreme_t}")

    details = f"（{'；'.join(detail_parts)}）" if detail_parts else ""
    if start_t and end_t and start_t != end_t:
        return f"{start_t} 至 {end_t} {direction_word} {signed}{total:.2f}{unit}{details}"
    return f"{start_t} {'瞬时上冲' if je.get('dir') == '+' else '瞬时下探'} {signed}{total:.2f}{unit}{details}"


if has_curve_stream:
    for code in valid_codes:
        actual_col = resolve_actual_col(df_ts, selected_system, code)
        if actual_col is None:
            continue
        series = df_ts[actual_col]
        r_meta = active_system_df[active_system_df['编码'] == code].iloc[0]

        lim_h4, lim_h3, lim_h2, lim_h1 = (
            get_limit(r_meta.get('高4报')), get_limit(r_meta.get('高3报')),
            get_limit(r_meta.get('高2报')), get_limit(r_meta.get('高报'))
        )
        lim_l1, lim_l2, lim_l3, lim_l4 = (
            get_limit(r_meta.get('低报')), get_limit(r_meta.get('低2报')),
            get_limit(r_meta.get('低3报')), get_limit(r_meta.get('低4报'))
        )

        c_max, c_min = series.max(), series.min()
        if code == primary_code: p_max, p_min = c_max, c_min

        high_levels = [x for x in [lim_h1, lim_h2, lim_h3, lim_h4] if x is not None]
        low_levels = [x for x in [lim_l1, lim_l2, lim_l3, lim_l4] if x is not None]
        safe_high = min(high_levels) if high_levels else None  # 最先触发的高侧报警线
        safe_low = max(low_levels) if low_levels else None     # 最先触发的低侧报警线

        # 只保留三类检测：越限、临近报警线、短时快速变化/突变。
        # 不再把安全区间内的缓慢趋势/平台偏移作为异常报警，避免正常工况调节被误报。
        span_for_margin = (safe_high - safe_low) if (safe_low is not None and safe_high is not None and safe_high > safe_low) else None
        high_margin = _near_margin(series, safe_high, span_for_margin) if safe_high is not None else None
        low_margin = _near_margin(series, safe_low, span_for_margin) if safe_low is not None else None

        is_h = safe_high is not None and c_max >= safe_high
        is_l = safe_low is not None and c_min <= safe_low
        is_app_h = (not is_h) and safe_high is not None and c_max >= (safe_high - high_margin)
        is_app_l = (not is_l) and safe_low is not None and c_min <= (safe_low + low_margin)

        engineering_span = _engineering_span(series, safe_low, safe_high)
        jump_events = _detect_jump_events(series, df_ts['Time'], engineering_span)

        alarm_triggers = []
        if lim_h4 is not None and (series >= lim_h4).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series >= lim_h4, df_ts['Time'])} 突破高4报线 ({lim_h4}{unit})"); global_is_severe = True
        elif lim_h3 is not None and (series >= lim_h3).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series >= lim_h3, df_ts['Time'])} 突破高3报线 ({lim_h3}{unit})"); global_is_severe = True
        elif lim_h2 is not None and (series >= lim_h2).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series >= lim_h2, df_ts['Time'])} 突破高2报线 ({lim_h2}{unit})"); global_is_severe = True
        elif lim_h1 is not None and (series >= lim_h1).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series >= lim_h1, df_ts['Time'])} 突破高报线 ({lim_h1}{unit})"); global_is_severe = True

        if lim_l4 is not None and (series <= lim_l4).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series <= lim_l4, df_ts['Time'])} 突破低4报线 ({lim_l4}{unit})"); global_is_severe = True
        elif lim_l3 is not None and (series <= lim_l3).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series <= lim_l3, df_ts['Time'])} 突破低3报线 ({lim_l3}{unit})"); global_is_severe = True
        elif lim_l2 is not None and (series <= lim_l2).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series <= lim_l2, df_ts['Time'])} 突破低2报线 ({lim_l2}{unit})"); global_is_severe = True
        elif lim_l1 is not None and (series <= lim_l1).any():
            alarm_triggers.append(
                f"在 {get_alarm_ranges(series <= lim_l1, df_ts['Time'])} 突破低报线 ({lim_l1}{unit})"); global_is_severe = True

        if len(alarm_triggers) > 0 or is_app_h or is_app_l or len(jump_events) > 0:
            global_has_anomaly = True
            c_name = r_meta['测点名称']
            faults = []

            if alarm_triggers:
                if is_h:
                    suffix_txt = f"；最高值 {c_max:.2f}{unit}"
                elif is_l:
                    suffix_txt = f"；最低值 {c_min:.2f}{unit}"
                else:
                    suffix_txt = ""
                faults.append("越限报警：" + "；".join(alarm_triggers) + suffix_txt)
            else:
                if is_app_h:
                    gap = safe_high - c_max
                    faults.append(f"临近高报警线：当前最高值 {c_max:.2f}{unit}，距高报警线 {safe_high:g}{unit} 仅 {gap:.2f}{unit}")
                if is_app_l:
                    gap = c_min - safe_low
                    faults.append(f"临近低报警线：当前最低值 {c_min:.2f}{unit}，距低报警线 {safe_low:g}{unit} 仅 {gap:.2f}{unit}")

            if len(jump_events) > 0:
                jump_texts = [_format_jump_event(je, unit) for je in jump_events[:2]]
                faults.append(f"参数突变：{'；'.join(jump_texts)}")

            # 工况曲线只标注异常极值：高侧/上升异常标红色最高值，低侧/下降异常标蓝色最低值。
            numeric_series = pd.to_numeric(series, errors='coerce')
            valid_series = numeric_series.dropna()
            if not valid_series.empty:
                max_idx = valid_series.idxmax()
                min_idx = valid_series.idxmin()
                max_time = df_ts.loc[max_idx, 'Time']
                min_time = df_ts.loc[min_idx, 'Time']
                max_value = float(valid_series.loc[max_idx])
                min_value = float(valid_series.loc[min_idx])

                if is_h or (not alarm_triggers and is_app_h):
                    _register_curve_key_point(
                        code, max_time, max_value, '最高值', 'high_extreme'
                    )
                if is_l or (not alarm_triggers and is_app_l):
                    _register_curve_key_point(
                        code, min_time, min_value, '最低值', 'low_extreme'
                    )

            # 参数突变只标注真正偏离正常稳态的波峰/波谷。
            # 反向回到正常值属于“恢复过程”，不再把恢复后的正常值误标成新的极值点。
            if not valid_series.empty:
                nominal_value = float(valid_series.median())
                nominal_band = max(
                    _noise_sigma(valid_series) * 6.0,
                    abs(nominal_value) * 0.01,
                    _robust_data_scale(valid_series) * 0.02,
                    1e-6,
                )

                for je in jump_events[:2]:
                    extreme_ts = je.get('extreme_timestamp', je.get('extreme_time'))
                    extreme_value = je.get('extreme_value')
                    baseline_value = je.get('baseline_value', je.get('start_value'))
                    try:
                        extreme_value = float(extreme_value)
                        baseline_value = float(baseline_value)
                    except Exception:
                        continue

                    # 只有极值比事件起点更远离全局正常稳态时才标注。
                    # 这样会保留真实突变顶峰/低谷，并过滤“低谷后回升到正常值”之类的恢复点。
                    extreme_deviation = abs(extreme_value - nominal_value)
                    baseline_deviation = abs(baseline_value - nominal_value)
                    if extreme_deviation <= baseline_deviation + nominal_band:
                        continue

                    if je.get('dir') == '+' and extreme_value > nominal_value + nominal_band:
                        _register_curve_key_point(
                            code, extreme_ts, extreme_value, '最高值', 'high_extreme'
                        )
                    elif je.get('dir') == '-' and extreme_value < nominal_value - nominal_band:
                        _register_curve_key_point(
                            code, extreme_ts, extreme_value, '最低值', 'low_extreme'
                        )

            all_fault_descs.append(f"【{c_name}】({code})：" + "；".join(faults))

fault_desc_str = " \n\n".join(all_fault_descs)

# 把异常极值点写入主图。正常情况下 curve_key_points 为空，不显示任何标注。
# 只显示红色最高值圆点或蓝色最低值圆点，并在点旁显示数值；不画垂线、不标时间。
def _deduplicate_curve_extremes(points):
    """
    按“同一次异常波峰/波谷”进行最终去重，而不是只按固定时间窗去重。

    判定原则：
    - 两个同方向候选点之间，如果曲线没有回到正常稳态附近，则属于同一个波峰/波谷；
    - 同一个波峰只保留一个最高点，同一个波谷只保留一个最低点；
    - 平顶/平底存在多个相同极值采样点时，取这些极值点的中间时刻，只画一个圆点；
    - 两次异常之间若已经回归稳态，则保留为两个独立极值点。
    """
    raw_points = list(points)
    if len(raw_points) <= 1:
        return raw_points

    grouped = {}
    for point in raw_points:
        grouped.setdefault((str(point.get('code')), point.get('kind')), []).append(point)

    final_points = []
    for (code, kind), group in grouped.items():
        group = sorted(group, key=lambda p: pd.to_datetime(p.get('time')))
        actual_col = resolve_actual_col(df_ts, selected_system, code)
        if actual_col is None or actual_col not in df_ts.columns:
            # 无法读取曲线时，至少按较宽时间窗做一次保底合并。
            clusters = []
            for point in group:
                if not clusters or pd.to_datetime(point['time']) - pd.to_datetime(clusters[-1][-1]['time']) > pd.Timedelta(hours=6):
                    clusters.append([point])
                else:
                    clusters[-1].append(point)
        else:
            numeric_series = pd.to_numeric(df_ts[actual_col], errors='coerce')
            valid_series = numeric_series.dropna()
            if valid_series.empty:
                final_points.extend(group)
                continue

            nominal_value = float(valid_series.median())
            steady_band = max(
                _noise_sigma(valid_series) * 8.0,
                abs(nominal_value) * 0.015,
                _robust_data_scale(valid_series) * 0.035,
                1e-6,
            )

            clusters = [[group[0]]]
            for point in group[1:]:
                previous = clusters[-1][-1]
                t1 = pd.to_datetime(previous['time'])
                t2 = pd.to_datetime(point['time'])
                left_t, right_t = min(t1, t2), max(t1, t2)
                between_mask = (df_ts['Time'] >= left_t) & (df_ts['Time'] <= right_t)
                between = numeric_series.loc[between_mask].dropna()

                if between.empty:
                    returned_to_steady = (right_t - left_t) > pd.Timedelta(hours=6)
                elif kind == 'high_extreme':
                    # 高侧两个候选点之间降回稳态附近，才视为两个独立波峰。
                    returned_to_steady = float(between.min()) <= nominal_value + steady_band
                else:
                    # 低侧两个候选点之间升回稳态附近，才视为两个独立波谷。
                    returned_to_steady = float(between.max()) >= nominal_value - steady_band

                if returned_to_steady:
                    clusters.append([point])
                else:
                    clusters[-1].append(point)

        for cluster in clusters:
            if len(cluster) == 1:
                final_points.append(cluster[0])
                continue

            cluster_start = min(pd.to_datetime(p['time']) for p in cluster)
            cluster_end = max(pd.to_datetime(p['time']) for p in cluster)

            if actual_col is not None and actual_col in df_ts.columns:
                numeric_series = pd.to_numeric(df_ts[actual_col], errors='coerce')
                region_mask = (df_ts['Time'] >= cluster_start) & (df_ts['Time'] <= cluster_end)
                region = numeric_series.loc[region_mask].dropna()
            else:
                region = pd.Series(dtype=float)

            if not region.empty:
                extreme_value = float(region.max() if kind == 'high_extreme' else region.min())
                tolerance = max(abs(extreme_value) * 1e-7, 1e-9)
                equal_extreme_idx = region.index[np.isclose(region.to_numpy(dtype=float), extreme_value, rtol=0.0, atol=tolerance)]
                chosen_idx = equal_extreme_idx[len(equal_extreme_idx) // 2]
                chosen_time = pd.to_datetime(df_ts.loc[chosen_idx, 'Time'])
            else:
                if kind == 'high_extreme':
                    extreme_value = max(float(p['value']) for p in cluster)
                else:
                    extreme_value = min(float(p['value']) for p in cluster)
                same_extreme = [p for p in cluster if np.isclose(float(p['value']), extreme_value, rtol=0.0, atol=max(abs(extreme_value) * 1e-7, 1e-9))]
                same_extreme = sorted(same_extreme, key=lambda p: pd.to_datetime(p['time']))
                chosen_time = pd.to_datetime(same_extreme[len(same_extreme) // 2]['time'])

            representative = dict(cluster[0])
            representative['time'] = chosen_time
            representative['value'] = extreme_value
            final_points.append(representative)

    return sorted(final_points, key=lambda p: pd.to_datetime(p.get('time')))


_key_point_styles = {
    'high_extreme': dict(color='#e53935', symbol='circle', size=10, textposition='top center'),
    'low_extreme': dict(color='#1e88e5', symbol='circle', size=10, textposition='bottom center'),
}

_deduplicated_curve_points = _deduplicate_curve_extremes(curve_key_points.values())
for point in _deduplicated_curve_points[:30]:
    style = _key_point_styles.get(point['kind'], _key_point_styles['high_extreme'])
    fig.add_trace(go.Scatter(
        x=[point['time']],
        y=[point['value']],
        mode='markers+text',
        marker=dict(
            color=style['color'],
            symbol=style['symbol'],
            size=style['size'],
            line=dict(color='white', width=1)
        ),
        text=[f"{point['value']:.2f}{unit}"],
        textposition=style['textposition'],
        textfont=dict(size=10, color=style['color']),
        hoverinfo='skip',
        showlegend=False,
        cliponaxis=False,
    ))

chart_placeholder.plotly_chart(
    fig,
    use_container_width=True,
    config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False}
)

st.markdown("<h3 class='ai-section-title'>🧠 AI 监测预警中心</h3>", unsafe_allow_html=True)

if not has_curve_stream:
    with st.expander("⚪ AI 盲测提示：等待工况数据输入", expanded=True):
        st.info("💡 该系统已有预设的标准模拟输入。规则树已就绪，静待总线推流触发演算。")
elif global_has_anomaly:
    expander_title = f"🚨 AI 检测警报：捕获到 {len(all_fault_descs)} 个运行指标劣化越限！" if global_is_severe else f"⚠️ AI 预警提示：部分工艺参数存在突变/临近报警/越限风险"
    with st.expander(expander_title, expanded=True):
        if global_is_severe:
            st.error(f"🔴 **实时工况异常报告：**\n\n{fault_desc_str}")
        else:
            st.warning(f"🟡 **实时工况波动报告：**\n\n{fault_desc_str}")

        if st.button("🧠 联合调阅核电知识规程，一键生成 AI 专家诊断卡", type="primary", use_container_width=True):
            with st.spinner("🔄 正在翻阅规程库执行多参量深度推理... "):
                # Dify 的 System_Name 已改为“文本输入”后，这里必须传真实系统名，
                # 不再用 RHR/RCV 作为新系统的占位值。
                fault_info_for_dify = f"""所属系统：{selected_system}

系统联合巡检发现如下多并发异常：
{fault_desc_str}

检索提示：
请优先检索与当前系统名称、设备名称、测点类型、报警类型直接相关的规程资料。
如果知识库中没有当前系统的专属资料，可以检索相似设备、相似参数或相似报警逻辑的资料作为参考。
但不得把其他系统资料当作当前系统专属规程依据。
"""

                payload = {
                    "inputs": {
                        "System_Name": selected_system,
                        "Fault_info": fault_info_for_dify
                    },
                    "query": "请根据当前异常工况和知识库资料，生成核电设备专家诊断报告。",
                    "response_mode": "blocking",
                    "user": "operator"
                }
                final_answer = "大模型应答响应异常。"
                import urllib3

                urllib3.disable_warnings()
                try:
                    response = requests.post(
                        DIFY_API_URL,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {DIFY_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        timeout=120,
                        verify=False
                    )

                    raw_text = response.text or ""
                    try:
                        resp_json = response.json()
                    except Exception:
                        resp_json = {}

                    def _dig_answer(obj):
                        """兼容 Dify chat-messages、workflow/run 以及部分代理网关的不同返回结构。"""
                        if not isinstance(obj, dict):
                            return None
                        for key in ["answer", "text", "result", "content"]:
                            value = obj.get(key)
                            if isinstance(value, str) and value.strip():
                                return value.strip()
                        data = obj.get("data")
                        if isinstance(data, dict):
                            nested = _dig_answer(data)
                            if nested:
                                return nested
                        outputs = obj.get("outputs")
                        if isinstance(outputs, dict):
                            nested = _dig_answer(outputs)
                            if nested:
                                return nested
                            for value in outputs.values():
                                if isinstance(value, str) and value.strip():
                                    return value.strip()
                        return None

                    answer = _dig_answer(resp_json)
                    if answer:
                        final_answer = answer
                    else:
                        msg = ""
                        if isinstance(resp_json, dict):
                            msg = str(
                                resp_json.get("message")
                                or resp_json.get("error")
                                or resp_json.get("code")
                                or resp_json.get("status")
                                or ""
                            )
                            keys = ", ".join(resp_json.keys()) if resp_json else "无"
                        else:
                            keys = "非字典JSON"
                        if response.status_code < 200 or response.status_code >= 300:
                            final_answer = f"大模型接口调用失败：HTTP {response.status_code}。{msg or raw_text[:300]}"
                        else:
                            final_answer = (
                                "大模型接口已返回，但没有找到 answer 字段。"
                                f"返回字段：{keys}。"
                                f"接口提示：{msg or raw_text[:300] or '无'}"
                            )
                except Exception as e:
                    final_answer = f"大模型接口调用失败: {e}"

                st.session_state['last_ai_response'] = final_answer
                st.rerun()

        if 'last_ai_response' in st.session_state:
            st.info(st.session_state['last_ai_response'])
else:
    with st.expander("🟢 工况平稳运行中 (点击展开 AI 状态监测面板)", expanded=False):
        st.success("🟢 经过全景参数范围对齐扫描，当前所有接入测点的时序波形均处于安全工艺区间内。")

# ==========================================
# 5. 全量清单列表复刻
# ==========================================
col_table_head, col_btn_right = st.columns([8, 2])
with col_table_head: st.markdown("#### 📋 系统全量测点监控、实时值及游标截面清单")
with col_btn_right:
    if st.button("🧹 清空对比选区", use_container_width=True):
        st.session_state['active_point_codes'] = [active_system_df['编码'].iloc[0]]
        st.rerun()

st.session_state['compare_mode'] = st.toggle("🔗 开启多测点同屏对比模式",
                                             value=st.session_state.get('compare_mode', False))

table_data = active_system_df[['编码', '测点名称', '正常范围', '单位']].copy()
status_list, realtime_vals, cursor_vals, alarm_aggregates = [], [], [], []
cursor_idx = (df_ts['Time'] - cursor_time).abs().idxmin() if not df_ts.empty else 0

for _, row in active_system_df.iterrows():
    c = str(row['编码']).strip()
    actual_col = resolve_actual_col(df_ts, row.get('系统', selected_system), c)
    actual_col_full = resolve_actual_col(df_ts_full, row.get('系统', selected_system), c)
    stream_ok = actual_col is not None and not df_ts[actual_col].isna().all()
    full_stream_ok = actual_col_full is not None and not df_ts_full[actual_col_full].isna().all()

    if not stream_ok:
        status_list.append("⚪ 等待数据接入")
        realtime_vals.append("无")
        cursor_vals.append("无")
    else:
        actual_curve = df_ts[actual_col]
        v_max, v_min = actual_curve.max(), actual_curve.min()
        h_candidates = [get_limit(row.get(k)) for k in ['高报', '高2报', '高3报', '高4报']]
        l_candidates = [get_limit(row.get(k)) for k in ['低报', '低2报', '低3报', '低4报']]
        h_valid = [x for x in h_candidates if x is not None]
        l_valid = [x for x in l_candidates if x is not None]
        h_lim = min(h_valid) if h_valid else float('inf')
        l_lim = max(l_valid) if l_valid else float('-inf')

        row_safe_high = h_lim if np.isfinite(h_lim) else None
        row_safe_low = l_lim if np.isfinite(l_lim) else None
        row_span = _engineering_span(actual_curve, row_safe_low, row_safe_high)
        row_high_margin = _near_margin(actual_curve, row_safe_high, row_span if row_safe_low is not None and row_safe_high is not None else None) if row_safe_high is not None else None
        row_low_margin = _near_margin(actual_curve, row_safe_low, row_span if row_safe_low is not None and row_safe_high is not None else None) if row_safe_low is not None else None
        row_jump_events = _detect_jump_events(actual_curve, df_ts['Time'], row_span)

        if v_max >= h_lim:
            status_list.append("🚨 越限超高")
        elif v_min <= l_lim:
            status_list.append("🔵 越限超低")
        elif row_safe_high is not None and v_max >= row_safe_high - row_high_margin:
            status_list.append("⚠️ 临近高报")
        elif row_safe_low is not None and v_min <= row_safe_low + row_low_margin:
            status_list.append("⚠️ 临近低报")
        elif row_jump_events:
            status_list.append("⚡ 参数突变")
        else:
            status_list.append("🟢 正常")

        if full_stream_ok:
            latest_series = df_ts_full[actual_col_full].dropna()
            latest_val = latest_series.iloc[-1] if not latest_series.empty else np.nan
            realtime_vals.append(f"{latest_val:.2f}")
        else:
            realtime_vals.append("无")

        c_val = actual_curve.iloc[cursor_idx] if not df_ts.empty else np.nan
        cursor_vals.append(f"{c_val:.2f}")

    alarms = []
    for k_name, k_col in [('L4', '低4报'), ('L3', '低3报'), ('L2', '低2报'), ('L', '低报'), ('H', '高报'),
                          ('H2', '高2报'), ('H3', '高3报'), ('H4', '高4报')]:
        if k_col in row and pd.notna(row[k_col]) and str(row[k_col]).strip() != '':
            alarms.append(f"{k_name}: {float(row[k_col]):.2f}")
    alarm_aggregates.append(" | ".join(alarms) if alarms else "无规则")

table_data.insert(2, '检测结果', status_list)
table_data.insert(3, '🕒实时检测值', realtime_vals)
table_data.insert(4, '📍游标时刻值', cursor_vals)
table_data.insert(5, '报警限值 (合并)', alarm_aggregates)

selection = st.dataframe(
    table_data,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row" if st.session_state['compare_mode'] else "single-row",
    key=f"monitor_point_table_{hashlib.md5(str(selected_system).encode('utf-8')).hexdigest()[:8]}"
)

if selection and len(selection.selection.rows) > 0:
    clicked_codes = table_data.iloc[selection.selection.rows]['编码'].tolist()
    if st.session_state['active_point_codes'] != clicked_codes:
        st.session_state['active_point_codes'] = clicked_codes
        st.rerun()

# ==========================================
# 6. 报告导出舱 (高精度新格式与快照转换)
# ==========================================
ai_response_text = st.session_state.get('last_ai_response', "工况监控收敛稳定，大模型尚未触发排障指令。").replace('**',
                                                                                                                '').replace(
    '### ', '').replace('## ', '')
report_fault_html = (fault_desc_str if global_has_anomaly else "正常").replace('\n', '<br>')
ai_response_html = ai_response_text.replace('\n', '<br>')

is_severe = global_is_severe
title_suffix = f" (同屏多参数比对)" if len(valid_codes) > 1 else ""

export_fig = copy.deepcopy(fig)
export_fig.update_layout(height=380, paper_bgcolor='#ffffff', plot_bgcolor='#ffffff', font=dict(color='black'))
fig_json = json.dumps(export_fig, cls=plotly.utils.PlotlyJSONEncoder)

popup_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>重大设备状态智能监测预警 - 故障诊断报告单</title>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <style>
        @media print {{ @page {{ size: A4 vertical; margin: 8mm 15mm; }} body {{ background: #fff; color: #000; -webkit-print-color-adjust: exact; }} .no-print {{ display: none !important; }} }}
        body {{ font-family: 'Microsoft YaHei', sans-serif; line-height: 1.35; margin: 0; padding: 0; background-color: #fff; }}
        .container {{ padding: 12px; border: 1.5px solid #000; box-sizing: border-box; max-width: 800px; margin: 10px auto; }}
        th, td {{ font-size: 12px !important; padding: 4px 6px !important; border: 1px solid #000; }}
        .bg-gray {{ background: #f2f2f2; font-weight: bold; }}
        .loading {{ text-align: center; padding: 20px; font-size: 16px; font-weight: bold; color: #cc0000; }}
    </style>
</head>
<body>
    <div id="loading-status" class="loading no-print">⏳ 正在渲染高精度多路关联曲线图像...</div>
    <div id="print-container" class="container">
        <h3 style="text-align: center; margin: 0 0 4px 0; font-size: 17px;">重大设备状态智能监测预警 - 联合诊断报告单</h3>
        <p style="text-align: center; font-size: 11px; color: #555; margin: 0 0 8px 0;">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp; 报告人：MCR_Operator</p>
        <hr style="border: 0.5px solid #000; margin: 0;"/>
        <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
            <tr><td class="bg-gray" style="width: 20%;">所属系统</td><td style="width: 30%;">{selected_system}</td><td class="bg-gray" style="width: 20%;">主参数测点</td><td style="width: 30%;">{primary_code}</td></tr>
            <tr><td class="bg-gray">联合监测项目</td><td>{point_name}{title_suffix}</td><td class="bg-gray">监测范围标准</td><td>{point_info['正常范围']} {unit}</td></tr>
            <tr><td class="bg-gray">主测点最高值</td><td style="color: #cc0000; font-weight: bold;">{p_max:.2f} {unit}</td><td class="bg-gray">主测点最低值</td><td style="color: #0000cc; font-weight: bold;">{p_min:.2f} {unit}</td></tr>
        </table>
        <div style="margin-top: 8px; text-align: center; font-weight: bold; font-size: 12px; color: #333;">【实时历史工艺多维度曲线比对图】</div>
        <div id="plotly-snap-area" style="width: 100%; margin: 2px auto; text-align: center;"></div>
        <div style="margin-top: 6px; padding: 6px; border: 1px solid {'#cc0000' if is_severe else '#ffa500'}; background: {'#fff5f5' if is_severe else '#fffdf0'}; border-radius: 4px;">
            <b style="font-size: 12px; color: {'#cc0000' if is_severe else '#cc8800'};">🚨 系统报告：</b>
            <p style="font-size: 11.5px; margin: 2px 0 0 0; text-indent: 2em; line-height: 1.4;">{report_fault_html}</p>
        </div>
        <div style="margin-top: 6px; padding: 8px; border: 1px solid #00aa66; background: #f5fbf7; border-radius: 4px;">
            <b style="font-size: 12px; color: #00aa66;">🧠 AI 专家全景分析与排障结论：</b>
            <div style="font-size: 11.5px; margin: 3px 0 0 0; line-height: 1.4; color: #111;">{ai_response_html}</div>
        </div>
        <div style="margin-top: 25px; font-size: 12px; text-align: right; font-weight: bold;">
            <span>确认系统设备工程师签字: __________________ </span><span style="margin-left: 30px;">安全工程师签字: __________________</span>
        </div>
    </div>
    <script>
        window.onload = function() {{
            var figData = {fig_json};
            figData.layout.template = "plotly_white"; figData.layout.paper_bgcolor = "#ffffff"; figData.layout.plot_bgcolor = "#ffffff";
            figData.layout.width = 800; figData.layout.height = 380; figData.layout.margin = {{l: 50, r: 50, t: 50, b: 60}};
            if(figData.layout.legend) {{ figData.layout.legend.orientation = "h"; figData.layout.legend.x = 0.5; figData.layout.legend.xanchor = "center"; figData.layout.legend.y = 1.15; }}
            Plotly.toImage({{data: figData.data, layout: figData.layout}}, {{format: 'png', width: 800, height: 380, scale: 2}})
            .then(function(dataUrl) {{
                document.getElementById('plotly-snap-area').innerHTML = '<img src="' + dataUrl + '" style="width: 100%; max-height: 380px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px;" />';
                document.getElementById('loading-status').style.display = 'none';
                setTimeout(function() {{ window.print(); setTimeout(function() {{ window.close(); }}, 1000); }}, 500);
            }}).catch(function(err) {{ document.getElementById('loading-status').innerHTML = "❌ 高精度曲线生成失败。"; }});
        }};
    </script>
</body>
</html>
"""

b64_html = base64.b64encode(popup_html.encode('utf-8')).decode('utf-8')

# 按钮已调整为配合页面的科技暗灰/深青色调调优
st.components.v1.html(
    f'<button onclick="openPrint()" style="background-color: #2b3a42; color: #00ffcc; border: 1px solid #00ffcc; border-radius: 0.3rem; padding: 0.6rem 1rem; font-size: 14px; width: 100%; cursor: pointer; font-family: sans-serif; font-weight: bold; letter-spacing: 1px;">📑 导出联合 PDF 诊断报告</button><script>function openPrint() {{ var win = window.open("", "_blank"); win.document.write(decodeURIComponent(escape(window.atob("{b64_html}")))); win.document.close(); }}</script>',
    height=45)
