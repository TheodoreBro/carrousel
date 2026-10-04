#!/usr/bin/env python
"""Version Markdown du papier (paper/paper.md) à partir de paper/paper.tex, via pandoc (binaire fourni par pypandoc_binary).

- titre et résumés (EN/FR) en tête, puis le corps et les annexes (tableaux `\input` résolus, citations résolues avec references.bib) ;
- les figures pointent vers les .png de figures/ (les .pdf ne s'affichent pas dans un dépôt).
Usage : python scripts/22_paper_md.py   (appelé par `make paper`).
"""
from __future__ import annotations

import re
from pathlib import Path

import pypandoc

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def main() -> int:
    tex = (PAPER / "paper.tex").read_text(encoding="utf-8")
    title = re.search(r"\\title\{(.*?)\}\n", tex, re.S).group(1).replace("\\\\", " ").replace("\n", " ")
    title = re.sub(r"\s+", " ", title).strip()
    abstract = tex[tex.index(r"\begin{abstract}") + len(r"\begin{abstract}"): tex.index(r"\end{abstract}")]
    abstract = re.sub(r"\\selectlanguage\{[^}]*\}", "", abstract)
    pre = tex[: tex.index(r"\begin{document}")]
    args = ["--wrap=none", "--citeproc", "--bibliography=references.bib", "--resource-path=.:.."]
    abs_md = pypandoc.convert_text(pre + r"\begin{document}" + abstract + r"\end{document}", "gfm", format="latex", extra_args=args, cworkdir=str(PAPER))
    body_md = pypandoc.convert_file(str(PAPER / "paper.tex"), "gfm", extra_args=args, cworkdir=str(PAPER))
    md = f"# {title}\n\n*Working paper — version de travail, ne pas citer. Généré par scripts/22_paper_md.py à partir de paper/paper.tex ; version PDF : paper/paper.pdf.*\n\n{abs_md.strip()}\n\n{body_md.strip()}\n"
    def fig(m: re.Match) -> str:  # pandoc rend \includegraphics par <embed src="fig.pdf" /> (sans \graphicspath)
        name = m.group(1)
        ext = ".png" if (ROOT / "figures" / f"{name}.png").exists() else ".pdf"
        return f"![{name}](../figures/{name}{ext})"
    md = re.sub(r'<embed src="([A-Za-z0-9_]+)\.pdf" />', fig, md)
    (PAPER / "paper.md").write_text(md, encoding="utf-8")
    print("paper/paper.md :", len(md.split()), "mots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
