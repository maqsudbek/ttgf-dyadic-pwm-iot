# Tooling Setup (MCP · Plugins · HDL toolchain)

Host: Orange Pi 5 Plus, Debian 12 arm64. `sudo` authorized.

## MCP servers (project scope)
Config lives at **repo-root `.mcp.json`** — the path Claude Code auto-loads (the old
`.claude/.mcp.json` was never read and has been removed). It is gitignored (Claude tooling, not
part of the TT submission).

Servers configured (both launched with `uvx`, so they need `uv`):
- **markitdown** → `uvx markitdown-mcp` — convert docs/HTML/PDF/Office → terse Markdown (token-efficient ingestion).
- **fetch** → `uvx mcp-server-fetch` — fetch web pages as Markdown.

Install `uv` (provides `uvx`) if missing:
```bash
pip install --user uv        # or: curl -LsSf https://astral.sh/uv/install.sh | sh
uvx markitdown-mcp --help     # warms/caches the server
uvx mcp-server-fetch --help
```
`uvx` lives in `~/.local/bin`, which is already on `PATH` via `~/.zshrc` and `~/.profile`.

Verify from Claude Code: restart the session, then `claude mcp list` (CLI) should show
`markitdown` and `fetch` connected. In the VSCode extension, MCP servers load from the same
`.mcp.json` on session start (approve the project servers when prompted). If the VSCode extension
can't find `uvx` (different PATH), replace `"command": "uvx"` in `.mcp.json` with the absolute path
`/home/orangepi/.local/bin/uvx`.

> Note: markitdown-mcp prints harmless `onnxruntime ... Failed to detect devices` warnings on this
> headless SBC — it still works.

## Plugins — Superpowers
Structured plan/test/review workflow + a large skills library. Installed via **interactive slash
commands the user runs** (the agent cannot invoke `/plugin`):
```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```
(Alternatively `/plugin install superpowers@claude-plugins-official`.)
If `/plugin` is unrecognized, update Claude Code and restart:
```bash
sudo npm update -g @anthropic-ai/claude-code
```

## Python venv (test deps)
System Python is **3.11.2**, pip **23.0.1**. Per best practice, project Python deps live in a
**`.venv`** at the repo root (gitignored). Already created with the pinned `test/requirements.txt`
(`cocotb==2.0.1`, `pytest==8.4.2`):
```bash
uv venv .venv --python 3.11
uv pip install --python .venv -r test/requirements.txt
```
Activate before running tests: `source .venv/bin/activate` (the Makefile calls `cocotb-config`).
Note: `uvx`-launched MCP servers do **not** use this venv — they self-manage their own envs.

## HDL toolchain (system, for local sim — needed when development starts)
The cocotb tests also need the **Icarus Verilog** simulator; waveforms need GTKWave (both via apt):
```bash
sudo apt-get update && sudo apt-get install -y iverilog gtkwave
```
The GDS/hardening flow (LibreLane, GF180MCU PDK) is heavier — see the `local-harden` skill and
<https://www.tinytapeout.com/guides/local-hardening/>.
