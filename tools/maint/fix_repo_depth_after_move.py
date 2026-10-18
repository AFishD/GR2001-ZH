# -*- coding: utf-8 -*-
r"""fix_repo_depth_after_move.py -- second half of the work\ -> tools\ fix-up.

Scripts that lived in work\tools\        (repo-relative depth 2) now live in
                    tools\re\toolbelt\   (depth 3), and
scripts that lived in work\_planc\       (depth 2) now live in
                    tools\rounds\planc\  (depth 3).

Their repo-root computation is therefore one level short:
    REPO = os.path.abspath(os.path.join(HERE, '..', '..'))          -> tools\
Fix: append one more '..' -- but ONLY on the line that assigns the root
variable, and only for the two directories that actually changed depth.

Directories whose depth did NOT change are untouched:
    work\builds\<B>\            -> tools\rounds\<theme>\           (3 -> 3)
    work\builds\<B>\tools\      -> tools\rounds\<theme>\tools\     (4 -> 4)
    work\builds\<B>\temp\rNN\   -> tools\rounds\<theme>\temp\rNN\  (5 -> 5)
    work\tools\ghidra_scripts\  -> tools\re\ghidra_scripts\        (3 -> 3)
Files with a hardcoded absolute REPO (68 of them) are already correct and are
not matched by these patterns.

Usage:  python tools\maint\fix_repo_depth_after_move.py [--apply]
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCOPE = [os.path.join(REPO, 'tools', 're', 'toolbelt'),
         os.path.join(REPO, 'tools', 'rounds', 'planc')]

# only the root-variable assignment line
ROOTLINE = re.compile(r'^\s*(REPO|ROOT|_ROOT|REPO_ROOT|BASE_DIR)\s*=')

# append one '..' to a two-levels-up join
PATTERNS = [
    (re.compile(r"""(['"])\.\.\1(\s*,\s*)(['"])\.\.\3(?!\s*,\s*['"]\.\.['"])\s*\)"""),
     lambda m: "%s..%s%s%s..%s, %s..%s)" % (m.group(1), m.group(1), m.group(2),
                                            m.group(3), m.group(3),
                                            m.group(3), m.group(3))),
]


def fix_line(line):
    if not ROOTLINE.match(line):
        return line, False
    new, n = PATTERNS[0][0].subn(PATTERNS[0][1], line)
    return new, (n > 0)


def main():
    apply = '--apply' in sys.argv
    files = []
    for root in SCOPE:
        for n in sorted(os.listdir(root)):
            if n.lower().endswith('.py'):
                files.append(os.path.join(root, n))

    changed = 0
    for path in files:
        with open(path, 'rb') as fh:
            text = fh.read().decode('latin-1')
        out = []
        hits = []
        for line in text.split('\n'):
            nl, ok = fix_line(line)
            out.append(nl)
            if ok:
                hits.append((line.strip(), nl.strip()))
        if not hits:
            continue
        changed += 1
        rel = os.path.relpath(path, REPO).replace('/', '\\')
        print(rel.encode('ascii', 'backslashreplace').decode('ascii'))
        for before, after in hits:
            print(("    " + before + "\n      -> " + after)
                  .encode('ascii', 'backslashreplace').decode('ascii'))
        if apply:
            with open(path, 'wb') as fh:
                fh.write('\n'.join(out).encode('latin-1'))

    print("")
    print("scanned=%d  changed=%d  mode=%s" % (len(files), changed,
                                               'APPLY' if apply else 'REPORT-ONLY'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
