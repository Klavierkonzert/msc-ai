import pickle, pprint, sys
p = sys.argv[1] if len(sys.argv) > 1 else 'stats/2026-06-05_16/HoF-f9-0-0.logbook.pkl'
print('Loading', p)
with open(p, 'rb') as f:
    lb = pickle.load(f)
print('Type:', type(lb))
ch = getattr(lb, 'chapters', None)
print('Has chapters:', ch is not None)
if ch is not None:
    try:
        print('Chapter keys:', list(ch.keys()))
    except Exception as e:
        print('Error listing chapters:', e)
print('run_duration_s attr:', getattr(lb, 'run_duration_s', None))
print('len(lb)=', len(lb))
print('\nFirst entry preview:')
if len(lb) > 0:
    e = lb[0]
    print('Type of entry:', type(e))
    if isinstance(e, dict):
        pprint.pprint({k: (str(v)[:200] if not isinstance(v, (list, dict)) else f'<{type(v).__name__} len={len(v)}>') for k, v in e.items()})
    else:
        print(repr(e)[:1000])
print('\nAll attributes containing duration/time:')
for a in dir(lb):
    if 'duration' in a or 'time' in a:
        try:
            print(a, getattr(lb, a))
        except Exception:
            print(a, '<unreadable>')
print('Done')
