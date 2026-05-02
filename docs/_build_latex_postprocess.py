#!/usr/bin/env python3
"""Patch the generated LaTeX to fix bmatrix inside varwidth cells."""
import re
import sys

tex_path = sys.argv[1] if len(sys.argv) > 1 else "unifiedquantum.tex"

with open(tex_path, "r", encoding="utf-8") as f:
    content = f.read()

# The issue: bmatrix & chars inside varwidth are treated as Sphinx table column &
# Fix: wrap bmatrix/Bmatrix/pmatrix with \sphinxfixmatrix to suppress local &
original = content
content = re.sub(
    r'(\\begin\{(?:?:s(?:phinx)?)?[Bbmp]matrix\})',
    r'\\sphinxfixmatrix\1',
    content,
)

# Define the fix command in the preamble
fix = r"""
% Fix: locally suppress Sphinx table column tracking inside matrix envs
\makeatletter
\newif\ifsphinx@fixmatrix
\preto\begin{bmatrix}{\sphinx@fixmatrixtrue}% 
\preto\end{bmatrix}{\sphinx@fixmatrixfalse}%
\preto\begin{Bmatrix}{\sphinx@fixmatrixtrue}%
\preto\end{Bmatrix}{\sphinx@fixmatrixfalse}%
\preto\begin{pmatrix}{\sphinx@fixmatrixtrue}%
\preto\end{pmatrix}{\sphinx@fixmatrixfalse}%
\makeatother
"""
# Insert after \begin{document}
content = content.replace(r"\begin{document}", r"\begin{document}" + fix, 1)

with open(tex_path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Patched: {tex_path}")
