# START HERE

This kit is the project's memory for Claude Code. `CLAUDE.md` loads automatically every session;
the docs, agents and skills are read when needed. Everything is a specification and a set of rules:
**no application code exists yet**. Claude Code builds it by following these files.

## 1. Put the kit in your project folder

```bash
mkdir -p ~/dev && cd ~/dev
unzip ~/Downloads/realdrop-kit.zip      # creates ~/dev/realdrop
cd realdrop
code .
```

Open the VS Code terminal (`` Ctrl+` ``) and run:

```bash
git init -b main
git add . && git commit -m "docs: project kit (claude.md, docs, agents, skills)"
claude
```

VS Code will offer to install the recommended extensions: accept.

## 2. First prompt to give Claude Code

Press `Shift+Tab` to enter plan mode, then paste:

```
Read CLAUDE.md, then docs/SETUP.md and docs/ROADMAP.md. Today is Sat 24 Oct 2026, Day 1.
Do Phase 1 from docs/SETUP.md only: check what is already installed, show me a short plan, wait for my
approval, then run it step by step with a verification after each step. Do not start anything from
week 1 of the roadmap yet. Ask me before anything that needs my login or my API key.
```

## 3. Read the files once (20 minutes)

In this order: `docs/PRODUCT.md`, `docs/ROADMAP.md`, `docs/AI_DESIGN.md`. You are the owner; you should
be able to explain the real-drop rule and the number-grounding guard to someone else.

## 4. How you use the agents and skills

- Ask for them by name: "use the architect agent to plan the alerts feature", "have the reviewer
  check this diff". Claude Code also delegates automatically using each agent's description.
- Skills are checklists Claude follows: "use the add-brand-collector skill for LC Waikiki".

## What files cannot do

They give Claude the rules, context and checklists; they do not run anything. The "agent loops" in
`docs/AI_DESIGN.md` are designs the code will implement, and the evals are what prove they work.
If Claude Code ever contradicts a file, tell it to re-read the file; if the file is wrong, change the file.
