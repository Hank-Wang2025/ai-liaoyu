# Repository Guidelines Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a concise AGENTS.md contributor guide titled "Repository Guidelines" (~230-320 words) aligned with the approved design.

**Architecture:** Single Markdown file at repo root summarizing structure, commands, style, testing, and PR practices with frontend/backend split notes.

**Tech Stack:** Markdown, FastAPI backend context, Electron/Vue frontend context, pytest, npm scripts.

---

## Chunk 1: Drafting AGENTS.md

### Task 1: Gather references

**Files:**
- Read: `README.md`, `backend/requirements.txt`, `app/package.json`, `backend/tests/*.py`, `docs/superpowers/specs/2026-03-16-repository-guidelines-design.md`

- [ ] Run `rg --files` or `Get-ChildItem` to confirm key directories exist (`backend`, `app`, `content`, `config`, `data`).
- [ ] Re-open `app/package.json` to capture command names exactly.
- [ ] Skim `backend/tests/test_database_crud.py` (already reviewed) to quote pytest patterns if needed.

### Task 2: Draft AGENTS.md

**Files:**
- Create/Modify: `AGENTS.md`

- [ ] Start file with `# Repository Guidelines`.
- [ ] Write “Project Structure & Module Organization” section referencing backend/frontend directories per design.
- [ ] Write “Build, Test & Development Commands” section with platform-specific bullets.
- [ ] Add “Coding Style & Naming Conventions,” “Testing Guidelines,” “Commit & Pull Request Guidelines” as designed.
- [ ] Keep total word count 230-320 words (use `Measure-Object -Word`).
- [ ] Embed concrete command snippets (e.g., `uvicorn main:app --reload`, `npm run electron:dev`).

## Chunk 2: Review & polish

### Task 3: Self-review

**Files:**
- Read: `AGENTS.md`

- [ ] Proofread for clarity, professional tone, macOS vs Windows callouts.
- [ ] Ensure commands and paths match repository reality (backend/app/test directories, node scripts).
- [ ] Confirm no Security section; integrate any cautionary text elsewhere.

### Task 4: Word count & formatting check

- [ ] Run `Get-Content AGENTS.md | Measure-Object -Word` to confirm range.
- [ ] Verify Markdown headings use `##` as needed and there’s no trailing whitespace.

### Task 5: Finalize

- [ ] Present final summary + testing/verification steps to user.
