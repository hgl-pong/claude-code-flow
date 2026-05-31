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
  RUNTIME_PART="${SEP}${DIM}rt:${RUNTIME_STATUS}${RUNTIME_PART}"
  [ -n "$SMOKE_STATUS" ] && RUNTIME_PART="${RUNTIME_PART} smoke:${SMOKE_STATUS}"
  [ "$CRASH_DETECTED" = "true" ] && RUNTIME_PART="${RUNTIME_PART} crash"
  [ "$HANG_DETECTED" = "true" ] && RUNTIME_PART="${RUNTIME_PART} hang"
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
  [ -n "$VIM_PART" ] && out="${out}${VIM_PART}"
  printf "%s" "$out"
}

printf "%s\n" "$(build_line1)${SEP}${DIM}claude-code-flow${R}"
