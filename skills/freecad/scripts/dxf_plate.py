# 2D DXF (outline + letters) -> printable plate with raised text and an optional key-ring hole.
# Run with freecadcmd; arguments come after "--" (inches). See ../SKILL.md.
import sys, os, argparse
import FreeCAD, Part, importDXF, Mesh, MeshPart
from FreeCAD import Vector as V

IN = 25.4
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--dxf", required=True)
ap.add_argument("--out")
ap.add_argument("--base", type=float, default=0.1, help="background thickness, in")
ap.add_argument("--text", type=float, default=0.03, help="letter height above background, in")
ap.add_argument("--hole", type=float, default=0.17, help="hole diameter, in (0 = none)")
ap.add_argument("--wall", type=float, default=0.047, help="min material around hole, in")
ap.add_argument("--corner", default="top-left", choices=["top-left", "top-right", "bottom-left", "bottom-right"])
ap.add_argument("--deflection", type=float, default=0.02, help="STL linear deflection, mm")
a = ap.parse_args(argv)
out = a.out or os.path.splitext(a.dxf)[0] + "_keychain"

src = FreeCAD.newDocument("src")
importDXF.insert(a.dxf, src.Name)
wires = [Part.Wire(o.Shape.Edges) for o in src.Objects
         if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Edges]
open_ = [w for w in wires if not w.isClosed()]
if open_:
    sys.exit("ERROR: %d open contour(s) in DXF; close them first" % len(open_))
wires.sort(key=lambda w: -Part.Face(w).Area)
outline, letters = wires[0], wires[1:]

bb = outline.BoundBox
shift = V(-bb.XMin, -bb.YMin, 0)
outline.translate(shift)
for w in letters:
    w.translate(shift)
outline_face = Part.Face(outline)
letter_face = Part.makeFace(letters, "Part::FaceMakerBullseye") if letters else None

base = outline_face.extrude(V(0, 0, a.base * IN))
if a.hole > 0:
    r, wall = a.hole * IN / 2, a.wall * IN
    bb = outline.BoundBox
    cx = bb.XMin if "left" in a.corner else bb.XMax
    cy = bb.YMax if "top" in a.corner else bb.YMin
    corner = V(cx, cy, 0)
    best, step = None, 0.25
    y = bb.YMin
    while y <= bb.YMax:
        x = bb.XMin
        while x <= bb.XMax:
            p = V(x, y, 0)
            d = (p - corner).Length
            if (best is None or d < best[0]) and outline_face.isInside(p, 1e-6, True):
                v = Part.Vertex(p)
                if v.distToShape(outline)[0] >= r + wall and \
                   (letter_face is None or v.distToShape(letter_face)[0] >= r + wall):
                    best = (d, p)
            x += step
        y += step
    if best is None:
        sys.exit("ERROR: no room for the hole with that wall")
    hp = best[1]
    base = base.cut(Part.makeCylinder(r, a.base * IN + 2, hp + V(0, 0, -1)))
    print("hole centre (in): %.3f, %.3f" % (hp.x / IN, hp.y / IN))

doc = FreeCAD.newDocument(os.path.basename(out).replace("-", "_"))
objs = [doc.addObject("Part::Feature", "Base")]
objs[0].Shape = base
parts = [("base", base)]
if letter_face:
    text = letter_face.extrude(V(0, 0, a.text * IN))
    text.translate(V(0, 0, a.base * IN))
    t = doc.addObject("Part::Feature", "Letters")
    t.Shape = text
    objs.append(t)
    parts += [("letters", text), ("combined", base.fuse(text).removeSplitter())]
doc.recompute()
FreeCAD.closeDocument(src.Name)
doc.saveAs(out + ".FCStd")
Part.export(objs, out + ".step")
for name, shp in parts:
    MeshPart.meshFromShape(shp, LinearDeflection=a.deflection, AngularDeflection=0.2).write(out + "_%s.stl" % name)

bb = base.BoundBox
print("base %.3f x %.3f x %.3f in, valid=%s" % (bb.XLength / IN, bb.YLength / IN, bb.ZLength / IN, base.isValid()))
if letter_face:
    print("letters %d solids, top at %.3f in, valid=%s" % (len(text.Solids), text.BoundBox.ZMax / IN, text.isValid()))
print("wrote", out + ".{FCStd,step}", "+ STLs")
