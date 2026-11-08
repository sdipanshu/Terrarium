#!/usr/bin/env bash
# Restart the glm/qwen re-run sweeper once the glm/qwen B batch has exited (keeps load under the rate limit).
cd /c/Users/dipan/Terrarium/experiments/deadline_swarm
while [ "$(powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'run_batch_b\.py' -and \$_.CommandLine -notmatch '--one' }).Count" | tr -d '\r')" != "0" ]; do sleep 120; done
echo "$(date +%T) B batch done; starting sweeper" >> outputs/rerun_sweeper.log
PYTHONPATH="C:/Users/dipan/Terrarium" /c/Users/dipan/Documents/Codex/2026-10-25/referenced-chatgpt-conversation-this-is-an/work/research-env/Scripts/python.exe -W ignore -u rerun_sweeper.py --models glm-5.2,qwen3.5-397b >> outputs/rerun_sweeper.log 2>&1
