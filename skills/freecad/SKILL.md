---
name: freecad
description: Model, convert, or edit CAD in FreeCAD 1.1 — prompt-to-part, DXF/SVG outline to 3D-printable plate/keychain/sign with raised text, STEP/STL/DXF export, editing .FCStd files, or live edits in the user's open FreeCAD window via the freecad MCP server. Use whenever the user mentions FreeCAD, .FCStd, or wants a 3D-printable part made from a description or a 2D file.
---

# FreeCAD

- Default Windows install: `C:\Program Files\FreeCAD 1.1\bin\` — `freecadcmd.exe` (headless), `freecad.exe` (GUI).
  On macOS/Linux use `FreeCADCmd`/`freecadcmd` and `freecad` from the install. Check the version before assuming APIs.
- User mod dir (Windows): `%APPDATA%\FreeCAD\v1-1\Mod` — the FreeCADMCP addon lives here.
- Internal units are **mm**. If the user works in inches, convert with `IN = 25.4` and report back in inches.

## Two ways to drive it

1. **Headless script (default for building/exporting).** Write a `.py` in the scratchpad and run
   `freecadcmd script.py`. Output is noisy — grep away the banner/progress lines. `print()` works.
   No `ViewObject`/colours/screenshots here.
2. **Live, in the user's open window** via the [freecad-mcp](https://github.com/neka-nat/freecad-mcp)
   server. Needs FreeCAD open with the addon's RPC server running (**MCP Addon** workbench →
   **Start RPC Server**, or **Auto-Start Server** ticked in its menu, stored in
   `<UserAppData>/freecad_mcp_settings.json` as `{"auto_start_rpc": true}`). Use it for anything visual:
   colours, view, screenshots to check work, editing what the user is looking at.
   - If tool calls fail with connection errors, ask the user to start the RPC server — don't relaunch FreeCAD.
   - MCP servers load at session start. If the tools aren't available yet, call the addon directly:
     `xmlrpc.client.ServerProxy("http://127.0.0.1:9875").execute_code(code)` → `{'success', 'message'/'error'}`.
   - Screenshots: `FreeCADGui.ActiveDocument.ActiveView.saveImage(path, w, h, "White")`, then read the PNG.

Never kill a FreeCAD process you didn't start; the user may have their own window with unsaved work.
On Windows check with `Get-Process freecad | Select Id, StartTime, MainWindowTitle`.

## Gotchas learned the hard way

- **DXF import:** `import importDXF; importDXF.insert(path, docName)`. It honours `$INSUNITS` (inch files
  arrive scaled ×25.4 → mm). HATCH entities are skipped (fine, outlines are SPLINE/polyline). Each closed
  spline becomes one `Part::Feature` with one edge; build wires with `Part.Wire(shape.Edges)`.
- **Text/letters with holes (D, a, o, the dot of i):** `Part.makeFace(wires, "Part::FaceMakerBullseye")`
  nests counters correctly. Don't fuse letter faces one by one.
- **Outline vs letters:** the largest-area closed wire is normally the background outline.
- **Placing a hole "at a corner"** on an irregular outline: grid-search points nearest the bbox corner,
  accept the first where `outline_face.isInside(p, 1e-6, True)` and `Part.Vertex(p).distToShape(...)`
  ≥ r + wall to both the outline and the letters. Report the min wall; < 1.5 mm is weak for a key ring.
- **Colours** are GUI-only (`ViewObject.ShapeColor`) — headless saves have no `GuiDocument.xml`. Set
  them through the MCP server, or launch `freecad script.py` (runs the script in a GUI instance).
- **Thumbnail** saved right after a scripted open is blank — don't use it to verify; take a screenshot
  or plot edges with matplotlib (bundled with FreeCAD's Python) to a PNG and look at it.
- **Claude desktop app on Windows is MSIX-sandboxed:** writes into *new* folders under
  `%LOCALAPPDATA%`/`%APPDATA%` (and the session `%TEMP%`) are redirected into the app's private
  `...\Packages\Claude_*\LocalCache` and are invisible to FreeCAD. Folders that already exist (e.g. FreeCAD's
  own) are fine. Put new tool installs and screenshot targets under `%USERPROFILE%` instead.
- STL via `MeshPart.meshFromShape(shape, LinearDeflection=0.02, AngularDeflection=0.2)` is very fine
  (~10 MB for a keychain); use 0.05 if the slicer complains.

## Output conventions

- Save next to the source file (e.g. `Name_keychain.*` beside `Name.dxf`) unless told otherwise.
- Deliver: `.FCStd` (separate named objects per colour/body), `.step` (all bodies), one STL per colour
  (shared coordinates so they stack in the slicer), plus a `_combined.stl` for single-colour printing.
- Verify before reporting: `shape.isValid()`, bounding box in the user's units, solid count, and a picture.

## Parametric (PartDesign) version — when the user wants a feature tree

Body → `OutlineSketch` (outline splines + hole circle, on XY) → `BasePad`; `LetterSketch` on XY with
`.AttachmentOffset.Base.z = Params.BaseT` (avoid attaching to pad faces — topological naming) → `LetterPad`.
Spreadsheet `Params` aliases BaseT/TextT/HoleD drive pad lengths and the hole's Diameter constraint.
Import DXF curves with `sk.addGeometry(edge.Curve.copy())` (segment if trimmed) + a `Block` constraint each.
One body = one solid, so colour via `body.ViewObject.DiffuseColor` per face (faces with ZMax > BaseT = letters);
per-colour STLs come from `BasePad.Shape` and `LetterPad.AddSubShape`.

## Recipe: 2D outline + raised text → printable plate

`scripts/dxf_plate.py` (next to this file) does the whole keychain job:

```bash
freecadcmd "<skill dir>/scripts/dxf_plate.py" -- \
  --dxf "path/to/Name.dxf" --base 0.1 --text 0.03 --hole 0.17 --corner top-left
```

Args are inches; `--hole 0` for no hole; `--wall` min material around the hole (default 0.047");
`--out` path prefix (default: DXF path without extension + `_keychain`). It prints the hole centre,
sizes and validity. Then open the `.FCStd` in the user's FreeCAD (or via MCP) and colour the parts.
