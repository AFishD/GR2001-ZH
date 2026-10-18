import io, json, os, sys
sys.path.insert(0, r"tools\re\toolbelt"); sys.path.insert(0, r"tools\text_csv"); sys.path.insert(0, r"tools\iso_build")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import tcslib as T
def run(iso, ncol, lead_hi, live_hi, outdir, prefix, tag):
    T.NCOL = ncol; T.LEAD_HI = lead_hi; T.PAIR_LEAD_HI = lead_hi
    cs_p = os.path.join(r"work\builds\GR_CAP2400\temp", "charset_live%d.json" % (live_hi + 1))
    T.Charset.__init__.__defaults__ = (cs_p,)
    import dump_font as DF
    DF.dump_font(os.path.abspath(iso), os.path.abspath(outdir), prefix, scale=1, want_png=True,
                 grid=True, only_sampled=True, verbose=False)
    s = json.load(io.open(os.path.join(outdir, prefix + "_font_summary.json"), encoding="utf-8"))
    g = s["glyph_geometry"]
    print("[%s] %dx%d ink=%d" % (tag, s["atlas"]["width"], s["atlas"]["height"], s["atlas"]["ink_texels"]))
    print("   verdict:", json.dumps(g["verdict"], ensure_ascii=False))
    print("   one_line:", g.get("one_line"))
    print("   capacity:", json.dumps(s["capacity"]["pair"], ensure_ascii=False)[:200])
    bad = [f for f in g.get("findings", []) if f.get("level") == "error"]
    for f in bad[:4]:
        print("   err:", json.dumps(f, ensure_ascii=False)[:240])
run(r"work\builds\GR_CAP2400\GR_CAP2400_h644_clean.iso", 64, 0xBA, 1735,
    r"work\builds\GR_CAP2400\temp\dump_h644_c64_clean_live", "h644c64clean", "CLEAN h=644/64 (无图案)")
