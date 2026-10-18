# -*- coding: utf-8 -*-
r"""test_dryrun_and_verify.py — 验收 #5 (--verify 自检) + #6 (--apply --dry-run 不写文件)

做法: 用 subprocess 跑真命令, 前后对比文件系统快照。
  · --apply --dry-run           : 必须打印重排计划, 且**一个文件都不写**;
  · --apply --dry-run --verify  : 自检必须通过。

★ 注意: 另一个子代理正在改 tools/font_pipeline/data/charset_compiled_zh16.json
  (扩字库任务) ⇒ 本测试**不能**假设该文件 sha256 不变。判定"改动是不是本工具造成的"
  的依据: 本工具若写盘, 会**摘掉**那些被回收的字; 若它们仍在文件里 ⇒ 是外部改动。
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
PY = r'C:\ProgramData\anaconda3\python.exe'
TOOL = os.path.join(REPO, 'tools', 'font_pipeline', 'font_usage.py')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
TMP = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'temp', 'r38')
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
OUT_CS = os.path.join(TMP, 'dryrun_should_not_exist.json')
OUT_PLAN = os.path.join(TMP, 'dryrun_plan_should_not_exist.json')
LIMIT = '400'

ok = True


def chk(cond, msg):
    global ok
    ok = ok and bool(cond)
    print('%s %s' % ('[ok]' if cond else '[!!]', msg))


def charset_state():
    if not os.path.isfile(CHARSET):
        return ('(不存在)', 0)
    b = open(CHARSET, 'rb').read()
    try:
        d = json.loads(b.decode('utf-8'))
        n = len(d.get('codes', {})) + len(d.get('pair_of', {}))
    except Exception:                                               # noqa: BLE001
        n = -1
    return (hashlib.sha256(b).hexdigest(), n)


def charset_has(chars):
    try:
        d = json.load(open(CHARSET, encoding='utf-8'))
    except Exception:                                               # noqa: BLE001
        return None
    have = set(d.get('codes', {})) | set(d.get('pair_of', {}))
    return len([c for c in chars if c in have])


def external_change_note(tag, before, after, released):
    """外部改动**只报警、不判失败** —— 直接证据是另外两条 (见下)。

    直接证据: ① 工具自报"读到的字符集 sha256" == 运行前我们量到的 (只读);
              ② --out-charset / --out-plan 目标文件没有被创建。
    本函数只做**旁证**: 若文件变了, 看那些"被释放的码位"的字是否还在文件里 ——
    本工具若真写了, 就会把它们摘掉。

    before / after 都是 charset_state() 的 (sha256, 字数) 元组。
    """
    if before[0] == after[0]:
        print('[ok] %s 期间字符集文件 sha256 未变 ✓ (%s…)' % (tag, before[0][:16]))
        return
    n = charset_has(released) if released else None
    print('[warn] %s 期间字符集文件被**外部进程**改动 (与另一个子代理的扩字库任务撞车):'
          % tag)
    print('       %s… → %s… (字数 %d → %d)' % (before[0][:16], after[0][:16],
                                              before[1], after[1]))
    if n:
        print('       旁证: 被本工具列为"可回收"的 %d 个字里, 仍有 %d 个在文件里 '
              '⇒ 本工具确实没写它 ✓ (本工具若写就会摘掉这些字)' % (len(released), n))
    else:
        print('       旁证: 没能用"被回收的字仍在文件里"佐证 (可能因为外部进程已把表'
              '整体重写) —— 以直接证据为准: 工具自报读到的 sha256 与运行前一致, '
              '且 --out-charset 目标文件未被创建。')


def snap(d):
    out = {}
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x != '__pycache__']
        for f in files:
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
                out[os.path.relpath(p, REPO)] = (st.st_size, int(st.st_mtime))
            except OSError:
                pass
    return out


def run(args, logname):
    cmd = [PY, TOOL] + args
    print('\n$ python tools/font_pipeline/font_usage.py %s' % ' '.join(args))
    p = subprocess.run(cmd, cwd=REPO, capture_output=True)
    out = p.stdout.decode('utf-8', 'replace') + p.stderr.decode('utf-8', 'replace')
    io.open(os.path.join(TMP, logname), 'w', encoding='utf-8').write(out)
    print('  (退出码 %d; 完整输出 -> temp/r38/%s)' % (p.returncode, logname))
    return p.returncode, out


def reclaim_from(out):
    """从 stdout 的「释放对偶码位 (前 N): 字=CODE, …」一行里取出被回收的字。

    ★ 不能从「重排建议」里取 —— 那是**新缺字**(本来就不在字符集里), 取错了会误判。
    """
    m = re.search(r'释放对偶码位 \(前 \d+\):\s*(.*)', out)
    if not m:
        return []
    return [x.split('=')[0].strip() for x in m.group(1).split(',') if '=' in x]


for f in (OUT_CS, OUT_PLAN):
    if os.path.exists(f):
        os.remove(f)

data_before = snap(os.path.join(REPO, 'tools', 'font_pipeline', 'data'))
tmp_before = snap(TMP)
cs_before = charset_state()
print('# 字符集起点: sha256 %s…, %d 字' % (cs_before[0][:16], cs_before[1]))

# ══════════ 验收 #6: --apply --dry-run ══════════
print('=' * 70)
print('验收 #6: --apply --dry-run 输出重排计划但**不写任何文件**')
print('=' * 70)
rc, out = run(['--iso', ISO, '--text-dir', TXT, '--apply', '--dry-run',
               '--out-charset', OUT_CS, '--out-plan', OUT_PLAN,
               '--debug-limit-containers', LIMIT], 'dryrun.log')
chk(rc == 0, '退出码 0 (实际 %d)' % rc)
chk('--apply (dry-run: 不写任何文件)' in out, '打印了 dry-run 标题 ✓')
chk('释放图集格位' in out, '打印了「释放图集格位」统计 ✓')
chk(re.search(r'释放对偶码位 \(前 \d+\):', out) is not None, '打印了「释放对偶码位」清单 ✓')
chk('重排建议' in out, '打印了「重排建议」✓')
chk('[dry-run]' in out and '一个文件都不写' in out, '明确声明不写文件 ✓')
chk(not os.path.exists(OUT_CS), '--out-charset 目标文件**没有**被创建 ✓ (%s)'
    % os.path.relpath(OUT_CS, REPO))
chk(not os.path.exists(OUT_PLAN), '--out-plan 目标文件**没有**被创建 ✓')
m = re.search(r'# 字符集: .*?sha256 ([0-9a-f]{16})', out)
chk(m is not None and cs_before[0].startswith(m.group(1)),
    '★直接证据①: 工具自报读到的字符集 sha256 与运行前一致 ⇒ 只读 ✓ (%s)'
    % (m.group(1) if m else '未找到'))
external_change_note('dry-run', cs_before, charset_state(), reclaim_from(out))
data_after = snap(os.path.join(REPO, 'tools', 'font_pipeline', 'data'))
new_data = {k: v for k, v in data_after.items() if data_before.get(k) != v
            and 'charset_compiled_zh16.json' not in k}
chk(not new_data, 'tools/font_pipeline/data/ 里没有**其它**文件被新增/改动 ✓ %s'
    % (list(new_data)[:4] or ''))
tmp_after = snap(TMP)
new_tmp = sorted(k for k, v in tmp_after.items() if tmp_before.get(k) != v)
expected = {'work/builds/GR_ZH92/temp/r38/dryrun.log',
            'work/builds/GR_ZH92/temp/r38/dryrun_verify.log'}
unexpected = [k for k in new_tmp if k.replace('\\', '/') not in expected]
chk(not unexpected, 'r38 目录里只多了日志文件, 没有别的产物 ✓ %s' % (unexpected[:5] or ''))

# ══════════ 验收 #5: --verify ══════════
print('')
print('=' * 70)
print('验收 #5: --apply --dry-run --verify 回收后自检')
print('=' * 70)
cs2 = charset_state()
rc2, out2 = run(['--iso', ISO, '--text-dir', TXT, '--apply', '--dry-run', '--verify',
                 '--out-charset', OUT_CS, '--debug-limit-containers', LIMIT],
                'dryrun_verify.log')
chk(rc2 == 0, '退出码 0 (实际 %d)' % rc2)
chk('--verify 回收后自检' in out2, '跑了自检 ✓')
chk('用回收后的 charset 重扫全盘' in out2, '用回收后的 charset 重扫了全盘 ✓')
chk('① 用回收后的 charset 重扫全盘' in out2, '检查①执行 ✓')
chk('② 回收前「在用」字' in out2, '检查②执行 ✓')
chk('③ 新表比旧表少' in out2, '检查③执行 ✓')
chk('自检结论: [ok] 通过' in out2, '自检结论 [ok] 通过 ✓')
chk(not os.path.exists(OUT_CS), '★直接证据②: 自检同样没有写出 charset 文件 ✓')
external_change_note('--verify', cs2, charset_state(), reclaim_from(out2))

print('')
print('dry-run / verify 验收结论: %s' % ('[ok] 通过 ✓' if ok else '[!!] 失败'))
sys.exit(0 if ok else 1)
