import io, json, os, sys
sys.path.insert(0, r"tools\re\toolbelt"); sys.path.insert(0, r"tools\text_csv"); sys.path.insert(0, r"tools\iso_build")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import tcslib as T
def run(iso, ncol, lead_hi, live_hi, outdir, prefix, tag):
    T.NCOL = ncol; T.LEAD_HI = lead_hi; T.PAIR_LEAD_HI = lead_hi
    cs_p = os.path.join(r"work\builds\GR_CAP2400\temp", "charset_live%d.json" % (live_hi + 1))
    T.Charset.__init__.__defaults__ = (cs_p,)
    import dump_font as DF
    DF.dump_font(os.path.abspath(iso), os.path.abspath(outdir), prefix, scale=1, want_png=False,
                 grid=False, only_sampled=False, verbose=False)
    s = json.load(io.open(os.path.join(outdir, prefix + "_font_summary.json"), encoding="utf-8"))
    g = s["glyph_geometry"]
    print("[%s] %dx%d" % (tag, s["atlas"]["width"], s["atlas"]["height"]))
    print("   verdict:", json.dumps(g["verdict"], ensure_ascii=False))
    print("   one_line:", g.get("one_line"))
    bad = [f for f in g.get("findings", []) if f.get("level") == "error"]
    for f in bad[:6]:
        print("   err:", json.dumps({k: f[k] for k in f if k not in ("note",)}, ensure_ascii=False)[:260])
run(r"work\builds\GR_CAP2400\_stage660.iso", 62, 0xBA, 1735, r"work\builds\GR_CAP2400\temp\dump_stage660_live", "stage660live", "STAGE h=660/62 (无图案, GATE 未改)")
