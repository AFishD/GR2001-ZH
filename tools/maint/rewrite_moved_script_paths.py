# -*- coding: utf-8 -*-
r"""rewrite_moved_script_paths.py -- minimal, mechanical path fix-up after the
work\ -> tools\ script relocation.

Why: ~150 relocated scripts bootstrap their shared libraries with
    sys.path.insert(0, os.path.join(REPO, 'work', 'tools'))
which pointed at the flat toolbelt that now lives in tools\re\toolbelt\.
Without this fix those scripts raise ModuleNotFoundError (zx_lib, tcslib,
cave_dis, cap_*, migrate_legacy, ...).

Policy -- only *code* references to moved scripts / the moved toolbelt are
rewritten.  Plain data references are left untouched on purpose:

  R1  import-bootstrap lines only (line contains `sys.path` or
      `spec_from_file_location`):
          'work', 'builds', 'GR_X'      ->  'tools', 'rounds', '<theme>'
          'work', 'tools'               ->  'tools', 're', 'toolbelt'
          r"work\tools"                 ->  r"tools\re\toolbelt"
          r"work\builds\GR_X\tools"     ->  r"tools\rounds\<theme>\tools"
  R2  any line, but only when the reference names a moved *script*:
          'work', 'tools', 'NAME.py'    ->  'tools', 're', 'toolbelt', 'NAME.py'
          work/tools/NAME.py            ->  tools/re/toolbelt/NAME.py
          work\tools\NAME.py            ->  tools\re\toolbelt\NAME.py

NOT rewritten (still valid -- these did NOT move):
  work\tools\ghidra\ , work\tools\jdk\ , work\tools\appdata\ ,
  work\tools\ghidra_out\ , work\tools\ghidra_proj*\ , work\tools\dl_urls*.txt ,
  work\tools\*.log , work\tools\gh.bat
NOT rewritten (historical data paths, registered in docs/CORRECTIONS.md):
  work/builds/GR_ZH93/GR_ZH93.iso  etc.

All patterns/replacements are pure ASCII and files are round-tripped through
latin-1, so every non-ASCII byte (GBK or UTF-8 comments alike) is preserved.

Usage:  python tools\maint\rewrite_moved_script_paths.py [--apply]
Without --apply it only reports what it would change.
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCOPE = [os.path.join(REPO, 'tools', 're', 'toolbelt'),
         os.path.join(REPO, 'tools', 'rounds')]

BOOTSTRAP = re.compile(r'sys\.path|spec_from_file_location')


def theme_of(build):
    b = build[3:] if build.startswith('GR_') else build
    return b.lower()


# ---------- R1: import-bootstrap lines ----------
R1_BUILDS = re.compile(r"""(['"])work\1(\s*,\s*)(['"])builds\3(\s*,\s*)(['"])(GR_[A-Za-z0-9_]+)\5""")
R1_TOOLS = re.compile(r"""(['"])work\1(\s*,\s*)(['"])tools\3""")
R1_RAW_BUILDS = re.compile(r"""(['"])work\\builds\\GR_([A-Za-z0-9_]+)((?:\\[^'"]*)?)\1""")
R1_RAW_TOOLS = re.compile(r"""(['"])work\\tools\1""")


def _fix_builds(m):
    q1, s1, q3, s2, q5, build = m.groups()
    return "%s%s%s%s%s%s%s%s%s" % (q1, 'tools', q1, s1, q3, 'rounds', q3, s2,
                                   q5 + theme_of(build) + q5)


def _fix_tools(m):
    q1, s1, q3 = m.groups()
    return "%s%s%s%s%s%s%s%s%s%s%s" % (q1, 'tools', q1, s1, q3, 're', q3, s1,
                                      q3, 'toolbelt', q3)


def _fix_raw_builds(m):
    q, build, tail = m.groups()
    return "%s%s%s" % (q, 'tools\\rounds\\' + theme_of(build) + tail, q)


def _fix_raw_tools(m):
    q = m.group(1)
    return "%s%s%s" % (q, 'tools\\re\\toolbelt', q)


# ---------- R2: script-name references on any line ----------
R2_JOIN_SCRIPT = re.compile(r"""(['"])work\1(\s*,\s*)(['"])tools\3(\s*,\s*)(['"])([A-Za-z0-9_.\-]+\.(?:py|java))\5""")
R2_RAW_SCRIPT = re.compile(r"""(['"])work\\tools\\([A-Za-z0-9_.\-]+\.(?:py|java))\1""")
R2_SLASH_SCRIPT = re.compile(r"""work/tools/([A-Za-z0-9_.\-]+\.(?:py|java))""")


def _fix_join_script(m):
    q1, s1, q3, s2, q5, name = m.groups()
    parts = [q1, 'tools', q1, s1, q3, 're', q3, s1, q3, 'toolbelt', q3, s2, q5, name, q5]
    return "".join(parts)


def _fix_raw_script(m):
    q, name = m.groups()
    return "%s%s%s" % (q, 'tools\\re\\toolbelt\\' + name, q)


def _fix_slash_script(m):
    return 'tools/re/toolbelt/' + m.group(1)


def rewrite_line(line):
    log = []
    if BOOTSTRAP.search(line):
        for name, rx, fn in (('R1-builds', R1_BUILDS, _fix_builds),
                             ('R1-raw-builds', R1_RAW_BUILDS, _fix_raw_builds),
                             ('R1-tools', R1_TOOLS, _fix_tools),
                             ('R1-raw-tools', R1_RAW_TOOLS, _fix_raw_tools)):
            def _s(m, _n=name, _f=fn):
                out = _f(m)
                if out != m.group(0):
                    log.append((_n, m.group(0), out))
                return out
            line = rx.sub(_s, line)
    for name, rx, fn in (('R2-join-script', R2_JOIN_SCRIPT, _fix_join_script),
                         ('R2-raw-script', R2_RAW_SCRIPT, _fix_raw_script),
                         ('R2-slash-script', R2_SLASH_SCRIPT, _fix_slash_script)):
        def _s2(m, _n=name, _f=fn):
            out = _f(m)
            if out != m.group(0):
                log.append((_n, m.group(0), out))
            return out
        line = rx.sub(_s2, line)
    return line, log


def main():
    apply = '--apply' in sys.argv
    files = []
    for root in SCOPE:
        for dirpath, _dirs, names in os.walk(root):
            for n in names:
                if os.path.splitext(n)[1].lower() in ('.py', '.ps1'):
                    files.append(os.path.join(dirpath, n))
    files.sort()

    changed = 0
    total_edits = 0
    for path in files:
        with open(path, 'rb') as fh:
            raw = fh.read()
        text = raw.decode('latin-1')
        out_lines = []
        log = []
        for line in text.split('\n'):
            nl, lg = rewrite_line(line)
            out_lines.append(nl)
            log.extend(lg)
        new = '\n'.join(out_lines)
        if new == text:
            continue
        changed += 1
        total_edits += len(log)
        rel = os.path.relpath(path, REPO).replace('/', '\\')
        print(rel.encode('ascii', 'backslashreplace').decode('ascii'))
        agg = {}
        for name, before, after in log:
            agg[(name, before, after)] = agg.get((name, before, after), 0) + 1
        for (name, before, after), cnt in sorted(agg.items()):
            msg = "    [%s] %s  ->  %s%s" % (name, before, after,
                                             "" if cnt == 1 else "   (x%d)" % cnt)
            print(msg.encode('ascii', 'backslashreplace').decode('ascii'))
        if apply:
            with open(path, 'wb') as fh:
                fh.write(new.encode('latin-1'))

    print("")
    print("scanned=%d  changed=%d  edits=%d  mode=%s"
          % (len(files), changed, total_edits, 'APPLY' if apply else 'REPORT-ONLY'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
