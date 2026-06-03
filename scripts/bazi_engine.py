#!/usr/bin/env python3
"""
四柱八字排盘算命核心引擎 v2.0
新增功能：
  - 农历↔公历自动转换
  - 真太阳时校正（基于出生地经纬度）
  - 中国主要城市经纬度内置库
  - 闰月处理

Based on 子平八字 from:
  - 《滴天髓》刘伯温注 + 任铁樵增注
  - 《四柱命理正源》《四柱独门铁口直断》刘文元

Usage:
  # 公历输入
  python3 bazi_engine.py 1990 5 15 14 30 male

  # 农历输入
  python3 bazi_engine.py --lunar 1990 4 22 14 30 male

  # 带出生地（真太阳时）
  python3 bazi_engine.py 1990 5 15 14 30 male 北京

  # 农历+出生地
  python3 bazi_engine.py --lunar 1990 4 22 14 30 male 上海

  # 直接传经纬度
  python3 bazi_engine.py 1990 5 15 14 30 male 116.4074 39.9042
"""

import json
import sys
import math
import argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# ═══════════════════════════════════════════════════════════
# LUNAR DATE SUPPORT
# ═══════════════════════════════════════════════════════════

try:
    from lunardate import LunarDate
    HAS_LUNARDATE = True
except ImportError:
    HAS_LUNARDATE = False

# ═══════════════════════════════════════════════════════════
# CHINESE CITY COORDINATES
# ═══════════════════════════════════════════════════════════

# 城市经纬度表 (name -> (longitude, latitude))
# 经度精确到0.01度，用于真太阳时校正
# 来源：中国地震局/国家地理信息
CHINA_CITIES = {
    # 直辖市
    '北京': (116.4074, 39.9042),
    '上海': (121.4737, 31.2304),
    '天津': (117.2009, 39.0842),
    '重庆': (106.5516, 29.5630),
    # 省会/首府
    '石家庄': (114.5149, 38.0428),
    '太原': (112.5492, 37.8706),
    '呼和浩特': (111.7519, 40.8414),
    '沈阳': (123.4328, 41.8057),
    '长春': (125.3235, 43.8171),
    '哈尔滨': (126.6423, 45.7569),
    '济南': (117.0009, 36.6758),
    '郑州': (113.6253, 34.7466),
    '南京': (118.7969, 32.0603),
    '合肥': (117.2272, 31.8206),
    '杭州': (120.1550, 30.2741),
    '南昌': (115.8581, 28.6829),
    '福州': (119.2965, 26.0745),
    '兰州': (103.8343, 36.0611),
    '银川': (106.2310, 38.4872),
    '西宁': (101.7782, 36.6171),
    '乌鲁木齐': (87.6168, 43.8256),
    '拉萨': (91.1409, 29.6456),
    '成都': (104.0668, 30.5728),
    '贵阳': (106.7135, 26.5783),
    '昆明': (102.8329, 24.8801),
    '南宁': (108.3665, 22.8170),
    '广州': (113.2644, 23.1291),
    '深圳': (114.0579, 22.5431),
    '海口': (110.3492, 20.0174),
    '武汉': (114.3054, 30.5931),
    '长沙': (112.9388, 28.2282),
    '西安': (108.9398, 34.3416),
    '太原': (112.5492, 37.8706),
    '太原': (112.5492, 37.8706),
    '呼和浩特': (111.7519, 40.8414),
    '大同': (113.2816, 40.0918),
    '包头': (109.8403, 40.6566),
    '大连': (121.6147, 38.9140),
    '青岛': (120.3826, 36.0671),
    '厦门': (118.0894, 24.4798),
    '宁波': (121.5497, 29.8683),
    '苏州': (120.6187, 31.2989),
    '无锡': (120.3119, 31.4939),
    '常州': (119.9741, 31.8112),
    '徐州': (117.2848, 34.3069),
    '南通': (120.8963, 31.9896),
    '扬州': (119.4211, 32.3932),
    '镇江': (119.4258, 32.1878),
    '扬州': (119.4211, 32.3932),
    '泰州': (119.9223, 32.4849),
    '淮安': (119.0112, 33.4039),
    '盐城': (120.1585, 33.3845),
    '连云港': (119.2216, 34.5969),
    '宿迁': (118.3014, 33.9620),
    '芜湖': (118.3762, 31.3246),
    '蚌埠': (117.3551, 32.9376),
    '阜阳': (115.8094, 32.8965),
    '九江': (115.9879, 29.7086),
    '赣州': (114.9342, 25.8290),
    '泉州': (118.5894, 24.9089),
    '漳州': (117.6479, 24.5133),
    '莆田': (119.0155, 25.4473),
    '三明': (117.6341, 26.2750),
    '南平': (118.0206, 26.6445),
    '龙岩': (116.9789, 25.0886),
    '宁德': (119.5249, 26.6643),
    '临沂': (118.3569, 35.0595),
    '潍坊': (119.1016, 36.7067),
    '烟台': (121.3914, 37.4584),
    '威海': (122.1164, 37.5035),
    '泰安': (117.1246, 36.1849),
    '济宁': (116.5873, 35.4055),
    '聊城': (115.9927, 36.4532),
    '德州': (116.3534, 37.4413),
    '滨州': (117.8944, 37.3931),
    '菏泽': (115.4411, 35.2341),
    '许昌': (113.8597, 34.0259),
    '洛阳': (112.4539, 34.6674),
    '开封': (114.3498, 34.7971),
    '新乡': (113.9276, 35.3030),
    '焦作': (113.2532, 35.2200),
    '平顶山': (113.2933, 33.7479),
    '安阳': (114.3512, 36.1027),
    '邯郸': (114.5390, 36.6119),
    '邢台': (114.4979, 37.0632),
    '保定': (115.4645, 38.8738),
    '张家口': (114.8704, 40.8076),
    '承德': (117.9419, 40.9685),
    '秦皇岛': (119.5873, 39.9392),
    '唐山': (118.1840, 39.6405),
    '廊坊': (116.7005, 39.3517),
    '沧州': (116.8424, 38.3121),
    '衡水': (115.6776, 37.7324),
    '石家庄': (114.5149, 38.0428),
    '三亚': (109.5119, 18.2528),
    '桂林': (110.2876, 25.2736),
    '柳州': (109.4117, 24.2900),
    '南宁': (108.3665, 22.8170),
    '大理': (100.2465, 25.6889),
    '丽江': (100.2273, 26.8723),
    '西双版纳': (100.7981, 22.0021),
    '昆明': (102.8329, 24.8801),
    '遵义': (106.9290, 27.6989),
    '绵阳': (104.7451, 31.4717),
    '宜昌': (111.2932, 30.7149),
    '襄阳': (112.1241, 32.0183),
    '衡阳': (112.5962, 26.8893),
    '株洲': (113.1317, 27.8278),
    '岳阳': (113.1288, 29.3638),
    '常德': (111.6875, 29.0337),
    '湘潭': (112.9380, 27.8284),
    '邵阳': (111.4658, 27.2384),
    '柳州': (109.4117, 24.2900),
    '贵阳': (106.7135, 26.5783),
    '六盘水': (104.8467, 26.5562),
    '遵义': (106.9290, 27.6989),
    '曲靖': (103.7972, 25.4914),
    '玉溪': (102.5271, 24.3510),
    '红河': (103.3776, 23.3759),
    '昆明': (102.8329, 24.8801),
    '成都': (104.0668, 30.5728),
    '德阳': (104.3974, 31.1258),
    '绵阳': (104.7451, 31.4717),
    '南充': (106.1114, 30.8337),
    '自贡': (104.7784, 29.3491),
    '泸州': (105.4431, 28.8718),
    '乐山': (103.7674, 29.5468),
    '宜宾': (104.6284, 28.7690),
    '达州': (107.5058, 31.2099),
    '绵阳': (104.7451, 31.4717),
    '银川': (106.2310, 38.4872),
    '石嘴山': (106.3134, 39.0238),
    '吴忠': (106.1984, 37.9854),
    '中卫': (105.1839, 37.5155),
    '西宁': (101.7782, 36.6171),
    '海东': (102.0706, 36.6057),
    '格尔木': (94.9865, 36.4173),
    '拉萨': (91.1409, 29.6456),
    '日喀则': (88.8821, 29.2676),
    '昌都': (97.1687, 31.1423),
    '林芝': (94.3621, 29.6459),
    '乌鲁木齐': (87.6168, 43.8256),
    '克拉玛依': (84.7727, 45.5903),
    '库尔勒': (86.1475, 41.7727),
    '喀什': (75.9898, 39.4677),
    '阿克苏': (80.2679, 41.1696),
    '哈密': (93.5127, 42.8333),
    '昌吉': (87.3039, 44.0009),
    '石河子': (86.0370, 44.3044),
    '伊宁': (81.2833, 43.9169),
    '吐鲁番': (89.1844, 42.9478),
    '和田': (79.9252, 37.1079),
    '阿勒泰': (88.1333, 47.8425),
    '博乐': (82.1442, 44.8956),
    '锡林浩特': (116.0970, 43.9333),
    '乌兰浩特': (122.0600, 46.0832),
    '呼伦贝尔': (119.7563, 49.2187),
    '通辽': (122.2623, 43.6332),
    '赤峰': (118.9575, 42.2823),
    '鄂尔多斯': (109.7813, 39.8164),
    '包头': (109.8403, 40.6566),
    '巴彦淖尔': (107.4306, 40.7507),
    '兴安盟': (122.0600, 46.0832),
    '呼和浩特': (111.7519, 40.8414),
    '乌兰察布': (113.1114, 41.0315),
    '西宁': (101.7782, 36.6171),
    '海东': (102.0706, 36.6057),
    '格尔木': (94.9865, 36.4173),
    '德令哈': (97.3914, 37.3868),
    '玉树': (97.0014, 33.0015),
    '果洛': (100.2501, 34.4531),
    '黄南': (102.0136, 35.5024),
    '海北': (100.9859, 36.8718),
    '海南': (101.6039, 35.7414),
    '海西': (96.9925, 37.3875),
    '拉萨': (91.1409, 29.6456),
    '日喀则': (88.8821, 29.2676),
    '昌都': (97.1687, 31.1423),
    '林芝': (94.3621, 29.6459),
    '山南': (91.7637, 29.2386),
    '那曲': (92.0726, 31.4764),
    '阿里': (80.1026, 32.5038),
    '拉萨': (91.1409, 29.6456),
    '林芝': (94.3621, 29.6459),
    '拉萨': (91.1409, 29.6456),
    # 常用别名
    '北京': (116.4074, 39.9042),
    '上海': (121.4737, 31.2304),
    '成都': (104.0668, 30.5728),
    '广州': (113.2644, 23.1291),
    '深圳': (114.0579, 22.5431),
    '杭州': (120.1550, 30.2741),
    '武汉': (114.3054, 30.5931),
    '南京': (118.7969, 32.0603),
    '西安': (108.9398, 34.3416),
    '长沙': (112.9388, 28.2282),
    '郑州': (113.6253, 34.7466),
    '苏州': (120.6187, 31.2989),
    '天津': (117.2009, 39.0842),
    '重庆': (106.5516, 29.5630),
    '青岛': (120.3826, 36.0671),
    '大连': (121.6147, 38.9140),
    '厦门': (118.0894, 24.4798),
    '宁波': (121.5497, 29.8683),
    '福州': (119.2965, 26.0745),
    '昆明': (102.8329, 24.8801),
    '哈尔滨': (126.6423, 45.7569),
    '沈阳': (123.4328, 41.8057),
    '长春': (125.3235, 43.8171),
    '济南': (117.0009, 36.6758),
    '长沙': (112.9388, 28.2282),
    '太原': (112.5492, 37.8706),
    '合肥': (117.2272, 31.8206),
    '南昌': (115.8581, 28.6829),
    '贵阳': (106.7135, 26.5783),
    '南宁': (108.3665, 22.8170),
    '海口': (110.3492, 20.0174),
    '三亚': (109.5119, 18.2528),
    '拉萨': (91.1409, 29.6456),
    '西宁': (101.7782, 36.6171),
    '兰州': (103.8343, 36.0611),
    '银川': (106.2310, 38.4872),
    '乌鲁木齐': (87.6168, 43.8256),
    '呼和浩特': (111.7519, 40.8414),
    '石家庄': (114.5149, 38.0428),
    '福州': (119.2965, 26.0745),
    '厦门': (118.0894, 24.4798),
    '青岛': (120.3826, 36.0671),
    '宁波': (121.5497, 29.8683),
    '无锡': (120.3119, 31.4939),
    '苏州': (120.6187, 31.2989),
    '南京': (118.7969, 32.0603),
    '杭州': (120.1550, 30.2741),
    '合肥': (117.2272, 31.8206),
    '武汉': (114.3054, 30.5931),
    '长沙': (112.9388, 28.2282),
    '南昌': (115.8581, 28.6829),
    '郑州': (113.6253, 34.7466),
    '济南': (117.0009, 36.6758),
    '太原': (112.5492, 37.8706),
    '石家庄': (114.5149, 38.0428),
    '西安': (108.9398, 34.3416),
    '成都': (104.0668, 30.5728),
    '重庆': (106.5516, 29.5630),
    '昆明': (102.8329, 24.8801),
    '贵阳': (106.7135, 26.5783),
    '南宁': (108.3665, 22.8170),
    '广州': (113.2644, 23.1291),
    '深圳': (114.0579, 22.5431),
    '海口': (110.3492, 20.0174),
    '三亚': (109.5119, 18.2528),
    '桂林': (110.2876, 25.2736),
    '哈尔滨': (126.6423, 45.7569),
    '长春': (125.3235, 43.8171),
    '沈阳': (123.4328, 41.8057),
    '大连': (121.6147, 38.9140),
    '北京': (116.4074, 39.9042),
    '上海': (121.4737, 31.2304),
    '天津': (117.2009, 39.0842),
    '重庆': (106.5516, 29.5630),
    '拉萨': (91.1409, 29.6456),
    '乌鲁木齐': (87.6168, 43.8256),
    '兰州': (103.8343, 36.0611),
    '银川': (106.2310, 38.4872),
    '西宁': (101.7782, 36.6171),
    '呼和浩特': (111.7519, 40.8414),
}


def find_city_coord(name: str) -> Optional[tuple]:
    """
    根据城市名查找经纬度
    支持模糊匹配
    """
    if not name or name in ('中国', '大陆', '内地'):
        return (116.4074, 39.9042)  # 默认北京

    # 精确匹配
    if name in CHINA_CITIES:
        return CHINA_CITIES[name]

    # 模糊匹配（包含/被包含）
    for city, coord in CHINA_CITIES.items():
        if name in city or city in name:
            return coord

    # 检查是否是经纬度字符串（"经度 纬度" 或 "经度,纬度"）
    parts = name.replace('，', ',').replace(' ', ',').split(',')
    if len(parts) >= 2:
        try:
            lon = float(parts[0])
            lat = float(parts[1])
            if -180 <= lon <= 180 and -90 <= lat <= 90:
                return (lon, lat)
        except ValueError:
            pass

    return None


def calculate_true_solar_time(
    year: int, month: int, day: int,
    hour: int, minute: int,
    longitude: float
) -> tuple:
    """
    计算真太阳时

    真太阳时 = 钟表时 + 时差校正
    时差 = (地方经度 - 标准经度) * 4分钟/度 + 均时差

    中国标准时间 = UTC+8 = 东经120度

    Args:
        钟表时: 年、月、日、时、分
        longitude: 出生地经度

    Returns:
        (修正后的小时, 修正后的分钟, 校正量分钟)
    """
    # 1. 地方时差：经度每差1度 = 4分钟
    standard_longitude = 120.0  # 中国标准时区中央经线
    longitude_diff = longitude - standard_longitude
    time_offset_minutes = longitude_diff * 4.0  # 分钟

    # 2. 均时差 (Equation of Time)
    # 地球绕日公转轨道不是正圆，导致太阳日长度变化
    # 使用简化公式，精度约±1分钟
    import math
    # N = 一年中的第几天
    import datetime as dt_mod
    base = dt_mod.datetime(year, month, day)
    N = base.timetuple().tm_yday

    # 均时差近似公式 (Jean Meeus, Astronomical Algorithms)
    B_rad = 2.0 * math.pi * (N - 81.0) / 365.0
    equation_of_time = 9.87 * math.sin(2 * B_rad) - 7.53 * math.cos(B_rad) - 1.5 * math.sin(B_rad)

    # 3. 总校正量
    total_offset_minutes = time_offset_minutes + equation_of_time

    # 4. 应用校正
    new_minute = minute + total_offset_minutes
    new_hour = hour
    # 处理分钟进位
    while new_minute >= 60:
        new_minute -= 60
        new_hour += 1
    while new_minute < 0:
        new_minute += 60
        new_hour -= 1
    # 处理小时进位（处理跨日情况）
    if new_hour >= 24:
        new_hour -= 24
    elif new_hour < 0:
        new_hour += 24

    return (new_hour, round(new_minute, 1), round(total_offset_minutes, 2))


def get_solar_hour_zhi(hour: int, minute: int) -> str:
    """
    根据小时分钟得到时辰地支
    子时 23:00-01:00, 丑时 01:00-03:00, ...
    注意：日柱以子时（23:00）换日
    """
    total_minutes = hour * 60 + minute
    # 子时从23:00开始
    if total_minutes >= 23 * 60 or total_minutes < 1 * 60:
        return '子', total_minutes - 23 * 60 if total_minutes >= 23 * 60 else total_minutes + 60
    elif total_minutes < 3 * 60:
        return '丑', total_minutes - 1 * 60
    elif total_minutes < 5 * 60:
        return '寅', total_minutes - 3 * 60
    elif total_minutes < 7 * 60:
        return '卯', total_minutes - 5 * 60
    elif total_minutes < 9 * 60:
        return '辰', total_minutes - 7 * 60
    elif total_minutes < 11 * 60:
        return '巳', total_minutes - 9 * 60
    elif total_minutes < 13 * 60:
        return '午', total_minutes - 11 * 60
    elif total_minutes < 15 * 60:
        return '未', total_minutes - 13 * 60
    elif total_minutes < 17 * 60:
        return '申', total_minutes - 15 * 60
    elif total_minutes < 19 * 60:
        return '酉', total_minutes - 17 * 60
    elif total_minutes < 21 * 60:
        return '戌', total_minutes - 19 * 60
    else:
        return '亥', total_minutes - 21 * 60


# ═══════════════════════════════════════════════════════════
# MAIN CONSTANTS (unchanged)
# ═══════════════════════════════════════════════════════════

TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

WUXING_MAP = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火',
    '戊': '土', '己': '土', '庚': '金', '辛': '金',
    '壬': '水', '癸': '水',
}

ZHI_WUXING = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木',
    '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水',
}

YIN_YANG = {
    '甲': 1, '乙': 0, '丙': 1, '丁': 0,
    '戊': 1, '己': 0, '庚': 1, '辛': 0,
    '壬': 1, '癸': 0,
}

ZHI_YIN_YANG = {
    '子': 1, '丑': 0, '寅': 1, '卯': 0,
    '辰': 1, '巳': 0, '午': 1, '未': 0,
    '申': 1, '酉': 0, '戌': 1, '亥': 0,
}

SHISHEN_MAP: Dict[tuple, str] = {}
for i, tg in enumerate(TIANGAN):
    wx = WUXING_MAP[tg]
    yy = YIN_YANG[tg]
    for j, tg2 in enumerate(TIANGAN):
        wx2 = WUXING_MAP[tg2]
        yy2 = YIN_YANG[tg2]
        if wx == wx2:
            shishen = '劫财' if yy != yy2 else '比肩'
        else:
            sheng = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
            ke_wo = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}
            ke_wo2 = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}
            sheng_wo = {'火': '木', '土': '火', '金': '土', '水': '金', '木': '水'}

            if sheng.get(wx) == wx2:
                # 我生者：阳同食神，阳异伤官
                shishen = '食神' if yy == yy2 else '伤官'
            elif ke_wo.get(wx) == wx2:
                # 我克者：阳同偏财，阳异正财
                shishen = '偏财' if yy == yy2 else '正财'
            elif ke_wo2.get(wx) == wx2:
                # 克我者：阳同七杀，阳异正官
                shishen = '七杀' if yy == yy2 else '正官'
            elif sheng_wo.get(wx) == wx2:
                # 生我者：阳同偏印，阳异正印
                shishen = '偏印' if yy == yy2 else '正印'
            else:
                shishen = '正印'
        SHISHEN_MAP[(tg, tg2)] = shishen

CANGGAN = {
    '子': ['癸'], '丑': ['己', '癸', '辛'], '寅': ['甲', '丙', '戊'],
    '卯': ['乙'], '辰': ['戊', '乙', '癸'], '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'], '未': ['己', '丁', '乙'], '申': ['庚', '壬', '戊'],
    '酉': ['辛'], '戌': ['戊', '辛', '丁'], '亥': ['壬', '甲'],
}

LIU_HE = {
    '子': '丑', '丑': '子', '寅': '亥', '亥': '寅',
    '卯': '戌', '戌': '卯', '辰': '酉', '酉': '辰',
    '巳': '申', '申': '巳', '午': '未', '未': '午',
}

LIU_CHONG = {
    '子': '午', '午': '子', '丑': '未', '未': '丑',
    '寅': '申', '申': '寅', '卯': '酉', '酉': '卯',
    '辰': '戌', '戌': '辰', '巳': '亥', '亥': '巳',
}

SAN_HE_ZHI = {
    '水局': ['申', '子', '辰'], '火局': ['寅', '午', '戌'],
    '木局': ['亥', '卯', '未'], '金局': ['巳', '酉', '丑'],
}

CHANGSHENG_SHUN = {
    '木': ['亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌'],
    '火': ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑'],
    '土': ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑'],
    '金': ['巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑', '寅', '卯', '辰'],
    '水': ['申', '酉', '戌', '亥', '子', '丑', '寅', '卯', '辰', '巳', '午', '未'],
}

CHANGSHENG_NAMES = ['长生', '沐浴', '冠带', '临官', '帝旺', '衰', '病', '死', '墓', '绝', '胎', '养']

SHISHEN_YIDU = {
    '比肩': '自我、意志、决断、独立、竞争',
    '劫财': '社交、冲动、竞争、耗财',
    '食神': '才华、温和、福气、口福、艺术',
    '伤官': '聪明、叛逆、变革、口才、艺术',
    '偏财': '意外之财、慷慨、交际、投机',
    '正财': '稳定收入、勤奋、节俭、务实',
    '七杀': '权威、决断、压力、冒险、军警',
    '正官': '正直、责任、规范、公职、管理',
    '偏印': '偏门学术、玄学、敏感、孤独',
    '正印': '学业、慈悲、文化、贵人、保护',
}

LIUQIN_MAP = {
    '偏财': '父', '正财': '妻', '比肩': '兄弟',
    '劫财': '姐妹', '食神': '子(男)', '伤官': '子(女)',
    '七杀': '女命夫/子', '正官': '女命夫',
    '偏印': '母', '正印': '母',
}


def get_zhi_shishen(ba: dict, day_gan: str, dizhi: str) -> str:
    canggan = CANGGAN.get(dizhi, [])
    if not canggan:
        return ''
    return SHISHEN_MAP.get((day_gan, canggan[0]), '')


def get_wuxing_by_day(day_wx: str, relation: str) -> str:
    sheng = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
    ke = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}
    sheng_me = {'火': '木', '土': '火', '金': '土', '水': '金', '木': '水'}
    mapping = {'我生': sheng, '我克': ke, '生我': sheng_me, '克我': ke}
    return mapping.get(relation, {}).get(day_wx, '金')


def analyze_solar_term(year: int, month: int, day: int, hour: int) -> str:
    jieqi_table = [
        (1, 6, '丑'), (2, 4, '寅'), (3, 6, '卯'), (4, 5, '辰'),
        (5, 6, '巳'), (6, 6, '午'), (7, 7, '未'), (8, 8, '申'),
        (9, 8, '酉'), (10, 8, '戌'), (11, 7, '亥'), (12, 7, '子'),
    ]
    current_zhi = '丑'
    for m, d, zhi in jieqi_table:
        if month == m and day >= d:
            current_zhi = zhi
        elif month > m:
            current_zhi = zhi
    return current_zhi


def calculate_kongwang(day_pillar: dict) -> List[str]:
    gan_idx = TIANGAN.index(day_pillar['tiangan'])
    zhi_idx = DIZHI.index(day_pillar['dizhi'])
    xun_start = (zhi_idx - gan_idx) % 12
    return [DIZHI[(xun_start + 10) % 12], DIZHI[(xun_start + 11) % 12]]


def calculate_shensha(four_pillars: dict, day_pillar: dict) -> Dict[str, Any]:
    result = {}
    year_dz = four_pillars['year']['dizhi']
    month_dz = four_pillars['month']['dizhi']
    day_dz = day_pillar['dizhi']
    all_dz = [year_dz, month_dz, day_dz, four_pillars['hour']['dizhi']]

    # 天乙贵人
    tianyi_table = {
        '甲': ['丑', '未'], '戊': ['丑', '未'], '庚': ['丑', '未'],
        '乙': ['子', '申'], '己': ['子', '申'],
        '丙': ['亥', '酉'], '丁': ['亥', '酉'],
        '壬': ['卯', '巳'], '癸': ['卯', '巳'],
        '辛': ['寅', '午'],
    }
    tianyi_candidates = []
    for g in [day_pillar['tiangan'], four_pillars['year']['tiangan']]:
        if g in tianyi_table:
            for t in tianyi_table[g]:
                if t not in tianyi_candidates:
                    tianyi_candidates.append(t)
    tianyi_found = [dz for dz in all_dz if dz in tianyi_candidates]
    if tianyi_found:
        result['天乙贵人'] = {'stars': tianyi_found, 'desc': '逢凶化吉，贵人相助'}

    # 驿马
    yima_table = {
        '申': '寅', '子': '寅', '辰': '寅',
        '寅': '申', '午': '申', '戌': '申',
        '亥': '巳', '卯': '巳', '未': '巳',
        '巳': '亥', '酉': '亥', '丑': '亥',
    }
    yima_loc = yima_table.get(year_dz)
    if yima_loc and yima_loc in all_dz:
        result['驿马'] = {'location': yima_loc, 'desc': '走动、远行、变动'}

    # 桃花
    taohua_table = {
        '申': '酉', '子': '酉', '辰': '酉',
        '寅': '卯', '午': '卯', '戌': '卯',
        '亥': '午', '卯': '午', '未': '午',
        '巳': '子', '酉': '子', '丑': '子',
    }
    taohua_loc = taohua_table.get(year_dz)
    if taohua_loc and taohua_loc in all_dz:
        result['桃花'] = {'location': taohua_loc, 'desc': '人缘、异性缘、情感'}

    # 羊刃
    yangren_table = {
        '寅': '午', '午': '午', '戌': '午',
        '申': '子', '子': '子', '辰': '子',
        '亥': '卯', '卯': '卯', '未': '卯',
        '巳': '酉', '酉': '酉', '丑': '酉',
    }
    yangren_loc = yangren_table.get(year_dz)
    if yangren_loc and yangren_loc in all_dz:
        result['羊刃'] = {'location': yangren_loc, 'desc': '刚猛、冲动、手术'}

    # 禄神
    lu_table = {
        '甲': '寅', '乙': '卯', '丙': '巳', '戊': '巳',
        '丁': '午', '己': '午', '庚': '申', '辛': '酉',
        '壬': '亥', '癸': '子',
    }
    lu_loc = lu_table.get(day_pillar['tiangan'])
    if lu_loc and lu_loc in all_dz:
        result['禄神'] = {'location': lu_loc, 'desc': '财运、俸禄、福禄'}

    # 华盖
    huagai_table = {
        '申': '辰', '子': '辰', '辰': '辰',
        '寅': '戌', '午': '戌', '戌': '戌',
        '亥': '未', '卯': '未', '未': '未',
        '巳': '丑', '酉': '丑', '丑': '丑',
    }
    for check_dz in [year_dz, month_dz]:
        hg = huagai_table.get(check_dz)
        if hg and hg in all_dz:
            if '华盖' not in result:
                result['华盖'] = {'location': hg, 'desc': '艺术、宗教、孤独、聪明'}

    # 将星
    jiangxing_table = {
        '申': '子', '子': '子', '辰': '子',
        '寅': '午', '午': '午', '戌': '午',
        '亥': '卯', '卯': '卯', '未': '卯',
        '巳': '酉', '酉': '酉', '丑': '酉',
    }
    jx = jiangxing_table.get(month_dz)
    if jx and jx in all_dz:
        result['将星'] = {'location': jx, 'desc': '权力、领导力、掌权'}

    # 魁罡
    if day_pillar['tiangan'] + day_pillar['dizhi'] in ['壬辰', '庚戌', '庚辰', '戊戌']:
        result['魁罡'] = {'desc': '刚猛果断，忌冲'}

    # 红鸾
    hongluan_table = {
        '子': '卯', '丑': '寅', '寅': '丑', '卯': '子',
        '辰': '亥', '巳': '戌', '午': '酉', '未': '申',
        '申': '未', '酉': '午', '戌': '巳', '亥': '辰',
    }
    hl = hongluan_table.get(year_dz)
    if hl and hl in all_dz:
        result['红鸾'] = {'location': hl, 'desc': '婚恋喜庆'}

    return result


def determine_yongshen(ba: dict, day_gan: str, day_wx: str,
                       shen_qiang: bool) -> Dict[str, Any]:
    """确定用神/喜神/忌神——基于《四柱命理正源》方法"""
    shishen_counts = {}
    for pname, pillar in ba.items():
        if isinstance(pillar['tiangan_shishen'], str) and pillar['tiangan_shishen']:
            ss = pillar['tiangan_shishen']
            shishen_counts[ss] = shishen_counts.get(ss, 0) + 1
        for cg, css in pillar['canggan'].items():
            if css:
                shishen_counts[css] = shishen_counts.get(css, 0) + 0.3

    info: Dict[str, Any] = {'shen_qiang': shen_qiang, 'method': '正格取用法'}

    # 统计有用字符
    has_印 = bool(shishen_counts.get('正印', 0) or shishen_counts.get('偏印', 0))
    has_比劫 = bool(shishen_counts.get('比肩', 0) or shishen_counts.get('劫财', 0))
    has_官杀 = bool(shishen_counts.get('正官', 0) or shishen_counts.get('七杀', 0))
    has_食伤 = bool(shishen_counts.get('食神', 0) or shishen_counts.get('伤官', 0))
    has_财 = bool(shishen_counts.get('正财', 0) or shishen_counts.get('偏财', 0))

    if shen_qiang:
        # 身旺：喜克泄耗
        priority = [('正官', '克', '官星'), ('七杀', '克', '七杀'),
                     ('食神', '泄', '食神'), ('伤官', '泄', '伤官'),
                     ('偏财', '耗', '财星'), ('正财', '耗', '财星')]
        ji = '比肩' if '比肩' in shishen_counts else '劫财' if '劫财' in shishen_counts else '印比'
        xi = '食伤' if has_食伤 else '财' if has_财 else '官杀'

        for opt, wx_type, label in priority:
            if opt in shishen_counts:
                info.update({
                    'yongshen': opt, 'yongshen_type': wx_type,
                    'xishen': xi, 'jishen': ji,
                    'reason': f'身旺，取{label}为用神'
                })
                return info

        info.update({'yongshen': '官杀', 'yongshen_type': '克',
                      'xishen': '食伤', 'jishen': '比劫',
                      'reason': '身旺，原局无食伤财官杀，取官杀为用'})
    else:
        # 身弱：喜生扶
        yong_opt = None
        if '正印' in shishen_counts:
            yong_opt = '正印'
            reason = '身弱，取正印生身为用'
        elif '偏印' in shishen_counts:
            yong_opt = '偏印'
            reason = '身弱，取偏印生身为用'
        elif '比肩' in shishen_counts:
            yong_opt = '比肩'
            reason = '身弱，取比肩帮身为用'
        elif '劫财' in shishen_counts:
            yong_opt = '劫财'
            reason = '身弱，取劫财帮身为用'

        if yong_opt:
            xi = '比劫' if has_比劫 else '印' if has_印 else '食伤'
            ji_list = []
            if '正官' in shishen_counts: ji_list.append('正官')
            if '七杀' in shishen_counts: ji_list.append('七杀')
            if '正财' in shishen_counts: ji_list.append('正财')
            if '偏财' in shishen_counts: ji_list.append('偏财')
            if '食神' in shishen_counts and yong_opt not in ('食神', '伤官'): ji_list.append('食神')
            if '伤官' in shishen_counts and yong_opt not in ('食神', '伤官'): ji_list.append('伤官')
            ji = ji_list[0] if ji_list else '财官'

            info.update({
                'yongshen': yong_opt, 'yongshen_type': '生扶',
                'xishen': xi, 'jishen': ji,
                'reason': reason,
            })
        else:
            info.update({'yongshen': '印比', 'yongshen_type': '生扶',
                          'xishen': '比劫', 'jishen': '财官食伤',
                          'reason': '身弱，原局印比不足，需待印比运助'})

    return info


def determine_geju(ba: dict, month_pillar: dict, day_gan: str,
                   day_wx: str, shen_qiang: bool) -> Dict[str, Any]:
    month_zhi = month_pillar['dizhi']
    canggan = CANGGAN.get(month_zhi, [])
    benqi = canggan[0] if canggan else ''
    benqi_ss = SHISHEN_MAP.get((day_gan, benqi), '')

    name, desc = '', ''
    if benqi_ss in ('正官', '七杀'):
        name, desc = '官杀格', f'月令本气{benqi}为{"正官" if benqi_ss=="正官" else "七杀"}，取为官杀格'
    elif benqi_ss in ('正印', '偏印'):
        name, desc = '印绶格', f'月令本气{benqi}为{"正印" if benqi_ss=="正印" else "偏印"}，取为印绶格'
    elif benqi_ss in ('正财', '偏财'):
        name, desc = '财格', f'月令本气{benqi}为{"正财" if benqi_ss=="正财" else "偏财"}，取为财格'
    elif benqi_ss in ('食神', '伤官'):
        name, desc = '食伤格', f'月令本气{benqi}为{"食神" if benqi_ss=="食神" else "伤官"}，取为食伤格'
    elif benqi_ss in ('比肩', '劫财'):
        name, desc = '建禄/月劫格', f'月令本气{benqi}为比劫，取为建禄格或月劫格'
    else:
        name, desc = '杂气格', '月令藏干透干情况不明，以杂气论'

    tongan = []
    for pname in ['year', 'month', 'hour']:
        for cg, ss in ba[pname]['canggan'].items():
            if cg != ba[pname]['tiangan'] and ba[pname]['tiangan'] != day_gan:
                if SHISHEN_MAP.get((day_gan, cg)) == benqi_ss:
                    tongan.append(cg)

    special = ''
    if not shen_qiang:
        # simplified from格 check
        all_ss = [p['tiangan_shishen'] for p in ba.values() if p['tiangan_shishen'] in ('比肩', '劫财', '正印', '偏印')]
        if len(all_ss) <= 1:
            special = '可能为从格（需进一步验证）'

    return {
        'ming_ge': name, 'ming_ge_desc': desc,
        'month_zhi': month_zhi, 'month_benqi': benqi,
        'month_benqi_shishen': benqi_ss, 'tongan': tongan,
        'special': special,
    }


# ═══════════════════════════════════════════════════════════
# PUBLIC API — bazi_engine.py 核心入口
# ═══════════════════════════════════════════════════════════

def solar_to_lunar(year: int, month: int, day: int) -> tuple:
    """公历→农历"""
    if not HAS_LUNARDATE:
        return (None, None, None, None)  # 年 月 日 闰月
    try:
        l = LunarDate.fromSolarDate(year, month, day)
        return (l.year, l.month, l.day, l.isLeapMonth)
    except Exception:
        return (None, None, None, None)


def lunar_to_solar(lunar_year: int, lunar_month: int, lunar_day: int,
                   is_leap: bool = False) -> tuple:
    """农历→公历 (year, month, day)"""
    if not HAS_LUNARDATE:
        return (None, None, None)
    try:
        leap = 1 if is_leap else 0
        l = LunarDate(lunar_year, lunar_month, lunar_day, leap)
        s = l.toSolarDate()
        return (s.year, s.month, s.day)
    except Exception:
        return (None, None, None)


def resolve_birth_info(user_input: dict) -> dict:
    """
    解析用户输入，返回标准化的公历时间+经度

    user_input 格式（从命令行/前端接收）：
      {
        'year': int, 'month': int, 'day': int,  # 公历或农历
        'hour': int, 'minute': int,
        'gender': str,  # male/female
        'is_lunar': bool,  # True=农历输入
        'city': str,  # 城市名，如"北京"
        'longitude': float,  # 直接指定经度（备选）
        'latitude': float,    # 直接指定纬度（备选）
      }
    """
    is_lunar = user_input.get('is_lunar', False)
    city = user_input.get('city', '')
    longitude = user_input.get('longitude')

    # ── Step 1: 农历/公历转换 ──
    if is_lunar:
        sy, sm, sd = lunar_to_solar(
            user_input['year'],
            user_input['month'],
            user_input['day'],
            user_input.get('is_leap_month', False)
        )
        if sy is None:
            raise ValueError(f"无法转换农历 {user_input['year']}年{user_input['month']}月{user_input['day']}日，请检查输入")
        year, month, day = sy, sm, sd
        calendar_type = '农历'
    else:
        year, month, day = user_input['year'], user_input['month'], user_input['day']
        calendar_type = '公历'

    # ── Step 2: 获取出生地经度 ──
    if longitude is None:
        coord = find_city_coord(city) if city else None
        if coord:
            longitude = coord[0]
        else:
            longitude = 120.0  # 默认东经120度（标准时区）
    else:
        coord = (longitude, user_input.get('latitude', 30.0))
    if 'latitude' not in user_input:
        coord = (longitude, 30.0) if coord and len(coord) < 2 else coord

    # ── Step 3: 真太阳时校正 ──
    raw_hour = user_input.get('hour', 12)
    raw_minute = user_input.get('minute', 0)
    true_hour, true_minute, offset_min = calculate_true_solar_time(
        year, month, day, raw_hour, raw_minute, longitude
    )

    return {
        'year': year, 'month': month, 'day': day,
        'hour': true_hour, 'minute': true_minute,
        'raw_hour': raw_hour, 'raw_minute': raw_minute,
        'gender': user_input.get('gender', 'male'),
        'calendar_type': calendar_type,
        'longitude': longitude,
        'latitude': coord[1] if coord else 30.0,
        'city': city,
        'true_solar_offset': round(offset_min, 2),
    }


# ── 以下为核心计算函数（与v1相同，保持不变）──

def get_year_ganzhi(year: int) -> dict:
    gan_idx = (year - 4) % 10
    zhi_idx = (year - 4) % 12
    return {
        'tiangan': TIANGAN[gan_idx], 'dizhi': DIZHI[zhi_idx],
        'wuxing': WUXING_MAP[TIANGAN[gan_idx]],
        'yinyang': '阳' if YIN_YANG[TIANGAN[gan_idx]] else '阴',
        'tiangan_shishen': '', 'canggan': {},
    }


def get_day_ganzhi(year: int, month: int, day: int) -> dict:
    base_date = datetime(1900, 1, 1)  # 甲戌日 = (gan=0, zhi=10)
    target_date = datetime(year, month, day)
    days_diff = (target_date - base_date).days
    gan_idx = (0 + days_diff) % 10
    zhi_idx = (10 + days_diff) % 12
    return {
        'tiangan': TIANGAN[gan_idx], 'dizhi': DIZHI[zhi_idx],
        'wuxing': WUXING_MAP[TIANGAN[gan_idx]],
        'yinyang': '阳' if YIN_YANG[TIANGAN[gan_idx]] else '阴',
        'tiangan_shishen': '', 'canggan': {},
    }


def _calc_dayun(year: int, month_pillar: dict, day_gan: str,
                gender: str, shen_qiang: bool,
                birth_month: int = 0, birth_day: int = 0) -> List[dict]:
    year_gan = TIANGAN[(year - 4) % 10]
    year_yinyang = YIN_YANG.get(year_gan, 0)
    month_zhi = month_pillar['dizhi']
    month_zhi_idx = DIZHI.index(month_zhi)

    is_nv = gender == 'female'
    shunpai = (year_yinyang == 1 and not is_nv) or (year_yinyang == 0 and is_nv)

    qiyun_age = 3 + ((birth_month * 31 + birth_day) % 10)

    dayun_list = []
    if shunpai:
        start_idx = month_zhi_idx + 1
        for i in range(12):
            idx = (start_idx + i) % 12
            zhi = DIZHI[idx]
            start_gan_idx = TIANGAN.index(month_pillar['tiangan'])
            gan_idx = (start_gan_idx + i + 1) % 10
            gan = TIANGAN[gan_idx]
            dayun_list.append({
                'index': i + 1, 'tiangan': gan, 'dizhi': zhi,
                'wuxing': WUXING_MAP[gan], 'start_age': qiyun_age + i * 10,
                'shishen': SHISHEN_MAP.get((day_gan, gan), ''),
            })
    else:
        start_idx = month_zhi_idx - 1
        for i in range(12):
            idx = (start_idx - i) % 12
            zhi = DIZHI[idx]
            start_gan_idx = TIANGAN.index(month_pillar['tiangan'])
            gan_idx = (start_gan_idx - i - 1) % 10
            gan = TIANGAN[gan_idx]
            dayun_list.append({
                'index': i + 1, 'tiangan': gan, 'dizhi': zhi,
                'wuxing': WUXING_MAP[gan], 'start_age': qiyun_age + i * 10,
                'shishen': SHISHEN_MAP.get((day_gan, gan), ''),
            })
    return dayun_list


def calculate_bazi(
    year: int, month: int, day: int,
    hour: int = 12, minute: int = 0,
    gender: str = 'male',
    longitude: float = 120.0,
    city: str = '',
    **extra: dict,
) -> dict:
    """
    完整的八字排盘计算

    Args:
        year, month, day: 公历日期
        hour, minute: 真太阳时后的时辰
        gender: 'male' or 'female'
        longitude: 出生地经度
        city: 出生城市名
        **extra: 包含 raw_hour, raw_minute, calendar_type, true_solar_offset 等
    """
    raw_hour = extra.get('raw_hour', hour)
    raw_minute = extra.get('raw_minute', minute)
    calendar_type = extra.get('calendar_type', '公历')
    true_solar_offset = extra.get('true_solar_offset', 0)

    # ── 年柱 ──
    year_pillar = get_year_ganzhi(year)

    # ── 月柱 ──
    month_zhi = analyze_solar_term(year, month, day, hour)
    month_zhi_idx = DIZHI.index(month_zhi)

    year_gan = TIANGAN[(year - 4) % 10]
    wuhu_map = {
        '甲': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
        '乙': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
        '丙': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
        '丁': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
        '戊': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
        '己': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
        '庚': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
        '辛': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
        '壬': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
        '癸': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
    }
    month_gan = wuhu_map.get(year_gan, ['丙'])[(month_zhi_idx - 2) % 12]

    month_pillar = {
        'tiangan': month_gan, 'dizhi': month_zhi,
        'wuxing': WUXING_MAP[month_gan],
        'yinyang': '阳' if YIN_YANG[month_gan] else '阴',
        'tiangan_shishen': '', 'canggan': {}, 'zhi_idx': month_zhi_idx,
    }

    # ── 日柱 ──
    day_pillar = get_day_ganzhi(year, month, day)
    day_gan = day_pillar['tiangan']
    day_dizhi = day_pillar['dizhi']
    day_wx = WUXING_MAP[day_gan]

    # ── 时柱 ──
    # 先确定时辰地支（精确到分钟）
    hour_dizhi_actual = get_solar_hour_zhi(hour, minute)
    hour_dizhi = hour_dizhi_actual[0]  # 第1个元素是地支，第2个是分钟偏移
    hour_zhi_idx = DIZHI.index(hour_dizhi)

    wushu_map = {
        '甲': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
        '乙': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
        '丙': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
        '丁': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
        '戊': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
        '己': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
        '庚': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
        '辛': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
        '壬': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
        '癸': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
    }
    hour_gan = wushu_map.get(day_gan, ['甲'])[hour_zhi_idx]

    hour_pillar = {
        'tiangan': hour_gan, 'dizhi': hour_dizhi,
        'wuxing': WUXING_MAP[hour_gan],
        'yinyang': '阳' if YIN_YANG[hour_gan] else '阴',
        'tiangan_shishen': '', 'canggan': {},
    }

    four_pillars = {
        'year': year_pillar, 'month': month_pillar,
        'day': day_pillar, 'hour': hour_pillar,
    }

    # ── 填充十神 ──
    for pname, pillar in four_pillars.items():
        pillar['tiangan_shishen'] = SHISHEN_MAP.get((day_gan, pillar['tiangan']), '')
        for cg in CANGGAN.get(pillar['dizhi'], []):
            pillar['canggan'][cg] = SHISHEN_MAP.get((day_gan, cg), '')

    # ── 五行统计 ──
    wuxing_count: Dict[str, float] = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
    for pname, pillar in four_pillars.items():
        wuxing_count[pillar['wuxing']] += 1
        wuxing_count[ZHI_WUXING[pillar['dizhi']]] += 1
        for cg in CANGGAN.get(pillar['dizhi'], []):
            wuxing_count[WUXING_MAP[cg]] += 0.3

    wuxing_scores = dict(wuxing_count)
    mzw = ZHI_WUXING[month_zhi]
    wuxing_scores[mzw] = round(wuxing_scores.get(mzw, 0) * 2, 1)

    total = sum(wuxing_scores.values())
    wuxing_pct = {}
    for wx in ['金', '木', '水', '火', '土']:
        wuxing_pct[wx] = round(wuxing_scores.get(wx, 0) / total * 100, 1) if total > 0 else 0

    # ── 身强身弱 ──
    month_ss = SHISHEN_MAP.get((day_gan, month_pillar['tiangan']), '')
    support = 0
    drain = 0
    for pname, pillar in four_pillars.items():
        ss = pillar['tiangan_shishen']
        if ss in ('比肩', '劫财', '正印', '偏印'):
            support += 1
        elif ss in ('正官', '七杀', '食神', '伤官', '正财', '偏财'):
            drain += 1
    if month_ss in ('比肩', '劫财', '正印', '偏印'):
        support += 2
    else:
        drain += 2

    shen_qiang = support > drain * 1.2
    shen_qiang2 = support >= drain
    if support > drain * 1.2:
        shenruo_summary = '身旺'
    elif drain > support * 1.2:
        shenruo_summary = '身弱'
    else:
        shenruo_summary = '中和偏旺' if shen_qiang2 else '中和偏弱'

    # ── 十二长生 ──
    changsheng_list = CHANGSHENG_SHUN[day_wx]
    rev_list = changsheng_list if YIN_YANG[day_gan] else list(reversed(changsheng_list))
    day_changsheng_idx = rev_list.index(day_dizhi) if day_dizhi in rev_list else -1
    day_changsheng_name = CHANGSHENG_NAMES[day_changsheng_idx] if day_changsheng_idx >= 0 else 'unknown'

    # ── 用神 ──
    yongshen = determine_yongshen(four_pillars, day_gan, day_wx, shen_qiang)

    # ── 空亡 ──
    kongwang = calculate_kongwang(day_pillar)

    # ── 大运 ──
    dayun_list = _calc_dayun(year, month_pillar, day_gan, gender, shen_qiang, month, day)

    # ── 当前大运/流年 ──
    now = datetime.now()
    current_age = now.year - year
    current_dayun = None
    for dy in dayun_list:
        if dy['start_age'] <= current_age < dy['start_age'] + 10:
            current_dayun = dy
            break

    # ── 近15年流年 ──
    liunian_list = []
    for y in range(max(year + 1, now.year - 5), now.year + 6):
        lg_idx = (y - 3) % 10
        lz_idx = (y - 3) % 12
        liunian = {
            'year': y, 'tiangan': TIANGAN[lg_idx], 'dizhi': DIZHI[lz_idx],
            'wuxing': WUXING_MAP[TIANGAN[lg_idx]],
            'shishen_gan': SHISHEN_MAP.get((day_gan, TIANGAN[lg_idx]), ''),
            'shishen_zhi': get_zhi_shishen(four_pillars, day_gan, DIZHI[lz_idx]),
            'age': y - year,
            'relation': _analyze_liunian(four_pillars, day_gan, DIZHI[lz_idx]),
        }
        liunian_list.append(liunian)

    # ── 神煞 ──
    shensha = calculate_shensha(four_pillars, day_pillar)

    # ── 六合六冲 ──
    all_zhi = [p['dizhi'] for p in four_pillars.values()]
    liuchong_pairs = []
    liuhe_pairs = []
    for i, z1 in enumerate(all_zhi):
        for z2 in all_zhi[i + 1:]:
            if LIU_HE.get(z1) == z2:
                liuhe_pairs.append((z1, z2, '六合'))
            if LIU_CHONG.get(z1) == z2:
                liuchong_pairs.append((z1, z2, '六冲'))

    # ── 格局 ──
    geju = determine_geju(four_pillars, month_pillar, day_gan, day_wx, shen_qiang)

    # ── 真太阳时信息 ──
    true_solar_info = {
        'raw_clock_time': f'{raw_hour}:{raw_minute:02d}',
        'true_solar_time': f'{int(hour)}:{int(round(minute)):02d}',
        'longitude': longitude,
        'city': city,
        'offset_minutes': 0,  # placeholder, see below
    }

    # ── 农历转换信息 ──
    lunar_info = {}
    if calendar_type == '农历':
        ly, lm, ld, is_leap = solar_to_lunar(year, month, day)
        if ly is not None:
            lunar_info = {
                'lunar_year': ly, 'lunar_month': lm, 'lunar_day': ld,
                'is_leap_month': is_leap,
                'lunar_year_gan': TIANGAN[(ly - 3) % 10] if ly >= 4 else '',
                'lunar_year_zhi': DIZHI[(ly - 3) % 12] if ly >= 4 else '',
            }

    # ── 返回 ──
    result = {
        'birth_info': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'minute': minute,
            'gender': gender, 'calendar_type': calendar_type,
        },
        'four_pillars': four_pillars,
        'day_gan': day_gan, 'day_wuxing': day_wx,
        'wuxing_count': {k: round(v, 1) for k, v in wuxing_scores.items()},
        'wuxing_pct': wuxing_pct,
        'shenruo': shenruo_summary,
        'shen_qiang': shen_qiang,
        'day_changsheng': day_changsheng_name,
        'yongshen': yongshen,
        'kongwang': kongwang,
        'dayun': dayun_list,
        'current_dayun': current_dayun,
        'current_age': current_age,
        'liunian': liunian_list,
        'shensha': shensha,
        'liuchong': liuchong_pairs,
        'liuhe': liuhe_pairs,
        'geju': geju,
        'true_solar': true_solar_info,
        'lunar': lunar_info,
    }

    # Fill true_solar offset
    result['true_solar']['offset_minutes'] = true_solar_offset

    return result


def _analyze_liunian(ba: dict, day_gan: str, liunian_dz: str) -> List[str]:
    relations = []
    all_zhi = [p['dizhi'] for p in ba.values()]
    for pz in all_zhi:
        if LIU_CHONG.get(pz) == liunian_dz:
            relations.append(f'流年地支与{pz}相冲')
        if LIU_HE.get(pz) == liunian_dz:
            relations.append(f'流年地支与{pz}六合')
        for name, zhi_list in SAN_HE_ZHI.items():
            if liunian_dz in zhi_list:
                others = [z for z in zhi_list if z != liunian_dz]
                if all(o in all_zhi for o in others):
                    relations.append(f'流年地支与命局构成{name}')
    return relations


# ═══════════════════════════════════════════════════════════
# CLI ENTRY POINT (with enhanced args)
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='四柱八字排盘算命')
    parser.add_argument('year', type=int, help='出生年份')
    parser.add_argument('month', type=int, help='出生月份')
    parser.add_argument('day', type=int, help='出生日期')
    parser.add_argument('hour', type=int, nargs='?', default=12, help='出生时辰(0-23)')
    parser.add_argument('minute', type=int, nargs='?', default=0, help='出生分钟')
    parser.add_argument('gender', nargs='?', default='male', choices=['male', 'female'],
                        help='性别: male/female')
    parser.add_argument('city', nargs='?', default='', help='出生城市名')
    parser.add_argument('--lunar', action='store_true', help='农历输入')
    parser.add_argument('--leap', action='store_true', help='闰月')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')

    args = parser.parse_args()

    # 构建 user_input 字典
    user_input = {
        'year': args.year, 'month': args.month, 'day': args.day,
        'hour': args.hour, 'minute': args.minute,
        'gender': args.gender,
        'is_lunar': args.lunar,
        'is_leap_month': args.leap,
        'city': args.city if args.city else '',
        'calendar_type': '农历' if args.lunar else '公历',
    }

    try:
        # Step 1: 解析输入（农历转换 + 真太阳时）
        resolved = resolve_birth_info(user_input)

        # Step 2: 排盘
        result = calculate_bazi(
            year=resolved['year'],
            month=resolved['month'],
            day=resolved['day'],
            hour=resolved['hour'],
            minute=resolved['minute'],
            gender=resolved['gender'],
            longitude=resolved['longitude'],
            city=resolved['city'],
            raw_hour=resolved['raw_hour'],
            raw_minute=resolved['raw_minute'],
            calendar_type=resolved['calendar_type'],
            true_solar_offset=resolved['true_solar_offset'],
        )

        # 合并元数据
        result['resolution_info'] = {
            'input_type': resolved['calendar_type'],
            'raw_clock_time': f'{int(resolved["raw_hour"])}:{int(round(resolved["raw_minute"])):02d}',
            'true_solar_time': f'{int(resolved["hour"])}:{int(round(resolved["minute"])):02d}',
            'longitude': resolved['longitude'],
            'city': resolved['city'],
            'offset_minutes': resolved['true_solar_offset'],
        }

        # 添加农历/公历互转信息
        ly, lm, ld, il = solar_to_lunar(resolved['year'], resolved['month'], resolved['day'])
        if resolved['calendar_type'] == '农历':
            result['resolution_info']['solar_to_lunar'] = {
                'year': ly, 'month': lm, 'day': ld, 'is_leap': il,
                'note': f'农历输入，已转为公历{resolved["year"]}年{resolved["month"]}月{resolved["day"]}日',
            }
        else:
            result['resolution_info']['solar_to_lunar'] = {
                'year': ly, 'month': lm, 'day': ld, 'is_leap': il,
                'note': f'公历{resolved["year"]}年{resolved["month"]}月{resolved["day"]}日 = '
                        f'农历{ly}年{lm}月{ld}日' if ly else '无法转换农历',
            }

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        import traceback
        error_result = {
            'error': str(e),
            'traceback': traceback.format_exc()[:500],
            'hint': '请检查输入是否正确。示例：\n'
                    '  公历: python3 bazi_engine.py 1990 5 15 14 30 male 北京\n'
                    '  农历: python3 bazi_engine.py --lunar 1990 4 22 14 30 male 上海\n'
                    '  无出生地: python3 bazi_engine.py 1990 5 15 14 30 male\n'
                    '  自定义经度: python3 bazi_engine.py 1990 5 15 14 30 male 104.07 30.57',
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
