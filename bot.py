#!/usr/bin/env python3
"""
Claude Code Telegram Control Bot

A production-grade Telegram bot for remote control and monitoring of Claude Code sessions.
Enables mobile-first AI development workflow with instant notifications and approval management.

Author: Ariel Shapira
License: MIT
Repository: https://github.com/Everest18/claude-code-telegram-control
"""

import os
import sys
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration - ALL paths MUST be set via environment variables
TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USER_ID: Optional[str] = os.getenv('TELEGRAM_USER_ID')

# File paths - NO DEFAULTS, must be explicitly configured
STATUS_FILE = Path(os.getenv('CLAUDE_STATUS_FILE', ''))
APPROVAL_FILE = Path(os.getenv('CLAUDE_APPROVAL_FILE', ''))
RESPONSE_FILE = Path(os.getenv('CLAUDE_RESPONSE_FILE', ''))
TASKS_DIR = Path(os.getenv('CLAUDE_TASKS_DIR', ''))

# Security constants
MAX_TASK_DESCRIPTION_LENGTH = 500
ALLOWED_TASK_CHARS = re.compile(r'^[a-zA-Z0-9\s\-_.,!?]+$')


def validate_configuration() -> None:
    """
    Validate all required configuration is present.
    Fails fast if security-critical config is missing.
    """
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN not set")
    
    # SECURITY FIX #1: Fail closed - require user ID
    if not AUTHORIZED_USER_ID:
        errors.append("TELEGRAM_USER_ID not set - bot would be open to ALL users!")
    
    # SECURITY FIX #3: No default paths - all must be explicitly configured
    if not STATUS_FILE or str(STATUS_FILE) == '.':
        errors.append("CLAUDE_STATUS_FILE not set")
    if not APPROVAL_FILE or str(APPROVAL_FILE) == '.':
        errors.append("CLAUDE_APPROVAL_FILE not set")
    if not RESPONSE_FILE or str(RESPONSE_FILE) == '.':
        errors.append("CLAUDE_RESPONSE_FILE not set")
    if not TASKS_DIR or str(TASKS_DIR) == '.':
        errors.append("CLAUDE_TASKS_DIR not set")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        logger.error("\nPlease set all required environment variables in .env file")
        sys.exit(1)


def is_authorized(user_id: int) -> bool:
    """
    Check if user is authorized to use the bot.
    SECURITY FIX #1: No fallback to open access.
    """
    return str(user_id) == AUTHORIZED_USER_ID


def sanitize_task_description(description: str) -> str:
    """
    SECURITY FIX #4 & #5: Sanitize user input for task descriptions.
    
    Prevents:
    - Path traversal attacks
    - Content injection
    - Malicious characters
    
    Args:
        description: Raw user input
        
    Returns:
        Sanitized description
        
    Raises:
        ValueError: If input contains forbidden characters
    """
    # Remove leading/trailing whitespace
    description = description.strip()
    
    # Check length
    if len(description) > MAX_TASK_DESCRIPTION_LENGTH:
        raise ValueError(f"Description too long (max {MAX_TASK_DESCRIPTION_LENGTH} chars)")
    
    # Check for allowed characters only
    if not ALLOWED_TASK_CHARS.match(description):
        raise ValueError("Description contains forbidden characters")
    
    # Additional check: no path separators
    if '/' in description or '\\' in description or '..' in description:
        raise ValueError("Path separators not allowed in description")
    
    return description


def safe_error_message(error: Exception) -> str:
    """
    SECURITY FIX #6: Convert exception to safe user-facing message.
    
    Logs full error internally but only returns generic message to user.
    Prevents information disclosure.
    """
    logger.error(f"Error occurred: {type(error).__name__}: {str(error)}", exc_info=True)
    return "An error occurred. Please try again or contact support."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not is_authorized(update.effective_user.id):
        logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    await update.message.reply_text(
        "✅ **Claude Code Remote Control**\n\n"
        "/task <desc> - Create task\n"
        "/status - Current status\n"
        "/approve - Approve action\n"
        "/reject - Reject action\n"
        "/ping - Test bot"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ping command."""
    if not is_authorized(update.effective_user.id):
        return
    await update.message.reply_text("🏓 Pong!")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /status command.
    SECURITY FIX #2: Removed PowerShell subprocess call.
    """
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        status_msg = "📊 **Claude Code Status**\n\n"
        
        # Read status from file only (safer than subprocess)
        if STATUS_FILE.exists():
            status_msg += STATUS_FILE.read_text(encoding='utf-8')
        else:
            status_msg += "⚪ No status file found"
        
        if APPROVAL_FILE.exists():
            status_msg += "\n\n🚨 **APPROVAL PENDING**"
        
        await update.message.reply_text(status_msg)
    except Exception as e:
        await update.message.reply_text(safe_error_message(e))


async def create_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /task command with input validation.
    SECURITY FIXES #4 & #5: Input sanitization and validation.
    """
    if not is_authorized(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/task <description>`")
        return
    
    try:
        raw_description = ' '.join(context.args)
        
        # SECURITY FIX #5: Sanitize input
        description = sanitize_task_description(raw_description)
        
        # Create tasks directory if needed
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        
        # SECURITY FIX #4: Use timestamp-based filename (no user input in filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        task_file = TASKS_DIR / f"telegram_{timestamp}.md"
        
        # Create task file content (sanitized description only)
        task_content = f"""# Task from Telegram

**Created:** {datetime.now().isoformat()}
**Status:** pending

## Description
{description}

## Instructions
Execute autonomously. Report progress to status file.
"""
        
        task_file.write_text(task_content, encoding='utf-8')
        
        # Update status file
        STATUS_FILE.write_text(
            f"""🟢 New Task

Task: {description}
Started: {datetime.now().strftime('%I:%M %p')}
File: {task_file.name}
""",
            encoding='utf-8'
        )
        
        await update.message.reply_text(
            f"✅ Task Created\n\n{description}\n\n`{task_file.name}`"
        )
        logger.info(f"Task created: {description} ({task_file.name})")
        
    except ValueError as e:
        # Input validation error - safe to show
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        # SECURITY FIX #6: Generic error message
        await update.message.reply_text(safe_error_message(e))


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /approve command."""
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        if not APPROVAL_FILE.exists():
            await update.message.reply_text("✅ No pending approvals")
            return
        
        RESPONSE_FILE.write_text("APPROVED", encoding='utf-8')
        APPROVAL_FILE.unlink()
        
        await update.message.reply_text("✅ APPROVED - Claude Code will continue")
        logger.info(f"Approval granted by user {update.effective_user.id}")
        
    except Exception as e:
        await update.message.reply_text(safe_error_message(e))


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reject command."""
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        if not APPROVAL_FILE.exists():
            await update.message.reply_text("✅ No pending approvals")
            return
        
        RESPONSE_FILE.write_text("REJECTED", encoding='utf-8')
        APPROVAL_FILE.unlink()
        
        await update.message.reply_text("❌ REJECTED - Claude Code will stop")
        logger.info(f"Approval rejected by user {update.effective_user.id}")
        
    except Exception as e:
        await update.message.reply_text(safe_error_message(e))


def main() -> None:
    """Main entry point with security validation."""
    # SECURITY FIX #1: Validate configuration before starting
    validate_configuration()
    
    logger.info("🤖 Claude Code Telegram Control Bot starting...")
    logger.info(f"Authorized user: {AUTHORIZED_USER_ID}")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("task", create_task))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("reject", reject))
    
    logger.info("✅ Bot started and listening for commands")
    
    # Start bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
