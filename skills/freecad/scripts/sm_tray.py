"""Rectangular sheet-metal tray/table top with flanges on all four sides, built with the
FreeCAD SheetMetal workbench (Params spreadsheet -> sketch -> base wall -> flanges -> unfold).

Run headless (the unfold can crash a GUI session if networkx is missing):

    freecadcmd sm_tray.py -- --length 48 --width 36 --flange 2 --thk 0.125 --ir 0.083 --k 0.4289 --out tray.FCStd

All sizes in inches. Flange height is the overall outside height. Needs the SheetMetal add-on and
networkx (pip install --target <UserAppData>/AdditionalPythonPackages/py311 networkx).
Open the saved file in the GUI and set Unfold.GenerateSketch = True to get the unfold sketches.
"""
import argparse, sys
import FreeCAD as App, Part, Sketcher
from FreeCAD import Vector as V
import SheetMetalBaseCmd as B, SheetMetalCmd as C, SheetMetalUnfoldCmd as U

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--length", type=float, default=48.0)
ap.add_argument("--width", type=float, default=36.0)
ap.add_argument("--flange", type=float, default=2.0)
ap.add_argument("--thk", type=float, default=0.125)
ap.add_argument("--ir", type=float, default=0.083)
ap.add_argument("--k", type=float, default=0.4289)
ap.add_argument("--up", action="store_true", help="flanges up (tray) instead of down (table top)")
ap.add_argument("--out", default="sm_tray.FCStd")
a = ap.parse_args(argv)
IN = 25.4

doc = App.newDocument("SMTray")
doc.UnitSystem = "Imperial decimal (in, lb)"
sp = doc.addObject("Spreadsheet::Sheet", "Params")
# aliases must not look like cell refs (T, K, IR ... are rejected)
for r, (n, v, al) in enumerate([("Length", f"{a.length} in", "Length"), ("Width", f"{a.width} in", "Width"),
                                 ("Flange height (outer)", f"{a.flange} in", "FlangeH"),
                                 ("Thickness", f"{a.thk} in", "Thickness"),
                                 ("Inside radius", f"{a.ir} in", "InnerRadius"),
                                 ("K-factor (ANSI)", f"{a.k}", "KFactor")], start=1):
    sp.set(f"A{r}", n); sp.set(f"B{r}", "=" + v); sp.setAlias(f"B{r}", al)
doc.recompute()

L, W = a.length * IN, a.width * IN
sk = doc.addObject("Sketcher::SketchObject", "TopSketch")
p = [V(0, 0, 0), V(L, 0, 0), V(L, W, 0), V(0, W, 0)]
for i in range(4): sk.addGeometry(Part.LineSegment(p[i], p[(i + 1) % 4]))
for i in range(4): sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
sk.addConstraint(Sketcher.Constraint("Horizontal", 0)); sk.addConstraint(Sketcher.Constraint("Horizontal", 2))
sk.addConstraint(Sketcher.Constraint("Vertical", 1)); sk.addConstraint(Sketcher.Constraint("Vertical", 3))
sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, L))
sk.addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, W))
sk.setExpression("Constraints[9]", "Params.Length"); sk.setExpression("Constraints[10]", "Params.Width")

base = doc.addObject("Part::FeaturePython", "BaseWall")
B.SMBaseBend(base, sk)
base.setExpression("Thickness", "Params.Thickness"); base.setExpression("Radius", "Params.InnerRadius")
doc.recompute()
s = base.Shape
top = [f for f in s.Faces if abs(f.normalAt(0, 0).z) > 0.99 and f.BoundBox.ZMax > 1e-6][0]
edges = ["Edge%d" % (i + 1) for i, be in enumerate(s.Edges) if any(be.isSame(e) for e in top.Edges)]

fl = doc.addObject("Part::FeaturePython", "Flanges")
C.SMBendWall(fl, base, edges)
fl.setExpression("radius", "Params.InnerRadius"); fl.setExpression("length", "Params.FlangeH")
fl.LengthSpec = "Outer Sharp"      # flange length = overall outside height
fl.BendType = "Material Inside"    # outside size stays = sketch
fl.angle = 90; fl.AutoMiter = True
fl.invert = not a.up               # edges are on the top face: invert sends flanges down
doc.recompute()
f = fl.Shape; bb = f.BoundBox
print("FORMED valid", f.isValid(), "solids", len(f.Solids),
      "bbox in", round(bb.XLength / IN, 4), round(bb.YLength / IN, 4), round(bb.ZLength / IN, 4))

planes = [(i + 1, fc) for i, fc in enumerate(f.Faces)
          if fc.Surface.TypeId == "Part::GeomPlane" and abs(fc.normalAt(0, 0).z) > 0.99]
face = "Face%d" % max(planes, key=lambda t: t[1].Area)[0]
uf = doc.addObject("Part::FeaturePython", "Unfold")
U.SMUnfold(uf, fl, [face])
uf.KFactorStandard = "ansi"; uf.MaterialSheet = "_manual"
uf.setExpression("KFactor", "Params.KFactor")
uf.GenerateSketch = False          # needs a ViewObject; enable in the GUI
doc.recompute()
u = uf.Shape
if u.isNull():
    print("UNFOLD failed (is networkx installed?)", uf.State)
else:
    ub = u.BoundBox
    print("UNFOLD valid", u.isValid(), "flat in", round(ub.XLength / IN, 4), round(ub.YLength / IN, 4))
doc.saveAs(a.out)
print("saved", a.out)
