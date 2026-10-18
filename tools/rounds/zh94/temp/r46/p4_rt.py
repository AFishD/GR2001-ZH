# -*- coding: utf-8 -*-
r"""p4_rt.py — 验证「整体改码位后 inject 的 stale 守卫不会误报」。

守卫逻辑 (inject_text_csv.py L1042-1046):
    _t_old, _ = cs.decode(old);  stale = (cs.encode_strict(_t_old) != old)
即: 用**新** charset 解盘上旧字节, 再编回去, 必须逐字节相同。

本脚本: 造一个"把所有已用对偶码整体轮转 +1 槽"的新 charset (模拟重排后的映射),
对一批合成的字节串 (ASCII / 全部已用对偶码 / 单字节码 / 变成空槽的旧对偶码) 做上述往返。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                          # noqa: E402

cs0 = tcslib.Charset()
n = tcslib.pair_capacity()
used = {}
for ch, (b1, b2) in cs0.enc_pair.items():
    if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
        used[tcslib.pair_slot(b1, b2)] = ch
print('[cs ] 已用 pair 槽 %d / 容量 %d' % (len(used), n))

# 新映射 = 把已用槽按升序搬到"前 %d 个可用槽"(顺序保持) —— 与重排工具同一算法
usable = [s for s in range(n) if not tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((s // 62, s % 62))]
newchars = {}
for i, s in enumerate(sorted(used)):
    newchars[used[s]] = usable[i]
print('[cs ] 造新映射: %d 个字 → 新槽 (前 %d 个可用槽)' % (len(newchars), len(newchars)))
freed = sorted(set(used) - set(newchars.values()))
print('[cs ] 旧槽里变成"空槽"的: %d 个, 例 %s' % (len(freed), freed[:6]))

j = json.load(io.open(tcslib.CHARSET, encoding='utf-8'))
j2 = json.loads(json.dumps(j))
for ch, s in newchars.items():
    j2['pair_of'][ch] = [tcslib.PAIR_LEAD_LO + s // 94, tcslib.PAIR_TRAIL_LO + s % 94]
tmp = os.path.join(HERE, '_p4_charset.json')
io.open(tmp, 'w', encoding='utf-8', newline='\n').write(json.dumps(j2, ensure_ascii=False, indent=1))
cs1 = tcslib.Charset(tmp)

# 合成字节串: 真实文本里会出现的东西
samples = {}
samples['ascii'] = bytes(range(0x20, 0x7F))
samples['all_pair_used'] = b''.join(bytes(v) for v in sorted(cs0.enc_pair.values()))
samples['all_single'] = bytes(sorted(cs0.enc_single.values()))
samples['freed_pairs'] = b''.join(bytes([tcslib.PAIR_LEAD_LO + s // 94,
                                         tcslib.PAIR_TRAIL_LO + s % 94]) for s in freed[:200])
samples['mixed'] = (b'Hello' + bytes(cs0.enc_pair['区']) + bytes([0xB1]) + b' ' +
                    bytes(cs0.enc_single['键']) + bytes([0xE7]) + b'!')

fail = 0
for name, old in samples.items():
    try:
        t, _ = cs1.decode(old)
        back = cs1.encode_strict(t)
        ok = (back == old)
        why = ''
    except Exception as e:                                     # noqa: BLE001
        ok, back, why = False, None, '%s: %s' % (type(e).__name__, e)
    print('[rt ] %-16s len=%-6d round_trip=%s %s' % (name, len(old), 'OK' if ok else '**FAIL**', why))
    if not ok:
        fail += 1
        if back is not None:
            for k in range(min(len(old), len(back))):
                if old[k] != back[k]:
                    print('        首个不同 @%d: old=0x%02X back=0x%02X' % (k, old[k], back[k]))
                    break
os.remove(tmp)
print('[rt ] 失败 %d 组 (期望 0 ⇒ 重排后整体重编码不会被 stale 守卫拦下)' % fail)
sys.exit(1 if fail else 0)
