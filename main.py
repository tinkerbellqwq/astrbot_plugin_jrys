from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

import os
import json
import random
import hashlib
import base64
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

plugin_dirname = "data/plugins/astrbot_plugin_jrys"

# 加载运势数据
with open(os.path.join(os.path.dirname(__file__), "jrys.json"), 'r', encoding='utf-8') as f:
    jrys_json = json.load(f)

# 默认运势概率表
default_fortune_probability = [
    {"Fortune": "☆☆☆☆☆☆☆", "luckValue": 0, "Probability": 5},
    {"Fortune": "★☆☆☆☆☆☆", "luckValue": 14, "Probability": 10},
    {"Fortune": "★★☆☆☆☆☆", "luckValue": 28, "Probability": 12},
    {"Fortune": "★★★☆☆☆☆", "luckValue": 42, "Probability": 15},
    {"Fortune": "★★★★☆☆☆", "luckValue": 56, "Probability": 30},
    {"Fortune": "★★★★★☆☆", "luckValue": 70, "Probability": 35}
]

# 默认配置
config = {
    "command": "jrys",
    "command2": "查看运势背景图",
    "GetOriginalImageCommand": True,
    "autocleanjson": True,
    "Checkin_HintText": "正在分析你的运势哦~请稍等~~",
    "recallCheckin_HintText": True,
    "GetOriginalImage_Command_HintText": "2",
    "FortuneProbabilityAdjustmentTable": default_fortune_probability,
    "BackgroundURL": [
                    os.path.join(plugin_dirname,"backgrounds/魔卡.txt"),
                    os.path.join(plugin_dirname,"backgrounds/ba.txt"),
                    os.path.join(plugin_dirname,"backgrounds/猫羽雫.txt"),
                    os.path.join(plugin_dirname,"backgrounds/miku.txt"),
                    os.path.join(plugin_dirname,"backgrounds/白圣女.txt")],
    "screenshotquality": 50,
    "HTML_setting": {
        "UserNameColor": "rgba(255,255,255,1)",
        "MaskColor": "rgba(0,0,0,0.5)",
        "Maskblurs": 10,
        "HoroscopeTextColor": "rgba(255,255,255,1)",
        "luckyStarGradientColor": True,
        "HoroscopeDescriptionTextColor": "rgba(255,255,255,1)",
        "DashedboxThickn": 5,
        "Dashedboxcolor": "rgba(255, 255, 255, 0.5)",
        "fontPath": os.path.join(plugin_dirname, "/font/lite.ttf")
    },
    "enablecurrency": False,
    "currency": "jrys",
    "maintenanceCostPerUnit": 100,
    "retryexecute": False,
    "Repeated_signin_for_different_groups": False,
    "consoleinfo": False
}

# 创建数据目录
data_dir = Path('data/jrys-prpr')
data_dir.mkdir(parents=True, exist_ok=True)
json_file_path = data_dir / 'OriginalImageURL_data.json'

# 初始化JSON文件
if not json_file_path.exists():
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump([], f)


class Random:
    def __init__(self, seed_func=None):
        self.seed_func = seed_func or random.random

    def weightedPick(self, weights):
        """在带权重的选项中随机选择一个"""
        total = sum(weights.values())
        r = self.seed_func() * total

        cumulative = 0
        for item, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return item

        # 如果因为浮点数精度问题没有返回，就返回最后一个
        return list(weights.keys())[-1]


def get_font_base64(font_path: str) -> str:
    """读取字体文件并转换为Base64编码"""
    try:
        if not os.path.exists(font_path):
            print(f"警告: 字体文件不存在: {font_path}")
            return ""
        with open(font_path, 'rb') as f:
            font_data = f.read()
        return base64.b64encode(font_data).decode('utf-8')
    except Exception as e:
        print(f"读取字体文件时出错: {e}")
        return ""


def convert_to_base64_if_local(url: str) -> str:
    """如果是本地文件，则转换为Base64数据URL"""
    if url.startswith('file:///'):
        path = url[8:]  # 去掉file:///前缀
        try:
            with open(path, 'rb') as f:
                file_data = f.read()
            mime_type = get_mime_type(path)
            base64_data = base64.b64encode(file_data).decode('utf-8')
            return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            print(f"转换本地文件到Base64时出错: {e}")
    return url

def get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取MIME类型"""
    ext = os.path.splitext(file_path.lower())[1]
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    if ext in mime_types:
        return mime_types[ext]
    raise ValueError(f"不支持的文件类型: {ext}")

def get_random_background(config: Dict) -> str:
    """获取随机背景图片URL"""
    background_path = random.choice(config["BackgroundURL"])

    # 如果是网络URL，直接返回
    if background_path.startswith(('http://', 'https://')):
        return background_path

    # 如果是txt文件路径
    if background_path.endswith('.txt'):
        try:
            with open(background_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            if urls:
                return random.choice(urls)
        except Exception as e:
            print(f"读取txt文件时出错: {e}")

    # 如果是文件夹路径
    if os.path.isdir(background_path):
        try:
            image_files = [f for f in os.listdir(background_path)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))]
            if image_files:
                return f"file:///{os.path.join(os.path.abspath(background_path), random.choice(image_files))}"
        except Exception as e:
            print(f"读取文件夹时出错: {e}")

    # 如果是图片文件绝对路径
    if os.path.isfile(background_path):
        try:
            if background_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                return f"file:///{os.path.abspath(background_path)}"
        except Exception as e:
            print(f"读取图片文件时出错: {e}")

    # 如果上述条件都不满足，返回默认网络图片
    return "https://i.loli.net/2021/03/19/2UZcj1TsEPiDhGI.jpg"

def get_jrys(user_id: str) -> Dict:
    """获取今日运势数据"""
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    # 获取当前时间
    now = datetime.datetime.now()
    etime = int(datetime.datetime(now.year, now.month, now.day).timestamp() * 1000)

    # 处理用户ID
    if user_id.isdigit():
        final_user_id = int(user_id)
    else:
        sha256_hash.update((user_id + str(etime)).encode())
        hash_hex_digest = sha256_hash.hexdigest()
        final_user_id = int(int(hash_hex_digest, 16) % 1000000001)

    # 获取运势概率表
    fortune_probability_table = config["FortuneProbabilityAdjustmentTable"] or default_fortune_probability

    # 检查所有概率是否都为0
    all_probabilities_zero = all(entry["Probability"] == 0 for entry in fortune_probability_table)
    if all_probabilities_zero:
        fortune_probability_table = default_fortune_probability

    # 使用种子确保随机结果的一致性
    seed_input = str(final_user_id) + str(etime) + now.strftime("%Y-%m-%d")
    md5_hash.update(seed_input.encode())
    seed = int(md5_hash.hexdigest()[:8], 16)
    random.seed(seed)

    # 选择运势
    weights = {entry["luckValue"]: entry["Probability"]
               for entry in fortune_probability_table if entry["Probability"] > 0}

    # 将字典转换为Random类可用的格式
    random_gen = Random(lambda: seed / 0xffffffff)
    fortune_category = random_gen.weightedPick(weights)

    # 获取对应运势的文案
    today_jrys = jrys_json[str(fortune_category)]

    # 随机选择文案
    random_index = int((((etime / 100000) * final_user_id % 1000001) * 2333) % len(today_jrys))

    return today_jrys[random_index]

def get_formatted_date() -> str:
    """获取格式化的日期"""
    today = datetime.datetime.now()
    year = today.year
    month = today.month
    day = today.day

    # 格式化日期
    month_str = f"0{month}" if month < 10 else str(month)
    day_str = f"0{day}" if day < 10 else str(day)

    return f"{year}/{month_str}/{day_str}"

def generate_fortune_html(user_id: str, avatar_url: str = "https://q1.qlogo.cn/g?b=qq&nk=10001&s=640") -> str:
    """生成今日运势HTML"""
    try:
        # 获取背景图片
        background_url = get_random_background(config)
        print(f"选择的背景图片URL: {background_url}")
        background_url_base64 = background_url
        if background_url.startswith('file:///'):
            background_url_base64 = convert_to_base64_if_local(background_url)

        # 获取运势数据
        d_json = get_jrys(user_id)

        # 获取日期
        formatted_date = get_formatted_date()

        # 获取字体Base64
        font_path = config["HTML_setting"]["fontPath"]
        font_base64 = get_font_base64(font_path)
        font_family_name = "CustomFont"  # 统一字体名称

        # 设置星星样式
        lucky_star_html = """
        .lucky-star {
        font-size: 60px;
        margin-bottom: 10px;
        }
        """

        if config["HTML_setting"]["luckyStarGradientColor"]:
            lucky_star_html = """
            .lucky-star {
            font-size: 60px;
            margin-bottom: 10px;
            background: linear-gradient(to right,
            #fcb5b5, #fcd6ae, #fde8a6, #c3f7b1, #aed6fa, #c4aff5, #f1afcc);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            }
            """

        # 构建HTML
        html_source = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>运势卡片</title>
        <style>
        @font-face {{
        font-family: "{font_family_name}";
        src: url('data:font/ttf;base64,{font_base64}') format('truetype');
        }}
        body, html {{
        height: 100%;
        margin: 0;
        overflow: hidden;
        font-family: "{font_family_name}", sans-serif;
        }}
        .background {{
        background-image: url('{background_url_base64}');
        background-size: cover;
        background-position: center;
        position: relative;
        width: 100%;
        height: 100vh;
        }}
        .overlay {{
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        min-height: 1%;
        background-color: {config["HTML_setting"]["MaskColor"]};
        backdrop-filter: blur({config["HTML_setting"]["Maskblurs"]}px);
        border-radius: 20px 20px 0 0;
        overflow: visible;
        }}
        .user-info {{
        display: flex;
        align-items: center;
        padding: 10px 20px;
        position: relative;
        }}
        .user-avatar {{
        width: 120px;
        height: 120px;
        border-radius: 60px;
        background-image: url('{avatar_url}');
        background-size: cover;
        background-position: center;
        margin-left: 20px;
        position: absolute;
        top: 40px;
        }}
        .username {{
        margin-left: 10px;
        color: {config["HTML_setting"]["UserNameColor"]};
        font-size: 50px;
        padding-top: 28px;
        }}
        .fortune-info1 {{
        display: flex;
        color: {config["HTML_setting"]["HoroscopeTextColor"]};
        flex-direction: column;
        align-items: center;
        position: relative;
        width: 100%;
        justify-content: center;
        margin-top: 100px;
        }}
        .fortune-info1 > * {{
        margin: 10px;
        }}
        .fortune-info2 {{
        color: {config["HTML_setting"]["HoroscopeDescriptionTextColor"]};
        padding: 0 20px;
        margin-top: 40px;
        }}
        .lucky-star, .sign-text, .unsign-text {{
        margin-bottom: 12px;
        font-size: 42px;
        }}
        .fortune-summary {{
        font-size: 60px;
        }}
        {lucky_star_html}
        .sign-text, .unsign-text {{
        font-size: 32px;
        line-height: 1.6;
        padding: 10px;
        border: {config["HTML_setting"]["DashedboxThickn"]}px dashed {config["HTML_setting"]["Dashedboxcolor"]};
        border-radius: 15px;
        margin-top: 10px;
        }}
        .today-text {{
        font-size: 45px;
        margin-bottom: 10px;
        background: linear-gradient(to right,
        #fcb5b5, #fcd6ae, #fde8a6, #c3f7b1, #aed6fa, #c4aff5, #f1afcc);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        }}
        /* 调试信息样式 */
        .debug-info {{
            position: fixed;
            top: 10px;
            left: 10px;
            background-color: rgba(255,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            z-index: 9999;
            font-family: Arial, sans-serif;
        }}
        </style>
        </head>
        <body>
        <div class="background">
        <div class="overlay">
            <div class="user-info">
                <div class="user-avatar"></div>
            </div>
            <div class="fortune-info1">
                <div class="today-text">{formatted_date}</div>
                <div class="fortune-summary">{d_json["fortuneSummary"]}</div>
                <div class="lucky-star">{d_json["luckyStar"]}</div>
            </div>
            <div class="fortune-info2">
                <div class="sign-text">{d_json["signText"]}</div>
                <div class="unsign-text">{d_json["unsignText"]}</div>
                <!-- 不要迷信哦 -->
                <div style="text-align: center; font-size: 24px; margin-bottom: 15px;">
                    仅供娱乐 | 相信科学 | 请勿迷信
                </div>
            </div>
        </div>
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('DOM完全加载');
        }});
        window.onload = function() {{
            console.log('页面完全加载，包括所有资源');
        }};
        // 检测背景图片加载情况
        (function() {{
            var bgImg = new Image();
            bgImg.onload = function() {{ 
                console.log('背景图片加载成功'); 
                document.querySelector('.debug-info').textContent += ' | 背景图加载成功';
            }};
            bgImg.onerror = function() {{ 
                console.log('背景图片加载失败'); 
                document.querySelector('.debug-info').textContent += ' | 背景图加载失败';
                // 尝试使用备用背景
                document.querySelector('.background').style.backgroundColor = '#333';
            }};
            bgImg.src = '{background_url_base64}';
        }})();
        </script>
        </body>
        </html>
        """
        return html_source
    except Exception as e:
        # 出错时返回简单的调试HTML
        error_msg = str(e)
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>错误</title></head>
        <body>
            <h1>生成运势卡片时出错</h1>
            <p>错误信息: {error_msg}</p>
        </body>
        </html>
        """



@register("jrys",
          "tinker",
          "精美的jrys图",
          "1.0",
          "https://github.com/tinkerbellqwq/astrbot_plugin_jrys")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("插件初始化完成！")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("插件销毁完成！")

    @filter.command("jrys", alias={'今日运势', '运势'})
    async def jrys(self, event: AstrMessageEvent):
        """ 今日运势 """
        logger.info("收到今日运势请求")
        yield event.make_result().message("正在分析你的运势哦~请稍等~~")
        # 获取用户ID 和 头像
        user_id = event.get_sender_id()
        avatar = f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"
        # 生成HTML
        html = generate_fortune_html(user_id, avatar)
        # 截图并发送
        url = await self.html_render(html, {})
        # 发送图片
        yield event.make_result().url_image(url)
        logger.info("今日运势请求处理完成")
