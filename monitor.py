import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime
from urllib.parse import urljoin

# ================= 配置区 =================

TARGET_QQ = 2161879699  # 请修改为你的 QQ 号
LANGBOT_PORT = 3000    # NapCatQQ HTTP 端口
STATE_FILE = "monitor_state.json"
HEARTBEAT_INTERVAL = 1800 

TARGETS = [
{
        "school_name": "哈工大",
        "url": "https://yzb.hit.edu.cn/8822/list.htm",
        "selector": ".news_title a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "电子科大",
        "url": "https://yz.uestc.edu.cn/sszs/tzgg.htm",
        "selector": ".main-text-list ul li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京交通",
        "url": "https://yzb.bjtu.edu.cn/tzgg/index.htm",
        "selector": ".list01 li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    {
        "school_name": "北京理工",
        "url": "https://grd.bit.edu.cn/zsgz/zsxx/index.htm",
        "selector": ".block-list.list-unstyled.gp-f16 li a",
        "keywords": ["调剂", "接收", "名额", "复试"]
    },
    # {
    #     "school_name": "北邮",
    #     "url": "https://yzb.bupt.edu.cn/tzgg.htm",
    #     "selector": ".tzgg ul li",
    #     "keywords": ["调剂", "接收", "名额", "复试"]
    # }
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
    api_url = f"http://127.0.0.1:{LANGBOT_PORT}/send_private_msg"
    payload = {"user_id": TARGET_QQ, "message": message}
    try:
        resp = requests.post(api_url, json=payload, timeout=5)
        if resp.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 消息推送成功！")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 推送发生异常: {e}")

def check_updates():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    current_state = load_state()
    state_changed = False

    with requests.Session() as session:
        for target in TARGETS:
            school = target["school_name"]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在深度扫描 {school} 前5条公告...")

            # 【数据结构升级】兼容旧版的单字符串状态，转换为列表集合
            if school not in current_state:
                current_state[school] = []
            elif isinstance(current_state[school], str):
                current_state[school] = [current_state[school]]

            try:
                resp = session.get(target["url"], headers=headers, timeout=10)
                resp.encoding = resp.apparent_encoding 
                soup = BeautifulSoup(resp.text, 'html.parser')

                # 【核心修改】用 select 抓取所有匹配元素，并切片取前 5 个
                elements = soup.select(target["selector"])[:5]
                if not elements:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {school} 选择器未匹配。(HTTP 状态码: {resp.status_code})")
                    continue

                # 倒序遍历（reversed），这样如果学校连发两条，我们会先处理较早的那条，符合人类阅读习惯
                for elem in reversed(elements):
                    a_tag = elem if elem.name == 'a' else elem.find('a')
                    if not a_tag:
                        continue

                    href = a_tag.get('href', '')
                    full_link = urljoin(target["url"], href)
                    
                    title = a_tag.get('title') or a_tag.get_text(strip=True)
                    title = " ".join(title.split())

                    # 判断这条公告是否在已读列表中
                    if title and title not in current_state[school]:
                        hit_keyword = any(kw in title for kw in target["keywords"])
                        if hit_keyword:
                            msg = f"🔔【{school} 研招网更新】\n命中关键词公告：\n{title}\n🔗 链接：\n{full_link}"
                            send_qq_msg(msg)
                        else:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {school} 有更新，未命中调剂关键词: {title}")

                        # 将新公告加入集合
                        current_state[school].append(title)
                        state_changed = True
                
                # 防止集合无限增大，每个学校最多保留最近的 20 条记录防重
                if len(current_state[school]) > 20:
                    current_state[school] = current_state[school][-20:]

            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查 {school} 时发生网络错误: {e}")

    if state_changed:
        save_state(current_state)

if __name__ == "__main__":
    print("🚀 研招网调剂监控脚本已启动...")
    send_qq_msg("✅ 监控脚本已启动，每 5 分钟检查一次，并每 30 分钟汇报一次状态。")
    last_heartbeat_time = time.time()
    
    while True:
        check_updates()
        
        current_time = time.time()
        if current_time - last_heartbeat_time >= HEARTBEAT_INTERVAL:
            current_state = load_state()
            msg_lines = ["【状态测试】监控正常运行中 🟢"]
            for target in TARGETS:
                school = target["school_name"]
                
                # 获取该学校的最新一条标题（列表的最后一个元素）
                school_history = current_state.get(school, [])
                if isinstance(school_history, str):  # 兼容没来得及转化的旧数据
                    latest_title = school_history
                else:
                    latest_title = school_history[-1] if school_history else "暂无数据"
                    
                msg_lines.append(f"[{school}]：{latest_title[:25]}...")
            
            msg_lines.append("👉 过去30分钟未找到新的调剂通知。")
            send_qq_msg("\n".join(msg_lines))
            last_heartbeat_time = current_time
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 已发送状态汇报。")
        
        time.sleep(300)