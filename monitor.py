from DrissionPage import ChromiumPage
from bs4 import BeautifulSoup
import json
import os
import time
import requests
from datetime import datetime
from urllib.parse import urljoin
from dotenv import load_dotenv  # 🟢 新增：引入 dotenv 库

# 🟢 加载 .env 文件中的配置到环境变量中
load_dotenv()

# ================= 配置区 =================
# 使用 os.getenv() 读取环境变量，并进行必要的类型转换
TARGET_QQ = int(os.getenv("TARGET_QQ", 0))          # 转为整数，默认值为 0
SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")     # 字符串，默认本地
LANGBOT_PORT = int(os.getenv("LANGBOT_PORT", 3000)) # 转为整数，默认 3000
NAPCAT_TOKEN = os.getenv("NAPCAT_TOKEN", "")        # 字符串，默认为空

STATE_FILE = "monitor_state.json"
HEARTBEAT_INTERVAL = 7200  


TARGETS = [
    {
        "school_name": "哈工大",
        "url": "https://yzb.hit.edu.cn/8822/list.htm",
        "selector": ".news_title a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "哈工大计学部",
        "url": "https://computing.hit.edu.cn/11474/list.htm",
        "selector": ".news_title a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "电子科大计科院",
        "url": "https://www.scse.uestc.edu.cn/tzgg/ygk.htm",
        "selector": ".text-list ul li a",
        "keywords": ["调剂", "接收", "名额", "复试", "复核", "初试"]
    },
    {
        "school_name": "电子科大信软院",
        "url": "https://sise.uestc.edu.cn/xwtz/tzgg/ygk.htm",
        "selector": ".list-content > a",
        "keywords": ["调剂", "接收", "名额", "复试", "复核", "初试"]
    },
    {
        "school_name": "电子科大智能院",
        "url": "https://icct.uestc.edu.cn/xwzx/tzgg.htm",
        "selector": ".listtext_tit a",
        "keywords": ["调剂", "接收", "名额", "复试", "复核", "初试"]
    },
    {
        "school_name": "电子科大深研院",
        "url": "https://sias.uestc.edu.cn/rcpy/yanjzs.htm",
        "selector": ".lm_list ul li a",
        "keywords": ["调剂", "接收", "名额", "复试", "复核", "初试"]
    },
    {
        "school_name": "北京交通",
        "url": "https://yzb.bjtu.edu.cn/tzgg/index.htm",
        "selector": ".list01 li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京交通软学院",
        "url": "https://sse.bjtu.edu.cn/cms/item/?cat=108&page=1",
        "selector": ".second_R_list li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京交通计学院",
        "url": "https://cs.bjtu.edu.cn/tzgg/index.htm",
        "selector": ".list01 li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京理工",
        "url": "https://grd.bit.edu.cn/zsgz/zsxx/index.htm",
        "selector": ".block-list.list-unstyled.gp-f16 li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京理工计学院",
        "url": "https://cs.bit.edu.cn/tzgg/index.htm",
        "selector": ".sub_054.ul-inline.sub_054_2 li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京理工网安院",
        "url": "https://cst.bit.edu.cn/zsjy/yjszs/index.htm",
        "selector": ".sub_list003.ul-inline.effect.effect2.isView li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京理工人智院",
        "url": "https://ai.bit.edu.cn/tzgg/index.htm",
        "selector": ".sub_01 ul li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北邮",
        "url": "https://yzb.bupt.edu.cn/tzgg.htm",
        "selector": ".tzgg ul li",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "南开计网院",
        "url": "https://cc.nankai.edu.cn/13297/list.htm",
        "selector": "table tr[onclick]",  # 完美避开没有 onclick 的表头(<th>)
        "keywords": ["调剂", "接收", "名额", "复试", "初试"]
    }
]

# ================= 核心逻辑 =================
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

def send_qq_msg(message):
    api_url = f"http://{SERVER_IP}:{LANGBOT_PORT}/send_private_msg"
    payload = {"user_id": TARGET_QQ, "message": message}
    
    # 🟢 新增请求头：拿着 Token 去敲门
    headers = {
        "Authorization": f"Bearer {NAPCAT_TOKEN}"
    }
    
    try:
        # 🟢 注意：这里加了 headers=headers
        resp = requests.post(api_url, json=payload, headers=headers, timeout=5)
        if resp.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] QQ 消息推送成功！")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 推送失败，状态码: {resp.status_code}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 推送网络异常: {e}")

def check_updates(page):
    current_state = load_state()
    state_changed = False

    for target in TARGETS:
        school = target["school_name"]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在深度扫描 {school} ...")

        if school not in current_state:
            current_state[school] = []
        elif isinstance(current_state[school], str):
            current_state[school] = [current_state[school]]

        try:
            # 使用 DrissionPage 访问页面
            page.get(target["url"])
            
            # 强制等待 3 秒，让你的真实浏览器完成所有验证码和盾的渲染
            time.sleep(3) 
            
            # 获取页面源码
            html_content = page.html
            soup = BeautifulSoup(html_content, 'html.parser')

            # ... 前面保持不变 ...
            elements = soup.select(target["selector"])[:5]
            if not elements:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {school} 选择器未匹配。(HTTP 状态码: {resp.status_code})")
                continue

            for elem in reversed(elements):
                href = ""
                title = ""

                # 【逻辑分支 1】传统的 <a> 标签模式（兼容之前的学校）
                a_tag = elem if elem.name == 'a' else elem.find('a')
                if a_tag:
                    href = a_tag.get('href', '')
                    title = a_tag.get('title') or a_tag.get_text(strip=True)
                
                # 【逻辑分支 2】南开大学特供：隐藏在 tr onclick 里的链接模式
                elif elem.name == 'tr' and elem.has_attr('onclick'):
                    import re
                    # 用正则把 window.location.href='' 里面的链接抠出来
                    match = re.search(r"window\.location\.href=['\"]([^'\"]+)['\"]", elem['onclick'])
                    if match:
                        href = match.group(1)
                    
                    # 优先找带有特定 class 的 td 提取标题，找不到就提取整行的文字
                    title_td = elem.find('td', class_='text-align-title')
                    if title_td:
                        title = title_td.get_text(strip=True)
                    else:
                        title = elem.get_text(strip=True)

                # 如果两个分支都没拿到数据，说明匹配到了奇怪的东西，跳过
                if not href and not title:
                    continue

                full_link = urljoin(target["url"], href)
                title = " ".join(title.split())

                if title and title not in current_state[school]:
            # ... 下面发送 QQ 消息的逻辑保持不变 ...
                    hit_keyword = any(kw in title for kw in target["keywords"])
                    if hit_keyword:
                        msg = f"🔔【{school} 本地监控更新】\n公告：{title}\n🔗 链接：{full_link}"
                        send_qq_msg(msg)
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 更新未命中: {title}")

                    current_state[school].append(title)
                    state_changed = True
        
            if len(current_state[school]) > 20:
                current_state[school] = current_state[school][-20:]

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 扫描异常: {e}")

    if state_changed:
        save_state(current_state)

if __name__ == "__main__":
    print("🚀 DrissionPage 真实浏览器接管模式启动...")
    send_qq_msg("✅ 监控脚本已启动，每 5 分钟检查一次，并每"+ str(HEARTBEAT_INTERVAL/60) + "分钟汇报一次状态。")
    # 启动接管真实 Chrome 浏览器
    # 运行这行代码时，你的电脑会自动打开一个 Chrome 浏览器窗口
    page = ChromiumPage() 
    
    last_heartbeat_time = time.time()
    
    while True:
        check_updates(page)
        
        current_time = time.time()
        if current_time - last_heartbeat_time >= HEARTBEAT_INTERVAL:
            send_qq_msg("【状态汇报】DrissionPage 监控正常运行中 🟢")
            last_heartbeat_time = current_time
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 扫描完成，等待 5 分钟后继续...")
        time.sleep(300)