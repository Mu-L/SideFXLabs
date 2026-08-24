"""Plan safe attribute and group renames for Houdini parameters.

This module reads a parameter's original source and storage type, chooses the
appropriate language rewriter, and builds the edit record used by the shelf
tool. Houdini-specific checks, such as a Wrangle's Run Over setting, stay here
so the language rewriters do not depend on ``hou``.

Planning is read-only. The UI runs the planner again immediately before each
edit to make sure the parameter is still safe to change.
"""

import re

import hou

from . import labs_rename_attributes_rewriters as rewriters


# Public planning API

WORD = r"(?<![A-Za-z0-9_]){0}(?![A-Za-z0-9_])"
ATTRIBUTE_TOKEN = re.compile(
    r"^(?P<prefix>\^?)(?P<name>[A-Za-z_][A-Za-z0-9_]*)$")
GROUP_TOKEN = re.compile(
    r"^(?P<prefix>[!^&]?)(?P<name>[A-Za-z_][A-Za-z0-9_]*)$")


def plan_parameter_rewrite(
    node,
    parm,
    rename_kind,
    item_class,
    old_name,
    new_name,
    rename_vex=True,
    rename_python=True,
    aggressive_vex=False,
):
    """Plan one parameter rewrite without changing Houdini state.

    Return ``(edit, [], skipped)``. ``edit`` is ``None`` or a dictionary for
    one safe change. The empty middle list preserves the shelf tool's planner
    API. Each skipped item contains ``node_path``, ``parm_name``, and
    ``reason``.

    ``rename_vex`` and ``rename_python`` can disable their language rewriters.
    ``aggressive_vex`` is retained for compatibility and intentionally unused.

    Invalid arguments raise ``ValueError``. ``hou.OperationInterrupted``
    propagates, while other ``hou.Error`` failures become skip records.
    """
    kind, owner, old, new = rewriters.validate_request(
        rename_kind, item_class, old_name, new_name)
    try:
        edit, notes = _plan_parm_rewrite(
            node,
            parm,
            kind,
            owner,
            old,
            new,
            rename_vex=bool(rename_vex),
            rename_python=bool(rename_python),
        )
    except hou.OperationInterrupted:
        raise
    except hou.Error as error:
        edit, notes = None, [
            "could not inspect parameter: {}".format(error)]

    node_path = node.path()
    parm_name = parm.name()
    skipped = [
        {
            "node_path": node_path,
            "parm_name": parm_name,
            "reason": str(note),
        }
        for note in dict.fromkeys(note for note in notes if note)
    ]
    return edit, [], skipped


def inspect_plain_field(node, parm):
    """Return ``(kind, owner)`` when metadata identifies a plain name field."""
    kind = _plain_field_kind(node, parm)
    if kind == "attribute":
        owner, _problem = _plain_attribute_owner(node, parm, None)
        return kind, owner
    if kind == "group":
        owner, _problem = _plain_group_owner(node, parm, None)
        return kind, owner
    return None, None


def _plain_attribute_names(text):
    """Return exact attribute identifiers from comma or whitespace operands."""
    names = []
    for operand in re.split(r"[\s,]+", str(text or "")):
        match = ATTRIBUTE_TOKEN.match(operand)
        if match and match.group("name") not in names:
            names.append(match.group("name"))
    return tuple(names)


def _attribute_pattern_references(text, attribute_name):
    """Return whether a non-exact attribute pattern can match the name.

    A lone ``*`` needs no rewrite because it continues to match after a rename.
    Other globs are reported when Houdini says they currently match the chosen
    attribute, even if they do not contain its literal spelling.
    """
    for operand in re.split(r"[\s,]+", str(text or "")):
        pattern = operand[1:] if operand.startswith("^") else operand
        if not pattern or pattern == "*" or ATTRIBUTE_TOKEN.match(operand):
            continue
        if re.search(WORD.format(re.escape(attribute_name)), operand):
            return True
        if not any(character in pattern for character in "*?[]{}"):
            continue
        try:
            if hou.text.patternMatch(pattern, attribute_name):
                return True
        except hou.OperationInterrupted:
            raise
        except (hou.Error, TypeError, ValueError):
            return True
    return False


def _inspect_attribute_reference(node, parm, attribute_name):
    """Return ``(owner, problem)`` for one exact plain attribute reference."""
    if _plain_field_kind(node, parm) != "attribute":
        return None, (
            "parameter metadata does not identify an attribute-name field")
    return _plain_attribute_owner(node, parm, str(attribute_name or ""))


def _plain_group_names(text):
    """Return exact group identifiers from simple whitespace operands.

    Houdini's ``!``, ``^``, and ``&`` operators change how a group participates
    in a selection, but the following identifier still names one concrete
    group. Complex patterns are deliberately omitted so discovery never offers
    a candidate that the planner cannot rewrite safely.
    """
    names = []
    for operand in re.findall(r"\S+", str(text or "")):
        match = GROUP_TOKEN.match(operand)
        if match and match.group("name") not in names:
            names.append(match.group("name"))
    return tuple(names)


def _inspect_group_reference(node, parm, group_name):
    """Return ``(owner, problem)`` for one exact plain group reference."""
    if _plain_field_kind(node, parm) != "group":
        return None, "parameter metadata does not identify a group-name field"
    return _plain_group_owner(node, parm, str(group_name or ""))


def _plan_parm_rewrite(
        node, parm, kind, item_class, old, new,
        rename_vex=True, rename_python=True):
    """Choose a rewriter for one parameter and build its edit record."""
    text, source_kind, language, storage_type = parameter_source(parm)
    if text is None:
        # A keyed string can evaluate to the old name without having one source
        # string we can safely edit. Report the ambiguity instead of rewriting
        # the evaluated value.
        if (
            parm.parmTemplate().dataType() == hou.parmData.String
            and parm.keyframes()
            and old in parm.evalAsString()
        ):
            return None, [
                "string parameter has multiple or ambiguous keyframes"]
        return None, []
    # chs() may hide the requested name in another parameter. Send it to the
    # rewriter even when the old name is absent so the indirect reference is
    # reported instead of silently ignored.
    if old not in text and not re.search(r"\bchs\s*\(", text, re.I):
        possible_attribute_pattern = (
            source_kind == "value"
            and kind == "attribute"
            and _attribute_pattern_references(text, old)
            and _plain_field_kind(node, parm) == "attribute"
        )
        if not possible_attribute_pattern:
            return None, []

    # Houdini's expression-language enum is authoritative. Never guess the
    # language of an expression with an unknown enum. For plain string values,
    # recognize Python before VEX from exact node and parameter metadata; text
    # that matches neither code field continues to the plain-field rules.
    if source_kind == "expression":
        language_kind = _expression_language_kind(language)
    elif source_kind == "value" and _looks_like_python(node, parm):
        language_kind = "python"
    elif source_kind == "value" and _looks_like_vex(node, parm):
        language_kind = "vex"
    else:
        language_kind = None
    code_type = {
        "hscript": "HScript",
        "python": "Python",
        "vex": "VEX",
    }.get(language_kind, "Plain")

    if language_kind == "hscript":
        result = rewriters.rewrite_hscript(
            text, kind, item_class, old, new)
    elif language_kind == "python":
        if rename_python:
            result = rewriters.rewrite_python(
                text, kind, item_class, old, new)
        else:
            result = _unchanged(text, "Python rewrite disabled")
    elif language_kind == "vex":
        if rename_vex:
            result = rewriters.rewrite_vex(
                text,
                kind,
                item_class,
                old,
                new,
                run_over_class=_wrangle_run_over_class(node, parm),
            )
        else:
            result = _unchanged(text, "VEX rewrite disabled")
    elif source_kind == "expression":
        result = _unchanged(
            text, "unsupported expression language or syntax")
    else:
        updated, reasons, plain_skipped = _plain_rewrite(
            node, parm, text, kind, item_class, old, new)
        result = rewriters.make_result(
            text, updated, reasons=reasons, skipped=plain_skipped)

    edit = (
        _edit_record(
            node,
            parm,
            text,
            result,
            source_kind,
            storage_type,
            language,
            code_type,
        )
        if result.changed
        else None
    )
    return edit, list(result.skipped)


def _unchanged(text, skipped):
    """Create an unchanged result with one skip reason."""
    return rewriters.make_result(text, text, skipped=(skipped,))


# Parameter source and edit records

def parameter_source(parm):
    """Return source text, source kind, language, and storage type.

    The tuple is ``(text, source_kind, language, storage_type)``. Source kind
    is ``"expression"`` or ``"value"``; language is the original Houdini enum
    or ``None``; and storage type is the stable edit-record label.

    Expressions use their unevaluated text and Houdini language enum. Plain
    strings use unexpanded text. Unsupported or multiply keyed parameters
    return ``None`` instead of an evaluated value.

    Preview and apply compare this representation when checking for stale
    edits. Evaluating strings, expanding variables, or regenerating expression
    text here would make that comparison unreliable.
    """
    try:
        value = parm.expression()
        language = parm.expressionLanguage()
        return value, "expression", language, _storage_type(parm)
    except hou.OperationFailed:
        pass

    if parm.parmTemplate().dataType() != hou.parmData.String:
        return None, None, None, _storage_type(parm)
    if parm.keyframes():
        return None, None, None, "string"
    return parm.unexpandedString(), "value", None, "string"


def _storage_type(parm):
    """Return the storage label used in edit records."""
    data_type = parm.parmTemplate().dataType()
    if data_type == getattr(hou.parmData, "String", None):
        return "string"
    if data_type == getattr(hou.parmData, "Int", None):
        return "int"
    if data_type == getattr(hou.parmData, "Float", None):
        return "float"
    return None


def _edit_record(
        node,
        parm,
        old_value,
        rewrite,
        source_kind,
        storage_type,
        language,
        code_type):
    """Build the parameter edit record used by preview and apply.

    Records cross the preview/apply boundary, so paths replace live
    ``hou.Node`` and ``hou.Parm`` handles. Their stable shape is::

        {
            "node_path": "/obj/geo1/wrangle1", "parm_name": "snippet",
            "old_value": "f@old = 1;", "new_value": "f@new = 1;",
            "reasons": ("VEX @ binding",),
            "value_kind": "value", "storage_type": "string",
            "code_type": "VEX", "risk": "safe",
        }

    Expressions also retain ``language`` and ``language_label``. Reasons are
    deduplicated without changing their discovery order.
    """
    result = {
        "node_path": node.path(),
        "parm_name": parm.name(),
        "old_value": old_value,
        "new_value": rewrite.text,
        "reasons": tuple(dict.fromkeys(
            reason for reason in rewrite.reasons if reason)),
        "value_kind": source_kind,
        "storage_type": storage_type,
        "code_type": code_type,
        "risk": "safe",
    }
    if language is not None:
        result["language"] = language
        result["language_label"] = _expression_language_kind(language) or ""
    return result


# Plain attribute and group fields

def _plain_rewrite(node, parm, text, kind, item_class, old, new):
    """Rewrite concrete operands in a metadata-identified plain field.

    Kind and owner must match the request. Group operands use whitespace;
    attribute operands also allow commas. Exact group identifiers may carry
    Houdini's ``!``, ``^``, or ``&`` selection operator. Wildcards, ranges,
    braced expressions, and other compound uses are not rewritten.

    If any operand uses the old name non-concretely, reject the whole field.
    A partial rewrite could otherwise change the field's meaning.
    """
    field_kind = _plain_field_kind(node, parm)
    if field_kind != kind:
        return text, (), ()

    if kind == "group":
        return _plain_group_rewrite(
            node, parm, text, item_class, old, new)
    return _plain_attribute_rewrite(
        node, parm, text, item_class, old, new)


def _plain_attribute_rewrite(node, parm, text, item_class, old, new):
    """Rewrite exact attribute operands after proving the field's owner."""
    exact = []
    complex_operands = []
    for operand in re.split(r"[\s,]+", text):
        match = ATTRIBUTE_TOKEN.match(operand)
        if match and match.group("name") == old:
            exact.append(operand)
        elif _attribute_pattern_references(operand, old):
            complex_operands.append(operand)

    if complex_operands:
        return text, (), (
            "complex attribute pattern containing '{}' was left unchanged".
            format(old),
        )
    if not exact:
        return text, (), ()

    owner, problem = _plain_attribute_owner(node, parm, old)
    if owner != item_class:
        if problem:
            return text, (), (problem,)
        if owner:
            return text, (), (
                "attribute field belongs to {} attributes, not {} attributes".
                format(owner, item_class),
            )
        return text, (), ("attribute owner is not proven",)

    value, count = re.subn(
        r"(?<![^\s,])(\^?)" + re.escape(old) + r"(?=$|[\s,])",
        lambda match: match.group(1) + new,
        text,
    )
    return value, (("parameter token",) if count else ()), ()


def _plain_group_rewrite(node, parm, text, item_class, old, new):
    """Rewrite exact group operands after proving the field's owner class."""
    exact = []
    complex_operands = []
    for operand in re.findall(r"\S+", text):
        match = GROUP_TOKEN.match(operand)
        if match and match.group("name") == old:
            exact.append(operand)
        elif re.search(WORD.format(re.escape(old)), operand):
            complex_operands.append(operand)

    if complex_operands:
        return text, (), (
            "complex group pattern containing '{}' was left unchanged".
            format(old),
        )
    if not exact:
        return text, (), ()

    owner, problem = _plain_group_owner(node, parm, old)
    if owner != item_class:
        if problem:
            return text, (), (problem,)
        if owner:
            return text, (), (
                "group field belongs to {} groups, not {} groups".format(
                    owner, item_class),
            )
        return text, (), ("group owner is not proven",)

    value, count = re.subn(
        r"(?<!\S)([!^&]?)" + re.escape(old) + r"(?=$|\s)",
        lambda match: match.group(1) + new,
        text,
    )
    return value, (("parameter token",) if count else ()), ()


def _plain_attribute_field_info(node, parm):
    """Describe a proven attribute-name field and its owner metadata."""
    template = parm.parmTemplate()
    if template.dataType() != hou.parmData.String:
        return None

    raw_name = parm.name().lower()
    compact_name = re.sub(r"[^a-z0-9]+", "", raw_name)
    label = re.sub(
        r"[^a-z0-9]+", " ", template.label().lower()).strip()
    if re.search(r"(?:default|value|data)", compact_name) or re.search(
            r"\b(?:default|value|data)\b", label):
        return None

    node_type = _base_node_type_name(node)
    owner_hints = set()
    companion_names = ()
    required_companion = False
    source_kind, source_index = "input", 0
    match_companions = ()
    recognized = False

    owner_codes = {
        "pt": "point",
        "point": "point",
        "pr": "primitive",
        "prim": "primitive",
        "primitive": "primitive",
        "vtx": "vertex",
        "vertex": "vertex",
        "dtl": "detail",
        "detail": "detail",
        "global": "detail",
    }

    if node_type in ("attribute", "attribdelete"):
        match = re.fullmatch(r"(pt|vtx|prim|dtl)(del|keep)", raw_name)
        if match:
            recognized = True
            owner_hints.add(owner_codes[match.group(1)])

    if node_type == "attribute":
        match = re.fullmatch(r"(from|to)(pt|vtx|pr|dtl)\d+", raw_name)
        if match:
            recognized = True
            owner_hints.add(owner_codes[match.group(2)])
            if match.group(1) == "to":
                source_kind = "output"

    promote_fields = {
        "inname": (("inclass",), "input"),
        "outname": (("outclass",), "output"),
        "pieceattrib": (("outclass",), "input"),
        "indexattrib": (("outclass",), "output"),
    }
    if node_type == "attribpromote" and raw_name in promote_fields:
        companion_names, source_kind = promote_fields[raw_name]
        required_companion = recognized = True

    if node_type == "attribcopy":
        if raw_name == "attribname":
            companion_names = ("class",)
            required_companion = recognized = True
            source_kind = "copy_source"
        elif raw_name == "newname":
            companion_names = ("class",)
            required_companion = recognized = True
            source_kind = "output"
        elif raw_name == "attributetomatch":
            match_companions = ("srcgrouptype", "destgrouptype")
            required_companion = recognized = True

    transfer_fields = {
        "detailattriblist": "detail",
        "primattriblist": "primitive",
        "pointattriblist": "point",
        "vertexattriblist": "vertex",
    }
    if node_type == "attribtransfer" and raw_name in transfer_fields:
        recognized = True
        owner_hints.add(transfer_fields[raw_name])

    match = re.fullmatch(r"(?:src|dst)attribs(\d+)", raw_name)
    if node_type == "attribswap" and match:
        companion_names = ("class" + match.group(1),)
        required_companion = recognized = True

    match = re.fullmatch(r"attribs(\d+)", raw_name)
    if node_type == "attribcast" and match:
        companion_names = ("class" + match.group(1),)
        required_companion = recognized = True

    match = re.fullmatch(r"name(\d+)", raw_name)
    if node_type == "attribcreate" and match:
        companion_names = ("class" + match.group(1),)
        required_companion = recognized = True
        source_kind = "output"

    name_match = re.fullmatch(
        r"(?P<direction>input|output|source|dest|src|dst|in|out)?"
        r"(?P<owner>point|pt|primitive|prim|vertex|vtx|detail|global)?"
        r"(?:attr|attrib|attribute)"
        r"(?:name|names|list|pattern|mask|s)?\d*",
        compact_name,
    )
    label_match = re.fullmatch(
        r"(?:(?P<owner>point|points|primitive|primitives|vertex|vertices|"
        r"detail|global)\s+)?"
        r"(?:(?P<direction>input|output|source|destination)\s+)?"
        r"(?:attribute|attrib)s?"
        r"(?:\s+(?:name|names|list|pattern|mask))?(?:\s+\d+)?",
        label,
    )
    if name_match or label_match:
        recognized = True
        for candidate in (name_match, label_match):
            if candidate and candidate.groupdict().get("owner"):
                owner_hints.update(
                    _owner_terms(candidate.group("owner"), "attribute"))
        direction = next(
            (candidate.groupdict().get("direction")
             for candidate in (name_match, label_match)
             if candidate and candidate.groupdict().get("direction")),
            None,
        )
        if direction in ("out", "output", "dst", "dest", "destination"):
            source_kind = "output"

    if not recognized:
        return None

    tag_input, tag_problem = _attribute_input_tag(template)
    if tag_input is not None and source_kind != "copy_source":
        source_kind, source_index = "input", tag_input

    if not owner_hints and not companion_names and not match_companions:
        companion_names = _attribute_companion_names(raw_name)

    return {
        "owner_hints": owner_hints,
        "companion_names": companion_names,
        "required_companion": required_companion,
        "match_companions": match_companions,
        "source_kind": source_kind,
        "source_index": source_index,
        "metadata_problem": tag_problem,
    }


def _attribute_input_tag(template):
    """Read an exact non-negative ``sop_input`` tag when one is present."""
    try:
        tags = dict(template.tags())
    except (AttributeError, TypeError):
        return None, None
    if "sop_input" not in tags:
        return None, None
    value = str(tags.get("sop_input", ""))
    if re.fullmatch(r"\d+", value):
        return int(value), None
    return None, "attribute input metadata is malformed"


def _attribute_companion_names(parm_name):
    """Return exact class-menu candidates for a generic attribute field."""
    suffix_match = re.search(r"(\d+)$", parm_name)
    suffix = suffix_match.group(1) if suffix_match else ""
    match = re.fullmatch(
        r"(?P<direction>input|output|source|dest|src|dst|in|out)?"
        r"(?:attr|attrib|attribute)(?:name|names|list|pattern|mask|s)?\d*",
        parm_name,
    )
    direction = match.group("direction") if match else ""
    candidates = []
    if direction:
        candidates.extend((
            direction + "class" + suffix,
            direction + "attribclass" + suffix,
            direction + "attributeclass" + suffix,
        ))
    if suffix:
        candidates.extend((
            "class" + suffix,
            "attribclass" + suffix,
            "attributeclass" + suffix,
        ))
    if not direction and not suffix:
        candidates.extend(("class", "attribclass", "attributeclass"))
    return tuple(dict.fromkeys(candidates))


def _plain_attribute_owner(node, parm, old_name):
    """Resolve an exact attribute owner from metadata or matching geometry."""
    info = _plain_attribute_field_info(node, parm)
    if info is None:
        return None, (
            "parameter metadata does not identify an attribute-name field")
    if info["metadata_problem"]:
        return None, info["metadata_problem"]

    if info["match_companions"]:
        return _attribute_copy_match_owner(node, info["match_companions"])

    menu_owner, automatic, menu_problem = _attribute_menu_owner(
        node, info["companion_names"], info["required_companion"])
    if menu_problem:
        return None, menu_problem

    owners = set(info["owner_hints"])
    if menu_owner:
        owners.add(menu_owner)
    if len(owners) > 1:
        return None, "attribute owner metadata conflicts"
    if len(owners) == 1:
        return next(iter(owners)), None
    if old_name is None:
        return None, None
    if not automatic:
        return None, "attribute owner is not proven"

    return _attribute_owner_from_geometry(
        node,
        info["source_kind"],
        info["source_index"],
        old_name,
    )


def _attribute_menu_owner(node, names, required):
    """Resolve an explicit attribute class or an automatic class request."""
    selected, problem = _selected_menu_entry(node, names, required)
    if problem or selected is None:
        return None, False, problem

    item, label = selected
    owners = _owner_terms(item + " " + label, "attribute")
    if len(owners) == 1:
        return next(iter(owners)), False, None
    words = set(re.sub(r"[^a-z0-9]+", " ", item + " " + label).split())
    if words.intersection(("any", "guess", "auto", "automatic", "detect")):
        return None, True, None
    if "sameasgroup" in item.replace("_", "").lower() or (
            {"use", "group", "type"}.issubset(words)):
        selected_group, group_problem = _selected_menu_entry(
            node, ("srcgrouptype",), True)
        if group_problem:
            return None, False, group_problem
        group_owners = _owner_terms(
            selected_group[0] + " " + selected_group[1], "attribute")
        if len(group_owners) == 1:
            return next(iter(group_owners)), False, None
        return None, False, "source group type has no exact attribute owner"
    return None, False, "attribute class menu selection has no exact owner"


def _selected_menu_entry(node, names, required):
    """Return one current item/label pair from a real Houdini menu."""
    by_name = {
        candidate.name().lower(): candidate for candidate in node.parms()}
    selected_parm = next(
        (by_name[name] for name in names if name in by_name), None)
    if selected_parm is None:
        if required:
            return None, (
                "required attribute class parameter '{}' does not exist".
                format(names[0] if names else "<unknown>"))
        return None, None

    template = selected_parm.parmTemplate()
    items = tuple(template.menuItems())
    labels = tuple(template.menuLabels())
    if not items or len(items) != len(labels):
        return None, "attribute class menu metadata is malformed"

    token = str(selected_parm.evalAsString())
    matches = [
        (str(item), str(labels[index]))
        for index, item in enumerate(items)
        if token == str(item)
    ]
    if len(matches) != 1:
        return None, "attribute class menu selection is not recognized"
    return matches[0], None


def _attribute_copy_match_owner(node, companion_names):
    """Require Attribute Copy's source and destination element classes to agree."""
    owners = []
    for name in companion_names:
        selected, problem = _selected_menu_entry(node, (name,), True)
        if problem:
            return None, problem
        terms = _owner_terms(selected[0] + " " + selected[1], "attribute")
        if len(terms) != 1:
            return None, "attribute match class is not proven"
        owners.append(next(iter(terms)))
    if len(set(owners)) != 1:
        return None, (
            "Attribute Copy source and destination classes do not agree")
    return owners[0], None


def _attribute_owner_from_geometry(
        node, source_kind, source_index, old_name):
    """Prove an automatic owner when one geometry class has the attribute."""
    source_label = "{} {}".format(source_kind, source_index + 1)
    try:
        if source_kind == "copy_source":
            source_node = node.input(1)
            if source_node is not None:
                geometry = node.inputGeometry(1)
                source_label = "input 2"
            else:
                use_new_name = node.parm("usenewname")
                if use_new_name is None or not use_new_name.evalAsInt():
                    return None, "Attribute Copy source geometry is unavailable"
                geometry = node.inputGeometry(0)
                source_label = "input 1"
        elif source_kind == "input":
            geometry = node.inputGeometry(source_index)
        else:
            try:
                geometry = node.geometry(source_index)
            except TypeError:
                if source_index:
                    return None, "{} cannot be inspected".format(source_label)
                geometry = node.geometry()
    except hou.OperationInterrupted:
        raise
    except hou.Error as error:
        return None, "{} cannot be inspected: {}".format(source_label, error)
    if geometry is None:
        return None, "{} returned no geometry".format(source_label)

    owners = set()
    collections = (
        ("point", "pointAttribs"),
        ("primitive", "primAttribs"),
        ("vertex", "vertexAttribs"),
        ("detail", "globalAttribs"),
    )
    for owner, method_name in collections:
        try:
            if any(attribute.name() == old_name
                   for attribute in getattr(geometry, method_name)()):
                owners.add(owner)
        except hou.OperationInterrupted:
            raise
        except hou.Error as error:
            return None, "{} cannot be inspected: {}".format(
                source_label, error)

    if len(owners) == 1:
        return next(iter(owners)), None
    if not owners:
        return None, (
            "automatic attribute owner is not proven; '{}' is absent from {}".
            format(old_name, source_label))
    return None, (
        "automatic attribute owner is ambiguous; '{}' exists in {} attributes".
        format(old_name, " and ".join(sorted(owners))))


def _plain_group_field_info(node, parm):
    """Describe a proven plain group field and how to resolve its owner.

    Names and labels use an explicit grammar. Parameter callback text is read
    only for literal ``parmTuple`` and input-index metadata; it is never
    executed. The returned record stays private because it contains HOM-aware
    planning details rather than part of the edit-record contract.
    """
    template = parm.parmTemplate()
    if template.dataType() != hou.parmData.String:
        return None

    raw_name = parm.name().lower()
    compact_name = re.sub(r"[^a-z0-9]+", "", raw_name)
    label = re.sub(
        r"[^a-z0-9]+", " ", template.label().lower()).strip()
    node_type = _base_node_type_name(node)

    special_new_name = (
        node_type in ("grouprename", "grouppromote")
        and re.fullmatch(r"newname\d+", compact_name)
    )
    name_match = re.fullmatch(
        r"(?:(?:in|out|input|output|src|dst|source|dest|selection|base|"
        r"col|collision))?"
        r"(?P<owner>point|pt|prim|primitive|edge)?"
        r"group(?:names|name|list|pattern|mask|s)?(?:[a-d])?\d*",
        compact_name,
    )
    label_match = re.fullmatch(
        r"(?:(?P<owner>point|points|primitive|primitives|edge|edges)\s+)?"
        r"(?:(?:input|output|source|destination|selection|base|collision)\s+)?"
        r"groups?(?:\s+(?:names|name|list|pattern|mask))?(?:\s+\d+)?",
        label,
    )
    if not special_new_name and not name_match and not label_match:
        return None

    owner_hints = set()
    for match in (name_match, label_match):
        if match and match.groupdict().get("owner"):
            owner_hints.update(_owner_terms(match.group("owner"), "group"))

    tag_companion, tag_input, tag_owner, tag_problem = (
        _group_selector_tags(template))
    if tag_owner:
        owner_hints.add(tag_owner)
    if node_type == "grouprange" and re.fullmatch(
            r"(?:group|colgroup)\d+", raw_name):
        # Group Range builds the companion name from the multiparm index in its
        # callback. Resolve that documented built-in layout from the actual
        # parameter suffix instead of evaluating the callback expression.
        tag_problem = None
    if tag_owner:
        companion_names, required_companion = (), False
    else:
        companion_names, required_companion = _group_companion_names(
            node_type, raw_name, tag_companion)
    parm_names = {candidate.name().lower() for candidate in node.parms()}
    has_companion = any(name in parm_names for name in companion_names)
    if (
        not owner_hints
        and not tag_companion
        and not tag_problem
        and not required_companion
        and not has_companion
    ):
        # Words such as "group" are also used for agent, guide, and other
        # non-geometry concepts. Without an owner term, a real class menu, or
        # Houdini's group chooser metadata, geometry-name matching alone is not
        # enough to prove that this is a point/primitive/edge group field.
        return None
    source_kind, source_index = _group_geometry_source(
        node_type, raw_name, template, tag_input)
    return {
        "owner_hints": owner_hints,
        "companion_names": companion_names,
        "required_companion": required_companion,
        "source_kind": source_kind,
        "source_index": source_index,
        "metadata_problem": tag_problem,
    }


def _base_node_type_name(node):
    """Return the unversioned operator name used by exact built-in rules."""
    name = node.type().name().lower()
    parts = name.split("::")
    if len(parts) > 1 and re.fullmatch(r"\d+(?:\.\d+)*", parts[-1]):
        return parts[-2]
    return parts[-1]


def _group_selector_tags(template):
    """Read literal group chooser metadata without executing callback code."""
    try:
        tags = dict(template.tags())
    except (AttributeError, TypeError):
        return None, None, None, None

    script = str(tags.get("script_action", ""))
    companion = input_index = owner = None
    problem = None
    selector_calls = re.findall(
        r"(?m)^[ \t]*soputils\.selectGroupParm\(kwargs\)[ \t]*$", script)
    if selector_calls:
        companion_matches = re.findall(
            r"(?m)^[ \t]*kwargs\[['\"]geometrytype['\"]\]\s*=\s*"
            r"kwargs\[['\"]node['\"]\]\.parmTuple\(\s*"
            r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)[ \t]*$",
            script,
        )
        owner_matches = re.findall(
            r"(?m)^[ \t]*kwargs\[['\"]geometrytype['\"]\]\s*=\s*"
            r"\(?\s*hou\.geometryType\."
            r"(Points|Primitives|Edges|Vertices)\b\s*,?\s*\)?[ \t]*$",
            script,
        )
        input_matches = re.findall(
            r"(?m)^[ \t]*kwargs\[['\"]inputindex['\"]\]\s*=\s*"
            r"(\d+)[ \t]*$",
            script,
        )
        if len(selector_calls) != 1:
            problem = "group chooser metadata has multiple selector calls"
        elif len(companion_matches) + len(owner_matches) != 1:
            problem = "group chooser metadata has no single literal class"
        elif len(input_matches) > 1:
            problem = "group chooser metadata has multiple input indexes"
        elif companion_matches:
            companion = companion_matches[0].lower()
        else:
            owner = {
                "Points": "point",
                "Primitives": "primitive",
                "Edges": "edge",
                "Vertices": "vertex",
            }[owner_matches[0]]
        if input_matches:
            input_index = int(input_matches[0])

    return companion, input_index, owner, problem


def _group_companion_names(node_type, parm_name, tag_companion):
    """Return exact class-menu candidates in strongest-to-weakest order."""
    if tag_companion:
        return (tag_companion,), True

    suffix_match = re.search(r"(\d+)$", parm_name)
    suffix = suffix_match.group(1) if suffix_match else ""
    if node_type == "grouppromote":
        if re.fullmatch(r"group\d+", parm_name):
            return ("fromtype" + suffix,), True
        if re.fullmatch(r"newname\d+", parm_name):
            return ("totype" + suffix,), True
    if node_type == "grouprange" and re.fullmatch(
            r"(?:group|colgroup)\d+", parm_name):
        stem = "colgrouptype" if parm_name.startswith("colgroup") else "grouptype"
        return (stem + suffix,), True
    if node_type == "grouprename" and re.fullmatch(
            r"newname\d+", parm_name):
        return ("grouptype" + suffix,), True

    candidates = []
    stem = re.sub(r"\d+$", "", parm_name)
    if "group" in stem:
        derived = re.sub(r"group(?:name|names|s)?$", "grouptype", stem)
        if derived != stem:
            candidates.append(derived + suffix)
    if suffix:
        candidates.extend((
            "grouptype" + suffix,
            "groupclass" + suffix,
            "groupentity" + suffix,
            "entity" + suffix,
        ))
    candidates.extend(("grouptype", "groupclass", "groupentity", "entity"))
    return tuple(dict.fromkeys(candidates)), False


def _group_geometry_source(
        node_type, parm_name, template, tag_input_index):
    """Return the exact geometry surface used for automatic owner proof."""
    if tag_input_index is not None:
        return "input", tag_input_index
    try:
        sop_input = str(template.tags().get("sop_input", ""))
    except (AttributeError, TypeError):
        sop_input = ""
    if re.fullmatch(r"\d+", sop_input):
        return "input", int(sop_input)

    output_rules = {
        "grouprename": r"newname\d+",
        "grouppromote": r"newname\d+",
        "groupcombine": r"group\d+",
        "groupexpression": r"groupname\d+",
        "groupexpand": r"outputgroup",
        "groupcreate": r"groupname",
        "grouprange": r"groupname\d+",
        "grouppaint": r"groupname",
    }
    pattern = output_rules.get(node_type)
    if pattern and re.fullmatch(pattern, parm_name):
        return "output", 0
    return "input", 0


def _plain_group_owner(node, parm, old_name):
    """Resolve an exact group owner from metadata or uniquely matching geometry."""
    info = _plain_group_field_info(node, parm)
    if info is None:
        return None, "parameter metadata does not identify a group-name field"
    if info["metadata_problem"]:
        return None, info["metadata_problem"]

    menu_owner, automatic, menu_problem = _group_menu_owner(
        node,
        info["companion_names"],
        info["required_companion"],
    )
    if menu_problem:
        return None, menu_problem

    owners = set(info["owner_hints"])
    if menu_owner:
        owners.add(menu_owner)
    if len(owners) > 1:
        return None, "group owner metadata conflicts"
    if len(owners) == 1:
        return next(iter(owners)), None
    if old_name is None:
        return None, None
    if not automatic and info["required_companion"]:
        return None, "group owner is not proven"

    return _group_owner_from_geometry(
        node,
        info["source_kind"],
        info["source_index"],
        old_name,
    )


def _group_menu_owner(node, names, required):
    """Resolve one exact owner or identify an automatic class-menu choice."""
    by_name = {
        candidate.name().lower(): candidate for candidate in node.parms()}
    selected_parm = next(
        (by_name[name] for name in names if name in by_name), None)
    if selected_parm is None:
        if required:
            return None, False, (
                "required group class parameter '{}' does not exist".format(
                    names[0] if names else "<unknown>"))
        return None, False, None

    template = selected_parm.parmTemplate()
    items = tuple(template.menuItems())
    labels = tuple(template.menuLabels())
    if not items or len(items) != len(labels):
        return None, False, "group class menu metadata is malformed"

    token = str(selected_parm.evalAsString())
    matches = [
        (str(item), str(labels[index]))
        for index, item in enumerate(items)
        if token == str(item)
    ]
    if len(matches) != 1:
        return None, False, "group class menu selection is not recognized"

    item, label = matches[0]
    owners = _owner_terms(item + " " + label, "group")
    if len(owners) == 1:
        return next(iter(owners)), False, None
    words = set(re.sub(r"[^a-z0-9]+", " ", item + " " + label).split())
    if words.intersection(("any", "guess", "auto", "automatic")):
        return None, True, None
    return None, False, "group class menu selection has no exact owner"


def _group_owner_from_geometry(
        node, source_kind, source_index, old_name):
    """Prove an automatic owner when exactly one geometry class has the name."""
    source_label = "{} {}".format(source_kind, source_index + 1)
    try:
        if source_kind == "input":
            geometry = node.inputGeometry(source_index)
        else:
            try:
                geometry = node.geometry(source_index)
            except TypeError:
                if source_index:
                    return None, "{} cannot be inspected".format(source_label)
                geometry = node.geometry()
    except hou.OperationInterrupted:
        raise
    except hou.Error as error:
        return None, "{} cannot be inspected: {}".format(source_label, error)
    if geometry is None:
        return None, "{} returned no geometry".format(source_label)

    owners = set()
    collections = (
        ("point", "pointGroups"),
        ("primitive", "primGroups"),
        ("edge", "edgeGroups"),
    )
    for owner, method_name in collections:
        try:
            if any(group.name() == old_name
                   for group in getattr(geometry, method_name)()):
                owners.add(owner)
        except hou.OperationInterrupted:
            raise
        except hou.Error as error:
            return None, "{} cannot be inspected: {}".format(
                source_label, error)

    if len(owners) == 1:
        return next(iter(owners)), None
    if not owners:
        return None, (
            "automatic group owner is not proven; '{}' is absent from {}".
            format(old_name, source_label))
    return None, (
        "automatic group owner is ambiguous; '{}' exists in {} groups".
        format(old_name, " and ".join(sorted(owners))))


def _plain_field_kind(node, parm):
    """Identify plain attribute or group fields from parameter metadata.

    Attribute and group resolvers share their exact field grammar with owner
    resolution. This prevents discovery from accepting a field that planning
    later interprets differently.
    """
    if _plain_attribute_field_info(node, parm) is not None:
        return "attribute"
    if _plain_group_field_info(node, parm) is not None:
        return "group"
    return None


def _owner_terms(text, kind):
    """Return owner names found as complete words in the text."""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    terms = set()
    table = (
        {
            "point": ("point", "points", "pt"),
            "primitive": ("primitive", "primitives", "prim"),
            "vertex": ("vertex", "vertices", "vtx"),
            "detail": ("detail", "global"),
        }
        if kind == "attribute"
        else {
            "point": ("point", "points", "pt"),
            "primitive": ("primitive", "primitives", "prim"),
            "edge": ("edge", "edges"),
            "vertex": ("vertex", "vertices", "vtx"),
        }
    )
    words = set(normalized.split())
    for owner, aliases in table.items():
        if words.intersection(aliases):
            terms.add(owner)
    return terms


# Expression languages and code fields

def _expression_language_kind(language):
    """Return the supported name for a Houdini expression-language enum."""
    if language == getattr(hou.exprLanguage, "Python", None):
        return "python"
    if language == getattr(hou.exprLanguage, "Hscript", None):
        return "hscript"
    return None


def _looks_like_python(node, parm):
    """Return whether metadata identifies a plain Python code field."""
    return (
        "python" in node.type().name().lower()
        and parm.name().lower() in ("python", "pythoncode", "code", "script")
    )


def _looks_like_vex(node, parm):
    """Return whether metadata identifies a plain Wrangle VEX field."""
    return (
        "wrangle" in node.type().name().lower()
        and parm.name().lower() in (
            "snippet", "vexpression", "code", "vexcode")
    )


def _wrangle_run_over_class(node, parm):
    """Return the Wrangle owner selected by a valid Run Over menu.

    Run Over proves only VEX ``@`` bindings, whose spelling omits the element
    class. Allowlisted function names already identify their owner.

    The selected value must be a recognized token from a real menu with
    matching labels. A free-form parameter or plausible label is not enough.
    """
    if "wrangle" not in node.type().name().lower():
        return None
    if parm.name().lower() not in (
            "snippet", "vexpression", "code", "vexcode"):
        return None
    for name in ("class", "runover"):
        candidate = node.parm(name)
        if candidate is None:
            continue
        template = candidate.parmTemplate()
        items = tuple(str(item).lower() for item in template.menuItems())
        labels = tuple(template.menuLabels())
        if not items or len(items) != len(labels):
            continue
        token = str(candidate.evalAsString()).strip().lower()
        owner = {
            "point": "point",
            "points": "point",
            "primitive": "primitive",
            "primitives": "primitive",
            "vertex": "vertex",
            "vertices": "vertex",
            "detail": "detail",
        }.get(token)
        if owner and token in items:
            return owner
    return None


__all__ = ("plan_parameter_rewrite",)
