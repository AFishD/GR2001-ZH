# -*- coding: utf-8 -*-
r"""f364_probe2.py -- 只读: SFXML/LANG 里 0xB4 的精确落点（文本 payload vs 结构区/属性区）"""
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402

spec = importlib.util.spec_from_file_location(
    'inj', os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'))
INJ = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(INJ)
except SystemExit:
    pass
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def main():
    iso = T.Iso(sys.argv[1] if len(sys.argv) > 1
                else os.path.join(REPO, 'work', 'builds', 'GR_F364', '_stage640.iso'))
    for name, sp in T.RES.items():
        for cp in sp['copies']:
            e = iso.img_entry(cp[1], cp[2])
            blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
            offs = [i for i, b in enumerate(blob) if b == 0xB4]
            if name == 'LANG':
                ents, used = T.parse_lang(blob)
                rng = [(x.data_off, x.data_off + x.length) for x in ents]
                P('[%s] blob %d used_end %d 条目 %d 0xB4 %d' % (cp[3], len(blob), used,
                                                                len(ents), len(offs)))
            else:
                rng = [(o, o + l) for (_k, o, l, _b) in T.parse_sfxml(blob)]
                used = T.xml_tail_start(blob)
                attrs = INJ.parse_xml_attrs(blob)
                P('[%s] blob %d used_end %d 文本块 %d 属性 %d 0xB4 %d'
                  % (cp[3], len(blob), used, len(rng), len(attrs), len(offs)))
            arng = []
            if name == 'SFXML':
                arng = [(o, o + len(v)) for (_k, _t, o, v) in INJ.parse_xml_attrs(blob)]

            def hit(i, rs):
                return any(s <= i < t for (s, t) in rs)
            in_t = [i for i in offs if hit(i, rng)]
            in_a = [i for i in offs if hit(i, arng)]
            rest = [i for i in offs if not hit(i, rng) and not hit(i, arng)]
            P('    文本 payload %d ; 属性 %d ; 结构/陈旧尾 %d (其中 >= used_end 的 %d)'
              % (len(in_t), len(in_a), len(rest),
                 sum(1 for i in rest if i >= used)))
            for i in rest[:14]:
                P('      rest @%-7d %r' % (i, blob[max(0, i - 36):i + 16]))
            # 属性值里的样本
            for i in in_a[:8]:
                P('      attr @%-7d %r' % (i, blob[max(0, i - 36):i + 16]))
    iso.close()


if __name__ == '__main__':
    main()
