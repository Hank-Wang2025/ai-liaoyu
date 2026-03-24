# Codex Windows Training PPT Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-focused beginner training PPTX that explains Codex installation and day-one usage with a neutral technical tone.

**Architecture:** Create the deck from scratch with a dedicated PptxGenJS script so the output can be regenerated and edited safely. Keep source content in the script, write the final `.pptx` to a presentation output directory, then verify text extraction and slide rendering.

**Tech Stack:** Node.js, PptxGenJS, Codex CLI help output, OpenAI official Codex documentation

---

## Chunk 1: Source Content And File Layout

### Task 1: Create presentation file structure

**Files:**
- Create: `docs/presentations/.gitkeep`
- Create: `docs/superpowers/scripts/generate_codex_windows_training_ppt.js`

- [ ] **Step 1: Create the output directory marker**

Create `docs/presentations/.gitkeep` so generated presentations have a stable home in the repo.

- [ ] **Step 2: Create the generation script skeleton**

Add a Node.js script that imports `pptxgenjs`, sets metadata, defines theme helpers, and writes `docs/presentations/codex-windows-training.pptx`.

- [ ] **Step 3: Verify the script can be parsed**

Run: `node --check docs/superpowers/scripts/generate_codex_windows_training_ppt.js`
Expected: exit code `0`

## Chunk 2: Build Slide Content

### Task 2: Implement the 11-slide deck

**Files:**
- Modify: `docs/superpowers/scripts/generate_codex_windows_training_ppt.js`

- [ ] **Step 1: Add the shared visual system**

Implement color palette, typography helpers, command block helpers, card helpers, and slide chrome so slides remain visually consistent.

- [ ] **Step 2: Add slides 1-5**

Implement cover, product overview, use cases, prerequisites, and Windows installation flow.

- [ ] **Step 3: Add slides 6-11**

Implement login, usage modes, workflow example, troubleshooting, best practices, and Q&A.

- [ ] **Step 4: Run the generator**

Run: `node docs/superpowers/scripts/generate_codex_windows_training_ppt.js`
Expected: `docs/presentations/codex-windows-training.pptx` is created

## Chunk 3: Verify And Refine

### Task 3: Run content QA and visual QA

**Files:**
- Output: `docs/presentations/codex-windows-training.pptx`
- Optional output: extracted text or rendered images in a temp directory

- [ ] **Step 1: Run text extraction QA**

Run: `python -m markitdown docs/presentations/codex-windows-training.pptx`
Expected: extracted text follows the intended slide order and contains no placeholder content

- [ ] **Step 2: Render slides for visual inspection**

Run the best available local rendering path for this environment to produce slide images or a PDF for manual inspection.

- [ ] **Step 3: Fix layout or wording issues found in QA**

Update the generation script only if the rendered output reveals overflow, overlap, weak contrast, or inaccurate wording.

- [ ] **Step 4: Re-run generator and QA**

Run the generation script again, then repeat the text extraction and available visual verification commands.

- [ ] **Step 5: Summarize exact verification evidence**

Record which commands ran, whether the PPTX was produced, and any verification limits caused by missing local tools.

Plan complete and saved to `docs/superpowers/plans/2026-03-17-codex-windows-training-ppt.md`. Ready to execute?
