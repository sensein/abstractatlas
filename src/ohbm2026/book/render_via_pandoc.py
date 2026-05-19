"""pandoc subprocess wrappers for PDF + DOCX output.

PDF path: pandoc + xelatex with the LaTeX preamble (`-H header...`),
`\\makeindex` + `\\printindex` already in the markdown source. After
pandoc emits the PDF we strip the embedded timestamps for
determinism (R6).

DOCX path: implemented in T033 (US3). Currently a stub that raises;
keeps the import surface stable so the CLI can lazy-load it.
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import shutil
import subprocess
from importlib import resources

from ohbm2026.exceptions import BookBuildError


def _which_or_raise(binary: str, hint: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise BookBuildError(
            f"required system dep `{binary}` not on PATH; {hint}",
            details=f"shutil.which({binary!r}) returned None",
        )
    return path


def preflight(*, need_xelatex: bool) -> dict[str, str]:
    """Verify pandoc + (optionally) xelatex are on PATH.

    Returns a dict of `{name: version_line}` for provenance capture.
    Raises BookBuildError with an operator-actionable install hint
    when a binary is absent.
    """
    versions: dict[str, str] = {}
    pandoc = _which_or_raise(
        "pandoc",
        "install via `brew install pandoc` (macOS) or "
        "`apt-get install pandoc` (Linux). See quickstart.md step 2.",
    )
    versions["pandoc"] = _first_line(subprocess.check_output([pandoc, "--version"]))
    if need_xelatex:
        xelatex = _which_or_raise(
            "xelatex",
            "install Tectonic via `brew install tectonic` or full TeX Live "
            "via `apt-get install texlive-xetex`. See quickstart.md step 2.",
        )
        versions["xelatex"] = _first_line(
            subprocess.check_output([xelatex, "--version"])
        )
    return versions


def _first_line(b: bytes) -> str:
    return b.decode("utf-8", errors="replace").splitlines()[0].strip()


def _header_includes_path(style: str) -> pathlib.Path:
    """Return the absolute path to the right LaTeX header-includes
    file (plain vs tufte-book). Files live alongside the book
    package so the operator never has to manage them.
    """
    pkg = resources.files("ohbm2026.book.templates")
    if style == "tufte":
        return pathlib.Path(str(pkg.joinpath("header-includes-tufte.tex")))
    return pathlib.Path(str(pkg.joinpath("header-includes.tex")))


def to_pdf(
    md_path: pathlib.Path,
    output_path: pathlib.Path,
    *,
    style: str = "plain",
    strip_metadata: bool = True,
) -> None:
    """Run pandoc + xelatex against `md_path`, writing `output_path`.

    Strips `/CreationDate` + `/ModDate` from the resulting PDF for
    determinism (R6) unless `strip_metadata` is False (debug only).
    """
    pandoc = shutil.which("pandoc") or _which_or_raise(
        "pandoc", "see quickstart.md step 2"
    )
    # xelatex is required as the pdf-engine but pandoc invokes it
    # for us — we only assert it's on PATH so the failure mode is
    # clear before we burn time composing.
    _which_or_raise("xelatex", "see quickstart.md step 2")

    header_includes = _header_includes_path(style)
    if not header_includes.exists():
        raise BookBuildError(
            f"header-includes file missing at {header_includes} "
            f"(style={style!r})"
        )

    resource_path = md_path.parent
    argv = [
        pandoc,
        str(md_path),
        "--from=markdown+raw_tex+pandoc_title_block",
        "--to=pdf",
        "--pdf-engine=xelatex",
        "-H",
        str(header_includes),
        f"--resource-path={resource_path}",
        "--standalone",
        "--toc",
        "-o",
        str(output_path),
    ]
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise BookBuildError(
            f"pandoc returned non-zero ({proc.returncode}) building PDF",
            details=(proc.stderr or "").strip(),
        )

    if strip_metadata:
        _strip_pdf_metadata(output_path)


def _strip_pdf_metadata(pdf_path: pathlib.Path) -> None:
    """Overwrite /CreationDate + /ModDate to a fixed epoch (R6)."""
    import pikepdf

    fixed = "D:19700101000000Z"
    with pikepdf.Pdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        with pdf.open_metadata() as meta:
            # pikepdf's metadata helper handles XMP — clear the
            # producer/creator stamps too so two pandoc versions
            # produce the same body.
            for k in ("xmp:CreateDate", "xmp:ModifyDate", "xmp:MetadataDate"):
                if k in meta:
                    del meta[k]
        info = pdf.trailer.get("/Info")
        if info is not None:
            info["/CreationDate"] = fixed
            info["/ModDate"] = fixed
        pdf.save(pdf_path)


def to_docx(
    md_path: pathlib.Path,
    output_path: pathlib.Path,
    *,
    strip_metadata: bool = True,
) -> None:
    """US3 (T033). Stubbed for now so the CLI can lazy-import."""
    raise NotImplementedError(
        "DOCX rendering lands in US3 (T033); use --format md or --format pdf for now"
    )
