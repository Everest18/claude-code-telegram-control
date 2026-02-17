#!/usr/bin/env python3
"""
AgentRemote v3.0 Cloud Executor
Executes tasks using Claude API in GitHub Actions environment
"""

import os
import sys
import json
import subprocess
from anthropic import Anthropic

def execute_task():
    """Main task execution function"""
    
    # Get environment variables
    task_description = os.getenv('TASK_DESCRIPTION', 'No task description provided')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    greptile_key = os.getenv('GREPTILE_API_KEY')
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not anthropic_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    
    print(f"🚀 AgentRemote v3.0 Cloud Executor")
    print(f"📋 Task: {task_description}")
    print(f"🕐 Started: {subprocess.check_output(['date']).decode().strip()}")
    
    # Initialize Claude client
    client = Anthropic(api_key=anthropic_key)
    
    # Get repository context
    repo_files = subprocess.check_output(['find', '.', '-type', 'f', '-not', '-path', './.git/*', '-not', '-path', './node_modules/*']).decode()
    
    # Build system prompt
    system_prompt = f"""You are AgentRemote, an autonomous code execution agent running in GitHub Actions.

EXECUTION CONTEXT:
- Environment: GitHub Actions (Ubuntu latest)
- Working directory: Repository root
- Python: 3.11
- Available tools: git, bash, pip, npm
- Credentials available: GitHub token, Greptile API

YOUR TASK:
{task_description}

REPOSITORY FILES:
{repo_files[:5000]}

EXECUTION PHASES:
1. ANALYZE: Understand the task and plan approach
2. IMPLEMENT: Make necessary code changes
3. VERIFY: Run tests, Greptile audit if applicable
4. REPORT: Summarize what was done

RULES:
- Make atomic, focused changes
- Always test your changes
- Create meaningful commit messages
- If task needs clarification, state assumptions
- If Greptile audit fails (score <95), iterate until passing
- Output bash commands you'd run, prefixed with EXEC:

Output format:
ANALYSIS: [your analysis]
IMPLEMENTATION: [changes made]
VERIFICATION: [test results]
SUMMARY: [what was accomplished]
"""

    # Execute task with Claude
    print("\n🤖 Calling Claude Sonnet 4.5...")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=8000,
            temperature=0.3,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Execute this task: {task_description}"
                }
            ]
        )
        
        result = response.content[0].text
        print("\n" + "="*60)
        print(result)
        print("="*60)
        
        # Parse EXEC: commands and execute them
        has_changes = False
        for line in result.split('\n'):
            if line.startswith('EXEC:'):
                command = line[5:].strip()
                print(f"\n💻 Executing: {command}")
                try:
                    output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                    print(output.decode())
                    has_changes = True
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  Command failed: {e.output.decode()}")
        
        # Set outputs for GitHub Actions
        with open(os.getenv('GITHUB_OUTPUT', '/dev/stdout'), 'a') as f:
            f.write(f"result<<EOF\n{result}\nEOF\n")
            f.write(f"has_changes={'true' if has_changes else 'false'}\n")
        
        print(f"\n✅ Task completed successfully")
        print(f"🕐 Finished: {subprocess.check_output(['date']).decode().strip()}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        with open(os.getenv('GITHUB_OUTPUT', '/dev/stdout'), 'a') as f:
            f.write(f"result=ERROR: {str(e)}\n")
            f.write(f"has_changes=false\n")
        return 1

if __name__ == "__main__":
    sys.exit(execute_task())
