# Pulse FFmpeg MCP

**AI-powered video processing over the Model Context Protocol**

Pulse FFmpeg MCP turns natural-language video requests into reliable FFmpeg pipelines. It combines FastTrack analysis, multi-agent orchestration, and professional encoding defaults for music videos and automated edits.

Repository: [github.com/ismailubts/pulse-ffmpeg-mcp](https://github.com/ismailubts/pulse-ffmpeg-mcp)

---

## Why Pulse

| Area | What you get |
|------|----------------|
| Cost | FastTrack analysis around $0.02–0.05 per pass |
| Speed | ~2s automated analysis vs ~30s manual review |
| Reliability | Timebase/conflict checks before xfade and concat |
| Output | YouTube-friendly YUV420P finals |

## Core capabilities

### FastTrack analysis
- Detects alignment and timebase issues early
- Suggests strategies and transitions (44 xfade effects)
- Optional AI enhancement with heuristic offline fallback

### Multi-agent orchestration
- **Pulse** — master workflow coordinator
- **FastTrack** — cheap, precise video strategy
- **Build Detective** — CI/build failure triage
- **Komposteur bridge** — beat-synced music video flows
- **VideoRenderer** — crossfade and encode optimization

### Production defaults
- Separate video (`-an`) and external audio assembly
- Compatibility encode for player-safe delivery
- Structured MCP tools for Claude Desktop / Claude Code

---

## Project layout

```
pulse-ffmpeg-mcp/
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── src/                 # MCP server + FastTrack + processors
├── docs/                # Guides
├── tests/               # Unit and CI checks
├── tools/               # FastTrack CLI + Build Detective scripts
├── examples/            # Komposition templates and workflows
└── .claude/             # Agent configs
```

## Quick start

### Install
```bash
git clone https://github.com/ismailubts/pulse-ffmpeg-mcp.git
cd pulse-ffmpeg-mcp
uv sync
```

### Run the MCP server
```bash
uv run python -m src.server
```

### FastTrack CLI
```bash
./tools/ft .testdata/
```

### Claude Desktop / Claude Code config
```json
{
  "mcpServers": {
    "pulse-ffmpeg": {
      "command": "uv",
      "args": ["run", "python", "-m", "src.server"],
      "cwd": "/path/to/pulse-ffmpeg-mcp"
    }
  }
}
```

## Example prompts

- Create a 30-second music video from two clips and a 135 BPM track
- Analyze a clip and pick the best 10-second social cut
- Layer speech over background music while keeping dialogue clear

## Local CI check

```bash
uv run python tests/test_basic_ci.py && echo "CI PASSED"
```

## Author

**ismailubts**

## License

MIT — see `LICENSE`.
