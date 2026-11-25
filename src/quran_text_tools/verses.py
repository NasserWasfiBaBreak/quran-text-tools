"""Find the Quran quoted in any text, and check each quotation word by word against the Mushaf.

A pasted text (a sermon, an article, a post) is read word by word. Every run of words that is in the Quran is found
with its place, and compared with the Mushaf: a word changed, left out or added. Spelling is never a difference (see
``normalize.skeleton``), but «أ» written where the Mushaf has «إ» at the start of a word is.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from typing import Iterable

from .normalize import ARABIC_WORD, initial_hamza, skeleton

QUOTE = re.compile('[«»"“”﴿﴾]')            # a quotation never runs over one of these
STOP = re.compile(r'[.،؛:!?؟\n«»"“”﴿﴾()\[\]]')   # a mark that ends a quotation
PAUSE_END = re.compile('[ۖ-ۜ]$')      # a Quranic pause mark at the end of a word
MAX_WORDS = 8000


@dataclass
class Verse:
    surah: int
    ayah: int
    text: str


class Quran:
    """The Quran as a list of verses, in Mushaf order. Load it from the official text (not bundled with this package).

    Accepted sources: an iterable of (surah, ayah, text); a CSV with columns ``surah``, ``ayah``, ``text``; or a JSON
    list of objects with those keys (or of [surah, ayah, text] lists).
    """

    def __init__(self, verses: Iterable[tuple[int, int, str]]):
        self.verses = [Verse(int(s), int(a), t) for s, a, t in verses]
        if not self.verses:
            raise ValueError('no verses')
        self.words = [v.text.split() for v in self.verses]
        self._stream = None

    @classmethod
    def from_csv(cls, path: str) -> 'Quran':
        with open(path, encoding='utf-8-sig', newline='') as f:
            return cls((r['surah'], r['ayah'], r['text']) for r in csv.DictReader(f))

    @classmethod
    def from_json(cls, path: str) -> 'Quran':
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return cls((r['surah'], r['ayah'], r['text']) if isinstance(r, dict) else tuple(r[:3]) for r in data)

    # the whole text as one stream of skeleton words, each with its verse and its first and last word in that verse
    def stream(self):
        if self._stream is None:
            raw = []
            for v, ws in enumerate(self.words):
                for p, x in enumerate(ws):
                    s = skeleton(x)
                    if s:
                        raw.append({'s': s, 'h': initial_hamza(x), 'v': v, 'p': p, 'e': p})
            w = _join_ya(raw, lambda t, n: t['v'] == n['v'])
            idx3, idx2 = {}, {}
            for k in range(len(w) - 2):
                idx3.setdefault(w[k]['s'] + ' ' + w[k + 1]['s'] + ' ' + w[k + 2]['s'], []).append(k)
            for k in range(len(w) - 1):
                idx2.setdefault(w[k]['s'] + ' ' + w[k + 1]['s'], []).append(k)
            self._stream = (w, idx3, idx2)
        return self._stream

    def wording(self, fq: int, tq: int) -> str:
        """The Mushaf's own words for a run of the stream, with the verse numbers between verses."""
        W = self.stream()[0]
        out, v, p = [], W[fq]['v'], W[fq]['p']
        end_v, end_p = W[tq]['v'], W[tq]['e']
        while v < end_v or (v == end_v and p <= end_p):
            if p >= len(self.words[v]):
                out.append(f'({self.verses[v].ayah})')
                v += 1; p = 0
                continue
            out.append(self.words[v][p])
            p += 1
        return ' '.join(out)


def _join_ya(ts, apart):
    """يا and ها written apart (يا أيها، ها أنتم) are one word in the Mushaf (يَٰٓأَيُّهَا): joined on both sides."""
    out, k = [], 0
    while k < len(ts):
        t = ts[k]
        n = ts[k + 1] if k + 1 < len(ts) else None
        if t['s'] in ('ي', 'ه') and n and apart(t, n):
            m = dict(n); m['s'] = re.sub('ي+', 'ي', t['s'] + n['s'])   # يا+أيها folds like يَٰٓأَيُّهَا
            for key in ('a', 'p'):
                if key in t:
                    m[key] = t[key]
            out.append(m); k += 2
        else:
            out.append(t); k += 1
    return out


def _tokens(text: str):
    out = []
    for m in ARABIC_WORD.finditer(text):
        s = skeleton(m.group())
        if s:
            out.append({'s': s, 'h': initial_hamza(m.group()), 'a': m.start(), 'b': m.end()})
    return _join_ya(out, lambda t, n: text[t['b']:n['a']].strip() == '')


def _marked(text: str, T):
    """Token ranges inside quotation marks: ﴿…﴾ «…» "…" “…”."""
    segs, k = [], 0
    for m in re.finditer(r'[﴿﴾]([^﴿﴾]*)[﴿﴾]|«([^»]*)»|"([^"\n]*)"|“([^”]*)”', text):
        a, b = m.start(), m.end()
        while k < len(T) and T[k]['b'] <= a:
            k += 1
        e = k
        while e < len(T) and T[e]['b'] <= b:
            e += 1
        if e > k:
            segs.append((k, e - 1))
    return segs


def diff(a: list[str], b: list[str]) -> list[dict]:
    """Word-by-word differences of two runs (longest common subsequence).

    ``eq`` the same word; ``sub`` a word changed; ``ins`` a word added in ``a``; ``del`` a word of ``b`` left out.
    ``i`` indexes ``a`` and ``q`` indexes ``b``.
    """
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for x in range(n - 1, -1, -1):
        for y in range(m - 1, -1, -1):
            L[x][y] = L[x + 1][y + 1] + 1 if a[x] == b[y] else max(L[x + 1][y], L[x][y + 1])
    ops, ins, dele = [], [], []

    def flush():
        k = min(len(ins), len(dele))
        for j in range(k):
            ops.append({'t': 'sub', 'i': ins[j], 'q': dele[j]})
        ops.extend({'t': 'ins', 'i': i} for i in ins[k:])
        ops.extend({'t': 'del', 'q': q} for q in dele[k:])
        ins.clear(); dele.clear()

    x = y = 0
    while x < n and y < m:
        if a[x] == b[y]:
            flush(); ops.append({'t': 'eq', 'i': x, 'q': y}); x += 1; y += 1
        elif L[x + 1][y] >= L[x][y + 1]:
            ins.append(x); x += 1
        else:
            dele.append(y); y += 1
    ins.extend(range(x, n)); dele.extend(range(y, m))
    flush()
    return ops


@dataclass
class Quotation:
    """One run of the text found in the Quran."""
    start: int                  # character offsets of the quotation in the text
    end: int
    quoted: str                 # the text as written
    surah: int                  # where it starts and ends in the Mushaf
    ayah: int
    to_surah: int
    to_ayah: int
    mushaf: str                 # the Mushaf's own wording for that place
    correct: bool               # no word changed, left out or added
    differences: list[dict] = field(default_factory=list)   # {'kind': 'changed'|'missing'|'added', 'written', 'mushaf'}
    also_at: list[tuple[int, int]] = field(default_factory=list)   # other places with the same wording
    suggestion: str = ''        # the Mushaf's wording to use instead, when not correct

    @property
    def ref(self) -> str:
        if (self.surah, self.ayah) == (self.to_surah, self.to_ayah):
            return f'{self.surah}:{self.ayah}'
        if self.surah == self.to_surah:
            return f'{self.surah}:{self.ayah}-{self.to_ayah}'
        return f'{self.surah}:{self.ayah}-{self.to_surah}:{self.to_ayah}'


def find_quotations(text: str, quran: Quran) -> list[Quotation]:
    """Every run of ``text`` that is in the Quran, compared word by word with the Mushaf, in the order of the text."""
    W, idx3, idx2 = quran.stream()
    T = _tokens(text)[:MAX_WORDS]
    n = len(T)

    def apart(i, j):
        if not (0 <= i < n and 0 <= j < n):
            return False
        lo, hi = min(i, j), max(i, j)
        return bool(QUOTE.search(text[T[lo]['b']:T[hi]['a']]))

    def eq(i, q):
        return 0 <= i < n and 0 <= q < len(W) and T[i]['s'] == W[q]['s']

    def stop_after(k):
        return k >= n - 1 or bool(STOP.search(text[T[k]['b']:T[k + 1]['a']]))

    # 1. three words in a row found in the Mushaf (seeds), chained along the same alignment
    chains, live = [], {}
    for i in range(n - 2):
        for d in [d for d, c in live.items() if i - c['li'] > 6]:
            del live[d]
        ps = idx3.get(T[i]['s'] + ' ' + T[i + 1]['s'] + ' ' + T[i + 2]['s'])
        if not ps or len(ps) > 1500:
            continue
        for q in ps:
            d = q - i
            c = live.get(d)
            x = 1
            while x <= 3 and not c:
                c = live.get(d - x) or live.get(d + x); x += 1
            if c and q > c['lq'] and i > c['li'] and not apart(c['li'], i + 2):
                if c['d'] != d:
                    live.pop(c['d'], None); c['d'] = d; live[d] = c
                c['li'], c['lq'] = i, q
            else:
                c = {'fi': i, 'fq': q, 'li': i, 'lq': q, 'd': d}
                live[d] = c; chains.append(c)
    # inside quotation marks two words in a row are a start too
    marked = _marked(text, T)
    for s, e in marked:
        for i in range(s, e):
            ps = idx2.get(T[i]['s'] + ' ' + T[i + 1]['s'])
            if ps and len(ps) <= 300:
                chains.extend({'fi': i, 'fq': q, 'li': i - 1, 'lq': q - 1} for q in ps)

    # 2. each chain grown at both ends, over at most two changed, missing or added words
    def grow(i, q, dr):
        ed = 0
        while True:
            if apart(i, i + dr):
                break
            if eq(i + dr, q + dr):
                i += dr; q += dr; continue
            if ed >= 2:
                break
            if not apart(i, i + 2 * dr) and eq(i + dr, q + 2 * dr) and eq(i + 2 * dr, q + 3 * dr):
                i += dr; q += 2 * dr; ed += 1; continue          # a word left out
            if not apart(i, i + 3 * dr) and eq(i + 2 * dr, q + dr) and eq(i + 3 * dr, q + 2 * dr):
                i += 2 * dr; q += dr; ed += 1; continue          # a word added
            if not apart(i, i + 3 * dr) and eq(i + 2 * dr, q + 2 * dr) and eq(i + 3 * dr, q + 3 * dr):
                i += 2 * dr; q += 2 * dr; ed += 1; continue      # a word changed
            break
        return i, q

    found = {}
    for c in chains:
        fi, fq = grow(c['fi'], c['fq'], -1)
        ti, tq = grow(c['li'] + 2, c['lq'] + 2, 1)
        sg = next(((s, e) for s, e in marked if s <= ti and e >= fi), None)
        if sg and fi - sg[0] <= 4 and sg[1] - ti <= 4:          # inside quotation marks: the whole marked text
            if sg[0] < fi:
                fq = max(0, fq - (fi - sg[0])); fi = sg[0]
            if sg[1] > ti:
                tq = min(len(W) - 1, tq + (sg[1] - ti)); ti = sg[1]
        elif (not sg and not stop_after(ti) and stop_after(ti + 1) and tq + 1 < len(W) and W[tq + 1]['v'] == W[tq]['v']
              and (tq + 2 >= len(W) or W[tq + 2]['v'] != W[tq]['v'])):
            ti += 1; tq += 1                                    # the last word of a verse, changed, before a full stop
        key = (fi, ti, fq)
        if key in found:
            continue
        ops = diff([t['s'] for t in T[fi:ti + 1]], [w['s'] for w in W[fq:tq + 1]])
        eq_n = sum(o['t'] == 'eq' for o in ops)
        hz = 0
        for o in ops:                                           # أ against إ
            if o['t'] == 'eq':
                a_, b_ = T[fi + o['i']]['h'], W[fq + o['q']]['h']
                if a_ and b_ and a_ != b_:
                    o['t'] = 'sub'; hz += 1
        edits = sum(o['t'] != 'eq' for o in ops)
        if eq_n < (3 if sg else 4) or (edits - hz) * 3 > eq_n + 1:
            continue
        found[key] = {'fi': fi, 'ti': ti, 'fq': fq, 'tq': tq, 'ops': ops, 'eq': eq_n, 'edits': edits}

    # 3. the best reading of each part of the text; places as good as it are kept with it
    R = sorted(found.values(), key=lambda r: (-r['eq'], r['edits'], r['fi'], r['ops'][0]['t'] != 'eq', r['fq']))
    res = []
    for r in R:
        hit = next((o for o in res if r['fi'] <= o['ti'] and r['ti'] >= o['fi']), None)
        if not hit:
            r['alts'] = []; res.append(r)
        elif (r['eq'] == hit['eq'] and r['edits'] == hit['edits'] and abs(r['fi'] - hit['fi']) <= 1
              and abs(r['ti'] - hit['ti']) <= 1 and W[hit['fq']]['v'] != W[r['fq']]['v']
              and not any(W[x['fq']]['v'] == W[r['fq']]['v'] for x in hit['alts'])):
            hit['alts'].append(r)
    res.sort(key=lambda r: r['fi'])
    return [_quotation(r, text, T, W, quran) for r in res]


def _right(r, W, quran):
    """The Mushaf's wording to suggest: its place, less an edge word that a pause mark sets apart from the rest."""
    def ends(q):
        w = W[q]
        return bool(PAUSE_END.search(' '.join(quran.words[w['v']][w['p']:w['e'] + 1])))
    a, b = r['fq'], r['tq']
    for o in r['ops']:
        if o['t'] == 'eq':
            break
        if o.get('q') is not None and ends(r['fq'] + o['q']):
            a = r['fq'] + o['q'] + 1
        else:
            break
    for o in reversed(r['ops']):
        if o['t'] == 'eq':
            break
        if o.get('q') is not None and o['q'] > 0 and ends(r['fq'] + o['q'] - 1):
            b = r['fq'] + o['q'] - 1
        else:
            break
    return a, b


def _quotation(r, text, T, W, quran) -> Quotation:
    def where(q):
        v = quran.verses[W[q]['v']]
        return v.surah, v.ayah
    s1, a1 = where(r['fq'])
    s2, a2 = where(r['tq'])
    kinds = {'sub': 'changed', 'del': 'missing', 'ins': 'added'}
    diffs = []
    for o in r['ops']:
        if o['t'] == 'eq':
            continue
        written = text[T[r['fi'] + o['i']]['a']:T[r['fi'] + o['i']]['b']] if 'i' in o else ''
        mushaf = quran.wording(r['fq'] + o['q'], r['fq'] + o['q']) if 'q' in o else ''
        diffs.append({'kind': kinds[o['t']], 'written': written, 'mushaf': mushaf})
    correct = r['edits'] == 0
    return Quotation(
        start=T[r['fi']]['a'], end=T[r['ti']]['b'], quoted=text[T[r['fi']]['a']:T[r['ti']]['b']],
        surah=s1, ayah=a1, to_surah=s2, to_ayah=a2, mushaf=quran.wording(r['fq'], r['tq']), correct=correct,
        differences=diffs, also_at=[where(x['fq']) for x in r['alts']],
        suggestion='' if correct else quran.wording(*_right(r, W, quran)))
