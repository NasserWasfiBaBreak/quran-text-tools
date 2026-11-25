# quran-text-tools

Match the Uthmani (Mushaf) text of the Quran with ordinary typed Arabic, and find every verse quoted in a text and
check it word by word against the Mushaf.

From the makers of [Quranic Atlas](https://quranicatlas.com) (أطلس علاقات الكلمات القرآنية), where the same method
powers the verse checker (مدقق الآيات).

## Why

People type «الصلاة», «الرحمن», «يا أيها»; the Mushaf writes «ٱلصَّلَوٰةَ», «ٱلرَّحۡمَٰنِ», «يَٰٓأَيُّهَا». Plain string
matching fails on almost every word. Quotations in sermons, articles and posts often carry a changed word («ربي» for
«رب»), a missing one, or «أن» where the Mushaf has «إن». This library handles both.

## Install

```bash
pip install quran-text-tools
```

Or the latest code: `pip install git+https://github.com/NasserWasfiBaBreak/quran-text-tools`

Python 3.9+, no dependencies.

## The Quran text

The text is **not bundled**. Use the official text of the King Fahd Complex for the Printing of the Holy Quran
(مجمع الملك فهد لطباعة المصحف الشريف), Hafs from ʿĀṣim, and respect its terms. Load it from a CSV with columns `surah`,
`ayah`, `text`, or a JSON list:

```python
from quran_text_tools import Quran
quran = Quran.from_csv('quran_hafs.csv')
```

## Use

```python
from quran_text_tools import find_quotations, skeleton

skeleton('ٱلصَّلَوٰةَ') == skeleton('الصلاة')          # True

for q in find_quotations('قال تعالى: ﴿وقل ربي زدني علما﴾', quran):
    print(q.ref, q.correct)                         # 20:114 False
    print(q.differences)                            # [{'kind': 'changed', 'written': 'ربي', 'mushaf': 'رَّبِّ'}]
    print(q.suggestion)                             # وَقُل رَّبِّ زِدۡنِي عِلۡمٗا
```

From the command line:

```bash
echo 'قال تعالى: ﴿وقل ربي زدني علما﴾' | python -m quran_text_tools quran_hafs.csv
```

## What counts as a difference

- **Not a difference (spelling):** diacritics and Quranic marks; ٱ أ إ آ (= ا); ى (= ي); ة (= ه); hamza seats; the
  small alif and و with a small alif (الرحمن / الرحمان, الصلاة); the small و/ي heard after a final pronoun (بِهِۦ);
  «يا أيها» written as two words.
- **A difference:** a word changed, left out or added, and «أ» where the Mushaf has «إ» (or the reverse) at the start
  of a word.

A quotation needs at least four matching words (three inside quotation marks), with at most one edit for every three
matching words. Text inside quotation marks («…» ﴿…﴾ "…") is compared as a whole, and a quotation never runs across a
quotation mark. When the same wording occurs in several places, `also_at` lists them.

## License

MIT. The Quran text you load is under its own terms.
