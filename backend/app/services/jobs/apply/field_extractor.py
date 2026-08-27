"""Enumerate the visible form controls on an application page.

Strategy: tag every candidate control with a `data-autoapply-id` attribute
(set from JS, so the selector is stable across re-renders within one page
load), collect its accessible label, then group radio inputs that share a
`name` into a single choice field."""

from __future__ import annotations

from app.services.jobs.models import FormField

_EXTRACT_JS = r"""
() => {
  const SKIP = new Set(['hidden', 'submit', 'button', 'reset', 'image']);
  const controls = Array.from(document.querySelectorAll('input, textarea, select'));
  const out = [];
  let i = 0;
  for (const el of controls) {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || tag).toLowerCase();
    if (SKIP.has(type)) continue;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') continue;
    if (rect.width === 0 && rect.height === 0 && type !== 'file') continue;

    // Skip spam-trap / honeypot fields.
    const hp = (el.name + ' ' + el.id + ' ' + el.className).toLowerCase();
    if (hp.includes('honeypot') || hp.includes('captcha') || el.getAttribute('autocomplete') === 'nope') continue;
    if (el.tabIndex === -1 && type === 'text' && !el.getAttribute('aria-label') && !el.labels?.length) continue;

    const id = 'aa' + (i++);
    el.setAttribute('data-autoapply-id', id);

    let label = '';
    if (el.labels && el.labels.length) label = el.labels[0].innerText;
    if (!label && el.getAttribute('aria-label')) label = el.getAttribute('aria-label');
    if (!label && el.getAttribute('aria-labelledby')) {
      const l = document.getElementById(el.getAttribute('aria-labelledby'));
      if (l) label = l.innerText;
    }
    if (!label && el.placeholder) label = el.placeholder;
    if (!label) {
      const wrap = el.closest('div, li, fieldset, label');
      if (wrap) label = (wrap.innerText || '').split('\n')[0];
    }
    if (!label && el.name) label = el.name;

    if (/honeypot|hpot|do ?not ?fill|leave.*blank/i.test(label)) continue;

    const role = (el.getAttribute('role') || '').toLowerCase();
    const isCombobox = role === 'combobox'
      || el.getAttribute('aria-autocomplete') === 'list'
      || el.getAttribute('aria-haspopup') === 'listbox'
      || (el.getAttribute('aria-expanded') !== null && tag === 'input');

    let kind = type;
    if (tag === 'textarea') kind = 'textarea';
    else if (tag === 'select') kind = 'select';
    else if (isCombobox && ['text','search',''].includes(type === tag ? '' : type)) kind = 'combobox';
    else if (!['text','email','tel','url','number','file','checkbox','radio'].includes(type)) kind = 'text';

    let options = [];
    if (tag === 'select') {
      options = Array.from(el.options).map(o => (o.text || '').trim()).filter(Boolean);
    }

    out.push({
      selector: `[data-autoapply-id="${id}"]`,
      label: (label || '').replace(/\s+/g, ' ').trim().slice(0, 240),
      kind,
      type,
      options,
      name: el.name || '',
      value: (el.value || '').slice(0, 240),
      required: el.required || el.getAttribute('aria-required') === 'true',
      optionLabel: type === 'radio'
        ? ((el.labels && el.labels[0] && el.labels[0].innerText) || el.value || '').replace(/\s+/g, ' ').trim()
        : '',
    });
  }
  return out;
}
"""


async def extract_fields(page) -> list[FormField]:
    raw = await page.evaluate(_EXTRACT_JS)
    return _group(raw)


def _group(raw: list[dict]) -> list[FormField]:
    fields: list[FormField] = []
    radio_groups: dict[str, FormField] = {}

    for item in raw:
        kind = item["kind"]
        if kind == "radio":
            name = item["name"] or item["selector"]
            group = radio_groups.get(name)
            option_label = item["optionLabel"] or item["value"] or f"Option {len(group.options) + 1 if group else 1}"
            if group is None:
                # Strip a trailing option label off the wrapper text to get the question.
                question = item["label"]
                if option_label and question.endswith(option_label):
                    question = question[: -len(option_label)].strip(" :-*")
                group = FormField(
                    selector=item["selector"],
                    label=question or name,
                    kind="radio",
                    options=[],
                    required=item["required"],
                )
                radio_groups[name] = group
                fields.append(group)
            if option_label not in group.options:
                group.options.append(option_label)
            group.option_selectors[option_label] = item["selector"]
            continue

        _KNOWN = {"text", "email", "tel", "url", "number", "textarea", "select", "combobox", "file", "checkbox"}
        fields.append(
            FormField(
                selector=item["selector"],
                label=item["label"] or item["name"] or item["kind"],
                kind=kind if kind in _KNOWN else "text",
                options=item["options"],
                required=item["required"],
                value="" if kind == "file" else item["value"],
            )
        )

    return fields
