import io, json, os, sys
sys.path.insert(0, r"tools\re\toolbelt"); sys.path.insert(0, r"tools\text_csv"); sys.path.insert(0, r"tools\iso_build")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import tcslib as T
def run(iso, ncol, lead_hi, live_hi, outdir, prefix, tag):
    T.NCOL = ncol; T.LEAD_HI = lead_hi; T.PAIR_LEAD_HI = lead_hi
    raw = json.load(io.open(T.CHARSET, encoding="utf-8"))
    keep = {ch: p for ch, p in raw["pair_of"].items()
            if (int(p[0]) - T.LEAD_LO) * T.PAIR_STRIDE + (int(p[1]) - T.PAIR_TRAIL_LO) <= live_hi}
    cs_p = os.path.join(r"work\builds\GR_CAP2400\temp", "charset_live%d.json" % (live_hi + 1))
    if not os.path.exists(cs_p):
        t = dict(raw); t["pair_of"] = keep
        json.dump(t, io.open(cs_p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    T.Charset.__init__.__defaults__ = (cs_p,)
    import dump_font as DF
    DF.dump_font(os.path.abspath(iso), os.path.abspath(outdir), prefix, scale=1, want_png=True,
                 grid=True, only_sampled=True, verbose=False)
    s = json.load(io.open(os.path.join(outdir, prefix + "_font_summary.json"), encoding="utf-8"))
    g = s["glyph_geometry"]
    print("[%s] pair_of=%d 已用=%d 容量=%d" % (tag, len(keep), s["capacity"]["pair"]["used"], s["capacity"]["pair"]["capacity"]))
    print("   geometry verdict:", json.dumps(g["verdict"], ensure_ascii=False))
    print("   one_line:", g.get("one_line"))
    print("   atlas:", s["atlas"]["width"], "x", s["atlas"]["height"], "ink", s["atlas"]["ink_texels"])
    return s
run(r"work\builds\GR_ZH124\GR_ZH124.iso", 62, 0xB4, 1735, r"work\builds\GR_CAP2400\temp\dump_base_live", "baselive", "BASE h=512/62 (对照)")
run(r"work\builds\GR_CAP2400\GR_CAP2400.iso", 64, 0xBA, 1735, r"work\builds\GR_CAP2400\temp\dump_h644_c64_live", "h644c64live", "PROBE h=644/64")
run(r"work\builds\GR_CAP2400\GR_CAP2400_h660.iso", 62, 0xBA, 1735, r"work\builds\GR_CAP2400\temp\dump_h660_c62_live", "h660c62live", "PROBE h=660/62")
