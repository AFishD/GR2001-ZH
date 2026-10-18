# -*- coding: utf-8 -*-
"""_probe_env.py -- 环境探针: 检查 numpy / PIL / cv2 可用性。"""
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

for mod in ('numpy', 'PIL', 'cv2'):
    try:
        m = __import__(mod)
        print('%-6s OK   %s' % (mod, getattr(m, '__version__', '?')))
    except Exception as e:                                            # noqa: BLE001
        print('%-6s FAIL %r' % (mod, e))
print('python', sys.version)
