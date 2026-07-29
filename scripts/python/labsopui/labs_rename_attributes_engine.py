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
    return (
        (kind, _plain_field_owner(node, parm, kind))
        if kind is not None
        else (None, None)
    )


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
        updated, reasons = _plain_rewrite(
            node, parm, text, kind, item_class, old, new)
        result = rewriters.make_result(text, updated, reasons=reasons)

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
    attribute operands also allow commas. ``old`` and ``^old`` are concrete,
    while wildcards, ranges, and other compound uses are not.

    If any operand uses the old name non-concretely, reject the whole field.
    A partial rewrite could otherwise change the field's meaning.
    """
    field_kind = _plain_field_kind(node, parm)
    if field_kind != kind:
        return text, ()
    owner = _plain_field_owner(node, parm, kind)
    if owner != item_class:
        return text, ()

    if kind == "group":
        operands = re.findall(r"\S+", text)
        if any(
            old in operand and operand not in (old, "^" + old)
            for operand in operands
        ):
            return text, ()
        value, count = re.subn(
            r"(?<!\S)(\^?)" + re.escape(old) + r"(?=$|\s)",
            lambda match: match.group(1) + new,
            text,
        )
    else:
        operands = re.findall(r"[^\s,]+", text)
        if any(
            re.search(WORD.format(re.escape(old)), operand)
            and operand not in (old, "^" + old)
            for operand in operands
        ):
            return text, ()
        value, count = re.subn(
            r"(?<![^\s,])(\^?)" + re.escape(old) + r"(?=$|[\s,])",
            lambda match: match.group(1) + new,
            text,
        )
    return value, (("parameter token",) if count else ())


def _plain_field_kind(node, parm):
    """Identify plain attribute or group fields from parameter metadata.

    Classification uses normalized names and labels, never the current value.
    Default, value, and data fields are excluded because their contents do not
    prove that the field stores a name.

    A generic ``name`` parameter counts only on a node whose type metadata
    explicitly identifies it as an attribute node.
    """
    name = re.sub(r"[^a-z0-9]+", "", parm.name().lower())
    label = re.sub(
        r"[^a-z0-9]+", " ", parm.parmTemplate().label().lower()).strip()
    if re.search(r"(?:default|value|data)", name) or re.search(
            r"\b(?:default|value|data)\b", label):
        return None
    if re.match(
            r"^(?:(?:in|out|input|output|src|dst|source|dest))?"
            r"(?:point|pt|prim|primitive|vertex|vtx|detail|global)?"
            r"(?:attr|attrib|attribute)(?:name|names|list|pattern|mask)?\d*$",
            name,
    ) or re.search(
            r"\b(?:attribute|attrib)\b(?:\s+(?:name|names|list|pattern|mask))?$",
            label,
    ):
        return "attribute"
    if re.match(
            r"^(?:(?:in|out|input|output|src|dst|source|dest))?"
            r"(?:point|pt|prim|primitive|edge)?"
            r"group(?:name|names|list|pattern|mask)?\d*$",
            name,
    ) or re.search(
            r"\bgroup\b(?:\s+(?:name|names|list|pattern|mask))?$", label
    ):
        return "group"
    node_hint = "{} {}".format(
        node.type().name(), node.type().description()).lower()
    if (
        re.match(r"^name\d*$", name)
        and ("attribute" in node_hint or "attrib" in node_hint)
    ):
        return "attribute"
    return None


def _plain_field_owner(node, parm, kind):
    """Return the owner when field metadata identifies exactly one.

    Owner words in the name and label are combined with a companion class/type
    menu. Numbered and directional fields reuse their suffix and prefix:
    ``name2`` may pair with ``class2`` and ``outattrib1`` with
    ``outattribclass1``.

    Missing, malformed, unknown, or conflicting metadata returns ``None``.
    Never infer an owner from menu position or a value that merely resembles
    an owner name.
    """
    descriptor = "{} {}".format(
        parm.name(), parm.parmTemplate().label()).lower()
    owners = _owner_terms(descriptor, kind)
    name = parm.name().lower()
    suffix_match = re.search(r"(\d+)$", name)
    suffix = suffix_match.group(1) if suffix_match else ""
    prefix_match = re.match(
        r"^(in|out|input|output|src|dst|source|dest)", name)
    prefix = prefix_match.group(1) if prefix_match else ""
    stems = (
        ("class", "attribclass", "attributeclass")
        if kind == "attribute"
        else ("grouptype", "groupclass", "groupentity", "entity")
    )
    candidate_names = []
    if suffix:
        candidate_names.extend(stem + suffix for stem in stems)
    if prefix:
        candidate_names.extend(prefix + stem + suffix for stem in stems)
    if not suffix and not prefix:
        candidate_names.extend(stems)

    by_name = {
        candidate.name().lower(): candidate for candidate in node.parms()}
    for candidate_name in candidate_names:
        candidate = by_name.get(candidate_name)
        if candidate is None:
            continue
        template = candidate.parmTemplate()
        items = tuple(template.menuItems())
        labels = tuple(template.menuLabels())
        if not items or len(items) != len(labels):
            return None
        token = str(candidate.evalAsString())
        selected = []
        for index, item in enumerate(items):
            if token == str(item):
                selected.extend((item, labels[index]))
        companion = set()
        for value in selected:
            companion.update(_owner_terms(str(value), kind))
        if len(companion) != 1:
            return None
        owners.update(companion)
    return next(iter(owners)) if len(owners) == 1 else None


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
