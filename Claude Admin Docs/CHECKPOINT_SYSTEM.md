# Claude Checkpoint Management System

**Purpose**: Stay organized during complex, multi-step conversations with Claude

**Created**: 2026-01-16  
**Use**: Add to Claude custom instructions for all future chats

---

## Command Phrases

| Phrase | Action | What It Does |
|--------|--------|--------------|
| **"CHECKPOINT: [name]"** | Save state | Marks current discussion point for return |
| **"DETOUR"** or **"SIDE QUEST"** | Branch off | Notes we're leaving main thread |
| **"RETURN TO CHECKPOINT"** | Resume | Goes back to marked point |
| **"SHOW CHECKPOINTS"** | List | Shows all saved checkpoints |
| **"STATUS CHECK"** | Progress | Shows current checklist progress |

---

## How It Works

### Example Usage

```
You: I'm working through the issue_resolution checklist. 
     CHECKPOINT: Issue Resolution - Priority 2

Claude: ✓ Checkpoint saved: "Issue Resolution - Priority 2"
        Current task: Clean bad data (153 rows)

You: How do I view .bak files?  [DETOUR happens automatically]

Claude: [Answers question]

You: RETURN TO CHECKPOINT

Claude: ✓ Returning to checkpoint: "Issue Resolution - Priority 2"
        
        You were working on: Clean bad data
        Status: ✅ Backup files deleted
        
        Next task: Apply receptor normalization
```

---

## System Prompt Text

**Add this to Claude Settings → Custom Instructions → "How would you like Claude to respond?"**

```
Project Management Style:
- When I say "CHECKPOINT: [name]", save that discussion point
- When I say "DETOUR" or "SIDE QUEST", note we're branching
- When I say "RETURN TO CHECKPOINT", remind me where we were and show checklist progress
- Track multi-step processes with ✅ (done), 🔄 (current), ⏳ (pending)
- Auto-create checkpoints when I start working through a checklist or plan
```

---

## Enhanced Version (For Complex Projects)

**For detailed checklist tracking:**

```
# Checkpoint & Checklist Management

CHECKPOINT COMMANDS:
- "CHECKPOINT: [name]" → Save current discussion point
- "DETOUR" or "SIDE QUEST" → Branch off (auto-saves last context)
- "RETURN TO CHECKPOINT" → Resume saved discussion
- "SHOW CHECKPOINTS" → List all saved checkpoints
- "STATUS CHECK" → Show current checklist progress

CHECKLIST TRACKING:
When working through a checklist or multi-step process:
1. Track completed items with ✅
2. Track in-progress items with 🔄
3. Track pending items with ⏳
4. When returning from detour, show checklist state

RETURN FORMAT:
```
✓ Returning to checkpoint: "[name]"

Checklist progress:
✅ [completed items]
🔄 [current item]
⏳ [remaining items]

You were: [last discussed topic]
Next: [next logical step]
```

IMPLICIT CHECKPOINTS:
Auto-create checkpoints when user:
- Starts a numbered checklist
- Says "I'm working through [document/plan]"
- Uses phrases like "back to the main task"
```

---

## Where to Add in Claude.ai

### Steps:

1. Click your **profile icon** (bottom left)
2. Click **Settings**
3. Find **"Custom instructions"** or **"User preferences"**
4. Under **"How would you like Claude to respond?"**
5. Paste the system prompt text

### Mobile:
1. Tap profile icon
2. Settings → Profile
3. Scroll to custom instructions
4. Add text

---

## Testing the System

After adding to settings, test in a new chat:

```
You: CHECKPOINT: Testing checkpoint system
     I'm going to ask about Python, then return here.

Claude: ✓ Checkpoint saved: "Testing checkpoint system"

You: [Ask about Python]

You: RETURN TO CHECKPOINT

Claude: ✓ Returning to checkpoint: "Testing checkpoint system"
        You were about to test the checkpoint system...
```

---

## Tips for Effective Use

### When to Create Checkpoints:

✅ **DO create checkpoints when:**
- Starting a multi-step tutorial
- Working through a checklist
- Beginning a complex debugging session
- Planning a large project
- About to ask a quick side question

❌ **DON'T need checkpoints for:**
- Simple one-off questions
- Short conversations
- When you're naturally done with a topic

### Naming Checkpoints:

**Good names:**
- "CHECKPOINT: Database setup - Step 3"
- "CHECKPOINT: Issue Resolution Priority 2"
- "CHECKPOINT: Phase 4 planning"

**Bad names:**
- "CHECKPOINT: Thing"  (too vague)
- "CHECKPOINT: Help"  (not descriptive)

---

## Advanced Features

### Multiple Checkpoints

You can have multiple active checkpoints:

```
You: CHECKPOINT: Main project - Phase 1
     [work on Phase 1]
     
You: CHECKPOINT: Subproject - Database design
     [work on database]
     
You: SHOW CHECKPOINTS

Claude: Active checkpoints:
        1. Main project - Phase 1
        2. Subproject - Database design
```

### Status Checks Without Returning

```
You: STATUS CHECK

Claude: Current checkpoint: "Issue Resolution Priority 2"
        Progress: 60% complete (3/5 tasks done)
        Current task: Normalize receptors
```

---

## Troubleshooting

### "Claude isn't recognizing my checkpoints"

**Solutions:**
1. Make sure you added to custom instructions
2. Start a new chat (settings apply to new chats)
3. Be explicit: "I'm using the checkpoint system. CHECKPOINT: [name]"

### "I forgot what checkpoint I was at"

```
You: SHOW CHECKPOINTS
     or
You: What was my last checkpoint?
```

### "I want to abandon a checkpoint"

```
You: CLEAR CHECKPOINT [name]
     or
You: Ignore previous checkpoint, let's start fresh
```

---

## Integration with Other Systems

### Works Great With:

- ✅ Project-based Claude chats (automatic memory)
- ✅ Long coding/debugging sessions
- ✅ Tutorial following
- ✅ Research projects

### Also Consider:

- Use Claude Projects for persistent context
- Use conversation search to find old checkpoints
- Export important checkpoints to notes

---

## Summary

**Add to settings once** → Works in all future chats

**Commands to remember:**
- `CHECKPOINT: [name]` - Save point
- `DETOUR` - Branch off
- `RETURN TO CHECKPOINT` - Go back

**Benefits:**
- Stay organized in complex projects
- Never lose your place
- Handle interruptions gracefully
- Track progress visually

---

## Quick Reference Card

```
┌─────────────────────────────────────────┐
│   CLAUDE CHECKPOINT QUICK REFERENCE     │
├─────────────────────────────────────────┤
│ Save:   CHECKPOINT: [name]              │
│ Leave:  DETOUR / SIDE QUEST             │
│ Return: RETURN TO CHECKPOINT            │
│ List:   SHOW CHECKPOINTS                │
│ Status: STATUS CHECK                    │
└─────────────────────────────────────────┘
```

---

**Version**: 1.0  
**Last Updated**: 2026-01-16  
**Tested**: Yes, in PDSP database project
