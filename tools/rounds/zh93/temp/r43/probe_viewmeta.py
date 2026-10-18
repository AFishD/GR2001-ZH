import json, io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'work/builds/GR_ZH92/text/GR_ZH92_view_containers.meta.json'
d = json.load(io.open(p, encoding='utf-8'))
def show(o, ind=0, keys=None):
    for k, v in o.items():
        if isinstance(v, dict):
            print(' '*ind + '%s:' % k); show(v, ind+2)
        elif isinstance(v, list):
            print(' '*ind + '%s: [list %d] %s' % (k, len(v), str(v[:3])[:160]))
        else:
            s = str(v)
            print(' '*ind + '%s: %s' % (k, s[:200]))
show(d)
