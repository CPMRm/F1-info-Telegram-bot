import os
import requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ACTION_TYPE = os.getenv("ACTION_TYPE")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def send_telegram_message(message, show_buttons=True):
    """傳送訊息至 Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("錯誤：未設定 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    if show_buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": "🏎️ 查詢賽程資訊", "callback_data": "schedule"},
                    {"text": "🏆 查詢車手積分", "callback_data": "standings"}
                ]
            ]
        }
        
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print("Telegram 訊息發送成功！")
    else:
        print(f"發送失敗：{response.status_code}, {response.text}")

def format_utc_to_tw(iso_time_str):
    """將 ISO 時間字串轉換為台灣時間"""
    if not iso_time_str:
        return "未定"
    try:
        # 支援帶 Z 或帶偏移量的 ISO 時間
        iso_time_str = iso_time_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_time_str)
        tw_tz = pytz.timezone("Asia/Taipei")
        tw_dt = dt.astimezone(tw_tz)
        return tw_dt.strftime("%Y-%m-%d (%a) %H:%M")
    except Exception:
        return iso_time_str

def get_f1_driver_standings():
    """抓取最新 F1 車手積分榜 (Top 5)"""
    # 主要 API: F1-API Open Source
    url_primary = "https://raw.githubusercontent.com/f1db/f1db/main/src/data/standings/driver-standings.json"
    # 備用 API: Jolpica
    url_backup = "https://api.jolpi.ca/ergast/f1/current/driverstandings.json"
    
    # 嘗試預設與備用源
    try:
        # 先嘗試 Jolpica (若能連通資料最即時)
        res = requests.get(url_backup, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            standings_lists = data['MRData']['StandingsTable']['StandingsLists'][0]
            season = standings_lists['season']
            round_num = standings_lists['round']
            drivers = standings_lists['DriverStandings'][:5]
            
            lines = [f"🏆 **{season} 賽季車手積分榜 (R{round_num} 售後更新)**\n"]
            for d in drivers:
                pos = d['position']
                name = f"{d['Driver']['givenName']} {d['Driver']['familyName']}"
                constructor = d['Constructors'][0]['name'] if d['Constructors'] else ''
                points = d['points']
                lines.append(f"`P{pos}` **{name}** ({constructor}) — **{points} PTS**")
            return "\n".join(lines)
    except Exception as e:
        print(f"備用 API 無法連線，切換方案: {e}")

    # 若上述失敗，切換至 OpenF1 的 meeting 資料
    try:
        url_openf1 = "https://api.openf1.org/v1/position?session_key=latest"
        res = requests.get(url_openf1, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            return "🏆 **最新 F1 賽程與車手資料已同步，請手動確認最新賽事資訊！**"
    except Exception as e:
        pass
        
    return "⚠️ 暫時無法取得積分榜資料，請稍後再試。"

def get_next_race_schedule():
    """抓取下一場大獎賽賽程時間（自動轉台灣時間）"""
    # OpenF1 最新賽事 Endpoint
    url = "https://api.openf1.org/v1/meetings?year=2026"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            meetings = res.json()
            now_utc = datetime.now(pytz.utc)
            
            next_meeting = None
            for m in meetings:
                start_str = m.get("date_start")
                if start_str:
                    m_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if m_date > now_utc:
                        next_meeting = m
                        break
            
            if next_meeting:
                race_name = next_meeting.get("meeting_official_name") or next_meeting.get("meeting_name")
                location = f"{next_meeting.get('location')}, {next_meeting.get('country_name')}"
                start_tw = format_utc_to_tw(next_meeting.get("date_start"))
                
                schedule_lines = [
                    f"📍 **下一站賽事：{race_name}**",
                    f"🏛️ 地點：{location}\n",
                    "⏱️ **賽程時間表 (台灣時間)：**",
                    f"🔴 賽事週開跑時間：`{start_tw}`"
                ]
                return "\n".join(schedule_lines)
    except Exception as e:
        print(f"OpenF1 讀取失敗: {e}")

    # Fallback 到舊版 API
    try:
        url_backup = "https://api.jolpi.ca/ergast/f1/current/next.json"
        res = requests.get(url_backup, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            race = res.json()['MRData']['RaceTable']['Races'][0]
            race_name = race['raceName']
            circuit_name = race['Circuit']['circuitName']
            
            utc_datetime_str = f"{race['date']}T{race['time']}"
            tw_time = format_utc_to_tw(utc_datetime_str)
            
            return f"📍 **下一站賽事：{race_name}**\n🏛️ 賽道：{circuit_name}\n🔴 正賽 (台灣時間)：`{tw_time}`"
    except Exception as e:
        pass

    return "⚠️ 暫時無法取得賽程資料，請稍後再試。"

def main():
    if ACTION_TYPE == "schedule":
        message = get_next_race_schedule()
    elif ACTION_TYPE == "standings":
        message = get_f1_driver_standings()
    else:
        standings_text = get_f1_driver_standings()
        schedule_text = get_next_race_schedule()
        message = f"🏎️ **【F1 最新賽事與積分動態】**\n\n{standings_text}\n\n---\n\n{schedule_text}"
    
    send_telegram_message(message, show_buttons=True)

if __name__ == "__main__":
    main()
