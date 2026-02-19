# src/telegram_notifier.py
import os
import requests
from datetime import datetime

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message: str) -> bool:
        """텔레그램으로 메시지 전송"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram 전송 실패: {e}")
            return False
    
    def format_summary(self, summary_list: list) -> str:
        """분석 결과를 텔레그램 메시지로 포맷팅"""
        from config import settings
        
        today = datetime.now().strftime('%Y-%m-%d')
        lines = [f"📊 <b>Stock Analysis Report</b>", f"📅 {today}", ""]
        
        buy_signals = []
        watch_signals = []
        
        for item in summary_list:
            ticker = item['ticker']
            ticker_name = settings.TICKER_NAMES.get(ticker, ticker)
            current_price = item['current_price']
            
            # 매수가 계산
            buy_price_1 = current_price * (1 + item['s1'])
            buy_price_2 = current_price * (1 + item['s2'])
            buy_price_3 = current_price * (1 + item['s3'])
            
            # Signal 판단 (1σ 기준)
            is_buy = current_price <= buy_price_1
            signal = "🟢 매수" if is_buy else "⚪ 관망"
            
            line = (
                f"<b>{ticker}</b> ({ticker_name})\n"
                f"  현재가: ${current_price:.2f}({item['daily_change']*100:+.2f}%)\n"
                f"  1σ: ${buy_price_1:.2f} | 2σ: ${buy_price_2:.2f} | 3σ: ${buy_price_3:.2f}\n"
                f"  Signal: {signal}"
            )
            
            if is_buy:
                buy_signals.append(line)
            else:
                watch_signals.append(line)
        
        # 매수 신호 먼저 표시
        if buy_signals:
            lines.append("🚨 <b>매수 신호</b>")
            lines.extend(buy_signals)
            lines.append("")
        
        if watch_signals:
            lines.append("👀 <b>관망</b>")
            lines.extend(watch_signals)
        
        return "\n".join(lines)


def get_telegram_notifier():
    """환경변수에서 텔레그램 설정 로드"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        return TelegramNotifier(bot_token, chat_id)
    return None
