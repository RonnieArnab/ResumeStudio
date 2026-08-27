"""Radio-group collapsing in the form-field extractor (pure function)."""

from app.services.jobs.apply.field_extractor import _group


def test_radios_with_same_name_collapse_to_one_field():
    raw = [
        {"selector": "[data-autoapply-id=\"aa0\"]", "label": "Work authorization? Yes", "kind": "radio",
         "type": "radio", "options": [], "name": "auth", "value": "yes", "required": True, "optionLabel": "Yes"},
        {"selector": "[data-autoapply-id=\"aa1\"]", "label": "Work authorization? No", "kind": "radio",
         "type": "radio", "options": [], "name": "auth", "value": "no", "required": True, "optionLabel": "No"},
    ]
    fields = _group(raw)
    assert len(fields) == 1
    field = fields[0]
    assert field.kind == "radio"
    assert field.options == ["Yes", "No"]
    assert field.option_selectors["Yes"].endswith('aa0"]')
    assert field.label.startswith("Work authorization")


def test_non_radio_controls_pass_through():
    raw = [
        {"selector": "s1", "label": "Email", "kind": "email", "type": "email", "options": [],
         "name": "email", "value": "", "required": True, "optionLabel": ""},
        {"selector": "s2", "label": "Resume", "kind": "file", "type": "file", "options": [],
         "name": "resume", "value": "", "required": False, "optionLabel": ""},
    ]
    fields = _group(raw)
    assert [f.kind for f in fields] == ["email", "file"]
