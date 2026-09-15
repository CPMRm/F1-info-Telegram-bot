import os
import requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
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
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Telegram F1 訊息發送成功！")
    else:
        print(f"發送失敗：{response.status_code}, {response.text}")

def format_utc_to_tw(date_str, time_str):
    """輔助函式：將 UTC 日期與時間字串轉換為台灣時間格式"""
    if not date_str or not time_str:
        return "未定"
    utc_datetime_str = f"{date_str}T{time_str}"
    utc_dt = datetime.strptime(utc_datetime_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_dt = pytz.utc.localize(utc_dt)
    
    tw_tz = pytz.timezone("Asia/Taipei")
    tw_dt = utc_dt.astimezone(tw_tz)
    return tw_dt.strftime("%Y-%m-%d (%a) %H:%M")

def get_f1_driver_standings():
    """抓取最新 F1 車手積分榜 (Top 5)"""
    url = "https://api.jolpica.ca/ergast/f1/current/driverstandings.json"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return "⚠️ 無法取得積分榜資料"
        
        data = res.json()
        standings_lists = data['MRData']['StandingsTable']['StandingsLists']
        if not standings_lists:
            return "⚠️ 目前無積分榜資料"
            
        season = standings_lists[0]['season']
        round_num = standings_lists[0]['round']
        drivers = standings_lists[0]['DriverStandings'][:5] # 取前 5 名
        
        lines = [f"🏆 **{season} 賽季車手積分榜 (R{round_num} 售後更新)**\n"]
        for d in drivers:
            pos = d['position']
            name = f"{d['Driver']['givenName']} {d['Driver']['familyName']}"
            constructor = d['Constructors'][0]['name'] if d['Constructors'] else ''
            points = d['points']
            lines.append(f"`P{pos}` **{name}** ({constructor}) — **{points} PTS**")
            
        return "\n".join(lines)
    except Exception as e:
        return f"🚨 積分榜擷取失敗: {e}"

def get_next_race_schedule():
    """抓取下一場大獎賽完整時間表（含排位賽、衝刺賽，自動轉台灣時間）"""
    url = "https://api.jolpica.ca/ergast/f1/current/next.json"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return "⚠️ 無法取得下一場賽事資訊"
            
        data = res.json()
        races = data['MRData']['RaceTable']['Races']
        if not races:
            return "🏁 本賽季賽事已全部結束！"
            
        race = races[0]
        race_name = race['raceName']
        circuit_name = race['Circuit']['circuitName']
        locality = race['Circuit']['Location']['locality']
        country = race['Circuit']['Location']['country']
        
        # 1. 正賽時間
        race_tw_time = format_utc_to_tw(race.get('date'), race.get('time'))
        
        # 2. 排位賽時間
        qualifying = race.get('Qualifying', {})
        quali_tw_time = format_utc_to_tw(qualifying.get('date'), qualifying.get('time'))
        
        # 3. 衝刺賽時間 (若該站無衝刺賽則此欄位不存在)
        sprint = race.get('Sprint', {})
        sprint_tw_time = format_utc_to_tw(sprint.get('date'), sprint.get('time')) if sprint else None
        
        # 組裝時間表訊息
        schedule_lines = [
            f"📍 **下一站賽事：{race_name}**",
            f"🏛️ 賽道：{circuit_name} ({locality}, {country})\n",
            "⏱️ **賽程時間表 (台灣時間)：**"
        ]
        
        # 如果有衝刺賽，列出衝刺賽時間
        if sprint_tw_time:
            schedule_lines.append(f"⚡ 衝刺賽 (Sprint)：`{sprint_tw_time}`")
            
        schedule_lines.append(f"⏱️ 排位賽 (Quali)：`{quali_tw_time}`")
        schedule_lines.append(f"🔴 正賽 (Race)：`{race_tw_time}`")
        
        return "\n".join(schedule_lines)
    except Exception as e:
        return f"🚨 賽程擷取失敗: {e}"

def main():
    standings_text = get_f1_driver_standings()
    schedule_text = get_next_race_schedule()
    
    full_message = f"🏎️ **【F1 最新賽事與積分動態】**\n\n{standings_text}\n\n---\n\n{schedule_text}"
    send_telegram_message(full_message)

if __name__ == "__main__":
    main()
