"""Body-section selection policy for the Book of Abstracts.

The canonical six question_names whose response values count as
publishable scientific content. Every Oxford submission carries 30+
form fields (training institution, IRB approval, scanner field
strength, etc.); the book renders only the academic-section subset.

This is **editorial policy**, not external-schema state — projects
choose which submitter responses are publication-worthy. CA-007
applies to genuine external enumerations (Oxford schema, vendor
enums); the body-section list is a project decision. The
`--include-section <name>` CLI flag is the forward-compatibility
escape hatch when Oxford introduces a new academic section.

Order in this tuple is the rendering order — sections are emitted
in this sequence regardless of corpus order.
"""

from __future__ import annotations

BODY_SECTION_NAMES: tuple[str, ...] = (
    "Introduction",
    "Methods",
    "Results",
    "Conclusion",
    "Acknowledgement",
    "References/Citations",
)
