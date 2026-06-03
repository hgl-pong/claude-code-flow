#!/bin/bash
# Claude Code Flow statusline
# Reads JSON from stdin (Claude Code passes session data on every refresh)
# Configure: "statusLine": { "type": "command", "command": "bash <path>" }

# statusline generates a compact session status bar from live Claude Code JSON on stdin.
# Works without any hook scripts — self-contained.
# Reads: stdin JSON → model, dir, ctx%, cost, rate limits, git, thinking, vim mode, agent info

# ANSI colors
R=$'\033[0m'
DIM=$'\033[2m'
RED=$'\033[31m'
GRN=$'\033[32m'
YEL=$'\033[33m'
BLU=$'\033[34m'
CYN=$'\033[36m'

SEP="${DIM} | ${R}"

# ── Read JSON from stdin (non-blocking if TTY) ────────────
INPUT=""
[ ! -t 0 ] && INPUT=$(cat)

# ── Parse JSON fields (jq preferred, python3 fallback) ───
MODEL=""; DIR="$(pwd)"; CTX_RAW=0; COST_USD=0
FIVE_H=""; WEEK=""; EFFORT=""; THINKING="false"
WORKTREE=""; AGENT_NAME=""; VIM_MODE=""; RUNTIME_STATUS=""; SMOKE_STATUS=""; CRASH_DETECTED="false"; HANG_DETECTED="false"; EVIDENCE_DIR=""

if [ -n "$INPUT" ]; then
  if command -v jq &>/dev/null; then
    _jq() { echo "$INPUT" | jq -r "$1 // empty" 2>/dev/null; }
    MODEL=$(_jq '.model.display_name')
    DIR=$(_jq '.workspace.current_dir')
    CTX_RAW=$(_jq '.context_window.used_percentage')
    COST_USD=$(_jq '.cost.total_cost_usd')
    FIVE_H=$(_jq '.rate_limits.five_hour.used_percentage')
    WEEK=$(_jq '.rate_limits.seven_day.used_percentage')
    EFFORT=$(_jq '.effort.level')
    THINKING=$(_jq '.thinking.enabled')
    WORKTREE=$(_jq '.workspace.git_worktree')
    AGENT_NAME=$(_jq '.agent.name')
    VIM_MODE=$(_jq '.vim.mode')
    RUNTIME_STATUS=$(_jq '.runtime_verification.status')
    SMOKE_STATUS=$(_jq '.runtime_verification.smoke')
    CRASH_DETECTED=$(_jq '.runtime_verification.crash_detected')
    HANG_DETECTED=$(_jq '.runtime_verification.hang_detected')
    EVIDENCE_DIR=$(_jq '.runtime_verification.evidence_dir')
    if [ -z "$RUNTIME_STATUS" ] && [ -f ".claude/auto/state.json" ]; then
      RUNTIME_STATUS=$(jq -r '.runtime_verification.status // empty' .claude/auto/state.json 2>/dev/null)
      SMOKE_STATUS=$(jq -r '.runtime_verification.smoke // empty' .claude/auto/state.json 2>/dev/null)
      CRASH_DETECTED=$(jq -r '.runtime_verification.crash_detected // false' .claude/auto/state.json 2>/dev/null)
      HANG_DETECTED=$(jq -r '.runtime_verification.hang_detected // false' .claude/auto/state.json 2>/dev/null)
      EVIDENCE_DIR=$(jq -r '.runtime_verification.evidence_dir // empty' .claude/auto/state.json 2>/dev/null)
    fi
  elif command -v python3 &>/dev/null; then
    eval "$(echo "$INPUT" | python3 -c "
import sys, json, shlex
try:
    d = json.load(sys.stdin)
    m  = d.get('model') or {}
    w  = d.get('workspace') or {}
    cw = d.get('context_window') or {}
    co = d.get('cost') or {}
    rl = d.get('rate_limits') or {}
    fh = (rl.get('five_hour') or {})
    sd = (rl.get('seven_day') or {})
    ef = (d.get('effort') or {})
    th = (d.get('thinking') or {})
    vi = (d.get('vim') or {})
    ag = (d.get('agent') or {})
    rv = (d.get('runtime_verification') or {})
    fh_p = fh.get('used_percentage')
    sd_p = sd.get('used_percentage')
    print('MODEL=' + shlex.quote(str(m.get('display_name') or '')))
    print('DIR='   + shlex.quote(str(w.get('current_dir') or '')))
    print('CTX_RAW=' + shlex.quote(str(int(cw.get('used_percentage') or 0))))
    print('COST_USD=' + shlex.quote(str(co.get('total_cost_usd') or 0)))
    print('FIVE_H=' + shlex.quote(str(int(fh_p)) if fh_p is not None else ''))
    print('WEEK='  + shlex.quote(str(int(sd_p)) if sd_p is not None else ''))
    print('EFFORT='   + shlex.quote(str(ef.get('level') or '')))
    print('THINKING=' + shlex.quote(str(th.get('enabled', False)).lower()))
    print('WORKTREE=' + shlex.quote(str(w.get('git_worktree') or '')))
    print('AGENT_NAME=' + shlex.quote(str(ag.get('name') or '')))
    print('VIM_MODE=' + shlex.quote(str(vi.get('mode') or '')))
    print('RUNTIME_STATUS=' + shlex.quote(str(rv.get('status') or '')))
    print('SMOKE_STATUS=' + shlex.quote(str(rv.get('smoke') or '')))
    print('CRASH_DETECTED=' + shlex.quote(str(rv.get('crash_detected', False)).lower()))
    print('HANG_DETECTED=' + shlex.quote(str(rv.get('hang_detected', False)).lower()))
    print('EVIDENCE_DIR=' + shlex.quote(str(rv.get('evidence_dir') or '')))
except Exception:
    pass
" 2>/dev/null)"
    if [ -z "$RUNTIME_STATUS" ] && [ -f ".claude/auto/state.json" ]; then
      RUNTIME_STATUS=$(jq -r '.runtime_verification.status // empty' .claude/auto/state.json 2>/dev/null)
      SMOKE_STATUS=$(jq -r '.runtime_verification.smoke // empty' .claude/auto/state.json 2>/dev/null)
      CRASH_DETECTED=$(jq -r '.runtime_verification.crash_detected // false' .claude/auto/state.json 2>/dev/null)
      HANG_DETECTED=$(jq -r '.runtime_verification.hang_detected // false' .claude/auto/state.json 2>/dev/null)
      EVIDENCE_DIR=$(jq -r '.runtime_verification.evidence_dir // empty' .claude/auto/state.json 2>/dev/null)
    fi
  fi
fi

# Directory basename
DIRNAME="${DIR##*/}"
[ -z "$DIRNAME" ] && DIRNAME="$(basename "$(pwd)")"

# ── Context bar ───────────────────────────────────────────
CTX_PCT=0
[[ "$CTX_RAW" =~ ^[0-9]+(\.[0-9]+)?$ ]] && CTX_PCT=${CTX_RAW%.*}

BAR_WIDTH=10
FILLED=$(( CTX_PCT * BAR_WIDTH / 100 ))
EMPTY=$(( BAR_WIDTH - FILLED ))
CTX_BAR=""
for ((i=0; i<FILLED; i++)); do CTX_BAR="${CTX_BAR}#"; done
for ((i=0; i<EMPTY; i++)); do CTX_BAR="${CTX_BAR}-"; done

if [ "$CTX_PCT" -ge 90 ]; then
  CTX_COLOR="$RED"
elif [ "$CTX_PCT" -ge 70 ]; then
  CTX_COLOR="$YEL"
else
  CTX_COLOR="$GRN"
fi

# ── Git info ──────────────────────────────────────────────
GIT_PART=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  [ -z "$BRANCH" ] && BRANCH="#$(git rev-parse --short HEAD 2>/dev/null)"

  AHEAD=0; BEHIND=0
  if git rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" &>/dev/null; then
    AHEAD=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo 0)
    BEHIND=$(git rev-list --count "HEAD..@{upstream}" 2>/dev/null || echo 0)
  fi

  DIRTY=""
  git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null || DIRTY="*"

  BRANCH_COLOR="$GRN"
  [ -n "$DIRTY" ] && BRANCH_COLOR="$YEL"
  [ "$BEHIND" -gt 0 ] && BRANCH_COLOR="$RED"

  GIT_PART="${BRANCH_COLOR}${BRANCH}${R}"
  [ -n "$DIRTY" ] && GIT_PART="${GIT_PART}${YEL}*${R}"
  [ "$AHEAD" -gt 0 ] && GIT_PART="${GIT_PART}${CYN}↑${AHEAD}${R}"
  [ "$BEHIND" -gt 0 ] && GIT_PART="${GIT_PART}${RED}↓${BEHIND}${R}"
  [ -n "$WORKTREE" ] && GIT_PART="${GIT_PART}${DIM}[${WORKTREE}]${R}"
fi

# ── Cost ──────────────────────────────────────────────────
COST_PART=""
if [[ "$COST_USD" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk "BEGIN {exit !($COST_USD > 0)}" 2>/dev/null; then
  COST_PART="$(printf '$%.3f' "$COST_USD")"
fi

# ── Rate limits ───────────────────────────────────────────
LIMITS=""
if [ -n "$FIVE_H" ]; then
  FH=$(printf '%.0f' "$FIVE_H" 2>/dev/null)
  if [ "${FH:-0}" -ge 80 ]; then C="$RED"; elif [ "${FH:-0}" -ge 60 ]; then C="$YEL"; else C=""; fi
  LIMITS="${C}5h:${FH}%${R}"
fi
if [ -n "$WEEK" ]; then
  WK=$(printf '%.0f' "$WEEK" 2>/dev/null)
  if [ "${WK:-0}" -ge 80 ]; then C="$RED"; elif [ "${WK:-0}" -ge 60 ]; then C="$YEL"; else C=""; fi
  [ -n "$LIMITS" ] && LIMITS="${LIMITS} "
  LIMITS="${LIMITS}${C}7d:${WK}%${R}"
fi

# ── Extras ────────────────────────────────────────────────
EFFORT_PART=""
case "$EFFORT" in
  xhigh|max) EFFORT_PART=" ${RED}${EFFORT}${R}" ;;
  high)      EFFORT_PART=" ${YEL}high${R}" ;;
  low)       EFFORT_PART=" ${DIM}low${R}" ;;
esac

THINK_PART=""
[ "$THINKING" = "true" ] && THINK_PART=" think"

VIM_PART=""
[ -n "$VIM_MODE" ] && VIM_PART="${SEP}${CYN}${VIM_MODE}${R}"

AGENT_PART=""
[ -n "$AGENT_NAME" ] && AGENT_PART="${SEP}${DIM}@${AGENT_NAME}${R}"

RUNTIME_PART=""
if [ -n "$RUNTIME_STATUS" ]; then
  RUNTIME_PART="${SEP}${DIM}rt:${RUNTIME_STATUS}"
  [ -n "$SMOKE_STATUS" ] && RUNTIME_PART="${RUNTIME_PART} smoke:${SMOKE_STATUS}"
  [ "$CRASH_DETECTED" = "true" ] && RUNTIME_PART="${RUNTIME_PART} crash"
  [ "$HANG_DETECTED" = "true" ] && RUNTIME_PART="${RUNTIME_PART} hang"
fi

# ── Auto-run discovery: scan .claude/auto/*/state.json ─────
AUTO_PART=""
_auto_is_error="false"

if [ -d ".claude/auto" ]; then
  # Use python3 to discover active state files (portable across jq/no-jq)
  if command -v python3 &>/dev/null; then
    _auto_result=$(python3 -c "
import json, os, sys, shlex
from pathlib import Path

ACTIVE = {'ACTIVE', 'PAUSED_COMPACTING', 'BLOCKED_ESCALATING', 'STOPPED_ASK_USER', 'RUNNING'}
auto_dir = Path('.claude/auto')
candidates = []
has_any = False
has_error = False

for sf in sorted(auto_dir.glob('*/state.json')):
    has_any = True
    try:
        data = json.loads(sf.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        has_error = True
        continue
    if not isinstance(data, dict):
        has_error = True
        continue
    if 'task_name' not in data or 'status' not in data or 'updated_at' not in data:
        continue
    status = data.get('status', '')
    if status not in ACTIVE:
        continue
    ts = data.get('updated_at', '')
    dirname = sf.parent.name
    candidates.append((ts, dirname, str(sf)))

# Sort by updated_at desc, dirname desc for tie-breaking
candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

# Pick the first valid one; if newest is corrupt, note error
chosen = None
for ts, dn, sf in candidates:
    try:
        data = json.loads(Path(sf).read_text(encoding='utf-8'))
        chosen = data
        break
    except Exception:
        has_error = True
        continue

if chosen:
    task = str(chosen.get('task_name', ''))[:20]
    status = str(chosen.get('status', ''))
    phase = str(chosen.get('phase', '') or (chosen.get('progress') or {}).get('phase', '') or 'unknown')
    prog = chosen.get('progress') or {}
    t_total = prog.get('tasks_total', 0)
    t_done = prog.get('tasks_completed', prog.get('tasks_passed', 0))
    gates = prog.get('gates_passed', 0)
    ts = chosen.get('task_states') or {}
    blocked = sum(1 for v in ts.values() if isinstance(v, dict) and v.get('status') == 'blocked')
    rv = chosen.get('runtime_verification') or {}
    rt = rv.get('status', '')
    smoke = rv.get('smoke', '')
    parts = [f'AUTO_TASK={shlex.quote(task)}']
    parts.append(f'AUTO_STATUS={shlex.quote(status)}')
    parts.append(f'AUTO_PHASE={shlex.quote(phase)}')
    parts.append(f'AUTO_TTOTAL={shlex.quote(str(t_total))}')
    parts.append(f'AUTO_TDONE={shlex.quote(str(t_done))}')
    parts.append(f'AUTO_GATES={shlex.quote(str(gates))}')
    parts.append(f'AUTO_BLOCKED={shlex.quote(str(blocked))}')
    parts.append(f'AUTO_RT={shlex.quote(str(rt))}')
    parts.append(f'AUTO_SMOKE={shlex.quote(str(smoke))}')
    sys.stdout.write('\n'.join(parts))
elif has_error and has_any:
    sys.stdout.write('AUTO_ERROR=1')
" 2>/dev/null | tr -d '\r')

    if [ -n "$_auto_result" ]; then
      # Parse the output
      _auto_task=""; _auto_status=""; _auto_phase=""
      _auto_ttotal="0"; _auto_tdone="0"; _auto_gates="0"; _auto_blocked="0"
      _auto_rt=""; _auto_smoke=""
      while IFS='=' read -r _key _val; do
        [ -z "$_key" ] && continue
        # Strip surrounding quotes from shlex.quote
        _val="${_val#\'}"; _val="${_val%\'}"
        case "$_key" in
          AUTO_TASK)     _auto_task="$_val" ;;
          AUTO_STATUS)   _auto_status="$_val" ;;
          AUTO_PHASE)    _auto_phase="$_val" ;;
          AUTO_TTOTAL)   _auto_ttotal="$_val" ;;
          AUTO_TDONE)    _auto_tdone="$_val" ;;
          AUTO_GATES)    _auto_gates="$_val" ;;
          AUTO_BLOCKED)  _auto_blocked="$_val" ;;
          AUTO_RT)       _auto_rt="$_val" ;;
          AUTO_SMOKE)    _auto_smoke="$_val" ;;
          AUTO_ERROR)    _auto_is_error="true" ;;
        esac
      done <<< "$_auto_result"

      if [ -n "$_auto_task" ]; then
        AUTO_PART="${SEP}${CYN}auto:${_auto_task}${R} ${DIM}${_auto_phase}/${_auto_status}${R} tasks:${_auto_tdone}/${_auto_ttotal} gates:${_auto_gates}/7 blocked:${_auto_blocked}"
        [ -n "$_auto_rt" ] && AUTO_PART="${AUTO_PART} rt:${_auto_rt}"
        [ -n "$_auto_smoke" ] && AUTO_PART="${AUTO_PART} smoke:${_auto_smoke}"
      fi
    fi
  fi

  # Reset error flag if we found a valid state
  [ -n "$AUTO_PART" ] && _auto_is_error="false"

  if [ "$_auto_is_error" = "true" ] && [ -z "$AUTO_PART" ]; then
    AUTO_PART="${SEP}${RED}auto:state-error${R}"
  fi
fi

# ── Build line ────────────────────────────────────────────
build_line1() {
  local out=""
  [ -n "$MODEL" ] && out="${BLU}${MODEL}${R}${EFFORT_PART}${THINK_PART}"
  [ -n "$DIRNAME" ] && out="${out:+$out }${GRN}${DIRNAME}${R}"
  [ -n "$GIT_PART" ] && out="${out}  ${GIT_PART}"
  out="${out}${SEP}${CTX_COLOR}${CTX_BAR}${R} ${CTX_PCT}%"
  [ -n "$COST_PART" ] && out="${out}${SEP}${DIM}${COST_PART}${R}"
  [ -n "$LIMITS" ] && out="${out}${SEP}${LIMITS}"
  [ -n "$AGENT_PART" ] && out="${out}${AGENT_PART}"
  [ -n "$RUNTIME_PART" ] && out="${out}${RUNTIME_PART}"
  [ -n "$AUTO_PART" ] && out="${out}${AUTO_PART}"
  [ -n "$VIM_PART" ] && out="${out}${VIM_PART}"
  printf "%s" "$out"
}

printf "%s\n" "$(build_line1)${SEP}${DIM}claude-code-flow${R}"
