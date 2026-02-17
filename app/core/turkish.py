"""Turkish language utilities for character normalization.

Provides functions to normalize Turkish special characters (s, i, u, o, c,
g, I, S, etc.) to their ASCII equivalents.  This is essential for matching
province and district names that may arrive in different encodings from
external APIs (e.g. geoBoundaries, Google Trends, TKGM) vs. what is stored
in the database.

Examples of problematic name pairs:
    Sanliurfa  vs  Sanliurfa
    Kahramanmaras  vs  Kahramanmaras
    Kirsehir  vs  Kirsehir
    Duzce  vs  Duzce
    Agri  vs  Agri
    Mugla  vs  Mugla
    Istanbul  vs  Istanbul  (no special chars -- works without normalization)
"""
import unicodedata

# Direct mapping of Turkish-specific Unicode characters to ASCII equivalents.
_TURKISH_CHAR_MAP = str.maketrans({
    "\u015f": "s",   # s (Latin Small Letter S with Cedilla)
    "\u015e": "S",   # S (Latin Capital Letter S with Cedilla)
    "\u0131": "i",   # dotless i (Latin Small Letter Dotless I)
    "\u0130": "I",   # dotted I (Latin Capital Letter I with Dot Above)
    "\u00fc": "u",   # u with diaeresis
    "\u00dc": "U",   # U with diaeresis
    "\u00f6": "o",   # o with diaeresis
    "\u00d6": "O",   # O with diaeresis
    "\u00e7": "c",   # c with cedilla
    "\u00c7": "C",   # C with cedilla
    "\u011f": "g",   # g with breve
    "\u011e": "G",   # G with breve
    "\u00e2": "a",   # a with circumflex
    "\u00c2": "A",   # A with circumflex
    "\u00ee": "i",   # i with circumflex
    "\u00ce": "I",   # I with circumflex
    "\u00fb": "u",   # u with circumflex
    "\u00db": "U",   # U with circumflex
})


def normalize_turkish(text: str) -> str:
    """Normalize a Turkish string for safe comparison.

    Converts Turkish-specific letters to their ASCII equivalents and
    lowercases the result.  Also strips any remaining combining
    diacritical marks via NFD decomposition as a safety net for
    characters not covered by the explicit mapping.

    Args:
        text: The Turkish string to normalize.

    Returns:
        A lowercased, ASCII-safe version of the input string.

    Examples:
        >>> normalize_turkish("Sanliurfa")
        'sanliurfa'
        >>> normalize_turkish("Kahramanmaras")
        'kahramanmaras'
        >>> normalize_turkish("Istanbul")
        'istanbul'
        >>> normalize_turkish("Kirsehir")
        'kirsehir'
        >>> normalize_turkish("Duzce")
        'duzce'
        >>> normalize_turkish("Agri")
        'agri'
        >>> normalize_turkish("Mugla")
        'mugla'
        >>> normalize_turkish("SANLIURFA")
        'sanliurfa'
    """
    # First pass: direct Turkish character replacement
    result = text.translate(_TURKISH_CHAR_MAP)
    # Second pass: NFD decompose to strip any remaining accents
    result = unicodedata.normalize("NFD", result)
    result = "".join(ch for ch in result if unicodedata.category(ch) != "Mn")
    return result.lower().strip()
