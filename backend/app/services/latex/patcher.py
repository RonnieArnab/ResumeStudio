from app.services.latex.sectioner import parse_sections, render_document


def apply_section_patch(full_latex: str, section_id: str, new_body: str) -> str:
    """Replace one section's body in the full document, leaving every other
    section — and the preamble — untouched. Reuses render_document so the
    result goes through the exact same assembly path as a fresh upload."""
    sections = parse_sections(full_latex)
    if section_id not in sections:
        raise KeyError(f"Unknown section_id: {section_id}")
    sections[section_id] = new_body.strip()
    return render_document(sections)
