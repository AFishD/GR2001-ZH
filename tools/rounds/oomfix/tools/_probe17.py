import json
for t in ('OOMFIX2400','OOMFIX_lay1'):
    m = json.load(open(r"work\builds\GR_OOMFIX\%s.meta.json" % t, encoding='utf-8'))
    print("== %s" % t)
    for k in ('base_file','base_sha256','base_elf_sha256','base_elf_lba','base_elf_bytes',
              'out','sha256','bytes','out_elf_sha256','diff_run_count','diff_bytes','iso_offsets'):
        print("   %-18s %s" % (k, m.get(k)))
    print("   f1:", json.dumps(m['f1'], ensure_ascii=False)[:320])
    print("   selfcheck:", m['selfcheck'])
