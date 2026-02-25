# Public/Private Git Submodule Workflow

## Overview

This pattern separates a **public framework repo** from **private project repos** using git submodules.

```
public-repo/                    ← Public (anyone can see)
├── .gitmodules                 ← Submodule registry
├── projects/
│   ├── project-a/              ← Just a pointer (no files)
│   ├── project-b/              ← Just a pointer (no files)
│   └── project-c/              ← Just a pointer (no files)
├── docs/
├── lib/
└── ...
```

Each `project-X/` is a **private submodule** - the public repo only contains a reference, not the actual files.

---

## Setup Steps

### 1. Create Private Repos for Each Project

```bash
gh repo create project-a --private --description "Project A"
gh repo create project-b --private --description "Project B"
```

### 2. Move Project Files to Their Own Repos

```bash
# Create temp location
mkdir -p ~/temp_repos

# Copy project to temp
cp -r projects/project-a ~/temp_repos/project-a

# Initialize as separate repo
cd ~/temp_repos/project-a
git init
git add .
git commit -m "Initial commit - Project A"
git branch -M main
git remote add origin https://github.com/username/project-a.git
git push -u origin main
```

Repeat for each project.

### 3. Remove Old Folders from Public Repo

```bash
cd /path/to/public-repo

# Remove the old folders
rm -r projects/project-a
rm -r projects/project-b

# Update .gitignore (remove any rules blocking projects/*)
```

### 4. Add Submodules

```bash
git submodule add https://github.com/username/project-a.git projects/project-a
git submodule add https://github.com/username/project-b.git projects/project-b
```

### 5. Commit and Push

```bash
git add .gitmodules .gitignore projects/
git commit -m "feat: Convert projects to private submodules"
git push
```

---

## Daily Usage

### Cloning the Public Repo

```bash
# Clone with submodules (requires access to private repos)
git clone --recurse-submodules https://github.com/username/public-repo.git

# If you forgot --recurse-submodules
git submodule update --init --recursive
```

### Working Inside a Submodule

```bash
cd projects/project-a

# Pull latest changes
git pull origin main

# Make changes and push
git add .
git commit -m "Update feature"
git push
```

### Updating Submodules from Parent Repo

```bash
# Pull latest for all submodules
git submodule update --remote

# Then commit the updated pointer in parent
git add .
git commit -m "chore: Update submodules"
git push
```

---

## Key Files

### `.gitmodules`
Auto-generated, tracks submodule URLs:
```
[submodule "projects/project-a"]
    path = projects/project-a
    url = https://github.com/username/project-a.git
```

### `.gitignore`
Remove any rules that blocked `projects/*/`:
```gitignore
# OLD (remove this):
# projects/*/
# !projects/.gitkeep
```

---

## Access Control

| Who | What They See |
|-----|---------------|
| **Public** | Framework code + empty project folders (just pointers) |
| **You (with access)** | Framework + all private project files |

Anyone cloning the public repo without access to private submodules will get empty folders.

---

## Troubleshooting

### "Repository not found" when adding submodule
Make sure you're authenticated: `gh auth status`

### Submodule folder is empty
```bash
git submodule update --init --recursive
```

### Submodule shows dirty state
```bash
cd projects/project-a
git checkout main
```

### Want to remove a submodule
```bash
git submodule deinit projects/project-a
git rm projects/project-a
rm -rf .git/modules/projects/project-a
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Clone with submodules | `git clone --recurse-submodules <url>` |
| Update all submodules | `git submodule update --remote` |
| Work in submodule | `cd projects/X && git pull && git push` |
| Add new submodule | `git submodule add <url> projects/X` |
| Check submodule status | `git submodule status` |

---

## Example: Our Setup

```
fdx-gsd/                        (public)
├── projects/
│   ├── msg-1998/               → github.com/bretbouchard/msg-1998 (private)
│   ├── sand/                   → github.com/bretbouchard/sand (private)
│   └── test_disambig/          → github.com/bretbouchard/test-disambig (private)
├── .planning/
├── docs/
└── lib/
```
