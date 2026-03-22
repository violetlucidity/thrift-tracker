# COMMANDS — Thrift Tracker
**Last updated:** 2026Mar22-1200

---

## Setup

Install Python dependencies:
```
py -m pip install -r requirements.txt
```

Install Playwright browser:
```
py -m playwright install chromium
```

Create config file from template:
```
copy config.json.example config.json
```

---

## Running the Application

Start Thrift Tracker (prompts for port, default 5000):
```
py run.py
```

---

## URL Importer

Import URLs from thrift-links.txt into config.json:
```
py import_links.py thrift-links.txt
```

Convert a Firefox bookmarks HTML export to thrift-links.txt:
```
py import_links.py --convert bookmarks.html
```

---

## Git — Common Commands

Clone the repository:
```
git clone <repo-url>
cd thrift-tracker
```

Check current status:
```
git status
```

Stage all changes:
```
git add -A
```

Commit with a message:
```
git commit -m "your message here"
```

Push to a branch:
```
git push -u origin <branch-name>
```

Pull latest changes:
```
git pull origin <branch-name>
```

Create and switch to a new branch:
```
git checkout -b <branch-name>
```

Switch to an existing branch:
```
git checkout <branch-name>
```

View recent commits:
```
git log --oneline -10
```
