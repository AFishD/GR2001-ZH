# -*- coding: utf-8 -*-
r"""r58 快速复现: 把 plan_reencode 里两个"慢扫描"打桩, 只留**登记容器**那条路 (~30 秒)。
用来定位 "MENU.IMG#26 DE_STRINGS.RES 为什么没被追平"。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')

# ---- 打桩: 全盘粗扫 / 细扫 / 容器文本判别 ----
FC.scan_raw_iso = lambda iso, cs, verbose=True, min_bytes=None: []
FC.scan_short_text = lambda *a, **k: dict(candidates=[], stats=dict(
    spans=0, runs=0, runs_in_img=0, runs_outside=0, cand_runs=0, cand_spans=0,
    skipped_by_reason={}, n_pair_runs=0, n_pair_runs_outside=0,
    skipped_sample=[], pair_runs_outside=[]))

_orig_mig = FC.migration_index


def patched_index(mig):
    idx = _orig_mig(mig)
    print('[dbg] migration_index: %d 条' % len(idx))
    for k, v in idx.items():
        print('      %s  role=%-8s where=%s' % (k[:12], v['role'], v['where']))
    return idx


FC.migration_index = patched_index

_orig_reg = FC.registry_match


def patched_reg(name):
    r = _orig_reg(name)
    return r


FC.registry_match = patched_reg

res = FC.plan_compact(ISO, tcslib.CHARSET, verbose=False)
res['charset_path'] = tcslib.CHARSET
print('[dbg] plan_compact: changed=%s migration=%s' % (res['summary']['changed'],
                                                       bool(res['migration'])))
iso = tcslib.Iso(ISO)

# 手动看 mig_roles 的构造结果
mig_idx = FC.migration_index(res['migration'])
found = {}
for (tag, lba, idx, e) in FC.enumerate_containers(iso):
    rec = mig_idx.get(FC.sha256_b(iso.read(e['iso_off'], e['stored'])))
    if rec:
        found[(lba, idx)] = (tag, idx, e['name'], rec['role'])
print('[dbg] 内容寻址命中 %d 个:' % len(found))
for k, v in sorted(found.items(), key=lambda kv: kv[1][0]):
    print('      %-9s idx=%-5d %-24s role=%s' % v)

re_ = FC.plan_reencode(iso, res, verbose=False)
iso.close()
print('[dbg] writes:')
for w in re_['writes']:
    print('   %-34s %-8s %s' % (w['label'], w['detail']['kind'], w.get('method')))
print('[dbg] registry 报告:')
for r in re_['registry']:
    print('   %-34s role=%-10s src=%-28s 段 %-5d 重映射 %-5d 未变 %-5d 改 %d 字节  %s'
          % (r['container'], r['role'], r['src'], r['segments'], r['segments_changed'],
             r['segments_unchanged'], r['changed_bytes'], r.get('fingerprint') or ''))
