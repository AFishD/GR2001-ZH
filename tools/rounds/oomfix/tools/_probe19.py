import json, hashlib, os
for t in ('OOMFIX2400','OOMFIX_lay1'):
    m = json.load(open(r"work\builds\GR_OOMFIX\%s.meta.json" % t, encoding='utf-8'))
    iso = os.path.join('work','builds','GR_OOMFIX', t + '.iso')
    h = hashlib.sha256()
    with open(iso,'rb') as f:
        for b in iter(lambda: f.read(1<<22), b''): h.update(b)
    print("%s: meta.sha256=%s  实际=%s  %s" % (t, m['sha256'], h.hexdigest(), 'OK' if m['sha256']==h.hexdigest() else 'FAIL'))
    print("   新字段: %s" % [k for k in ('cave_rationale','cave_audit','savestate_note','verification','summary') if k in m])
