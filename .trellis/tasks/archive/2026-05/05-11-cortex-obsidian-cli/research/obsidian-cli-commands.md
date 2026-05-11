# Official Obsidian CLI Research

- **Query**: Map notesmd-cli (Yakitrak/obsidian-cli) actions used by cortex to official Obsidian CLI (v1.12.4+)
- **Scope**: external (help.obsidian.md) + internal (cortex usage audit)
- **Date**: 2026-05-11

## TL;DR

Official Obsidian CLI is the binary `obsidian` (installed via app Settings → General → Command line interface; **not** brew/scoop, it ships bundled inside `Obsidian.app` and registers a symlink/PATH entry). **It requires the Obsidian desktop app to be running** — first command auto-launches it. Command surface uses `cmd param=value` syntax (e.g. `obsidian read path=foo.md`). All 7 notesmd-cli actions have direct equivalents (`read`, `create`, `files`/`folders`, `search` / `search:context`, `move`, `property:set`/`:read`/`:remove`, `daily` family) and `move` **does auto-update internal links** (gated on vault setting "Automatically update internal links"). The CLI is GA in installer 1.12.7+; non-md / canvas / heading-anchor patch / metadata-cache graph still need `mcp__obsidian__*` fallback because there is no `patch_content target_type=heading|block` equivalent.

## Binary & Install

- **Name on PATH**: `obsidian` (all platforms). Subcommands invoked as `obsidian <cmd> [k=v ...] [flag]`. Bare `obsidian` opens a TUI with autocomplete + `Ctrl+R` history search.
- **Install**: bundled with the Obsidian desktop installer (≥ 1.12.7 required for stable CLI). Enable via **Settings → General → Command line interface**, then accept the registration prompt.
  - **macOS**: creates symlink `/usr/local/bin/obsidian → /Applications/Obsidian.app/Contents/MacOS/obsidian-cli` (needs admin password once). Manual fallback: `sudo ln -sf /Applications/Obsidian.app/Contents/MacOS/obsidian-cli /usr/local/bin/obsidian`.
  - **Linux**: copies binary to `~/.local/bin/obsidian` (must be in PATH).
  - **Windows**: needs `Obsidian.com` terminal redirector bundled with 1.12.7+ installer; CLI registration adds Obsidian dir to user PATH (requires terminal restart).
- **No brew/scoop/AUR.** Distribution is exclusively via the official installer download.
- **`obsidian-headless`** (separate npm package, `npm i -g obsidian-headless`, binary name `ob`) is open-beta and only does Sync — *not* a substitute for the CLI's vault commands.

## Command Surface Mapping

| Action | notesmd-cli | Official Obsidian CLI | Notes |
| --- | --- | --- | --- |
| Read note | `print <note>` | `obsidian read path=<path>` or `read file=<name>` | `file=` uses wikilink resolution (no extension); `path=` is exact path from vault root. Defaults to active file if neither given. |
| Create / overwrite | `create <note> --overwrite` | `obsidian create name=<name> [path=<path>] content="..." overwrite [open] [newtab] [template=<name>]` | `overwrite` is a boolean flag. Built-in template support via `template=`. |
| Append | `create <note> --append` | `obsidian append path=<path> content="..." [inline]` | Dedicated `append` command. `inline` = no leading newline. Daily-note variant: `daily:append content="..."`. There is also `prepend` (after frontmatter). |
| List directory | `list [<dir>]` | `obsidian files [folder=<path>] [ext=<ext>] [total]` (files) / `obsidian folders [folder=<path>]` (subfolders) / `obsidian folder path=<path>` (single folder info) | No combined "ls" — split by entity. Output is text by default. |
| Full-text search | `search-content <q> --format json` | `obsidian search query="..." [path=<folder>] [limit=N] [format=text\|json] [case] [total]` (paths only) / `obsidian search:context query="..." [...]` (grep-style `path:line: text`) | `search:context` is closer to what cortex-search wants (line context). Both support JSON. |
| Move + auto-update wikilinks | `move <src> <dst>` (auto-updates wikilinks) | `obsidian move {file=<name>\|path=<path>} to=<destination>` | Auto-updates internal links **iff** vault setting "Automatically update internal links" is on (per official doc). Separate `obsidian rename {file\|path} name=<new>` exists for rename-only (also link-aware). |
| Frontmatter — read | `frontmatter <note> --print` | `obsidian properties file=<name> active` / `obsidian property:read name=<prop> [file=<name>]` | `properties` lists all props on the file (`format=yaml\|json\|tsv`); `property:read` extracts a single property value. |
| Frontmatter — set | `frontmatter <note> --edit --key K --value V` | `obsidian property:set name=<k> value=<v> [type=text\|list\|number\|checkbox\|date\|datetime] [file=<name>\|path=<p>]` | Typed properties supported natively. Remove via `property:remove name=<k>`. |
| Daily note (open) | `daily` | `obsidian daily [paneType=tab\|split\|window]` | Same name, same intent. |
| Daily note (read body) | n/a | `obsidian daily:read` | New capability — direct read without opening. |
| Daily note (append) | n/a | `obsidian daily:append content="..." [inline] [open]` | Plus `daily:prepend` and `daily:path` (returns expected path even if file not created). |
| Delete | `delete <note>` | `obsidian delete {file=<name>\|path=<path>} [permanent]` | Goes to trash by default; `permanent` flag bypasses. |
| Multi-vault target | `--vault <name\|path>` (per command) | `obsidian vault=<name\|id> <cmd> ...` **as first parameter before the command**. CWD inside a vault folder = that vault by default; otherwise the currently active vault. TUI uses `vault:open name=<name>` to switch. | List vaults: `obsidian vaults [verbose]`. Show current: `obsidian vault [info=name\|path\|...]`. |

### Bonus capabilities not in notesmd-cli (relevant to cortex)

- `obsidian backlinks file=<name> [counts] [total] [format=json|tsv|csv]` — first-class backlink listing (cortex-linker today does this via SC/ripgrep).
- `obsidian links file=<name>` — outgoing links; `obsidian unresolved [verbose]` — broken wikilinks across vault; `obsidian orphans` / `obsidian deadends` (great for cortex-curator audits).
- `obsidian outline path=<p> [format=tree|md|json]` — heading outline (could replace ad-hoc parsing).
- `obsidian tags [counts] [file=<name>]` and `obsidian tag <subcommands>` — tag analytics.
- `obsidian commands` / `obsidian command id=<cmd-id>` — execute any registered Obsidian command id (effectively a remote command palette; could replace some MCP patches).
- `obsidian eval code="..."` — arbitrary JS in app context (developer; covers nearly anything else but is plugin-mode-restricted).
- `--copy` flag on any command copies stdout to clipboard.

## Headless Behavior

- **Requires the Obsidian app to be running.** Quote from official doc: *"Obsidian CLI requires the Obsidian app to be running. If Obsidian is not running, the first command you run launches Obsidian."* Implication for cortex cron/CI: first invocation has cold-start cost (Electron boot) and on a server/SSH session may not work at all (no GUI display).
- **Not a true headless client.** For headless/server use cases Obsidian ships a separate npm package `obsidian-headless` (binary `ob`) — but that is currently **Sync-only** (open beta), no vault read/write commands. So cortex automation that previously relied on notesmd-cli running with Obsidian closed cannot be 1:1 mapped — it needs Obsidian app running, or fall back to direct FS / MCP.
- TUI mode (`obsidian` with no args) is interactive; for scripting use one-shot `obsidian <cmd> ...`. CLI defaults to silent operation (per 1.12.4 changelog: *"CLI commands now default to silent operation and doesn't expect an active file by default."*) and ignores unrecognized `--` flags.
- Communication channel: socket file (dotfile on macOS/Linux since 1.12.4). On Windows uses `Obsidian.com` terminal redirector for stdin/stdout bridging.

## Move Auto-Update Wikilinks

**Retained.** Official doc on `move`:
> "This will automatically update internal links if turned on in your vault settings."

Gating differences vs notesmd-cli:
- notesmd-cli updates wikilinks unconditionally regardless of Obsidian setting (it parses md directly).
- Official CLI defers to the vault's "Automatically update internal links" setting (Settings → Files & Links). cortex-doctor / install hook should verify this setting is on, otherwise the L1 advantage over MCP collapses.

## Gaps (still need mcp__obsidian__ or other fallback)

Same gaps as today, plus one new one:

- **Heading-anchor patch** (`mcp__obsidian__obsidian_patch_content target_type=heading`) — no equivalent. Official CLI only supports whole-file `create`/`overwrite`/`append`/`prepend`. Cortex-cartographer's `<!-- cortex:auto-start/end -->` incremental update must still go through MCP `patch_content` or local `Edit`.
- **Block-id patch** (`target_type=block`) — no equivalent.
- **Canvas (`.canvas`) and non-md files** — not directly supported by content commands; `files` lists them but `read`/`create` are markdown-oriented.
- **Metadata cache / reverse-link graph as data** — `backlinks`, `links`, `unresolved`, `orphans`, `deadends` partially close this gap but do not expose Obsidian's full metadataCache structure programmatically (MCP doesn't either; only `eval` can).
- **No-Obsidian-app scenarios** — cortex cron tasks that previously ran while Obsidian was closed now need either (a) keep Obsidian running, (b) accept first-call cold start, or (c) bypass CLI to direct FS for read/list and accept loss of link-rename. notesmd-cli ran headlessly; official CLI does not.
- **CLI 1.12.7+ install gate** — older installers (1.12.0–1.12.6) lack stable CLI. cortex-doctor needs to check `obsidian version` and warn when < 1.12.7.
- **Vault-name resolution differs** — notesmd-cli reads `~/.config/obsidian/obsidian.json`; official CLI uses its own registered vault list via `obsidian vaults`. Migration must re-discover.

## Internal Cortex Files That Reference notesmd-cli (need update)

(from `grep -rn "notesmd-cli" plugins/tools/cortex`)

- `plugins/tools/cortex/AGENT.md` (lines 9, 14) — primary routing rules
- `plugins/tools/cortex/locales/{en,ja,zh-CN}.yml` (~lines 44–53) — i18n install instructions + doctor warning
- `plugins/tools/cortex/agents/cortex-{summarizer,linker,curator,cartographer,researcher,translator,historian,archivist}.md` — per-agent allowed-tools / examples
- `plugins/tools/cortex/docs/{设计决策.md,架构设计.md}` — architecture explanations (L1 = notesmd-cli)

## Sources

- https://help.obsidian.md/cli — Official "Obsidian CLI" reference (full command surface; fetched via `https://publish-01.obsidian.md/access/f786db9fac45774fa4f0d8112e232d67/Extending+Obsidian/Obsidian+CLI.md`)
- https://help.obsidian.md/obsidian-headless — Headless client overview (fetched via same publish API path `Extending+Obsidian/Obsidian+Headless.md`)
- https://obsidian.md/changelog/ — release notes: 1.12 introduces CLI; 1.12.3 fix Windows detection; 1.12.4 socket dotfile + silent default + unrecognized `--` flag ignore; 1.12.7+ required for stable CLI install/registration
- Yakitrak/obsidian-cli (now notesmd-cli) README — referenced via current cortex docs at `plugins/tools/cortex/docs/{设计决策.md,架构设计.md}`

## Caveats

- Behavior of `move` link-update is conditional on a vault setting — verify in install/doctor flow.
- TUI vs one-shot output formatting differs slightly; cortex skills must always pass explicit `format=json` where parsing is needed (`search`, `search:context`, `properties`, `backlinks`, `links`, `unresolved`, `tags`, `bookmarks`, `hotkeys`, `plugins`).
- Performance vs notesmd-cli: official CLI is much heavier (Electron-backed); each call goes through the running Obsidian process via socket. The "Go binary 10ms startup" advantage cited in `docs/设计决策.md` line 31 is **lost**. Latency profile shifts from "fast binary, no Obsidian needed" to "cheap socket call iff Obsidian already running, else multi-second cold start".
- `eval` command is power-user / dev mode; do not rely on it for production cortex paths without explicit user opt-in.
