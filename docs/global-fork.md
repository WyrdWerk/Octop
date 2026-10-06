# WyrdWerk global fork

This repository (`WyrdWerk/Octop`) is a fork of [TencentCloud/Octop](https://github.com/TencentCloud/Octop)
that turns it into an **English-first, global (non-China) product**. This page is the single record of
what the fork changes, why, and how to operate it. Keep it up to date with every fork change.

## Branch model

| Branch | Purpose |
|--------|---------|
| `global` | **Default branch.** All fork work lands here. Build and deploy from it. |
| `main` | Untouched mirror of `upstream/main` (TencentCloud). Never commit fork work to it. |

Remotes in a local clone: `origin` = `WyrdWerk/Octop`, `upstream` = `TencentCloud/Octop`.

Syncing upstream:

```bash
git fetch upstream
git checkout main && git merge --ff-only upstream/main && git push origin main
git checkout global && git merge main        # resolve conflicts, run tests, push
```

Merge conflicts usually land in `src/octop/i18n/{en,zh}.json`, `dashboard/src/locales/{en,zh}.json`
(both sides add keys: take the union) and in files where upstream added new Chinese strings.

## Design rules for fork changes

1. **Hide, don't delete.** China-specific features stay in the code and are filtered by allowlists /
   hidden-lists, so upstream merges stay cheap and anyone can turn them back on.
2. **Keep internal names.** The `octop` package and CLI, `~/.octop/`, `OCTOP_*` env vars and the
   `octop-*` libraries are not renamed (thousands of references; renaming only breaks merges).
3. **No hardcoded user-visible Chinese.** Every UI / API string goes through i18n with both an `en`
   and a `zh` entry (see [Internationalization](#1-english-first-internationalization)).
4. **Defaults flip, Chinese still works.** English is the default; choosing 中文 in the language
   switcher (or a Chinese browser) still gives the full Chinese experience.
5. **One focused commit per change area**, so upstream rebases/merges are reviewable.

## What the fork changes

### 1. English-first internationalization

**Dashboard (React).**
- Default UI locale is English (`dashboard/src/utils/localePrefs.ts`). Resolution order: a language the
  user *explicitly* picked on this device (`octop-ui-locale-explicit` flag in localStorage) → browser
  language → English. Unknown/missing values resolve to `en`.
- The server user locale no longer forces Chinese: `resolveUserLocale` honours a server `"en"` always,
  and a server `"zh"` only if the user explicitly picked Chinese here or the browser is Chinese.
- About 260 hardcoded Chinese strings in components/pages were moved into
  `dashboard/src/locales/{en,zh}.json` (Agent/Memory/Connectors/Channels pages, Control, Chat,
  Settings, Experts, Admin, Knowledge Bases, PWA debug, shared components).
- `public/offline.html` is English; `manifest.json` has `lang: "en"`.
- Remaining CJK in source is intentional: `t("key", "中文 fallback")` fallbacks (key exists in both
  locales), `isZh ? … : …` pairs with an English branch, language names (简体中文), and regexes /
  keyword matching that parse Chinese input.

**Backend (Python).**
- `DEFAULT_LOCALE = "en"` (`src/octop/infra/utils/locale.py`) and every `locale="zh"` /
  `language="zh-CN"` default parameter flipped to English (CLI, slash commands, users, setup, chat
  turn, voice `en-US`, experts, MBTI). New users — including the `octop init` admin, LDAP and SSO
  users — are created with locale `en`.
- The agent runtime (`octop-harness`) defaults to `language="zh"`; Octop now always passes a
  language: `AgentManager._harness_language()` → agent config `language` → owner's stored locale →
  `DEFAULT_LOCALE`. This drives seeded workspace templates, team/peer prompts and slash-skill prompts.
- Expert template locale overlay: `experts/library/<id>/locales/<loc>/<file>` replaces the base file
  when seeding for that locale. English overlays exist for `default/AGENTS.md` and
  `general-assistant/SOUL.md`.
- ~160 user-visible strings moved into `src/octop/i18n/{en,zh}.json` (connector gateway adapters,
  probes, Docker guidance, OAuth errors, …). Connector requests get a per-request locale from
  `Accept-Language` (`src/octop/infra/connectors/locale_ctx.py`).
- Default timezone is `UTC` (was `Asia/Shanghai`) in config, slash ctx, cron and proactive services.
  `Asia/Kolkata` was added to the cron timezone picker.

### 2. Connectors and Composio

- **Composio connector** (`composio`, first in the catalog): fields API key (secret), MCP server ID,
  optional full MCP URL (overrides server ID) and optional user ID. It builds a streamable-HTTP MCP
  connection to `https://backend.composio.dev/v3/mcp/<SERVER_ID>?user_id=<USER>` with header
  `x-api-key`. `user_id` defaults to the Octop username, so each household member's accounts stay
  separate. Code: `infra/connectors/catalog.py`, `builder.py` (`build_composio_mcp_url`),
  `api/routers/connectors.py`; logo `dashboard/src/assets/connectors/composio.svg`.
- **Connector allowlist** (`OCTOP_CONNECTOR_ALLOWLIST`), applied in `list_catalog()`. Default:
  `composio, notion, openalex, dify, weknora, qq-mail` (the last is a generic IMAP/SMTP mailbox).
  Custom MCP has its own tab and is always available. Hidden kinds still resolve, so existing
  instances keep working.

### 3. IM channels

`OCTOP_CHANNEL_ALLOWLIST`, default `telegram, discord, mqtt`; exposed as `channel_kinds` in
`/api/settings/capabilities` and applied by the dashboard Channels page. Feishu, DingTalk, QQ, WeCom,
WeChat, Xiaoyi and Yuanbao are hidden. Already-configured channels stay visible.
Note: this is a UI filter; the server does not refuse hidden kinds.

### 4. Experts and plugins

`OCTOP_EXPERT_HIDDEN` / `OCTOP_PLUGIN_HIDDEN` (hidden-lists; `none` shows everything).

| | Hidden by default | Shown |
|---|---|---|
| Experts | meituan-living-assistant, wechat-ops, cvm-ai-doctor, cvm-cluster-doctor, tencentcloud-api, clinical-learning-subscription, news-trend, stock-assistant, ai-safety-guardian, parenting-companion | default, general-assistant, ai-coding-coach, karpathy-knowledge-base, multi-agent-orchestrator, office-automation, ops-engineer, superpowers-methodology |
| Plugins | bilibili-anime, hot-topics, market-quotes, parcel-tracker, slack-calendar, what-to-eat, fortune, movie-search, daily-english, fun-facts, travel-inspire | air-quality, color-convert, github-trending, ip-lookup, meme-maker, mini-games, pomodoro, qrcode, server-status, short-link, sports-scores, tetris, unit-convert, weather, wiki-summary |

Kept plugins have English `plugin.yaml` names/descriptions; `wiki-summary` defaults to English Wikipedia.

### 5. Web search (privacy)

Upstream's harness default `"auto"` always mounts `searchfree`, which sends agent search queries to
the third-party `searchfree.site`. The fork passes an explicit provider list
(`src/octop/infra/agents/settings/web_search.py`):
- `OCTOP_WEB_SEARCH_PROVIDERS=auto` (default): only key-gated providers whose keys are set —
  `TAVILY_API_KEY`, `BRAVE_API_KEY`, `GOOGLE_API_KEY`+`GOOGLE_CSE_ID`, `MOONSHOT_API_KEY`.
  **With no key, agents have no web search.**
- `none` disables search; a comma list picks providers (listing `searchfree` opts in).
- `OCTOP_ENABLE_SEARCHFREE=1` adds searchfree to `auto`; `SEARCHFREE_ENDPOINT` points it at a
  self-hosted instance. An agent's own `web_search_tools` setting still wins.

### 6. Self-update disabled

Upstream self-update installs the official `octop` from PyPI, which would overwrite the fork.
`OCTOP_DISABLE_SELF_UPDATE` defaults to on: `/api/update/*` return status `managed_by_deployer`
without contacting PyPI, `/upgrade` returns 403, and `octop update` prints a notice. The dashboard
Update page says "Updates are managed by your deployer" and links to this repo.
Upgrade by rebuilding/redeploying the Docker image from `global`.

### 7. Model providers

`presets.py` / `presetUtils.ts` list OpenAI, Anthropic, OpenRouter, Gemini, OpenAI Codex and Groq
first; Chinese providers (Hunyuan, Moonshot, MiniMax, Volcengine, …) are under "more". The setup
wizard defaults to OpenAI. Media generation still defaults to Volcengine (unchanged).

### 8. Mirrors, installers and links

- `OCTOP_USE_CN_MIRRORS=1` opts back into mainland-China mirrors (tuna PyPI, npmmirror Playwright,
  COS/hf-mirror ONNX models, docker-ce mirrors); off by default in `scripts/install*.sh`,
  `install.ps1/.bat`, `desktop/portable/_common.sh`, `onnx_download.py`, `mobile/docker_install.py`.
- `OCTOP_REPO` in installers defaults to this fork. **Caveat:** the installers still install the
  upstream `octop` package from PyPI; use Docker to run the fork.
- Help & feedback link → <https://github.com/WyrdWerk/Octop/issues>.
- SkillHub-generated expert SOUL.md prompts are English and tell the agent to reply in the user's
  language.

## Configuration reference

All knobs are also listed in [`.env.example`](../.env.example).

| Variable | Default | Effect |
|----------|---------|--------|
| `OCTOP_CONNECTOR_ALLOWLIST` | global set (above) | Connector kinds shown; `*` = all; `default,<id>` extends |
| `OCTOP_CHANNEL_ALLOWLIST` | `telegram,discord,mqtt` | IM channels offered; `*` = all |
| `OCTOP_EXPERT_HIDDEN` | China-specific set | Bundled experts hidden; `none` = show all |
| `OCTOP_PLUGIN_HIDDEN` | China-specific set | Bundled plugins hidden; `none` = show all |
| `OCTOP_WEB_SEARCH_PROVIDERS` | `auto` | `auto` / `none` / comma list |
| `OCTOP_ENABLE_SEARCHFREE` | `0` | `1` adds searchfree.site to `auto` |
| `OCTOP_DISABLE_SELF_UPDATE` | `1` | `0` re-enables PyPI in-place upgrades (overwrites the fork!) |
| `OCTOP_USE_CN_MIRRORS` | `0` | `1` uses mainland-China mirrors |
| `OCTOP_PYPI_MIRRORS` | — | Extra PyPI indexes for self-update |

## Build and deploy

The Dockerfile uses BuildKit cache mounts, so the build host needs **Docker with `buildx`**.

```bash
git clone -b global https://github.com/WyrdWerk/Octop.git && cd Octop
bash docker/docker_build.sh octop-global:latest
docker run -d --name octop --restart unless-stopped -p 8088:8088 \
  -v octop-data:/data/.octop -e HOME=/data \
  -e OCTOP_ADMIN_USERNAME=admin -e OCTOP_DEFAULT_PASSWORD='<8+ chars, letters+digits>' \
  octop-global:latest
```

The build peaks at ~2 GB for the frontend step (`NODE_MAX_OLD_SPACE_SIZE=2048`); the image is ~3 GB.

After the first login, add a model under **Admin → Model Management** (`/admin/models`); agents
can't reply until a provider key is configured. Add a Tavily/Brave key if agents need web search.

### ACP coding-agent runners in Docker

Outbound ACP runners (`/acp`) spawn a coding-agent CLI **as a child process inside the Octop
process's environment**. The stock image contains Python and git but **no Node.js/npx**, so the
built-in runners (`claude_code`, `codex`, `pi` via `npx`; `opencode`, `kimi`, `cursor` CLIs) cannot
start in the container. To use them, extend the image with Node and the agent CLIs and pass their
credentials (e.g. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) as container env vars. See [acp.md](acp.md).

### Known behaviour after redeploys

The dashboard is a PWA. After a new frontend build is deployed, browsers that cached the old one show
"A new version is ready — Update now". Clicking it reloads onto the new build; it is unrelated to
Octop self-update.

## Testing baseline

- Backend: `uv run pytest tests -n 8` — full suite green on `global` (≈4,350 passed, 45 skipped).
- Dashboard: `npx tsc -b` clean. `npx vitest run` has **6 failures that also fail on upstream**
  (`DocumentPreviewCore.docxSanitize` — DOMMatrix in jsdom; `Skills/skillMarkdown` and
  `SkillDrawer` — pdfjs in jsdom; `knowledgeBases`, `publishedExperts`, `useSessions` mocks).
  Treat anything beyond those as a regression.
- Many upstream tests pin the old behaviour by setting env explicitly (allowlist `*`,
  `OCTOP_DISABLE_SELF_UPDATE=0`, CN mirrors on); follow that pattern rather than changing defaults back.

## Known gaps (not yet done)

- **Expert Market** uses SkillHub (`api.skillhub.cn`); content is mostly Chinese. clawhub.ai has no
  equivalent API, so switching needs a new client. (clawhub.ai is already the default for importing
  a skill by URL.)
- Runtime/UI-card text inside kept bundled plugins' `main.py` is still partly Chinese.
- `experts/library/general-assistant/skills/octop-assistant/SKILL.md` (26 KB) is Chinese only.
- The harness `current_time` tool appends a Chinese weekday (`Friday (周五)`) — lives in the
  `octop-harness` PyPI package, not this repo.
- MBTI `nickname_zh` meme nicknames have no English equivalent (only shown in zh).
- Existing databases keep users with `locale='zh'` and Chinese seeded role names (no migration).
- No rebrand: name, logo and mascot are still Octop.
