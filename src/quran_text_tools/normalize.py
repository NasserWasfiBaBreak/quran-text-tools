"""Fold Uthmani (Mushaf) spelling and ordinary typed Arabic to the same letters.

The Mushaf's spelling differs from what people type: diacritics and Quranic marks, the wasla alif (ٱ), the seats of
the hamza (أ إ آ ؤ ئ), alif maqsura (ى), ta marbuta (ة), the small alif (ٰ) that stands where modern spelling writes ا
or nothing (ٱلرَّحۡمَٰنِ: الرحمن / الرحمان), و with a small alif read as ا (ٱلصَّلَوٰةَ: الصلاة), and the small و and ي that
are only heard after a final pronoun (بِهِۦ). All of these fold away, so a word becomes its *skeleton*.
"""
import re

_SKIP = re.compile('[ً-ٟۖ-ۭـء]')     # marks, tatweel, bare hamza
_TO = {'ٱ': 'ا', 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ة': 'ه', 'ؤ': 'و', 'ئ': 'ي', 'ٰ': '~'}
_MARKS = re.compile('[ً-ٰٟۖ-ۭـ]')

ARABIC_WORD = re.compile('[ء-ٰٟٱۖ-ۭـ]+')


def fold(text: str) -> str:
    """Letters only: marks dropped, hamza seats and ٱ to ا, ى to ي, ة to ه; the small alif kept as «~»."""
    out = []
    for c in text:
        if c != 'ٰ' and _SKIP.match(c):
            continue
        out.append(_TO.get(c, c))
    return ''.join(out)


def strip_marks(text: str) -> str:
    """The text without diacritics and Quranic marks (letters unchanged)."""
    return _MARKS.sub('', text)


def skeleton(word: str) -> str:
    """A spelling-free key for one word: equal skeletons mean the same written word, however it is spelled.

    >>> skeleton('ٱلصَّلَوٰةَ') == skeleton('الصلاة')
    True
    """
    w = re.sub('[ۥۦ](?=[^ء-ي]*$)', '', word)     # small و/ي after a final pronoun: heard, not written
    w = re.sub('[ۦۧ]', 'ي', w).replace('ۥ', 'و')
    s = fold(w).replace('و~', '')
    s = re.sub('[ا~]', '', s)
    s = re.sub('و+', 'و', s)
    s = re.sub('ي+', 'ي', s)
    return re.sub(r'\s+', '', s)


def initial_hamza(word: str) -> str:
    """The hamza a word starts with (after و ف ب ك ل): «أ», «إ» or ''. Skeletons fold them together; this tells them apart."""
    m = re.match('^[وف]?[بكل]?([أإ])', _MARKS.sub('', word))
    return m.group(1) if m else ''


def near_one(a: str, b: str) -> bool:
    """True when two strings differ by at most one letter added, dropped or changed."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    i = j = d = 0
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1; j += 1; continue
        d += 1
        if d > 1:
            return False
        if la > lb:
            i += 1
        elif lb > la:
            j += 1
        else:
            i += 1; j += 1
    return d + (la - i) + (lb - j) <= 1
