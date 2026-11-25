"""Tools for working with the text of the Quran in Uthmani (Mushaf) script.

- ``skeleton``: fold Mushaf spelling and typed Arabic to the same key, so «ٱلصَّلَوٰةَ» matches «الصلاة».
- ``find_quotations``: find every verse quoted in a text and check it word by word against the Mushaf.
"""
from .normalize import fold, initial_hamza, near_one, skeleton, strip_marks
from .verses import Quotation, Quran, diff, find_quotations

__all__ = ['fold', 'strip_marks', 'skeleton', 'initial_hamza', 'near_one', 'Quran', 'Quotation', 'find_quotations', 'diff']
__version__ = '0.1.0'
