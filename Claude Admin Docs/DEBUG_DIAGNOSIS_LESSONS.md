# DEBUG_DIAGNOSIS_LESSONS — Why the Port Bug Took So Long and How to Fix That

## What Happened

A port selection feature was added via `sys.argv` in `run.py`. After a PR merge,
the feature appeared to be present (grep confirmed the code was there) but the
port always defaulted to 5000 regardless of the argument passed.

The root cause was a **silent overwrite**: a second `port = config.get("port", 5000)`
assignment existed lower in the file and ran after the `sys.argv` block, resetting
the port. Both assignments were present; the later one won at runtime.

**Time lost:** Most of the debugging session was spent on indirect evidence —
checking grep output, testing invocation syntax, considering environment issues —
rather than directly inspecting the file content the user was actually running.

---

## Why It Took So Long

### 1. Claude never verified what the user's file actually contained

Claude was working from server-side files (correct version) and assumed they matched
the user's local copy on GitHub main. They did not. Claude's grep results and the
user's grep results came from different versions of the file.

**The fix:** At the start of any debugging session involving a file, Claude should
immediately ask: *"Please show me the full contents of that file."* Not just a
search result — the whole thing.

### 2. Partial evidence was treated as confirmation

When the user's `Select-String "sys.argv" run.py` returned lines 19, 21, 23, this
was taken as confirmation the feature was working. But presence of code ≠ correct
behaviour. The overwriting line was not in the search pattern, so it was invisible.

**The fix:** When a feature is present in code but not working at runtime, the next
question should be *"what else in this file could affect this variable?"* not
*"why isn't the correct code running?"*

### 3. The file was only shown in fragments

The user ran `Select-String` and `Get-Content | Select-Object -Skip 25` separately.
Neither produced a view of the complete file. The overwriting line appeared only in
the second command's output — but by that point the session had spent significant
time on other hypotheses.

**The fix:** Ask for `Get-Content run.py` (full file) at the start of debugging,
not fragments from targeted searches.

### 4. The bug category was not identified early

"Silent overwrite" bugs — where a variable is assigned twice and the second wins —
are a specific, recognisable class of bug. If this category had been named early,
the diagnostic question would have been: *"Is port ever assigned again after line 21?"*
That question would have found the bug immediately.

**The fix:** When a variable has the right value at assignment but the wrong value
at use, always suspect a later reassignment before suspecting environment, shell,
or import issues.

### 5. Cross-environment mismatch was not suspected early enough

Claude's local files were correct; the user's GitHub main was different due to a
merge. This is a common real-world situation: the developer's environment diverges
from the canonical source. It was not treated as a hypothesis until late.

**The fix:** When a user says "this doesn't work" on a feature that passes all
local checks, ask: *"Is your local file identical to what's in the repo?"*

---

## Recommendations

### For the user's interactions with Claude

| Situation | Do This |
|---|---|
| Bug where code appears present but doesn't work | Paste the **full file** at the start, not search results |
| Feature works in Claude's checks but not on your machine | Run `git diff HEAD` and paste the output |
| Unexpected behaviour after a merge | Check `git log --oneline -5` and compare both sides of the merge |
| Claude asks a question that requires a shell command | Run the command and paste the **complete** output, not just the relevant-looking lines |

### For Claude's own debugging approach

1. **File-first rule.** When debugging a runtime mismatch, request the full file
   before forming hypotheses. Partial searches can confirm presence but not absence.

2. **Name the bug category early.** For "feature is present but wrong value at runtime",
   always check for later reassignment before anything else.

3. **Assume environment divergence.** If local checks pass but user reports failure,
   treat "user's file differs from server's file" as the top hypothesis.

4. **Silent-overwrite checklist.** For any variable that's behaving unexpectedly:
   grep for `variable_name\s*=` across the file and list every assignment site
   before debugging anything else.

5. **Request full output.** When asking the user to run a diagnostic command, specify
   that you need the complete output, not just the matching lines.

---

## Template: Fast Diagnosis for "Code Is There But Not Working"

When a user says a feature is present in code but not working at runtime, run through
this checklist in order:

1. `Get-Content <file>` (full file) — no fragments
2. Search for all assignments to the relevant variable: `Select-String "varname\s*=" file`
3. Check which assignment runs last
4. Verify the user's local file matches the repo: `git status`, `git diff`
5. Only after these pass: consider environment, import order, shell issues
