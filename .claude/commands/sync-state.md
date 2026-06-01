# /sync-state — Update STATE.md to reflect current project state

Sync chimera/STATE.md after completing a module or significant milestone.

## Steps

1. **Gather current state** — run these read-only commands:
   - `git log --oneline -5` → recent commits
   - `chimera/.venv/bin/pytest chimera/tests -q --co 2>&1 | tail -3` → total test count
   - `ls chimera/core/*.py | grep -v __ | wc -l` → module file count
   - `cat chimera/STATE.md` → current content

2. **Determine diff** — compare what changed:
   - Which modules moved from scaffold → done?
   - What's the new total test count?
   - What was the last commit hash?
   - Has the "Last completed" changed?

3. **Show planned diff before applying** — display the exact lines to change.

4. **Wait for operator approval** ("+" or explicit "go ahead").

5. **Apply changes**:
   - Edit chimera/STATE.md
   - Update: modules done count, test count, last completed, scaffold list
   - Keep date as `Updated: YYYY-MM-DD` (current date if needed)

6. **Propose commit message** in this format:
   docs(chimera): update STATE.md — <module> done, X/8 core modules
   
   Sync after Step 2.<N> (<module> green). Code status now reflects the
   <ordinal> implemented core module and the updated test count.
   
   - chimera/core/: X of 8 done — added <module> (§<section>, <hash>) to
     the list; remaining scaffold drops to <Y> (<list>)
   - Last completed bumped <prev> → <module>
   - Tests: <prev> → <new> (+ <delta> <module>)
   
   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

7. **Wait for approval, then commit + push.**

## Important

- Don't change anything beyond the listed fields
- Don't update date if it's already today
- Show diff before applying — never blind-edit STATE.md
