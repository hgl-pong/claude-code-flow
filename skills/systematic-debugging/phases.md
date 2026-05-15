# Debugging Phases Reference

## Phase 1: Root Cause Investigation

1. **Read error messages carefully** — Don't skip past errors. They often contain the exact solution. Read stack traces completely. Note line numbers, file paths, error codes.
2. **Reproduce consistently** — Can you trigger it reliably? What are the exact steps? If not reproducible: gather more data, don't guess.
3. **Check recent changes** — `git diff`, recent commits, new dependencies, config changes.
4. **Gather evidence in multi-component systems** — For each component boundary: log what enters, what exits, verify config propagation. Run once to gather evidence showing WHERE it breaks, then investigate that specific component.
5. **Trace data flow** — Where does the bad value originate? What called this with the bad value? Keep tracing up until you find the source.

## Phase 2: Pattern Analysis

1. **Find working examples** — Locate similar working code in the same codebase.
2. **Compare against references** — If implementing a pattern, read the reference completely. Don't skim.
3. **Identify differences** — What's different between working and broken? List every difference.
4. **Understand dependencies** — What other components, settings, config, environment does this need?

## Phase 3: Hypothesis and Testing

1. **Form single hypothesis** — "I think X is the root cause because Y." Be specific.
2. **Test minimally** — Smallest possible change to test hypothesis. One variable at a time.
3. **Verify before continuing** — Did it work? Yes → Phase 4. Didn't work? Form NEW hypothesis. Don't add more fixes on top.

## Phase 4: Implementation

1. **Create failing test** — Use `testing-strategy` (RED). Simplest possible reproduction.
2. **Implement single fix** — Address the root cause. One change. No "while I'm here" improvements.
3. **Verify fix** — Test passes? No regressions? Issue actually resolved?
4. **If fix doesn't work** — If < 3 failed fixes: return to Phase 1. If >= 3: **STOP and question the architecture**.

### 3+ Fixes Failed: Question Architecture

If each fix reveals new problems in different places, or fixes require massive refactoring — this is a wrong architecture, not a wrong fix. Discuss with the user before attempting more.

## Capability Tiers

**Standalone** (always works):
- Reproduce, localize, prove, fix, verify with project's test runner

**Enhanced** (with connected tools):
- + GitNexus: `gitnexus_query` to find execution flows, `gitnexus_context` on suspect symbols, `gitnexus_impact` on fix targets
- + IDE MCP: breakpoints, call stacks, watch variables
