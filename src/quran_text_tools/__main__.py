"""python -m quran_text_tools QURAN.csv [FILE]   — check the verses quoted in FILE (or standard input)."""
import sys

from . import Quran, find_quotations


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__.strip()); return 2
    src = argv[0]
    quran = Quran.from_json(src) if src.endswith('.json') else Quran.from_csv(src)
    text = open(argv[1], encoding='utf-8').read() if len(argv) > 1 else sys.stdin.read()
    bad = 0
    for q in find_quotations(text, quran):
        mark = 'OK ' if q.correct else 'FIX'
        print(f'{mark} {q.ref}: {q.quoted}')
        if not q.correct:
            bad += 1
            for d in q.differences:
                print(f"      {d['kind']}: {d['written'] or '—'} → {d['mushaf'] or '—'}")
            print(f'      Mushaf: {q.suggestion}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
