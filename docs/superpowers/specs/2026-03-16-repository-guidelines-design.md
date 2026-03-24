# Repository Guidelines Design (2026-03-16)

## Scope & Goals
- Produce `AGENTS.md` titled "Repository Guidelines" (~230-320 words) as the contributor guide.
- Tone: professional, directive, bilingual-safe but defaulting to concise English with inline Chinese terms only when file paths already contain them.
- Highlight macOS vs Windows/Linux differences wherever commands diverge; include example paths/commands inline.
- No dedicated security section; fold any sensitive-handling notes into relevant sections (e.g., testing data retention).

## Section Plan
1. **Project Structure & Module Organization**
   - Intro sentence summarizing backend (`backend/` FastAPI), frontend (`app/` Electron+Vue), shared assets (`content/`, `config/`, `data/`).
   - Bullet pairs describing backend subdirs (`api/`, `services/`, `db/`, `tests/`) and frontend subdirs (`src/`, `electron/`, `public/`, `scripts/`).
   - Mention packaging extras (electron-builder copies `config/` and `content/`) and reference supporting folders (`docs/`, `scripts/`, `data/`).

2. **Build, Test & Development Commands**
   - Environment setup: `python -m venv venv` + `source venv/bin/activate` (macOS/Linux) vs `venv\Scripts\activate` (Windows); `pip install -r requirements.txt`.
   - Backend run: `uvicorn main:app --reload`. Testing: `pytest`, `pytest backend/tests/test_database_crud.py`, `pytest -k integration`.
   - Frontend commands from `app/package.json`: `npm install`, `npm run dev`, `npm run electron:dev`, `npm run build`, `npm run electron:build*` options, `npm run preview`.
   - Note `app/scripts/notarize.js` invoked post-build and `scripts/` for helper shell scripts.

3. **Coding Style & Naming Conventions**
   - Backend: follow PEP8, 4-space indent, `snake_case` modules (e.g., `backend/services/therapy_engine.py`), type hints + docstrings, Loguru structured logging pattern from `backend/main.py`.
   - Frontend: Composition API with `<script setup lang="ts">`, 2-space indent in Vue/SCSS, components `PascalCase`, composables `camelCase`, shared styles in `app/src/styles/main.scss`.
   - Mention `vue-tsc --noEmit` gating builds even without dedicated lint config; suggest running Prettier/Vetur locally.

4. **Testing Guidelines**
   - Backend: tests in `backend/tests/` using `pytest` + `pytest-asyncio`; file naming `test_<target>[_properties].py`; prefer fixtures like `temp_db`, annotate async tests with `@pytest.mark.asyncio`.
   - Property-based style: highlight numerous `*_properties.py` files validating requirements (e.g., encryption, latency).
   - Frontend: currently manual verification by running `npm run dev`/`electron:dev`; describe steps/screenshots in PR until JS harness exists.
   - Coverage expectation: run full `pytest` + target suites before PR; mention sqlite/temp directories clean-up.

5. **Commit & Pull Request Guidelines**
   - Use Conventional Commits (see `c6425c7 feat: 初始化智能疗愈仓项目`).
   - One logical change per commit; include English summary even if title includes Chinese.
   - PRs must list affected modules, commands executed (`pytest`, `npm run build`, packaging if touched), and screenshots for UI updates.
   - Link issues/tasks, flag platform coverage (macOS vs Windows/Linux) when behavior differs.

## Risks & Open Questions
- No automated frontend tests exist; document manual verification expectation.
- Scripts in `/scripts` referenced by deployment docs—assume availability though not inspected.
- If guide needs localization later, revisit word limit.
