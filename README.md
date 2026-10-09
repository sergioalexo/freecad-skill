# freecad-skill

A [Claude Code](https://claude.com/claude-code) skill for driving [FreeCAD](https://www.freecad.org/) 1.1:
prompt-to-part modelling, turning a 2D DXF (outline + lettering) into a 3D-printable keychain/sign,
STEP/STL export, and live edits in an open FreeCAD window through the
[freecad-mcp](https://github.com/neka-nat/freecad-mcp) server.

It's mostly the gotchas that cost time in practice — DXF units, letters with counters, GUI-only colours,
blank thumbnails, the Windows Claude app sandbox — plus a ready-made plate/keychain script.

## Install

Copy the skill folder into your Claude skills directory:

```bash
git clone https://github.com/sergioalexo/freecad-skill.git
cp -r freecad-skill/skills/freecad ~/.claude/skills/
```

Claude Code picks it up automatically next session.

### Optional: live editing via MCP

1. Copy `addon/FreeCADMCP` from [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp) into
   FreeCAD's `Mod` folder (Windows: `%APPDATA%\FreeCAD\v1-1\Mod`), restart FreeCAD, switch to the
   **MCP Addon** workbench and click **Start RPC Server** (tick **Auto-Start Server** to keep it on).
2. Install the server (`uvx freecad-mcp`, or `pip install` it into a venv) and register it with Claude Code,
   e.g. in `~/.claude.json`:

   ```json
   "mcpServers": {
     "freecad": { "command": "uvx", "args": ["freecad-mcp"] }
   }
   ```

   On Windows with the Claude desktop app, put any venv under `%USERPROFILE%`, not AppData (see SKILL.md).

## The keychain script

```bash
freecadcmd skills/freecad/scripts/dxf_plate.py -- --dxf name.dxf --base 0.1 --text 0.03 --hole 0.17 --corner top-left
```

The DXF should contain closed contours: the largest is the background outline, the rest are the
letters. Dimensions are in inches. Outputs `name_keychain.FCStd`, `.step`, and base/letters/combined STLs.

## License

MIT
