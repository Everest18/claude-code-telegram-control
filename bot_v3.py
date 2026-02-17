#!/usr/bin/env python3
"""
AgentRemote v3.0 - Telegram Bot with Dual-Mode Execution
Supports both LOCAL (Claude Code desktop) and CLOUD (GitHub Actions) execution
"""

import os
import sys
import psutil
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_PAT', os.getenv('GITHUB_TOKEN'))
GITHUB_REPO = "Everest18/claude-code-telegram-control"

# Execution mode state (per user)
user_execution_mode = {}  # chat_id -> "local" or "cloud"

def detect_execution_mode():
    """Auto-detect if Claude Code is running locally"""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'claude' in cmdline.lower() or 'code' in proc.info['name'].lower():
                return "local"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return "cloud"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    mode = detect_execution_mode()
    await update.message.reply_text(
        f"""🤖 *AgentRemote v3.0*

I can execute development tasks for you!

*Current Mode:* {mode.upper()}
• LOCAL: Claude Code on your desktop
• CLOUD: GitHub Actions (serverless)

*Commands:*
/task [description] - Execute a task
/cloud - Switch to cloud mode
/local - Switch to local mode  
/auto - Auto-detect mode
/status - Check execution mode

*Example:*
`/task Fix BECA scraper regex issue from GitHub Issue #47`
""",
        parse_mode="Markdown"
    )

async def task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /task command"""
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a task description.\n\n"
            "Example: `/task Fix bug in scraper.py`",
            parse_mode="Markdown"
        )
        return
    
    task_description = ' '.join(context.args)
    
    # Get execution mode
    mode = user_execution_mode.get(chat_id, detect_execution_mode())
    
    await update.message.reply_text(
        f"🚀 *Task Queued*\n\n"
        f"*Mode:* {mode.upper()}\n"
        f"*Task:* {task_description}\n\n"
        f"⏳ Executing...",
        parse_mode="Markdown"
    )
    
    if mode == "cloud":
        # Trigger GitHub Actions
        success = await trigger_github_actions(chat_id, task_description, update.message.message_id)
        if success:
            await update.message.reply_text(
                "☁️ Cloud execution triggered via GitHub Actions.\n"
                "You'll receive a notification when complete."
            )
        else:
            await update.message.reply_text(
                "❌ Failed to trigger cloud execution.\n"
                "Check GitHub token and repository settings."
            )
    else:
        # Local execution via Claude Code
        success = await trigger_local_execution(task_description)
        if success:
            await update.message.reply_text(
                "💻 Task sent to local Claude Code.\n"
                "Check terminal for execution status."
            )
        else:
            await update.message.reply_text(
                "❌ Local execution failed.\n"
                "Is Claude Code running? Try /cloud mode."
            )

async def trigger_github_actions(chat_id, task_description, message_id):
    """Trigger GitHub Actions via repository_dispatch"""
    if not GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN not set")
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "event_type": "execute-task",
        "client_payload": {
            "task": task_description,
            "chat_id": str(chat_id),
            "message_id": str(message_id)
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 204:
            print(f"✅ GitHub Actions triggered for: {task_description}")
            return True
        else:
            print(f"❌ GitHub API error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error triggering GitHub Actions: {e}")
        return False

async def trigger_local_execution(task_description):
    """Trigger local Claude Code execution"""
    task_file = os.path.expanduser("~/claude_code_tasks/pending_task.txt")
    
    try:
        os.makedirs(os.path.dirname(task_file), exist_ok=True)
        with open(task_file, 'w') as f:
            f.write(task_description)
        print(f"✅ Task written to: {task_file}")
        return True
    except Exception as e:
        print(f"❌ Error writing task file: {e}")
        return False

async def cloud_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch to cloud execution mode"""
    chat_id = update.effective_chat.id
    user_execution_mode[chat_id] = "cloud"
    await update.message.reply_text(
        "☁️ *Switched to CLOUD mode*\n\n"
        "Tasks will execute via GitHub Actions.\n"
        "Works even when your desktop is offline!",
        parse_mode="Markdown"
    )

async def local_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch to local execution mode"""
    chat_id = update.effective_chat.id
    user_execution_mode[chat_id] = "local"
    await update.message.reply_text(
        "💻 *Switched to LOCAL mode*\n\n"
        "Tasks will execute via Claude Code on your desktop.\n"
        "Faster execution but requires desktop to be running.",
        parse_mode="Markdown"
    )

async def auto_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-detect execution mode"""
    chat_id = update.effective_chat.id
    mode = detect_execution_mode()
    user_execution_mode[chat_id] = mode
    await update.message.reply_text(
        f"🔄 *Auto-detect enabled*\n\n"
        f"Detected mode: {mode.upper()}\n\n"
        f"I'll automatically choose the best execution method.",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current execution mode and system status"""
    chat_id = update.effective_chat.id
    current_mode = user_execution_mode.get(chat_id, "auto")
    detected_mode = detect_execution_mode()
    
    # Check GitHub Actions availability
    github_available = bool(GITHUB_TOKEN)
    
    # Check local Claude Code
    local_available = detected_mode == "local"
    
    status_msg = f"""📊 *AgentRemote Status*

*Current Setting:* {current_mode.upper()}
*Auto-Detected Mode:* {detected_mode.upper()}

*Availability:*
• Local Claude Code: {'✅ Running' if local_available else '❌ Offline'}
• GitHub Actions: {'✅ Configured' if github_available else '❌ Not configured'}

*Active Mode:* {user_execution_mode.get(chat_id, detected_mode).upper()}
"""
    
    await update.message.reply_text(status_msg, parse_mode="Markdown")

def main():
    """Main bot entry point"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    
    print("🤖 AgentRemote v3.0 starting...")
    print(f"📡 Execution mode: {detect_execution_mode().upper()}")
    
    # Create application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("task", task_command))
    app.add_handler(CommandHandler("cloud", cloud_mode))
    app.add_handler(CommandHandler("local", local_mode))
    app.add_handler(CommandHandler("auto", auto_mode))
    app.add_handler(CommandHandler("status", status_command))
    
    # Start bot
    print("✅ AgentRemote v3.0 is running!")
    print("💬 Send /start in Telegram to begin")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
