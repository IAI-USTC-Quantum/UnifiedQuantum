#!/usr/bin/env python3
"""
Post-process Sphinx-generated .tex files to fix Unicode characters
that the PDF fonts cannot render.
"""
import sys

# UTF-8 → LaTeX replacements
REPLACEMENTS = {
    # Greek letters (math mode)
    b'\xcf\x88': r'\psi',       b'\xce\xb8': r'\theta',
    b'\xce\xbb': r'\lambda',    b'\xce\xb6': r'\phi',
    b'\xce\xb5': r'\epsilon',   b'\xcf\x80': r'\pi',
    b'\xce\xb2': r'\beta',       b'\xce\xb1': r'\alpha',
    b'\xce\xb3': r'\gamma',      b'\xce\xb4': r'\delta',
    b'\xce\xb7': r'\eta',        b'\xce\xbd': r'\nu',
    b'\xce\xbe': r'\xi',         b'\xce\xbf': r'\omega',
    b'\xce\xa1': r'\Alpha',      b'\xce\xa4': r'\Delta',
    b'\xce\xa7': r'\Eta',        b'\xce\xa8': r'\Theta',
    b'\xce\x9b': r'\Lambda',     b'\xce\x9c': r'\Xi',
    b'\xce\x9d': r'\Pi',         b'\xce\x9e': r'\Sigma',
    b'\xce\xa6': r'\Phi',        b'\xce\xa8': r'\Psi',
    b'\xce\xa9': r'\Omega',      b'\xce\xbc': r'\mu',
    b'\xce\xbd': r'\nu',         b'\xce\xb3': r'\gamma',
    # Math delimiters — use \rangle/\langle not \rightangle/\leftangle
    # so they work inside \addto\captionsenglish and other macro defs
    b'\xe2\x9f\xa9': r'\rangle', b'\xe2\x9f\xa8': r'\langle',
    # Math operators / relations — SKIP \cup / \cap / \div / \log / \ln
    # because they appear in LaTeX macro bodies (e.g. \addto\captionsenglish)
    # and replacing them there breaks the macro definitions.
    # Only replace operators that have no overlap with macro use.
    b'\xe2\x88\x82': r'\partial', b'\xe2\x89\xa0': r'\neq',
    b'\xe2\x89\x92': r'\approx',  b'\xe2\x89\xba': r'\infty',
    b'\xe2\x89\xa4': r'\leq',     b'\xe2\x89\xa5': r'\geq',
    b'\xe2\x8a\xa5': r'\geq',
    b'\xe2\x88\xab': r'\int',
    b'\xe2\x88\xbc': r'\sqrt',
    # XeTeX renders → natively in both text and math mode — no substitution needed
    b'\xe2\x86\x90': r'\gets',    b'\xe2\x86\x91': r'\uparrow',
    b'\xe2\x86\x93': r'\downarrow',
    b'\xe2\x9e\x86': r'\Rightarrow', b'\xe2\x9e\x84': r'\Leftarrow',
    # Math symbols
    b'\xe2\x88\x97': r'\cdot',   b'\xe2\x88\x98': r'\cdots',
    b'\xe2\x88\xbd': r'\frac',   b'\xe2\x96\xb2': r'\triangle',
    b'\xe2\x8a\x87': r'\rightarrow',
    b'\xe2\x8a\xbf': r'\rfloor', b'\xe2\x8a\xbe': r'\lceil',
    b'\xe2\x8a\xaa': r'\rceil',   b'\xe2\x8a\xab': r'\rfloor',
    b'\xe2\x97\x8b': r'\circ',    b'\xe2\x8a\x97': r'\oplus',
    b'\xe2\x8a\x99': r'\otimes', b'\xe2\x8a\x8b': r'\subseteq',
    b'\xe2\x8a\x8d': r'\subset', b'\xe2\x8a\x89': r'\supseteq',
    b'\xe2\x8a\x88': r'\supset',
    # Subscripts / superscripts
    b'\xe2\x82\x80': r'0',     b'\xe2\x82\x81': r'1',
    b'\xe2\x82\x82': r'2',       b'\xe2\x82\x83': r'3',
    b'\xe2\x82\x84': r'4',       b'\xe2\x82\x85': r'5',
    b'\xe2\x82\x86': r'6',       b'\xe2\x82\x87': r'7',
    b'\xe2\x82\x88': r'8',       b'\xe2\x82\x89': r'9',
    b'\xe2\x82\x90': r'+',       b'\xe2\x82\x91': r'-',
    b'\xe2\x82\x92': r'=',       b'\xe2\x82\x93': r'(',
    b'\xe2\x82\x94': r')',       b'\xe2\x82\x95': r'a',
    b'\xe2\x82\x96': r'e',       b'\xe2\x82\x97': r'o',
    b'\xe2\x82\x98': r'x',       b'\xe2\x82\x99': r'h',
    b'\xe2\x82\x9a': r'k',       b'\xe2\x82\x9b': r'l',
    b'\xe2\x82\x9c': r'm',       b'\xe2\x82\x9d': r'n',
    b'\xe2\x82\x9e': r'p',       b'\xe2\x82\x9f': r's',
    # Greek subscripts (U+2080..U+209F)
    b'\xe2\x82\x80': r'0',       # ₀
    b'\xe2\x82\x81': r'1',       # ₁
    b'\xe2\x82\x82': r'2',       # ₂
    b'\xe2\x82\x83': r'3',       # ₃
    b'\xe2\x82\x84': r'4',       # ₄
    b'\xe2\x82\x85': r'5',       # ₅
    b'\xe2\x82\x86': r'6',       # ₆
    b'\xe2\x82\x87': r'7',       # ₇
    b'\xe2\x82\x88': r'8',       # ₈
    b'\xe2\x82\x89': r'9',       # ₉
    # Box drawing / Pygments output
    b'\xe2\x94\x80': r'-',       b'\xe2\x94\x81': r'=',
    b'\xe2\x94\x82': r'|',       b'\xe2\x94\x8c': r'+',
    b'\xe2\x94\x90': r'+',       b'\xe2\x94\x94': r'+',
    b'\xe2\x94\x98': r'+',       b'\xe2\x94\x9c': r'+',
    b'\xe2\x94\xa0': r'+',       b'\xe2\x94\xac': r'+',
    b'\xe2\x94\xb4': r'+',       b'\xe2\x94\xbc': r'+',
    b'\xe2\x94\x8c': r'+',       b'\xe2\x94\x90': r'+',
    b'\xe2\x94\x8f': r'+',       b'\xe2\x94\x8b': r'+',
    b'\xe2\x94\x91': r'|',       b'\xe2\x94\x93': r'|',
    b'\xe2\x94\x83': r'|',       b'\xe2\x94\x8a': r'|',
    b'\xe2\x94\x9b': r'|',       b'\xe2\x94\x9d': r'|',
    b'\xe2\x94\x9f': r'|',       b'\xe2\x94\xa3': r'|',
    b'\xe2\x94\xa7': r'|',       b'\xe2\x94\xab': r'|',
    b'\xe2\x94\xaf': r'|',       b'\xe2\x94\xb3': r'|',
    b'\xe2\x94\xb7': r'|',       b'\xe2\x94\xbb': r'|',
    b'\xe2\x94\xbd': r'|',       b'\xe2\x95\x90': r'=',
    b'\xe2\x95\x91': r'|',       b'\xe2\x95\x92': r'+',
    b'\xe2\x95\x93': r'+',       b'\xe2\x95\x94': r'+',
    b'\xe2\x95\x95': r'+',       b'\xe2\x95\x96': r'+',
    b'\xe2\x95\x97': r'+',       b'\xe2\x95\x98': r'+',
    b'\xe2\x95\x99': r'+',       b'\xe2\x95\x9a': r'+',
    b'\xe2\x95\x9b': r'+',       b'\xe2\x95\x9c': r'+',
    b'\xe2\x95\x9d': r'+',       b'\xe2\x95\x9e': r'+',
    b'\xe2\x95\x9f': r'+',       b'\xe2\x95\xa0': r'+',
    b'\xe2\x95\xa1': r'|',       b'\xe2\x95\xa2': r'|',
    b'\xe2\x95\xa3': r'+',       b'\xe2\x95\xa4': r'+',
    b'\xe2\x95\xa5': r'+',       b'\xe2\x95\xa6': r'+',
    b'\xe2\x95\xa7': r'+',       b'\xe2\x95\xa8': r'+',
    b'\xe2\x95\xa9': r'+',       b'\xe2\x95\xaa': r'+',
    b'\xe2\x95\xab': r'+',       b'\xe2\x95\xac': r'+',
    b'\xe2\x95\xad': r'+',       b'\xe2\x95\xae': r'+',
    b'\xe2\x95\xaf': r'+',       b'\xe2\x95\xb0': r'+',
    b'\xe2\x95\xb1': r'+',       b'\xe2\x95\xb2': r'+',
    b'\xe2\x95\xb3': r'+',       b'\xe2\x95\xb4': r'+',
    b'\xe2\x95\xb5': r'+',       b'\xe2\x95\xb6': r'+',
    b'\xe2\x95\xb7': r'+',       b'\xe2\x94\xa8': r'+',
    b'\xe2\x94\xb0': r'+',       b'\xe2\x94\x8f': r'+',
    b'\xe2\x94\x9f': r'+',       b'\xe2\x94\x97': r'+',
    b'\xe2\x94\x8b': r'+',       b'\xe2\x94\x95': r'+',
    b'\xe2\x94\x89': r'+',       b'\xe2\x94\x8b': r'+',
    # Check marks / emoji
    b'\xe2\x9c\x93': r'[OK]',   b'\xe2\x9c\x94': r'[X]',
    b'\xe2\x9c\x85': r'[OK]',   b'\xe2\x9c\x97': r'[X]',
    b'\xe2\x9c\x98': r'[X]',    b'\xe2\x9d\x8c': r'[X]',
    # Greek letters in text (from MyST not converting)
    b'\xce\xb1': r'\alpha',     b'\xce\xb2': r'\beta',
    b'\xce\xb3': r'\gamma',     b'\xce\xb4': r'\delta',
    b'\xce\xb5': r'\epsilon',   b'\xce\xb6': r'\zeta',
    b'\xce\xb7': r'\eta',        b'\xce\xb8': r'\theta',
    b'\xce\xb9': r'\iota',       b'\xce\xba': r'\kappa',
    b'\xce\xbb': r'\lambda',     b'\xce\xbc': r'\mu',
    b'\xce\xbd': r'\nu',         b'\xce\xbe': r'\xi',
    b'\xce\xbf': r'\pi',         b'\xcf\x80': r'\rho',
    b'\xcf\x81': r'\sigma',     b'\xcf\x84': r'\tau',
    b'\xcf\x85': r'\upsilon',   b'\xcf\x86': r'\chi',
    b'\xcf\x87': r'\psi',       b'\xcf\x88': r'\omega',
    # Accents / combining
    b'\xcb\x86': r"'",          # combining acute
    b'\xcb\x90': r"`",          # combining grave
    b'\xcb\x8c': r'"',          # combining diaeresis
    b'\xcb\x9d': r'~',          # combining tilde
    # Arrows
    b'\xe2\x86\x92': r'\to',   b'\xe2\x86\x90': r'\gets',
    b'\xe2\x86\x91': r'\uparrow', b'\xe2\x86\x93': r'\downarrow',
    b'\xe2\x9e\x86': r'\Rightarrow', b'\xe2\x9e\x84': r'\Leftarrow',
    # Other symbols
    b'\xe2\x80\x94': r'--',     b'\xe2\x80\x93': r'-',
    b'\xe2\x80\x99': r"'",      b'\xe2\x80\x98': r"'",
    b'\xe2\x80\x9c': r'"',      b'\xe2\x80\x9d': r'"',
    b'\xe2\x80\xa6': r'...',    b'\xc2\xb0': r'^\circ',
    b'\xc2\xb1': r'\pm',        b'\xc2\xb7': r'\cdot',
    b'\xc3\x97': r'\times',     b'\xc3\xb7': r'\div',
    # Superscripts
    b'\xc2\xb2': r'^2',         b'\xc2\xb3': r'^3',
    # Special
    b'\xe2\x96\xb2': r'\triangle',  b'\xe2\x96\xbc': r'\triangledown',
}


# LaTeX commands that MyST emits but which XeTeX can render natively as Unicode.
# We do a string-level pass to convert these back to UTF-8 so they work in both
# text and math mode (XeTeX + fontspec handles Unicode chars natively).
LATEX_TO_UNICODE = {
    # Arrows (MyST converts Unicode → to \to, but \to is math-only)
    r'\to':       '→',
    r'\gets':     '←',
    r'\uparrow':  '↑',
    r'\downarrow': '↓',
    r'\Rightarrow': '⇒',
    r'\Leftarrow':  '⇐',
    r'\rightarrow': '→',
    # Relations / operators (these work in math mode but be safe)
    r'\partial':  '∂',
    r'\infty':    '∞',
    r'\neq':      '≠',
    r'\approx':   '≈',
    r'\leq':      '≤',
    r'\geq':      '≥',
    r'\cdot':     '·',
    r'\cdots':    '⋯',
    r'\div':      '÷',
    r'\times':    '×',
    r'\pm':       '±',
    r'\circ':     '∘',
    r'\triangle': '△',
    r'\sqrt':     '√',
    # Greek letters — let XeTeX's math font handle them
    r'\alpha':   'α',  r'\beta':    'β',  r'\gamma':  'γ',
    r'\delta':   'δ',  r'\epsilon': 'ε',  r'\zeta':   'ζ',
    r'\eta':     'η',  r'\theta':   'θ',  r'\iota':   'ι',
    r'\kappa':   'κ',  r'\lambda':  'λ',  r'\mu':     'μ',
    r'\nu':      'ν',  r'\xi':      'ξ',  r'\pi':     'π',
    r'\rho':     'ρ',  r'\sigma':   'σ',  r'\tau':    'τ',
    r'\upsilon': 'υ',  r'\phi':     'φ',  r'\chi':    'χ',
    r'\psi':     'ψ',  r'\omega':   'ω',
    r'\Alpha':   'Α',  r'\Beta':    'Β',  r'\Gamma':  'Γ',
    r'\Delta':   'Δ',  r'\Eta':     'Η',  r'\Theta':  'Θ',
    r'\Iota':    'Ι',  r'\Kappa':   'Κ',  r'\Lambda': 'Λ',
    r'\Mu':      'Μ',  r'\Nu':      'Ν',  r'\Xi':     'Ξ',
    r'\Omicron': 'Ο',  r'\Pi':      'Π',  r'\Rho':    'Ρ',
    r'\Sigma':   'Σ',  r'\Tau':     'Τ',  r'\Upsilon': 'Υ',
    r'\Phi':     'Φ',  r'\Chi':     'Χ',  r'\Psi':    'Ψ',
    r'\Omega':   'Ω',
    # Delimiters
    r'\rangle': '⟩',  r'\langle':  '⟨',
    r'\lceil':  '⌈',  r'\rceil':   '⌉',
    r'\rfloor': '⌋',  r'\lvert':   '|',  r'\rvert': '|',
    # Sets / logic
    r'\oplus':   '⊕',
    r'\otimes': '⊗',  r'\subseteq': '⊆',  r'\subset': '⊂',
    r'\supseteq': '⊇',  r'\supset': '⊃',
    # Punctuation
    r'\ldots': '…',
}


def patch_tex(filepath: str) -> None:
    with open(filepath, 'rb') as f:
        content = f.read()

    original = content

    # Pass 1: UTF-8 bytes → ASCII LaTeX (for raw Unicode that slipped through)
    for utf8_bytes, latex in REPLACEMENTS.items():
        content = content.replace(utf8_bytes, latex.encode('ascii'))

    # Pass 2: LaTeX commands → Unicode chars (XeTeX renders Unicode natively)
    # Work on decoded string so we can use str.replace with Unicode chars.
    # Re-encode to preserve other binary content (only .tex is ASCII-family).
    content = content.decode('utf-8', errors='replace')
    for latex_cmd, uchar in LATEX_TO_UNICODE.items():
        content = content.replace(latex_cmd, uchar)
    content = content.encode('utf-8')

    if content != original:
        with open(filepath, 'wb') as f:
            f.write(content)
        print(f"[tex-patch] Patched: {filepath}")
        # Report both passes
        for utf8_bytes, latex in REPLACEMENTS.items():
            count = original.count(utf8_bytes)
            if count:
                print(f"  byte {count}x {latex!r}")
    else:
        print(f"[tex-patch] No changes: {filepath}")



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 _tex_patch.py <file.tex>")
        sys.exit(1)
    patch_tex(sys.argv[1])
