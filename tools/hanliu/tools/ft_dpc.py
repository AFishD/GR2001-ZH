# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/ft_dpc.py (复制+路径改造: sys.path 改为相对本目录 (FONT.RES DP 压缩内核))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""ft_dpc.py - LZO1X DP 最优解析压缩器 (FONT.RES 翻案实验专用, 语法=原盘实证子集)

状态机语法 (与 lz77_decode.lzo1x_decompress 逐条对齐):
  - 首令牌: 字面量段 L∈[1,238], token=L+17, 之后 ctx=R
  - ctx R (上一匹配 k=0 或初始段后): 令牌>15 -> M2/M3; 令牌<=15 -> 字面量段 L>=4, 之后 ctx=B
  - ctx B (字面量段后): 令牌>15 -> M2/M3; 令牌<=15 -> M4B (len3, back 2049..3072, 2B)
  - ctx A (上一匹配 k=1..3): 令牌>15 -> M2/M3; 令牌<=15 -> M4A (len2, back<=1024, 2B)
  - M2: len 3..8,  back<=2048,  2B     M3: len 3..288+, back<=16384, 3B(+ext)
  - 匹配后随 k=gap (gap<3 / gap==3->3) 免费字面量; gap>=4 -> k=0 + 段(1-2B token)
  - EOF: 0x11 00 00
不使用 M1 (back>=16385, 数据 7222B 内不可能)。DP 保证在该语法下全局最优。
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lz77_decode import lzo1x_decompress
from lzo1x_c import _hash3_list, _mlen

INF = float('inf')
R, B, A = 0, 1, 2
CTXN = ('R', 'B', 'A')


def _run_cost(L):
    if L <= 18:
        return 1 + L
    rem = L - 3
    c = 1
    while rem > 270:
        c += 1
        rem -= 255
    return c + 1 + L


def dp_compress(data, use_m4b=False, chain_cap=256, run_cap=640, verbose=False,
                verify=True, debug=None):
    d = data
    n = len(d)
    n3 = n - 2
    # --- 3 字节哈希链 ---
    h3 = _hash3_list(d, 17)
    head = [-1] * (1 << 17)
    prev = [0] * n
    for i in range(n3):
        prev[i] = head[h3[i]]
        head[h3[i]] = i
    # --- 2 字节链 (M4A 用, back<=1024) ---
    last2 = {}
    prev2 = [-1] * n
    for i in range(n - 1):
        k2 = (d[i] << 8) | d[i + 1]
        prev2[i] = last2.get(k2, -1)
        last2[k2] = i

    def m2_1024(i):
        j = prev2[i]
        cnt = 0
        while j >= 0 and i - j <= 1024 and cnt < 64:
            return i - j            # 链首即最近邻 = 最小 back
        return None

    def cand3(i):
        """返回 (A_any, A_near, mmid, Lmax): 按 len 的最小 back (全部 / <=2048), [2049,3072] 最小 back"""
        imax = n - i
        cap = 288 if imax > 288 else imax
        A_any = {}
        A_near = {}
        mmid = None
        Lmax = 0
        if cap >= 3:
            j = head[h3[i]]
            while j >= i:               # 链含全局插入位置, 跳过 >= i 的
                j = prev[j]
            cnt = 0
            blen = 0
            while j >= 0 and i - j <= 16384 and cnt < chain_cap:
                if blen:
                    qi = i + blen
                    if qi >= n or d[j + blen] != d[qi]:
                        j = prev[j]
                        cnt += 1
                        continue
                if d[j:j + 3] == d[i:i + 3]:
                    l = _mlen(d, n, j, i, cap)
                    if l > blen:
                        blen = l
                        b = i - j
                        if l > Lmax:
                            Lmax = l
                        for L in range(3, l + 1):
                            if L not in A_any:
                                A_any[L] = b
                                if b <= 2048:
                                    A_near[L] = b
                            elif b <= 2048 and L not in A_near:
                                A_near[L] = b
                        if 2049 <= b <= 3072 and (mmid is None or b < mmid):
                            mmid = b
                        if l >= cap:
                            break
                j = prev[j]
                cnt += 1
        return A_any, A_near, mmid, Lmax

    # --- 预收集候选 ---
    cands = [None] * n
    m2s = [None] * n
    for i in range(n):
        cands[i] = cand3(i)
        m2s[i] = m2_1024(i)

    # --- DP ---
    dp = [[INF] * 3 for _ in range(n + 1)]
    par = [None] * (n + 1)          # par[j][ctx] = (action, ...)
    for L in range(1, min(238, n) + 1):
        c = 1 + L
        if c < dp[L][R]:
            dp[L][R] = c
            par[L] = par[L] or [None] * 3
            par[L][R] = ('init', L, 0, 0, -1, R)

    def relax(i, ctx, L, cost, back, base):
        gmax = n - i - L
        for g in range(0, min(3, gmax) + 1):
            tok = base + cost + g          # 后置字面量占 g 个真实字节
            j = i + L + g
            nctx = A if g > 0 else R
            if tok < dp[j][nctx]:
                if dp[j][nctx] == INF:
                    par[j] = par[j] or [None] * 3
                dp[j][nctx] = tok
                par[j][nctx] = ('m', L, back, g, i, ctx)

    for i in range(n):
        A_any, A_near, mmid, Lmax = cands[i]
        row = dp[i]
        for ctx in (R, B, A):
            base = row[ctx]
            if base == INF:
                continue
            m2 = m2s[i]
            if ctx == A and m2 is not None:
                relax(i, ctx, 2, 2, m2, base)
            for L in range(3, Lmax + 1):
                nb = A_near.get(L) if L <= 8 else None   # M2 len 上限 8
                if nb is not None:
                    relax(i, ctx, L, 2, nb, base)
                    continue
                if L == 3 and use_m4b and mmid is not None:
                    relax(i, ctx, L, 2, mmid, base)
                ab = A_any.get(L)
                if ab is not None:
                    relax(i, ctx, L, 3, ab, base)
            if ctx == R:
                maxL = n - i
                hi = min(maxL, run_cap)
                for L in range(4, hi + 1):
                    c = _run_cost(L)
                    j = i + L
                    t = base + c
                    if t < dp[j][B]:
                        if dp[j][B] == INF:
                            par[j] = par[j] or [None] * 3
                        dp[j][B] = t
                        par[j][B] = ('run', L, 0, 0, i, ctx)
                if maxL > run_cap:
                    L = maxL
                    c = _run_cost(L)
                    j = n
                    t = base + c
                    if t < dp[j][B]:
                        if dp[j][B] == INF:
                            par[j] = par[j] or [None] * 3
                        dp[j][B] = t
                        par[j][B] = ('run', L, 0, 0, i, ctx)

    endc = min(range(3), key=lambda c: dp[n][c])
    total = dp[n][endc] + 3
    if dp[n][endc] == INF:
        raise RuntimeError('DP 无解')
    if verbose:
        print('DP best=%d (+EOF 3 = %d)' % (dp[n][endc], total))

    # --- 回溯 ---
    items = []
    j, ctx = n, endc
    while j > 0:
        act = par[j][ctx]
        if act is None:
            raise RuntimeError('回溯断裂 @%d ctx=%s' % (j, CTXN[ctx]))
        items.append(act)
        j = act[4]
        ctx = act[5]
    items.reverse()

    # --- 序列化 ---
    out = bytearray()
    pos = 0
    for kind, L, back, g, src, sctx in items:
        if kind == 'init':
            out.append(L + 17)
            out += d[pos:pos + L]
            pos += L
        elif kind == 'run':
            if L <= 18:
                out.append(L - 3)
            else:
                out.append(0)
                rem = L - 3
                while rem > 270:
                    out.append(0)
                    rem -= 255
                out.append(rem - 15)
            out += d[pos:pos + L]
            pos += L
        else:  # match
            k = g
            if L == 2:                      # M4A (仅 ctx A 合法)
                assert sctx == A, 'L=2 但 ctx=%s' % CTXN[sctx]
                bd = back - 1
                out.append(((bd & 3) << 2) | k)
                out.append(bd >> 2)
            elif back <= 2048 and L <= 8:   # M2
                out.append(((L - 1) << 5) | (((back - 1) & 7) << 2) | k)
                out.append((back - 1) >> 3)
            elif use_m4b and sctx == B and 2049 <= back <= 3072 and L == 3:  # M4B (仅 ctx B)
                bd = back - 2049
                out.append(((bd & 3) << 2) | k)
                out.append(bd >> 2)
            else:                            # M3
                if L <= 33:
                    out.append(0x20 | (L - 2))
                else:
                    out.append(0x20)
                    rem = L - 2
                    while rem > 286:
                        out.append(0)
                        rem -= 255
                    out.append(rem - 31)
                out.append((((back - 1) & 63) << 2) | k)
                out.append((back - 1) >> 6)
            out += d[pos + L:pos + L + k]
            pos += L + k
    assert pos == n, 'pos=%d n=%d' % (pos, n)
    out += b'\x11\x00\x00'
    payload = bytes(out)

    if debug is not None:
        debug['items'] = items
        debug['payload'] = payload

    # --- 双模式自检 ---
    if verify:
        b1, e1, _ = lzo1x_decompress(payload, out_size=n)
        b2, e2, _ = lzo1x_decompress(payload)
        if e1 is not None or b1 != d:
            raise RuntimeError('out_size 模式自检失败: %s' % e1)
        if e2 is not None or b2 != d:
            raise RuntimeError('自由模式自检失败: %s' % e2)
    return payload


if __name__ == '__main__':
    data = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'ft_expanded.bin'), 'rb').read()
    for kw in ({'use_m4b': False}, {'use_m4b': True}):
        p = dp_compress(data, verbose=True, **kw)
        print('use_m4b=%s -> payload %d B (limit 4413, orig 4413, prev-best 4439)'
              % (kw['use_m4b'], len(p)))
        if len(p) <= 4413 and not kw['use_m4b']:
            open(os.path.join(REPO_ROOT, 'work', 'tmp', 'ft_payload_id.bin'), 'wb').write(p)
            print('saved ft_payload_id.bin (无 M4B, 最保守语法)')
        elif len(p) <= 4413:
            open(os.path.join(REPO_ROOT, 'work', 'tmp', 'ft_payload_id_m4b.bin'), 'wb').write(p)
