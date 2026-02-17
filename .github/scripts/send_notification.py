#!/usr/bin/env python3
"""
Send Telegram notification after task completion
"""

import os
import requests
import json

def send_notification():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    task_status = os.getenv('TASK_STATUS', 'unknown')
    task_result = os.getenv('TASK_RESULT', 'No result available')
    
    if not bot_token or not chat_id:
        print("⚠️  Missing Telegram credentials, skipping notification")
        return
    
    # Format message
    status_emoji = "✅" if task_status == "success" else "❌"
    message = f"""{status_emoji} *AgentRemote Cloud Execution Complete*

*Status:* {task_status.upper()}

*Result:*
```
{task_result[:3000]}
```

_Executed via GitHub Actions_
"""
    
    # Send to Telegram
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram notification sent successfully")
        else:
            print(f"⚠️  Telegram notification failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error sending notification: {e}")

if __name__ == "__main__":
    send_notification()
