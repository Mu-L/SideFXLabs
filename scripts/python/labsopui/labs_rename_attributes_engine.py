"""Conservative, read-only planning for Labs attribute and group renames.

The shelf UI owns discovery, preview, confirmation, application, undo, and
reporting.  This module owns only the language-aware decision for one Houdini
parameter.  Keeping that boundary explicit makes the parser independently
testable and prevents preview caches from retaining live ``hou.Node`` or
``hou.Parm`` objects.

Public contract
---------------

``plan_parameter_rewrite(...)`` returns ``(edit, extra_edits, skipped)``:

* ``edit`` is ``None`` or the planned edit for the supplied parameter.
* ``extra_edits`` is retained for API compatibility.  Indirect ``chs()``
  targets are reported but never planned automatically.
* ``skipped`` contains structured explanations for matches that are not safe
  enough to change.

An edit is compatible with the existing Labs preview/apply code.  It contains
``node_path``, ``parm_name``, ``old_value``, ``new_value``, ``reasons``,
``value_kind``, ``storage_type``, optional expression-language metadata,
``code_type``, and ``risk``.  A skip contains ``node_path``, ``parm_name``,
and ``reason``.  Neither shape contains a live HOM object.

The engine deliberately favors false negatives over speculative changes.
Unknown expression languages, ambiguous Python receivers, dynamically
computed names, wildcards, comments, and unrelated literals are left intact.
"""

import ast
import re

try:
    import hou
except ImportError:  # Pure parser helpers remain importable outside Houdini.
    hou = None


RENAME_KIND_ATTRIBUTE = "attribute"
RENAME_KIND_GROUP = "group"

ANY_GROUP_CLASS = "any"
UNSUPPORTED_GROUP_CLASS = "vertex"
_AMBIGUOUS_OWNER = object()

ATTRIBUTE_CLASSES = frozenset(("point", "primitive", "vertex", "detail"))
GROUP_CLASSES = frozenset(("point", "primitive", "edge", ANY_GROUP_CLASS))

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
WORD = r"(?<![A-Za-z0-9_]){0}(?![A-Za-z0-9_])"


# VEX function names are case-sensitive.  The argument index is the
# zero-based position that carries the attribute/group name.
ATTR_VEX = {
    "point": (
        ("setpointattrib", 1),
        ("point", 1),
        ("pointattrib", 1),
        ("haspointattrib", 1),
        ("pointattribtype", 1),
        ("pointattribsize", 1),
    ),
    "primitive": (
        ("setprimattrib", 1),
        ("prim", 1),
        ("primattrib", 1),
        ("hasprimattrib", 1),
        ("primattribtype", 1),
        ("primattribsize", 1),
    ),
    "vertex": (
        ("setvertexattrib", 1),
        ("vertex", 1),
        ("vertexattrib", 1),
        ("hasvertexattrib", 1),
        ("vertexattribtype", 1),
        ("vertexattribsize", 1),
    ),
    "detail": (
        ("setdetailattrib", 1),
        ("detail", 1),
        ("detailattrib", 1),
        ("hasdetailattrib", 1),
        ("detailattribtype", 1),
        ("detailattribsize", 1),
    ),
}

GROUP_VEX = {
    "point": (
        ("setpointgroup", 1),
        ("inpointgroup", 1),
        ("expandpointgroup", 1),
        ("npointsgroup", 1),
    ),
    "primitive": (
        ("setprimgroup", 1),
        ("inprimgroup", 1),
        ("expandprimgroup", 1),
        ("nprimitivesgroup", 1),
    ),
    "edge": (
        ("setedgegroup", 1),
        ("inedgegroup", 1),
        ("expandedgegroup", 1),
        ("nedgesgroup", 1),
    ),
}

PY_ATTR = {
    "point": (
        "findPointAttrib",
        "deletePointAttrib",
        "pointFloatAttribValues",
        "pointIntAttribValues",
        "pointStringAttribValues",
        "setPointFloatAttribValues",
        "setPointIntAttribValues",
        "setPointStringAttribValues",
    ),
    "primitive": (
        "findPrimAttrib",
        "deletePrimAttrib",
        "primFloatAttribValues",
        "primIntAttribValues",
        "primStringAttribValues",
        "setPrimFloatAttribValues",
        "setPrimIntAttribValues",
        "setPrimStringAttribValues",
    ),
    "vertex": (
        "findVertexAttrib",
        "deleteVertexAttrib",
        "vertexFloatAttribValues",
        "vertexIntAttribValues",
        "vertexStringAttribValues",
        "setVertexFloatAttribValues",
        "setVertexIntAttribValues",
        "setVertexStringAttribValues",
    ),
    "detail": (
        "findGlobalAttrib",
        "deleteGlobalAttrib",
        "setGlobalAttribValue",
    ),
}

PY_GROUP = {
    "point": (
        "findPointGroup",
        "createPointGroup",
        "deletePointGroup",
        "destroyPointGroup",
    ),
    "primitive": (
        "findPrimGroup",
        "createPrimGroup",
        "deletePrimGroup",
        "destroyPrimGroup",
    ),
    "edge": (
        "findEdgeGroup",
        "createEdgeGroup",
        "deleteEdgeGroup",
        "destroyEdgeGroup",
    ),
}

# HScript is case-insensitive.  Group expressions remain unsupported because
# group parameters have a distinct pattern grammar handled by the plain-field
# rewriter.
HSCRIPT_ATTR = {
    "point": (("point", 2), ("haspointattrib", 1)),
    "primitive": (("prim", 2), ("primuv", 2), ("hasprimattrib", 1)),
    "vertex": (("vertex", 3), ("hasvertexattrib", 1)),
    "detail": (
        ("detail", 1),
        ("details", 1),
        ("hasdetailattrib", 1),
    ),
}


# ---------------------------------------------------------------------------
# Public planning contract and canonical edit records
# ---------------------------------------------------------------------------


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
    """Return ``(edit, [], skipped)`` without changing Houdini state.

    Invalid kinds, owner classes, or names raise ``ValueError``. Houdini
    cancellation propagates so the caller can restore its preview state.
    """
    kind = str(rename_kind or "").strip().lower()
    item_class = str(item_class or "").strip().lower()
    old_name = str(old_name or "")
    new_name = str(new_name or "")

    if kind not in (RENAME_KIND_ATTRIBUTE, RENAME_KIND_GROUP):
        raise ValueError("rename_kind must be 'attribute' or 'group'")
    valid_classes = ATTRIBUTE_CLASSES if kind == RENAME_KIND_ATTRIBUTE else GROUP_CLASSES
    if item_class not in valid_classes:
        raise ValueError(
            "unsupported {0} class: {1}".format(kind, item_class or "<empty>")
        )
    if not old_name or not IDENT.match(old_name):
        raise ValueError("old_name must be a non-empty identifier")
    if not new_name or not IDENT.match(new_name):
        raise ValueError("new_name must be a non-empty identifier")
    if old_name == new_name:
        raise ValueError("old_name and new_name must be different")

    node_path = _node_path(node)
    parm_name = _parm_name(parm)
    try:
        text, value_kind, language, storage_type = _parm_text(parm)
    except Exception as error:
        if _is_interrupted(error):
            raise
        return None, [], [
            _skip_record(
                node_path,
                parm_name,
                "could not inspect parameter source: {0}".format(error),
            )
        ]

    if text is None:
        keyed_problem = _ambiguous_keyed_string_problem(parm, old_name)
        return (
            None,
            [],
            (
                [_skip_record(node_path, parm_name, keyed_problem)]
                if keyed_problem
                else []
            ),
        )
    if storage_type not in ("string", "int", "float"):
        return None, [], [
            _skip_record(
                node_path,
                parm_name,
                "unsupported parameter storage",
            )
        ]
    if old_name not in text and not re.search(r"\bchs\s*\(", text, re.I):
        return None, [], []

    language_kind = (
        _expression_language_kind(language)
        if value_kind == "expression"
        else None
    )
    code_type = "Plain"
    value, reasons, skipped = text, [], []

    if value_kind == "expression" and language_kind is None:
        skipped = ["unsupported expression language or syntax"]
    elif language_kind == "hscript":
        code_type = "HScript"
        if kind == RENAME_KIND_ATTRIBUTE:
            value, reasons, skipped = _hscript_rewrite(
                node, parm, text, item_class, old_name, new_name
            )
        else:
            skipped = ["unsupported expression language or syntax"]
    elif language_kind == "python" or _looks_like_python(
        node, parm, text, language
    ):
        code_type = "Python"
        if rename_python:
            value, reasons, skipped = _python_rewrite(
                text, kind, item_class, old_name, new_name
            )
        else:
            skipped = ["Python rewrite disabled"]
    elif (
        kind == RENAME_KIND_ATTRIBUTE
        and _hscript_metadata(node, parm, language)
    ):
        code_type = "HScript"
        value, reasons, skipped = _hscript_rewrite(
            node, parm, text, item_class, old_name, new_name
        )
    elif _looks_like_vex(node, parm, text):
        code_type = "VEX"
        if rename_vex:
            value, reasons, skipped = _vex_rewrite(
                node,
                parm,
                text,
                kind,
                item_class,
                old_name,
                new_name,
                aggressive_vex,
            )
        else:
            skipped = ["VEX rewrite disabled"]
    elif kind == RENAME_KIND_ATTRIBUTE and _looks_like_hscript(
        text, item_class
    ):
        code_type = "HScript"
        value, reasons, skipped = _hscript_rewrite(
            node, parm, text, item_class, old_name, new_name
        )
    elif value_kind == "expression":
        skipped = ["unsupported expression language or syntax"]
    else:
        code_type = "Plain"
        value, reasons, skipped = _plain_rewrite(
            node, parm, text, kind, item_class, old_name, new_name
        )

    edit = None
    if value != text:
        edit = _edit_record(
            node_path,
            parm_name,
            text,
            value,
            reasons,
            value_kind,
            storage_type,
            language,
            code_type,
        )

    structured_skips = [
        item
        if isinstance(item, dict)
        else _skip_record(node_path, parm_name, item)
        for item in skipped
        if item
    ]
    return edit, [], _dedupe_skips(structured_skips)


def _ambiguous_keyed_string_problem(parm, old_name):
    """Explain an old-name match hidden behind multiple string keyframes."""
    if hou is None:
        return None
    try:
        template = parm.parmTemplate()
        if template.dataType() != hou.parmData.String or not parm.keyframes():
            return None
        if old_name in parm.evalAsString():
            return "string parameter has multiple or ambiguous keyframes"
    except Exception as error:
        if _is_interrupted(error):
            raise
    return None


def _parm_text(parm):
    """Return source text, source kind, expression language, and storage."""
    if hou is None:
        raise RuntimeError("Houdini's hou module is required to inspect parameters")
    storage_type = _parm_storage_type(parm)
    try:
        return (
            parm.expression(),
            "expression",
            parm.expressionLanguage(),
            storage_type,
        )
    except hou.OperationInterrupted:
        raise
    except hou.OperationFailed:
        pass

    if storage_type != "string":
        return None, None, None, storage_type
    if parm.keyframes():
        return None, None, None, storage_type
    return parm.unexpandedString(), "value", None, storage_type


def _parm_storage_type(parm):
    """Return the stable storage category used by stale-preview validation."""
    data_type = parm.parmTemplate().dataType()
    if data_type == getattr(hou.parmData, "String", None):
        return "string"
    if data_type == getattr(hou.parmData, "Int", None):
        return "int"
    if data_type == getattr(hou.parmData, "Float", None):
        return "float"
    return None


def _edit_record(
    node_path,
    parm_name,
    old_value,
    new_value,
    reasons,
    value_kind="value",
    storage_type="string",
    language=None,
    code_type="Plain",
):
    """Build one canonical, HOM-object-free edit record."""
    unique_reasons = tuple(dict.fromkeys(reason for reason in reasons if reason))
    language_label = _expression_language_label(language)
    edit = {
        "node_path": str(node_path or ""),
        "parm_name": str(parm_name or ""),
        "old_value": old_value,
        "new_value": new_value,
        "reasons": unique_reasons,
        "value_kind": value_kind,
        "storage_type": storage_type,
    }
    if language is not None:
        edit["language"] = language
    if language_label:
        edit["language_label"] = language_label
    edit["code_type"] = code_type
    edit["risk"] = _edit_risk(code_type, value_kind, unique_reasons)
    return edit


def _skip_record(node_path, parm_name, reason):
    return {
        "node_path": str(node_path or ""),
        "parm_name": str(parm_name or ""),
        "reason": str(reason or ""),
    }


def _dedupe_skips(skips):
    result = []
    seen = set()
    for skip in skips:
        key = (
            skip.get("node_path", ""),
            skip.get("parm_name", ""),
            skip.get("reason", ""),
        )
        if key not in seen:
            seen.add(key)
            result.append(skip)
    return result


def _edit_risk(code_type, value_kind, reasons):
    reasons = " ".join(reasons).lower()
    if "aggressive vex" in reasons:
        return "High"
    if value_kind == "expression":
        return "Expression"
    return "Code" if code_type != "Plain" else "Plain"


def _node_path(node):
    try:
        return node.path()
    except Exception:
        return ""


def _parm_name(parm):
    try:
        return parm.name()
    except Exception:
        return ""


def _is_interrupted(error):
    interrupted = getattr(hou, "OperationInterrupted", None) if hou else None
    return bool(interrupted and isinstance(error, interrupted))


def _expression_language_kind(language):
    """Accept only exact Houdini expression-language identities."""
    if hou is None:
        return None

    python_language = getattr(hou.exprLanguage, "Python", None)
    hscript_language = getattr(hou.exprLanguage, "Hscript", None)
    if python_language is None or hscript_language is None:
        return None
    enum_type = type(python_language)
    if type(language) is not enum_type:
        return None
    if language == python_language:
        return "python"
    if language == hscript_language:
        return "hscript"
    return None


def _expression_language_label(language):
    kind = _expression_language_kind(language)
    if kind == "python":
        return "Python"
    if kind == "hscript":
        return "HScript"
    return str(language) if language is not None else ""


# ---------------------------------------------------------------------------
# HScript call parsing
# ---------------------------------------------------------------------------


def _hscript_rewrite(node, source_parm, text, item_class, old, new):
    """Rewrite literal class-specific HScript attribute arguments."""
    replacements = []
    skipped = []
    reasons = []
    code_mask = _hscript_code_mask(text)
    for function, (start, end) in _calls(
        text, HSCRIPT_ATTR[item_class], code_mask=code_mask
    ):
        value, quote, literal_start, literal_end = _literal(text, start, end)
        if value == old:
            replacements.append(
                (literal_start, literal_end, quote + new + quote)
            )
            reasons.append("HScript {0} literal".format(function))
            continue

        argument = text[start:end].strip()
        chs_match = re.match(
            r"^chs\s*\(\s*(['\"])([^'\"]+)\1\s*\)$",
            argument,
            re.I,
        )
        if chs_match:
            problem = _referenced_parm_problem(
                node,
                source_parm,
                chs_match.group(2),
                "HScript {0} chs()".format(function),
            )
            skipped.append(problem)
        elif old in argument:
            skipped.append(
                "HScript {0} uses a dynamic name".format(function)
            )
    return _replace(text, replacements), reasons, skipped


def _calls(text, table, case_sensitive=False, code_mask=None):
    """Locate allowlisted calls and their name-bearing argument spans."""
    if not table:
        return []
    if code_mask is None:
        code_mask, _strings = _lex_vex(text)
    names = "|".join(re.escape(name) for name, _index in table)
    indexes = dict(table)
    flags = 0 if case_sensitive else re.I
    result = []
    for match in re.finditer(r"\b(" + names + r")\s*\(", text, flags):
        if not _span_is_code(code_mask, match.start(), match.end()):
            continue
        close = _close_paren(text, match.end() - 1, code_mask)
        if close < 0:
            continue
        arguments = _arguments(text, match.end(), close, code_mask)
        function = match.group(1) if case_sensitive else match.group(1).lower()
        index = indexes.get(function)
        if index is not None and len(arguments) > index:
            result.append((function, arguments[index]))
    return result


def _hscript_code_mask(text):
    """Mask HScript comments without treating VEX preprocessor lines as comments."""
    code_mask, _strings = _lex_vex(text)
    index = 0
    while index < len(text):
        if text[index] == "#" and code_mask[index]:
            start = index
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            code_mask[start:index] = [False] * (index - start)
            continue
        index += 1
    return code_mask


def _span_is_code(code_mask, start, end):
    """Return whether a source span lies outside comments and strings."""
    if start < 0 or end < start or end > len(code_mask):
        return False
    return all(code_mask[start:end])


def _close_paren(text, start, mask=None):
    """Find a balanced closing parenthesis while ignoring masked source."""
    depth = 0
    index = start
    while index < len(text):
        if mask is not None and not mask[index]:
            index += 1
            continue
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _arguments(text, start, end, mask=None):
    """Return trimmed spans of top-level arguments in a known call."""
    spans = []
    begin = start
    depth = 0
    index = start
    while index < end:
        if mask is not None and not mask[index]:
            index += 1
            continue
        char = text[index]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            spans.append((begin, index))
            begin = index + 1
        index += 1
    spans.append((begin, end))

    result = []
    for span_start, span_end in spans:
        raw = text[span_start:span_end]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        result.append((span_start + left, span_start + right))
    return result


def _referenced_parm_problem(node, source_parm, parm_name, reason):
    """Report, but never follow, an indirect ``chs()`` name reference."""
    source_path = _node_path(node)
    source_name = _parm_name(source_parm)
    return _skip_record(
        source_path,
        source_name,
        "{0} uses indirect chs('{1}'); referenced parameters are not edited "
        "automatically".format(reason, parm_name),
    )


def _literal(text, start, end):
    """Return a sole quoted literal and its exact source span."""
    raw = text[start:end]
    matches = list(re.finditer(r"(['\"])(.*?)\1", raw, re.S))
    if len(matches) != 1:
        return None, None, None, None
    match = matches[0]

    def only_spacing_and_comments(fragment):
        fragment = re.sub(
            r"/\*.*?\*/|//[^\n]*(?:\n|$)|#[^\n]*(?:\n|$)",
            "",
            fragment,
            flags=re.S,
        )
        return not fragment.strip()

    if not (
        only_spacing_and_comments(raw[: match.start()])
        and only_spacing_and_comments(raw[match.end() :])
    ):
        return None, None, None, None
    return (
        match.group(2),
        match.group(1),
        start + match.start(),
        start + match.end(),
    )


def _replace(text, replacements):
    """Apply non-overlapping source replacements from right to left."""
    used = []
    for start, end, value in sorted(replacements, reverse=True):
        if (
            start < 0
            or end < start
            or any(start < used_end and end > used_start for used_start, used_end in used)
        ):
            continue
        text = text[:start] + value + text[end:]
        used.append((start, end))
    return text


# ---------------------------------------------------------------------------
# Python AST rewriting and conservative owner inference
# ---------------------------------------------------------------------------


def _python_rewrite(text, kind, item_class, old, new):
    """Rewrite allowlisted HOM calls using source-positioned Python AST nodes."""
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return text, [], [
            "Python could not be parsed: {0}".format(error)
        ]
    analysis = _PythonAnalysis(tree)

    method_table = PY_ATTR if kind == RENAME_KIND_ATTRIBUTE else PY_GROUP
    if kind == RENAME_KIND_GROUP and item_class == ANY_GROUP_CLASS:
        methods = tuple(
            method
            for class_methods in method_table.values()
            for method in class_methods
        )
    else:
        methods = method_table[item_class]

    receiver_owners = _python_owner_bindings(analysis)
    old_alias_names = _python_old_literal_names(old, receiver_owners)
    candidates = []
    skipped = []

    for call in (
        candidate
        for candidate in analysis.nodes
        if isinstance(candidate, ast.Call)
    ):
        candidate, problem = _python_call_candidate(
            text,
            call,
            kind,
            item_class,
            methods,
            receiver_owners,
            old,
            old_alias_names,
        )
        if problem:
            skipped.append(problem)
        if candidate is None:
            continue
        candidates.append(candidate)

    authorized_arguments = {id(candidate[2]) for candidate in candidates}
    aliases = _py_assignments(
        analysis, old, authorized_arguments, receiver_owners
    )
    replacements = []

    for _call, name, argument in candidates:
        assigned = None
        if isinstance(argument, ast.Name):
            scope = _python_context_scope(argument, receiver_owners)
            assigned = aliases.get((scope, argument.id))
        if isinstance(argument, ast.Constant) and argument.value == old:
            target = argument
        elif assigned and len(assigned) == 1 and assigned[0] is not None:
            target = assigned[0]
        else:
            target = None

        if target is not None:
            span = _python_node_span(text, target)
            if span:
                replacements.append(
                    (
                        span[0],
                        span[1],
                        _quoted_like(text[span[0] : span[1]], new),
                    )
                )
        elif assigned is not None:
            noun = "group " if kind == RENAME_KIND_GROUP else ""
            skipped.append(
                "Python {0} {1}reference '{2}' has ambiguous local assignments".format(
                    name, noun, argument.id
                )
            )
        else:
            argument_source = ast.get_source_segment(text, argument) or ""
            if old in argument_source:
                skipped.append(
                    "Python {0} uses a dynamic name".format(name)
                )

    changed = _replace(text, replacements)
    reasons = ["Python HOM method"] if changed != text else []
    return changed, reasons, skipped


def _python_call_candidate(
    text,
    call,
    kind,
    item_class,
    methods,
    receiver_owners,
    old,
    old_alias_names,
):
    """Return one class-safe HOM name argument and an optional skip reason."""
    name = _python_call_name(call)
    index = 0
    receiver = call.func.value if isinstance(call.func, ast.Attribute) else None
    call_scope = _python_context_scope(call, receiver_owners)

    if kind == RENAME_KIND_ATTRIBUTE and name in (
        "attribValue",
        "setAttribValue",
    ):
        if not call.args:
            return None, None
        owner = _infer_python_owner(
            receiver, receiver_owners, call_scope
        )
        method_supports_owner = (
            name == "attribValue"
            or owner in ("point", "primitive", "vertex")
        )
        if owner != item_class or not method_supports_owner:
            problem = None
            if owner is None and _python_argument_mentions_old(
                text,
                call.args[0],
                old,
                old_alias_names,
                receiver_owners,
                call_scope,
            ):
                problem = (
                    "Python {0} has an ambiguous HOM receiver or "
                    "attribute owner".format(name)
                )
            return None, problem

    elif kind == RENAME_KIND_ATTRIBUTE and name == "addAttrib":
        if len(call.args) <= 1:
            return None, None
        if (
            _infer_python_owner(
                receiver, receiver_owners, call_scope
            )
            != "detail"
        ):
            problem = None
            if _python_argument_mentions_old(
                text,
                call.args[1],
                old,
                old_alias_names,
                receiver_owners,
                call_scope,
            ):
                problem = (
                    "Python addAttrib has an ambiguous HOM geometry receiver"
                )
            return None, problem
        owner = _python_add_attrib_class(
            call, receiver_owners, call_scope
        )
        if owner != item_class:
            problem = None
            if owner is None and _python_argument_mentions_old(
                text,
                call.args[1],
                old,
                old_alias_names,
                receiver_owners,
                call_scope,
            ):
                problem = "Python addAttrib has an unknown attribute owner"
            return None, problem
        index = 1

    elif name in methods:
        if not call.args:
            return None, None
        if (
            _infer_python_owner(
                receiver, receiver_owners, call_scope
            )
            != "detail"
        ):
            problem = None
            if _python_argument_mentions_old(
                text,
                call.args[0],
                old,
                old_alias_names,
                receiver_owners,
                call_scope,
            ):
                problem = (
                    "Python {0} has an ambiguous HOM geometry receiver".format(
                        name
                    )
                )
            return None, problem
    else:
        return None, None

    if len(call.args) <= index:
        return None, None
    return (call, name, call.args[index]), None


def _python_argument_mentions_old(
    text,
    argument,
    old,
    old_alias_names,
    owners,
    scope,
):
    """Recognize direct old-name syntax or a local literal alias."""
    if (
        isinstance(argument, ast.Name)
        and (scope, argument.id) in old_alias_names
    ):
        return True
    for node in ast.walk(argument):
        if isinstance(node, ast.Constant) and node.value == old:
            return True
        if isinstance(node, ast.Name) and node.id == old:
            return True
    return False


def _python_old_literal_names(old, owners):
    """Return names that have at least one simple old-name literal binding."""
    result = set()
    for key, records in owners.get(_PY_BINDING_SOURCES_KEY, {}).items():
        if any(
            source_kind == "value"
            and isinstance(value, ast.Constant)
            and value.value == old
            for source_kind, value in records
        ):
            result.add(key)
    return result


def _py_assignments(analysis, old, authorized_arguments=(), owners=None):
    """Return literal aliases only when every binding and use is proven safe."""
    owners = owners or _python_owner_bindings(analysis)
    parents = owners.get(_PY_PARENTS_KEY, {})
    bindings = owners.get(_PY_BINDING_SOURCES_KEY, {})
    authorized_arguments = set(authorized_arguments)
    values = {}
    for (scope, name), name_bindings in bindings.items():
        if not _python_scope_allows_inference(scope, owners):
            continue
        literal_bindings = [
            value
            for source_kind, value in name_bindings
            if source_kind == "value"
            and isinstance(value, ast.Constant)
            and value.value == old
        ]
        if not literal_bindings:
            continue
        literal = literal_bindings[0]
        same_name_bindings = [
            records
            for (_other_scope, other_name), records in bindings.items()
            if other_name == name
        ]
        safe = (
            len(same_name_bindings) == 1
            and len(name_bindings) == 1
            and len(literal_bindings) == 1
        )
        if safe:
            loads = [
                node
                for node in analysis.nodes
                if isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id == name
                and _python_resolved_binding_scope(
                    _python_enclosing_scope(node, parents),
                    name,
                    owners,
                )
                is scope
            ]
            safe = bool(loads) and all(
                id(load) in authorized_arguments
                and _python_enclosing_scope(load, parents) is scope
                for load in loads
            )
        values[(scope, name)] = (
            [literal] if safe else [literal, None]
        )
    return values


def _python_enclosing_scope(node, parents):
    """Return the nearest lexical scope containing an AST node."""
    current = node
    while current is not None:
        if isinstance(current, _PY_SCOPE_TYPES):
            return current
        current = parents.get(current)
    return None


_PY_NODE_OWNER = "node"
_PY_SEQUENCE_SUFFIX = "_sequence"
_PY_PARENTS_KEY = object()
_PY_SCOPE_PARENTS_KEY = object()
_PY_SCOPE_BOUND_NAMES_KEY = object()
_PY_BINDING_SOURCES_KEY = object()
_PY_POISONED_SCOPES_KEY = object()
_PY_ATTRIB_TYPE_MUTATIONS_KEY = object()
_PY_HOU_FACTORY_MUTATIONS_KEY = object()
_PY_HOM_METHOD_MUTATIONS_KEY = object()
_PY_SCOPE_TYPES = (
    ast.Module,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
    ast.ClassDef,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)
_PY_ATTRIB_TYPE_OWNER_MEMBERS = frozenset(
    ("Point", "Prim", "Vertex", "Global")
)
_PY_TRUSTED_HOM_TYPES = frozenset(
    ("Node", "SopNode", "Geometry", "Point", "Prim", "Vertex")
)
_PY_TRUSTED_HOM_METHODS = frozenset(
    (
        "geometry",
        "point",
        "createPoint",
        "points",
        "iterPoints",
        "globPoints",
        "prim",
        "primAt",
        "createPolygon",
        "createNURBSCurve",
        "prims",
        "iterPrims",
        "globPrims",
        "vertices",
        "iterVertices",
        "attribValue",
        "setAttribValue",
        "addAttrib",
    )
    + tuple(
        method
        for table in (PY_ATTR, PY_GROUP)
        for methods in table.values()
        for method in methods
    )
)
_PY_NAMESPACE_MUTATORS = frozenset(
    (
        "update",
        "clear",
        "pop",
        "popitem",
        "setdefault",
        "__setitem__",
        "__delitem__",
    )
)
_PY_DYNAMIC_CALL_NAMES = frozenset(
    (
        "eval",
        "exec",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setitem",
        "delitem",
        "__setattr__",
        "__delattr__",
        "__setitem__",
        "__delitem__",
    )
)


class _PythonAnalysis:
    """One reusable inventory of a parsed Python parameter."""

    __slots__ = ("tree", "nodes", "parents", "scopes", "assignments", "defaults")

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tuple(ast.walk(tree))
        self.parents = {
            child: parent
            for parent in self.nodes
            for child in ast.iter_child_nodes(parent)
        }
        self.scopes = tuple(
            node for node in self.nodes if isinstance(node, _PY_SCOPE_TYPES)
        )
        assignments = []
        defaults = []
        for node in self.nodes:
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = (node.target,), node.value
            elif isinstance(node, ast.NamedExpr):
                targets, value = (node.target,), node.value
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                targets, value = (node.target,), node.iter
            else:
                targets = ()
                value = None
            assignments.extend(
                (name, value)
                for target in targets
                for name in _all_assignment_target_names(target)
            )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                defaults.extend(
                    (argument.arg, default)
                    for argument, default in _python_default_bindings(node.args)
                )
        self.assignments = tuple(assignments)
        self.defaults = tuple(defaults)


def _python_call_requests_object_dict(call):
    """Recognize bound or unbound getattr access to ``__dict__``."""
    return (
        isinstance(call, ast.Call)
        and _python_call_name(call) in ("getattr", "__getattribute__")
        and any(
            isinstance(argument, ast.Constant)
            and argument.value == "__dict__"
            for argument in call.args
        )
    )


def _python_expression_may_be_trusted_hom_type(
    expression,
    hou_aliases=("hou",),
    trusted_type_aliases=(),
):
    """Recognize conservative ways a trusted HOM class object is obtained."""
    if isinstance(expression, ast.Name):
        return expression.id in trusted_type_aliases

    if isinstance(expression, ast.Attribute) and expression.attr == "__class__":
        return True

    root_name, attributes, keys = _python_target_parts(expression)
    if root_name in hou_aliases and any(
        member in _PY_TRUSTED_HOM_TYPES
        for member in attributes + keys
        if member is not None
    ):
        return True

    if isinstance(expression, ast.Subscript):
        requested_type = _python_constant_subscript_key(expression)
        namespace = expression.value
        if requested_type in _PY_TRUSTED_HOM_TYPES:
            if (
                isinstance(namespace, ast.Call)
                and _python_call_name(namespace) == "vars"
                and namespace.args
                and isinstance(namespace.args[0], ast.Name)
                and namespace.args[0].id in hou_aliases
            ):
                return True
            namespace_root, namespace_attributes, _namespace_keys = (
                _python_target_parts(namespace)
            )
            if (
                namespace_root in hou_aliases
                and "__dict__" in namespace_attributes
            ):
                return True
        return _python_expression_may_be_trusted_hom_type(
            namespace,
            hou_aliases,
            trusted_type_aliases,
        )

    if isinstance(expression, ast.Call):
        call_name = _python_call_name(expression)
        if call_name == "type":
            return True
        if (
            call_name == "getattr"
            and len(expression.args) > 1
            and isinstance(expression.args[0], ast.Name)
            and expression.args[0].id in hou_aliases
            and isinstance(expression.args[1], ast.Constant)
            and expression.args[1].value in _PY_TRUSTED_HOM_TYPES
        ):
            return True
        if (
            call_name == "mro"
            and isinstance(expression.func, ast.Attribute)
            and _python_expression_may_be_trusted_hom_type(
                expression.func.value,
                hou_aliases,
                trusted_type_aliases,
            )
        ):
            return True
    return False


def _python_mutation_aliases(analysis):
    """Collect possible aliases of trusted HOM objects and namespaces."""
    hou_aliases = {"hou"}
    attrib_type_aliases = set()
    trusted_type_aliases = set()
    hou_namespace_aliases = set()
    attrib_namespace_aliases = set()
    dynamic_namespace_aliases = set()
    builtins_namespace_aliases = {"__builtins__", "builtins"}
    for node in analysis.nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "hou":
                    hou_aliases.add(alias.asname or "hou")
                elif alias.name == "builtins":
                    builtins_namespace_aliases.add(alias.asname or "builtins")
        elif isinstance(node, ast.ImportFrom) and node.module == "hou":
            trusted_type_aliases.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name in _PY_TRUSTED_HOM_TYPES
            )

    alias_sets = (
        hou_aliases,
        attrib_type_aliases,
        trusted_type_aliases,
        hou_namespace_aliases,
        attrib_namespace_aliases,
        dynamic_namespace_aliases,
        builtins_namespace_aliases,
    )
    while True:
        previous_sizes = tuple(len(aliases) for aliases in alias_sets)
        for target_name, value in analysis.assignments:
            def mark(condition, *targets):
                if condition:
                    for aliases in targets:
                        aliases.add(target_name)

            source_name = value.id if isinstance(value, ast.Name) else None
            for aliases in (
                hou_aliases,
                attrib_type_aliases,
                hou_namespace_aliases,
                attrib_namespace_aliases,
                dynamic_namespace_aliases,
            ):
                mark(source_name in aliases, aliases)
            mark(
                source_name in builtins_namespace_aliases,
                builtins_namespace_aliases,
                dynamic_namespace_aliases,
            )
            if (
                isinstance(value, ast.Attribute)
                and value.attr == "attribType"
                and isinstance(value.value, ast.Name)
            ):
                mark(value.value.id in hou_aliases, attrib_type_aliases)
            root_name, attributes, _keys = _python_target_parts(value)
            mark(
                _python_expression_may_be_trusted_hom_type(
                    value,
                    hou_aliases,
                    trusted_type_aliases,
                ),
                trusted_type_aliases,
            )
            if "__dict__" in attributes:
                if (
                    root_name in attrib_type_aliases
                    or (
                        root_name in hou_aliases
                        and "attribType" in attributes
                    )
                ):
                    mark(True, attrib_namespace_aliases)
                elif root_name in hou_aliases:
                    mark(True, hou_namespace_aliases)
                else:
                    mark(True, dynamic_namespace_aliases)
            if isinstance(value, ast.Call):
                call_name = _python_call_name(value)
                if call_name == "vars" and value.args:
                    value_root, value_attributes, _value_keys = (
                        _python_target_parts(value.args[0])
                    )
                    if (
                        value_root in attrib_type_aliases
                        or (
                            value_root in hou_aliases
                            and "attribType" in value_attributes
                        )
                    ):
                        mark(True, attrib_namespace_aliases)
                    elif value_root in hou_aliases:
                        mark(True, hou_namespace_aliases)
                    else:
                        mark(True, dynamic_namespace_aliases)
                elif _python_call_requests_object_dict(value):
                    mark(True, dynamic_namespace_aliases)
                elif call_name in ("globals", "locals"):
                    mark(True, dynamic_namespace_aliases)
            mark(
                any(
                    isinstance(part, ast.Attribute)
                    and part.attr == "__dict__"
                    for part in ast.walk(value)
                ),
                dynamic_namespace_aliases,
            )
        if previous_sizes == tuple(len(aliases) for aliases in alias_sets):
            break
    return (
        frozenset(hou_aliases),
        frozenset(attrib_type_aliases),
        frozenset(trusted_type_aliases),
        frozenset(hou_namespace_aliases),
        frozenset(attrib_namespace_aliases),
        frozenset(dynamic_namespace_aliases),
    )


def _python_default_bindings(arguments):
    """Return parameter/default pairs for functions and lambdas."""
    positional = tuple(getattr(arguments, "posonlyargs", ())) + tuple(
        arguments.args
    )
    defaults = tuple(arguments.defaults)
    result = list(
        zip(
            positional[len(positional) - len(defaults) :],
            defaults,
        )
    )
    result.extend(
        (argument, default)
        for argument, default in zip(
            arguments.kwonlyargs,
            arguments.kw_defaults,
        )
        if default is not None
    )
    return tuple(result)


def _alias_closure(assignments, seeds, predicate):
    """Expand assignment aliases until a shared conservative rule stabilizes."""
    aliases = set(seeds)
    while True:
        additions = {
            name
            for name, value in assignments
            if name not in aliases and predicate(value, aliases)
        }
        if not additions:
            return frozenset(aliases)
        aliases.update(additions)


def _python_dynamic_call_aliases(analysis):
    """Collect aliases that can execute code or mutate an unknown namespace."""
    risky = _PY_DYNAMIC_CALL_NAMES
    mutators = risky | _PY_NAMESPACE_MUTATORS
    seeds = {"__builtins__", "builtins"}
    for node in analysis.nodes:
        if isinstance(node, ast.Import):
            seeds.update(
                alias.asname or "builtins"
                for alias in node.names
                if alias.name == "builtins"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "builtins":
            seeds.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name in risky
            )

    def is_risky(value, aliases):
        names = risky | frozenset(aliases)
        if any(
            isinstance(part, ast.Name) and part.id in names
            or isinstance(part, ast.Attribute) and part.attr in mutators
            or isinstance(part, ast.Subscript)
            and _python_constant_subscript_key(part) in mutators
            for part in ast.walk(value)
        ):
            return True
        if not isinstance(value, ast.Call):
            return False
        call_name = _python_call_name(value)
        requested = (
            value.args[1].value
            if call_name == "getattr"
            and len(value.args) > 1
            and isinstance(value.args[1], ast.Constant)
            and isinstance(value.args[1].value, str)
            else None
        )
        return call_name == "getattr" or requested in mutators

    return _alias_closure(
        analysis.assignments + analysis.defaults, seeds, is_risky
    )


def _python_expression_contains_risky_callable(expression, aliases=()):
    """Detect a loaded callable that can execute code or mutate objects."""
    risky_names = (
        _PY_DYNAMIC_CALL_NAMES
        | _PY_NAMESPACE_MUTATORS
        | frozenset(aliases)
    )
    for part in ast.walk(expression):
        if (
            isinstance(part, ast.Name)
            and isinstance(part.ctx, ast.Load)
            and part.id in risky_names
        ):
            return True
        if isinstance(part, ast.Attribute) and part.attr in risky_names:
            return True
        if (
            isinstance(part, ast.Subscript)
            and _python_constant_subscript_key(part) in risky_names
        ):
            return True
    return False


def _python_uses_mock_patch(analysis):
    """Treat unittest.mock patching as an unbounded runtime mutation."""
    for node in analysis.nodes:
        if isinstance(node, ast.Import) and any(
            alias.name in ("unittest.mock", "mock")
            for alias in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom):
            if node.module in ("unittest.mock", "mock"):
                return True
            if (
                node.module == "unittest"
                and any(alias.name == "mock" for alias in node.names)
            ):
                return True
        if isinstance(node, ast.Call):
            function = node.func
            parts = []
            while isinstance(function, ast.Attribute):
                parts.append(function.attr)
                function = function.value
            if isinstance(function, ast.Name):
                parts.append(function.id)
            parts.reverse()
            if "patch" in parts:
                return True
    return False


def _python_owner_bindings(analysis):
    """Infer receiver owners from complete bindings in one lexical scope."""
    parents = analysis.parents
    scopes = analysis.scopes
    scope_parents = {
        scope: _python_enclosing_scope(parents.get(scope), parents)
        for scope in scopes
    }

    sources = {}
    bound_names = {scope: set() for scope in scopes}
    poisoned_scopes = set()
    attrib_type_mutations = set()
    hou_factory_mutations = set()
    hom_method_mutations = set()
    if _python_uses_mock_patch(analysis):
        hom_method_mutations.add(True)
    (
        hou_aliases,
        attrib_type_aliases,
        trusted_type_aliases,
        hou_namespace_aliases,
        attrib_namespace_aliases,
        dynamic_namespace_aliases,
    ) = _python_mutation_aliases(analysis)
    dynamic_call_aliases = _python_dynamic_call_aliases(analysis)

    def scope_for(node):
        return _python_enclosing_scope(node, parents)

    def mark_attrib_scope(node):
        target_scope = scope_for(node)
        if target_scope is not None:
            attrib_type_mutations.add(target_scope)
        return target_scope

    def add_source(names, source_kind, expression, node, scope=None):
        target_scope = scope if scope is not None else scope_for(node)
        if target_scope is None:
            return
        for name in names:
            if not name:
                continue
            bound_names.setdefault(target_scope, set()).add(name)
            sources.setdefault((target_scope, name), []).append(
                (source_kind, expression)
            )

    def add_unknown(names, node, scope=None):
        add_source(names, "unknown", None, node, scope)

    def mark_target_mutation(target, node):
        if _python_target_mutates_hou_attrib_type(
            target,
            hou_aliases,
            attrib_type_aliases,
            hou_namespace_aliases,
            attrib_namespace_aliases,
        ):
            mark_attrib_scope(node)
        hou_factory_mutations.update(
            _python_hou_factory_roots(target, hou_aliases, hou_namespace_aliases)
        )
        root_name, attributes, keys = _python_target_parts(target)
        if (
            _python_target_mutates_trusted_hom_type(
                target, hou_aliases, trusted_type_aliases
            )
            or _python_expression_accesses_object_dict(target)
            or any(
                member in _PY_TRUSTED_HOM_METHODS
                for member in attributes + keys
                if member is not None
            )
        ):
            hom_method_mutations.add(True)
        if root_name in dynamic_namespace_aliases:
            hou_factory_mutations.update(("node", "pwd"))
            hom_method_mutations.add(True)
            target_scope = mark_attrib_scope(node)
            if target_scope is not None:
                poisoned_scopes.add(target_scope)

    def add_binding(target, source_kind, expression, node):
        names = _assignment_target_names(target)
        if names and expression is not None:
            add_source(names, source_kind, expression, node)
        else:
            add_unknown(_all_assignment_target_names(target), node)

    def poison_dynamic_provenance(node):
        hou_factory_mutations.update(("node", "pwd"))
        hom_method_mutations.add(True)
        target_scope = mark_attrib_scope(node)
        if target_scope is not None:
            poisoned_scopes.add(target_scope)

    def expression_escapes_provenance(
        expression, include_trusted_objects=False
    ):
        return _python_expression_contains_risky_callable(
            expression,
            dynamic_call_aliases,
        ) or _python_expression_exposes_namespace(
            expression,
            hou_aliases,
            attrib_type_aliases,
            trusted_type_aliases,
            hou_namespace_aliases,
            attrib_namespace_aliases,
            dynamic_namespace_aliases,
            include_trusted_objects,
        )

    for node in analysis.nodes:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                mark_target_mutation(target, node)
                add_binding(target, "value", node.value, node)
        elif isinstance(node, ast.AnnAssign):
            mark_target_mutation(node.target, node)
            add_binding(node.target, "value", node.value, node)
        elif isinstance(node, (ast.AugAssign, ast.NamedExpr)):
            mark_target_mutation(node.target, node)
            add_unknown(_all_assignment_target_names(node.target), node)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            add_binding(node.target, "iteration", node.iter, node)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    add_unknown(
                        _all_assignment_target_names(item.optional_vars),
                        node,
                    )
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                mark_target_mutation(target, node)
                add_unknown(_all_assignment_target_names(target), node)
        unknown_names, unknown_scope = (), None
        if isinstance(node, ast.arg):
            unknown_names = (node.arg,)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            unknown_names = (node.name,)
            unknown_scope = _python_enclosing_scope(parents.get(node), parents)
        elif isinstance(node, ast.Import):
            unknown_names = tuple(
                alias.asname or alias.name.split(".", 1)[0]
                for alias in node.names
                if alias.name != "*"
                and not (
                    alias.name == "hou"
                    and (alias.asname is None or alias.asname == "hou")
                )
            )
        elif isinstance(node, ast.ImportFrom):
            if any(alias.name == "*" for alias in node.names):
                target_scope = scope_for(node)
                if target_scope is not None:
                    poisoned_scopes.add(target_scope)
            unknown_names = tuple(
                alias.asname or alias.name
                for alias in node.names
                if alias.name != "*"
            )
        elif isinstance(node, ast.ExceptHandler) and node.name:
            unknown_names = (node.name,)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            unknown_names = tuple(node.names)
        elif hasattr(ast, "MatchAs") and isinstance(node, ast.MatchAs):
            unknown_names = (node.name,)
        elif hasattr(ast, "MatchStar") and isinstance(node, ast.MatchStar):
            unknown_names = (node.name,)
        elif (
            hasattr(ast, "MatchMapping")
            and isinstance(node, ast.MatchMapping)
            and node.rest
        ):
            unknown_names = (node.rest,)
        elif hasattr(ast, "TypeAlias") and isinstance(node, ast.TypeAlias):
            unknown_names = ((
                node.name.id
                if isinstance(node.name, ast.Name)
                else str(node.name or "")
            ),)
        if unknown_names:
            add_unknown(unknown_names, node, unknown_scope)

        for parameter in getattr(node, "type_params", ()):
            parameter_scope = (
                node
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                else scope_for(node)
            )
            parameter_name = getattr(parameter, "name", "")
            if isinstance(parameter_name, ast.Name):
                parameter_name = parameter_name.id
            add_unknown((str(parameter_name or ""),), parameter, parameter_scope)

        include_trusted_objects = isinstance(
            node, (ast.Return, ast.Yield, ast.YieldFrom)
        )
        escaped_value = (
            getattr(node, "value", None)
            if include_trusted_objects
            or isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr, ast.AugAssign))
            else None
        )
        if (
            escaped_value is not None
            and expression_escapes_provenance(escaped_value, include_trusted_objects)
        ):
            poison_dynamic_provenance(node)

        if isinstance(node, ast.Call):
            escaped_arguments = tuple(node.args) + tuple(
                keyword.value for keyword in node.keywords
                if keyword.value is not None
            )
            if _python_expression_contains_risky_callable(
                node.func, dynamic_call_aliases
            ) or any(
                expression_escapes_provenance(expression, True)
                for expression in escaped_arguments
            ):
                poison_dynamic_provenance(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if any(
                expression_escapes_provenance(default, True)
                for _argument, default in _python_default_bindings(node.args)
            ):
                poison_dynamic_provenance(node)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _PY_NAMESPACE_MUTATORS
        ):
            namespace_expression = node.func.value
            if (
                isinstance(namespace_expression, ast.Name)
                and namespace_expression.id == "dict"
                and node.args
            ):
                namespace_expression = node.args[0]
            namespace_owner = _python_namespace_owner(
                namespace_expression,
                hou_aliases,
                attrib_type_aliases,
                hou_namespace_aliases,
                attrib_namespace_aliases,
                dynamic_namespace_aliases,
            )
            if namespace_owner == "dynamic":
                poison_dynamic_provenance(node)
            elif namespace_owner in ("hou", "attrib_type"):
                if namespace_owner == "hou":
                    hou_factory_mutations.update(("node", "pwd"))
                    hom_method_mutations.add(True)
                mark_attrib_scope(node)
            elif _python_target_is_trusted_hom_type(
                namespace_expression,
                hou_aliases,
                trusted_type_aliases,
            ):
                hom_method_mutations.add(True)
            else:
                _root, namespace_attributes, _keys = _python_target_parts(
                    namespace_expression
                )
                if (
                    "__dict__" in namespace_attributes
                    or (
                        isinstance(namespace_expression, ast.Call)
                        and _python_call_name(namespace_expression) == "vars"
                    )
                ):
                    hom_method_mutations.add(True)
        mutation = (
            _python_attribute_mutation(node)
            if isinstance(node, ast.Call)
            else None
        )
        if mutation is not None:
            target, attribute = mutation
            root_name, attributes, _keys = _python_target_parts(target)
            if (
                attribute is None
                or _python_target_is_trusted_hom_type(
                    target, hou_aliases, trusted_type_aliases
                )
                or attribute in _PY_TRUSTED_HOM_METHODS
            ):
                hom_method_mutations.add(True)
            hou_factory_mutations.update(
                _python_hou_factory_roots(
                    target, hou_aliases, hou_namespace_aliases
                )
            )
            if attribute in ("node", "pwd"):
                # A same-named attribute mutation may target a ``hou`` alias.
                hou_factory_mutations.add(attribute)
            elif attribute is None and root_name in hou_aliases:
                hou_factory_mutations.update(("node", "pwd"))
            if (
                (
                    root_name in attrib_type_aliases
                    or root_name in hou_aliases and "attribType" in attributes
                )
                and (
                    attribute is None
                    or attribute in _PY_ATTRIB_TYPE_OWNER_MEMBERS
                )
                or root_name in hou_aliases
                and attribute in ("attribType", None)
                or attribute in _PY_ATTRIB_TYPE_OWNER_MEMBERS
            ):
                mark_attrib_scope(node)

    metadata = {
        _PY_PARENTS_KEY: parents,
        _PY_SCOPE_PARENTS_KEY: scope_parents,
        _PY_SCOPE_BOUND_NAMES_KEY: {
            scope: frozenset(names)
            for scope, names in bound_names.items()
        },
        _PY_BINDING_SOURCES_KEY: sources,
        _PY_POISONED_SCOPES_KEY: frozenset(poisoned_scopes),
        _PY_ATTRIB_TYPE_MUTATIONS_KEY: frozenset(attrib_type_mutations),
        _PY_HOU_FACTORY_MUTATIONS_KEY: frozenset(hou_factory_mutations),
        _PY_HOM_METHOD_MUTATIONS_KEY: bool(hom_method_mutations),
    }
    owner_values = {}
    # HOM chains can require several passes (point -> geometry -> node).
    for _round in range(max(1, len(sources) + 1)):
        context = dict(metadata)
        context.update(owner_values)
        next_values = {}
        for (scope, name), name_sources in sources.items():
            if not _python_scope_allows_inference(scope, context):
                continue
            inferred = []
            complete = True
            for source_kind, expression in name_sources:
                if source_kind == "unknown" or expression is None:
                    complete = False
                    break
                owner = _infer_python_owner(
                    expression, context, scope
                )
                if source_kind == "iteration":
                    owner = _sequence_item_owner(owner)
                if owner is None:
                    complete = False
                    break
                inferred.append(owner)
            if complete and inferred and len(set(inferred)) == 1:
                next_values[(scope, name)] = inferred[0]
        if next_values == owner_values:
            break
        owner_values = next_values
    result = dict(metadata)
    result.update(owner_values)
    return result


def _python_context_scope(node, owners):
    """Return the lexical scope attached to a Python AST node."""
    return _python_enclosing_scope(
        node, owners.get(_PY_PARENTS_KEY, {})
    )


def _python_lookup_scopes(scope, owners):
    """Yield runtime lookup scopes, skipping non-closing class bodies."""
    scope_parents = owners.get(_PY_SCOPE_PARENTS_KEY, {})
    current = scope
    while current is not None:
        yield current
        parent = scope_parents.get(current)
        if (
            isinstance(parent, ast.ClassDef)
            and not isinstance(current, ast.ClassDef)
        ):
            parent = scope_parents.get(parent)
        current = parent


def _python_scope_allows_inference(scope, owners):
    """Reject dynamic or class-body namespaces before owner inference."""
    if scope is None or isinstance(scope, ast.ClassDef):
        return False
    poisoned = owners.get(_PY_POISONED_SCOPES_KEY, ())
    return not any(
        candidate in poisoned
        for candidate in _python_lookup_scopes(scope, owners)
    )


def _python_resolved_binding_scope(scope, name, owners):
    """Return the nearest lexical scope that explicitly binds a name."""
    bound = owners.get(_PY_SCOPE_BOUND_NAMES_KEY, {})
    for candidate in _python_lookup_scopes(scope, owners):
        if name in bound.get(candidate, ()):
            return candidate
    return None


def _python_name_is_unshadowed(name, scope, owners):
    """Require an injected module or builtin name to remain untouched."""
    return (
        _python_scope_allows_inference(scope, owners)
        and _python_resolved_binding_scope(scope, name, owners) is None
    )


def _python_target_parts(target):
    """Return a mutation target's root name, attributes, and subscript keys."""
    attributes = []
    keys = []
    current = target
    while isinstance(current, (ast.Attribute, ast.Subscript)):
        if isinstance(current, ast.Attribute):
            attributes.append(current.attr)
            current = current.value
        else:
            keys.append(_python_constant_subscript_key(current))
            current = current.value
    root_name = current.id if isinstance(current, ast.Name) else None
    return root_name, tuple(reversed(attributes)), tuple(keys)


def _python_expression_accesses_object_dict(expression):
    """Detect direct or computed access to an object's namespace mapping."""
    for part in ast.walk(expression):
        if isinstance(part, ast.Attribute) and part.attr == "__dict__":
            return True
        if _python_call_requests_object_dict(part):
            return True
    return False


def _python_target_is_trusted_hom_type(
    expression,
    hou_aliases=("hou",),
    trusted_type_aliases=(),
):
    """Return whether an expression denotes a trusted HOM class object."""
    root_name, attributes, _keys = _python_target_parts(expression)
    if root_name in trusted_type_aliases:
        return True
    return (
        root_name in hou_aliases
        and any(
            attribute in _PY_TRUSTED_HOM_TYPES
            for attribute in attributes
        )
    )


def _python_target_mutates_trusted_hom_type(
    target,
    hou_aliases=("hou",),
    trusted_type_aliases=(),
):
    """Detect a store or delete below a trusted HOM class object."""
    _root_name, attributes, keys = _python_target_parts(target)
    return (
        bool(attributes or keys)
        and _python_target_is_trusted_hom_type(
            target,
            hou_aliases,
            trusted_type_aliases,
        )
    )


def _python_target_mutates_hou_attrib_type(
    target,
    hou_aliases=("hou",),
    attrib_type_aliases=(),
    hou_namespace_aliases=(),
    attrib_namespace_aliases=(),
):
    """Detect stores/deletes anywhere below ``hou.attribType``."""
    root_name, attributes, keys = _python_target_parts(target)
    explicit_owner = any(
        value in _PY_ATTRIB_TYPE_OWNER_MEMBERS
        for value in attributes + keys
        if value is not None
    )
    explicit_container = "attribType" in attributes or "attribType" in keys
    aliased_container = root_name in attrib_type_aliases and bool(
        attributes or keys
    )
    dynamic_alias_write = (
        root_name in attrib_type_aliases and any(key is None for key in keys)
    ) or (
        root_name in hou_aliases
        and any(key is None for key in keys)
    )
    namespace_write = (
        root_name in attrib_namespace_aliases
        or root_name in hou_namespace_aliases
        or (
            root_name in hou_aliases
            and "__dict__" in attributes
        )
    ) and bool(attributes or keys)
    return (
        explicit_owner
        or explicit_container
        or aliased_container
        or dynamic_alias_write
        or namespace_write
    )


def _python_hou_factory_roots(
    expression, hou_aliases=("hou",), hou_namespace_aliases=()
):
    """Return trusted factories possibly changed by a mutation target."""
    root_name, attributes, keys = _python_target_parts(expression)
    factories = {
        value
        for value in attributes + keys
        if value in ("node", "pwd")
    }
    if root_name in hou_aliases and any(key is None for key in keys):
        factories.update(("node", "pwd"))
    if (
        root_name in hou_namespace_aliases
        or (
            root_name in hou_aliases
            and "__dict__" in attributes
        )
    ) and (attributes or keys):
        factories.update(("node", "pwd"))
    return frozenset(factories)


def _python_mutator_call_name(call):
    """Recognize bare or qualified setattr/delattr calls conservatively."""
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def _python_attribute_mutation(call):
    """Return the target and literal name of an attribute mutation call."""
    name = _python_mutator_call_name(call)
    target = None
    attribute_node = None
    if name in ("setattr", "delattr") and len(call.args) > 1:
        target, attribute_node = call.args[0], call.args[1]
    elif name == "__setattr__":
        if len(call.args) >= 3:
            target, attribute_node = call.args[0], call.args[1]
        elif (
            isinstance(call.func, ast.Attribute)
            and len(call.args) >= 2
        ):
            target, attribute_node = call.func.value, call.args[0]
    elif name == "__delattr__":
        if len(call.args) >= 2:
            target, attribute_node = call.args[0], call.args[1]
        elif isinstance(call.func, ast.Attribute) and call.args:
            target, attribute_node = call.func.value, call.args[0]
    if target is None:
        return None
    attribute = (
        attribute_node.value
        if isinstance(attribute_node, ast.Constant)
        and isinstance(attribute_node.value, str)
        else None
    )
    return target, attribute


def _python_namespace_owner(
    expression,
    hou_aliases,
    attrib_type_aliases,
    hou_namespace_aliases,
    attrib_namespace_aliases,
    dynamic_namespace_aliases,
):
    """Classify a mapping that can replace trusted Python bindings."""
    if isinstance(expression, ast.Name):
        if expression.id in hou_namespace_aliases:
            return "hou"
        if expression.id in attrib_namespace_aliases:
            return "attrib_type"
        if expression.id in dynamic_namespace_aliases:
            return "dynamic"

    if isinstance(expression, ast.Call):
        if _python_call_requests_object_dict(expression):
            return "dynamic"
        call_name = _python_call_name(expression)
        if call_name in ("globals", "locals"):
            return "dynamic"
        if call_name == "vars" and expression.args:
            root_name, attributes, _keys = _python_target_parts(
                expression.args[0]
            )
            if (
                root_name in attrib_type_aliases
                or (
                    root_name in hou_aliases
                    and "attribType" in attributes
                )
            ):
                return "attrib_type"
            if root_name in hou_aliases:
                return "hou"

    root_name, attributes, _keys = _python_target_parts(expression)
    if "__dict__" in attributes:
        if (
            root_name in attrib_type_aliases
            or (
                root_name in hou_aliases
                and "attribType" in attributes
            )
        ):
            return "attrib_type"
        if root_name in hou_aliases:
            return "hou"

    for child in ast.walk(expression):
        if (
            isinstance(child, ast.Call)
            and _python_call_name(child) in ("globals", "locals")
        ):
            return "dynamic"
    return None


def _python_expression_exposes_namespace(
    expression,
    hou_aliases,
    attrib_type_aliases,
    trusted_type_aliases,
    hou_namespace_aliases,
    attrib_namespace_aliases,
    dynamic_namespace_aliases,
    include_trusted_objects=False,
):
    """Detect a trusted or unknown namespace passed to another callable."""
    if (
        include_trusted_objects
        and _python_expression_is_trusted_escape_value(
            expression,
            hou_aliases,
            attrib_type_aliases,
            trusted_type_aliases,
        )
    ):
        return True
    for part in ast.walk(expression):
        owner = _python_namespace_owner(
            part,
            hou_aliases,
            attrib_type_aliases,
            hou_namespace_aliases,
            attrib_namespace_aliases,
            dynamic_namespace_aliases,
        )
        if owner is not None:
            return True
        _root_name, attributes, _keys = _python_target_parts(part)
        if "__dict__" in attributes:
            return True
    return False


def _python_expression_is_trusted_escape_value(
    expression,
    hou_aliases,
    attrib_type_aliases,
    trusted_type_aliases,
):
    """Recognize values that expose a mutable trusted object to a call."""
    if isinstance(expression, ast.Name):
        return expression.id in (
            set(hou_aliases)
            | set(attrib_type_aliases)
            | set(trusted_type_aliases)
        )
    if isinstance(expression, ast.Constant) and isinstance(
        expression.value, str
    ):
        return expression.value == "hou" or expression.value.startswith(
            "hou."
        )
    root_name, attributes, keys = _python_target_parts(expression)
    is_attrib_type_member = (
        root_name in hou_aliases
        and bool(attributes)
        and attributes[0] == "attribType"
    )
    if (
        not is_attrib_type_member
        and _python_expression_may_be_trusted_hom_type(
            expression,
            hou_aliases,
            trusted_type_aliases,
        )
    ):
        return True
    if root_name in hou_aliases and attributes == ("attribType",):
        return True
    if isinstance(expression, ast.Subscript) and any(
        key == "hou"
        or (isinstance(key, str) and key.startswith("hou."))
        for key in keys
    ):
        return True
    if isinstance(expression, (ast.Tuple, ast.List, ast.Set)):
        return any(
            _python_expression_is_trusted_escape_value(
                element,
                hou_aliases,
                attrib_type_aliases,
                trusted_type_aliases,
            )
            for element in expression.elts
        )
    if isinstance(expression, ast.Dict):
        return any(
            value is not None
            and _python_expression_is_trusted_escape_value(
                value,
                hou_aliases,
                attrib_type_aliases,
                trusted_type_aliases,
            )
            for value in tuple(expression.keys) + tuple(expression.values)
        )
    if isinstance(expression, ast.Starred):
        return _python_expression_is_trusted_escape_value(
            expression.value,
            hou_aliases,
            attrib_type_aliases,
            trusted_type_aliases,
        )
    return False


def _python_constant_subscript_key(expression):
    """Return one literal string subscript used by a mutation target."""
    index = getattr(expression, "slice", None)
    if hasattr(ast, "Index") and isinstance(index, ast.Index):
        index = index.value
    if isinstance(index, ast.Constant) and isinstance(index.value, str):
        return index.value
    return None


def _assignment_target_names(target):
    """Return a sole assignable name; reject ambiguous destructuring."""
    if isinstance(target, ast.Name):
        return (target.id,)
    # Destructuring cannot establish which returned value has which HOM type.
    return ()


def _all_assignment_target_names(target):
    """Return every name bound by a possibly destructuring target."""
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(
            name
            for element in target.elts
            for name in _all_assignment_target_names(element)
        )
    if isinstance(target, ast.Starred):
        return _all_assignment_target_names(target.value)
    return ()


def _infer_python_owner(expression, owners, scope=None):
    """Infer a HOM node/geometry-element type from a conservative AST chain."""
    if expression is None:
        return None
    if owners.get(_PY_HOM_METHOD_MUTATIONS_KEY, False):
        return None
    scope = scope or _python_context_scope(expression, owners)
    if not _python_scope_allows_inference(scope, owners):
        return None
    if isinstance(expression, ast.Name):
        return owners.get((scope, expression.id))

    if isinstance(expression, ast.Subscript):
        index = expression.slice
        if not (
            isinstance(index, ast.Constant)
            and isinstance(index.value, int)
            and not isinstance(index.value, bool)
        ):
            return None
        return _sequence_item_owner(
            _infer_python_owner(expression.value, owners, scope)
        )

    if isinstance(expression, (ast.List, ast.Tuple)):
        element_owners = [
            _infer_python_owner(element, owners, scope)
            for element in expression.elts
        ]
        if (
            element_owners
            and None not in element_owners
            and len(set(element_owners)) == 1
        ):
            owner = element_owners[0]
            return owner + _PY_SEQUENCE_SUFFIX
        return None

    if not isinstance(expression, ast.Call):
        return None

    if isinstance(expression.func, ast.Name):
        if (
            expression.func.id == "iter"
            and len(expression.args) == 1
            and _python_name_is_unshadowed("iter", scope, owners)
        ):
            return _infer_python_owner(
                expression.args[0], owners, scope
            )
        if (
            expression.func.id == "next"
            and len(expression.args) == 1
            and _python_name_is_unshadowed("next", scope, owners)
        ):
            return _sequence_item_owner(
                _infer_python_owner(
                    expression.args[0], owners, scope
                )
            )
        return None

    if not isinstance(expression.func, ast.Attribute):
        return None

    method = expression.func.attr
    receiver = expression.func.value
    if (
        isinstance(receiver, ast.Name)
        and receiver.id == "hou"
        and _python_name_is_unshadowed("hou", scope, owners)
        and method in ("pwd", "node")
        and method not in owners.get(_PY_HOU_FACTORY_MUTATIONS_KEY, ())
    ):
        return _PY_NODE_OWNER

    receiver_owner = _infer_python_owner(receiver, owners, scope)
    if method == "geometry" and receiver_owner == _PY_NODE_OWNER:
        return "detail"

    if receiver_owner == "detail":
        if method in ("point", "createPoint"):
            return "point"
        if method in ("points", "iterPoints", "globPoints"):
            return "point" + _PY_SEQUENCE_SUFFIX
        if method in ("prim", "primAt", "createPolygon", "createNURBSCurve"):
            return "primitive"
        if method in ("prims", "iterPrims", "globPrims"):
            return "primitive" + _PY_SEQUENCE_SUFFIX
        if method in ("vertices", "iterVertices"):
            return "vertex" + _PY_SEQUENCE_SUFFIX

    if receiver_owner in ("point", "primitive"):
        if method in ("vertices", "iterVertices"):
            return "vertex" + _PY_SEQUENCE_SUFFIX
        if method in ("points", "iterPoints"):
            return "point" + _PY_SEQUENCE_SUFFIX

    if receiver_owner == "vertex":
        if method == "point":
            return "point"
        if method == "prim":
            return "primitive"

    return None


def _sequence_item_owner(owner):
    """Convert an inferred sequence owner into its element owner."""
    if owner and owner.endswith(_PY_SEQUENCE_SUFFIX):
        return owner[: -len(_PY_SEQUENCE_SUFFIX)]
    return None


def _python_node_span(source, node):
    """Return character offsets for an AST node with UTF-8 byte columns."""
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return None
    lines = source.splitlines(True) or [""]
    line_offsets = []
    total = 0
    for line in lines:
        line_offsets.append(total)
        total += len(line)
    try:
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1
        # CPython reports AST columns as UTF-8 byte offsets, while slicing a
        # Python string requires character indexes.
        start = line_offsets[start_line] + _utf8_column_to_character_index(
            lines[start_line], node.col_offset
        )
        end = line_offsets[end_line] + _utf8_column_to_character_index(
            lines[end_line], node.end_col_offset
        )
    except (IndexError, TypeError, ValueError):
        return None
    if start < 0 or end < start or end > len(source):
        return None
    return start, end


def _utf8_column_to_character_index(line, byte_column):
    """Translate AST UTF-8 byte offsets into Python string indexes."""
    if byte_column <= 0:
        return 0
    encoded = line.encode("utf-8")
    byte_column = min(int(byte_column), len(encoded))
    while byte_column > 0:
        try:
            return len(encoded[:byte_column].decode("utf-8"))
        except UnicodeDecodeError:
            byte_column -= 1
    return 0


def _quoted_like(source, new):
    """Preserve a Python literal's prefix and quote style when possible."""
    match = re.match(
        r"^(?P<prefix>[rRuUbB]*)(?P<quote>'''|\"\"\"|'|\")"
        r"(?P<body>.*)(?P=quote)$",
        source,
        re.S,
    )
    if not match:
        return repr(new)
    prefix = match.group("prefix")
    quote = match.group("quote")
    escaped = new.replace("\\", "\\\\").replace(quote, "\\" + quote)
    return prefix + quote + escaped + quote


def _python_call_name(call):
    """Return a call name without evaluating its receiver."""
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _python_add_attrib_class(call, owners, scope=None):
    """Read an explicit, unshadowed ``hou.attribType`` addAttrib owner."""
    if not call.args:
        return None
    owner = call.args[0]
    if not isinstance(owner, ast.Attribute):
        return None
    container = owner.value
    valid_container = (
        isinstance(container, ast.Attribute)
        and isinstance(container.value, ast.Name)
        and container.value.id == "hou"
        and container.attr == "attribType"
        and _python_name_is_unshadowed("hou", scope, owners)
        and not owners.get(_PY_ATTRIB_TYPE_MUTATIONS_KEY, ())
    )
    if not valid_container:
        return None
    return {
        "Point": "point",
        "Prim": "primitive",
        "Vertex": "vertex",
        "Global": "detail",
    }.get(owner.attr)


# ---------------------------------------------------------------------------
# VEX lexing, allowlisted calls, bindings, and raw strings
# ---------------------------------------------------------------------------


class _VexAnalysis:
    """Lexed VEX source plus memoized structural analysis."""

    __slots__ = (
        "text",
        "code_mask",
        "strings",
        "executable",
        "logical_source",
        "preprocessed",
        "macro_records",
        "macros",
        "cache",
    )

    def __init__(self, text):
        self.text = text
        self.code_mask, self.strings = _lex_vex(text)
        self.executable = "".join(
            character
            if self.code_mask[index] or character in "\r\n"
            else " "
            for index, character in enumerate(text)
        )
        self.logical_source = re.sub(
            r"\\[ \t]*(?:\r\n|\r|\n)", " ", self.executable
        )
        self.preprocessed = re.sub(
            r"\\[ \t]*(?:\r\n|\r|\n)", "", self.executable
        )
        pattern = re.compile(
            r"^[ \t]*#[ \t]*define[ \t]+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"(?:\(([^\r\n]*?)\))?"
            r"(?:[ \t]+([^\r\n]*))?",
            re.M,
        )
        records = []
        self.macros = {}
        for match in pattern.finditer(self.logical_source):
            name, parameter_source, body = match.groups()
            body = body or ""
            parameters = tuple(
                item.strip()
                for item in (parameter_source or "").split(",")
                if item.strip()
            )
            record = {
                "name": name,
                "parameter_source": parameter_source,
                "parameters": parameters,
                "generic_formals": tuple(
                    index
                    for index, parameter in enumerate(parameters)
                    if IDENT.match(parameter)
                    and re.search(
                        r"##\s*{0}\b|\b{0}\s*##|(?<!#)#(?!#)\s*{0}\b".format(
                            re.escape(parameter)
                        ),
                        body,
                    )
                ),
                "function_like": parameter_source is not None,
                "body": body,
            }
            records.append(record)
            self.macros[name] = record
        self.macro_records = tuple(records)
        self.cache = {}

    def store(self, key, value):
        self.cache[key] = value
        return value


def _vex_rewrite(node, parm, text, kind, item_class, old, new, aggressive):
    """Rewrite allowlisted VEX calls, bindings, and unambiguous locals."""
    table = _vex_table(kind, item_class)
    analysis = _VexAnalysis(text)
    code_mask, strings = analysis.code_mask, analysis.strings
    replacements = []
    skipped = []
    reasons = []
    blocked_aggressive_spans = []
    calls, rejected_calls = _vex_calls(analysis, table)
    reported_rejected_spans = []

    for function, (start, end), rejection, call_span in rejected_calls:
        dependency_spans = _vex_argument_source_spans(analysis, start, end)
        blocked_aggressive_spans.append(call_span)
        blocked_aggressive_spans.extend(dependency_spans)
        if (
            _vex_argument_mentions_old(analysis, start, end, old)
            or _vex_spans_contain_exact_string(
                strings, dependency_spans, old
            )
        ):
            skipped.append(
                "VEX {0} {1}".format(function, rejection)
            )
            reported_rejected_spans.append(call_span)

    for macro_name, argument_spans, call_span in _vex_defined_macro_calls(
        analysis
    ):
        blocked_aggressive_spans.append(call_span)
        if (
            _vex_spans_contain_exact_string(
                strings, argument_spans, old
            )
            and not any(
                call_span[0] < reported_end
                and call_span[1] > reported_start
                for reported_start, reported_end
                in reported_rejected_spans
            )
        ):
            skipped.append(
                "VEX macro call '{0}' contains an untrusted exact "
                "string".format(macro_name)
            )

    alias_calls = {}
    for function, (start, end), _call_span in calls:
        value, quote, literal_start, literal_end = _literal(text, start, end)
        if value == old:
            replacements.append(
                (literal_start, literal_end, quote + new + quote)
            )
            reasons.append("VEX {0} literal".format(function))
            continue

        argument = text[start:end].strip()
        chs_match = re.match(
            r"^chs\s*\(\s*(['\"])([^'\"]+)\1\s*\)$", argument
        )
        if chs_match:
            blocked_aggressive_spans.append((start, end))
            problem = _referenced_parm_problem(
                node,
                parm,
                chs_match.group(2),
                "VEX {0} chs()".format(function),
            )
            skipped.append(problem)
        else:
            alias, alias_span = _vex_argument_identifier(analysis, start, end)
            if alias:
                alias_calls.setdefault(alias, []).append(
                    (function, (start, end), alias_span)
                )
            elif old in text:
                blocked_aggressive_spans.append((start, end))
                blocked_aggressive_spans.extend(
                    _vex_argument_source_spans(analysis, start, end)
                )
                skipped.append(
                    "VEX {0} uses a dynamic name".format(function)
                )

    for alias, uses in alias_calls.items():
        blocked_aggressive_spans.extend(
            _vex_name_dependency_spans(analysis, (alias,))
        )
        assignments = _vex_assignments(analysis, alias)
        assignment = assignments[0] if assignments else None
        function_names = sorted(
            set(function for function, _span, _alias_span in uses)
        )
        function_label = "/".join(function_names)
        if (
            assignment
            and assignment["kind"] == "literal"
            and assignment["value"] == old
        ):
            authorized_spans = tuple(
                alias_span
                for _function, _span, alias_span in uses
            )
            if _vex_alias_uses_are_authorized(
                analysis,
                alias,
                assignment,
                authorized_spans,
            ):
                replacements.append(
                    (
                        assignment["start"],
                        assignment["end"],
                        assignment["quote"]
                        + new
                        + assignment["quote"],
                    )
                )
                reasons.append(
                    "VEX {0} local string".format(function_label)
                )
            else:
                skipped.append(
                    "VEX {0} local name '{1}' is shadowed or used outside "
                    "selected-owner calls".format(function_label, alias)
                )
        elif assignment and assignment["kind"] == "chs":
            problem = _referenced_parm_problem(
                node,
                parm,
                assignment["parm_name"],
                "VEX {0} local chs()".format(function_label),
            )
            skipped.append(problem)
        elif not assignment:
            skipped.append(
                "VEX {0} local name has ambiguous assignments".format(
                    function_label
                )
            )

    # Accept numeric tuple/matrix prefixes (2@, 3@, 4@) here and in
    # _looks_like_vex so classification and rewrite eligibility stay aligned.
    binding = r"(?<![A-Za-z0-9_])([A-Za-z0-9]?)@" + (
        "group_" if kind == RENAME_KIND_GROUP else ""
    ) + re.escape(old) + r"(?![A-Za-z0-9_])"
    binding_class = _vex_binding_class(node)
    ambiguous_binding = False
    for match in re.finditer(binding, text):
        if _span_is_code(code_mask, match.start(), match.end()):
            binding_matches = binding_class == item_class or (
                kind == RENAME_KIND_GROUP
                and item_class == ANY_GROUP_CLASS
                and binding_class in ("point", "primitive")
            )
            if binding_matches:
                prefix = match.group(1) + "@"
                if kind == RENAME_KIND_GROUP:
                    prefix += "group_"
                replacements.append((match.start(), match.end(), prefix + new))
                reasons.append("VEX @ binding")
            elif binding_class is None:
                ambiguous_binding = True
    if ambiguous_binding:
        skipped.append("VEX @ binding has an ambiguous run-over class")

    if aggressive:
        occupied = [(start, end) for start, end, _value in replacements]
        for start, end, replacement in _exact_vex_string_replacements(
            strings, old, new
        ):
            if not any(
                start < occupied_end and end > occupied_start
                for occupied_start, occupied_end in (
                    occupied + blocked_aggressive_spans
                )
            ):
                replacements.append((start, end, replacement))
                reasons.append("aggressive VEX exact string")

    return _replace(text, replacements), reasons, skipped


def _vex_table(kind, item_class):
    table = ATTR_VEX if kind == RENAME_KIND_ATTRIBUTE else GROUP_VEX
    if kind == RENAME_KIND_GROUP and item_class == ANY_GROUP_CLASS:
        return tuple(entry for entries in table.values() for entry in entries)
    return table[item_class]


def _vex_calls(analysis, table):
    """Return only unqualified, builtin-resolving allowlisted VEX calls."""
    if not table:
        return [], []
    key = ("calls", tuple(table))
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    names = "|".join(re.escape(name) for name, _index in table)
    indexes = dict(table)
    blocked = dict(_vex_blocked_call_names(analysis, tuple(indexes)))
    if _vex_has_external_source_directive(analysis):
        for function in indexes:
            blocked[function] = (
                "authorization is ambiguous after an external include/import"
            )
    calls = []
    rejected = []
    executable = analysis.executable
    for match in re.finditer(r"\b(" + names + r")\s*\(", executable):
        name_end = match.start(1) + len(match.group(1))
        open_paren = match.end() - 1
        if (
            not _span_is_code(code_mask, match.start(1), name_end)
            or not code_mask[open_paren]
        ):
            continue
        close = _close_paren(text, open_paren, code_mask)
        if close < 0:
            continue
        arguments = _arguments(
            text, open_paren + 1, close, code_mask
        )
        function = match.group(1)
        index = indexes.get(function)
        if index is None or len(arguments) <= index:
            continue
        call_span = (match.start(), close + 1)
        candidate = (function, arguments[index], call_span)
        if _vex_call_is_qualified(text, match.start(), code_mask):
            rejected.append(
                (
                    function,
                    arguments[index],
                    "call is qualified, namespaced, or preprocessor-composed",
                    call_span,
                )
            )
        elif function in blocked:
            rejected.append(
                (
                    function,
                    arguments[index],
                    blocked[function],
                    call_span,
                )
            )
        else:
            calls.append(candidate)
    rejected.extend(_vex_preprocessor_composed_calls(analysis, indexes))
    return analysis.store(key, (calls, rejected))


def _vex_macro_invocations(analysis, name, all_definitions=True):
    """Return executable calls to one macro, excluding its definitions."""
    key = ("macro_invocations", name, all_definitions)
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    if all_definitions:
        spans_key = ("all_macro_definition_spans",)
        definition_spans = analysis.cache.get(spans_key)
        if definition_spans is None:
            definition_spans = tuple(
                span
                for macro_name in analysis.macros
                for span in _vex_macro_definition_spans(analysis, macro_name)
            )
            analysis.store(spans_key, definition_spans)
    else:
        definition_spans = _vex_macro_definition_spans(analysis, name)
    calls = []
    pattern = re.compile(WORD.format(re.escape(name)) + r"\s*\(")
    for match in pattern.finditer(analysis.executable):
        open_paren = match.end() - 1
        if (
            not _span_is_code(
                code_mask, match.start(), match.start() + len(name)
            )
            or not code_mask[open_paren]
            or any(start <= match.start() < end for start, end in definition_spans)
        ):
            continue
        close = _close_paren(text, open_paren, code_mask)
        if close >= 0:
            calls.append(
                (
                    match.start(),
                    tuple(_arguments(text, open_paren + 1, close, code_mask)),
                    close,
                )
            )
    return analysis.store(key, calls)


def _vex_defined_macro_calls(analysis):
    """Return invocation/result-call spans for every defined macro."""
    key = ("defined_macro_calls",)
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    definitions = {
        name: record["function_like"]
        for name, record in analysis.macros.items()
    }
    calls = []
    for macro_name, function_like in definitions.items():
        for call_start, arguments, close_paren in _vex_macro_invocations(
            analysis, macro_name
        ):
            argument_spans = list(arguments)
            call_end = close_paren + 1
            if function_like:
                result_open = _next_vex_code_index(
                    text, call_end, code_mask
                )
                if result_open >= 0 and text[result_open] == "(":
                    result_close = _close_paren(
                        text, result_open, code_mask
                    )
                    if result_close >= 0:
                        argument_spans.extend(
                            _arguments(
                                text,
                                result_open + 1,
                                result_close,
                                code_mask,
                            )
                        )
                        call_end = result_close + 1
            calls.append(
                (
                    macro_name,
                    tuple(argument_spans),
                    (call_start, call_end),
                )
            )
    return analysis.store(key, calls)


def _vex_preprocessor_composed_calls(analysis, indexes):
    """Reject calls whose allowlisted name is assembled by a macro."""
    key = ("preprocessor_composed_calls", tuple(sorted(indexes.items())))
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    targets = _vex_composed_macro_targets(analysis, indexes)
    if not targets:
        return analysis.store(key, [])

    rejected = []
    for macro_name, macro_record in targets.items():
        target_records = macro_record["targets"]
        function_like = macro_record["function_like"]
        for call_start, macro_arguments, macro_close in _vex_macro_invocations(
            analysis, macro_name, all_definitions=False
        ):
            invocation_records = list(target_records)
            static_functions = {
                record["function"] for record in invocation_records
            }
            for formal_index in macro_record["generic_formals"]:
                if len(macro_arguments) <= formal_index:
                    continue
                argument_start, argument_end = macro_arguments[
                    formal_index
                ]
                argument_source = text[
                    argument_start:argument_end
                ].strip()
                if (
                    argument_source in indexes
                    and argument_source not in static_functions
                ):
                    invocation_records.append(
                        {
                            "function": argument_source,
                            "formal_indexes": None,
                            "fallback_all_arguments": True,
                        }
                    )
            result_call = None
            for record in invocation_records:
                function = record["function"]
                formal_indexes = record["formal_indexes"]
                if formal_indexes is not None:
                    selected_arguments = tuple(
                        macro_arguments[index]
                        for index in formal_indexes
                        if len(macro_arguments) > index
                    )
                    call_span = (call_start, macro_close + 1)
                else:
                    if not function_like:
                        result_call = (
                            macro_arguments,
                            macro_close,
                        )
                    elif result_call is None:
                        call_open = _next_vex_code_index(
                            text, macro_close + 1, code_mask
                        )
                        if call_open < 0 or text[call_open] != "(":
                            result_call = ()
                        else:
                            call_close = _close_paren(
                                text, call_open, code_mask
                            )
                            if call_close < 0:
                                result_call = ()
                            else:
                                result_call = (
                                    _arguments(
                                        text,
                                        call_open + 1,
                                        call_close,
                                        code_mask,
                                    ),
                                    call_close,
                                )
                    if not result_call:
                        if record.get("fallback_all_arguments"):
                            selected_arguments = tuple(macro_arguments)
                            call_span = (call_start, macro_close + 1)
                        else:
                            continue
                    else:
                        result_arguments, call_close = result_call
                        index = indexes[function]
                        selected_arguments = (
                            (result_arguments[index],)
                            if len(result_arguments) > index
                            else ()
                        )
                        call_span = (call_start, call_close + 1)
                if not selected_arguments:
                    continue
                rejected.extend(
                    (
                        function,
                        selected_argument,
                        (
                            "call is preprocessor-composed by macro "
                            "'{0}'".format(macro_name)
                        ),
                        call_span,
                    )
                    for selected_argument in selected_arguments
                )
    return analysis.store(key, rejected)


def _vex_composed_macro_targets(analysis, indexes):
    """Resolve direct and wrapper macros that compose allowlisted names."""
    key = ("composed_macro_targets", tuple(sorted(indexes.items())))
    if key in analysis.cache:
        return analysis.cache[key]
    definitions = analysis.macros
    result = {macro_name: {} for macro_name in definitions}

    def mapped_formals(definition, selected_spans):
        return tuple(
            index
            for index, parameter in enumerate(
                definition["parameters"]
            )
            if re.match(
                r"^[A-Za-z_][A-Za-z0-9_]*$",
                parameter,
            )
            and any(
                re.search(
                    WORD.format(re.escape(parameter)),
                    definition["body"][start:end],
                )
                for start, end in selected_spans
            )
        )

    def add_target(macro_name, function, formal_indexes):
        key = (function, formal_indexes)
        if key in result[macro_name]:
            return False
        result[macro_name][key] = {
            "function": function,
            "formal_indexes": formal_indexes,
        }
        return True

    for macro_name, definition in definitions.items():
        body = definition["body"]
        for function in indexes:
            function_name = re.escape(function)
            composition = re.search(
                r"##\s*"
                + function_name
                + r"\b|\b"
                + function_name
                + r"\s*##|(?<!#)#(?!#)\s*"
                + function_name
                + r"\b",
                body,
            )
            if not composition:
                continue

            function_match = re.search(
                WORD.format(function_name),
                body[composition.start() : composition.end()],
            )
            function_end = (
                composition.start() + function_match.end()
                if function_match
                else composition.end()
            )
            call_open = function_end
            while call_open < len(body) and body[call_open].isspace():
                call_open += 1
            formal_indexes = None
            if call_open < len(body) and body[call_open] == "(":
                body_mask = [True] * len(body)
                call_close = _close_paren(
                    body, call_open, body_mask
                )
                if call_close >= 0:
                    body_arguments = _arguments(
                        body,
                        call_open + 1,
                        call_close,
                        body_mask,
                    )
                    selected_index = indexes[function]
                    formal_indexes = ()
                    if len(body_arguments) > selected_index:
                        formal_indexes = mapped_formals(
                            definition,
                            (body_arguments[selected_index],),
                        )
            add_target(macro_name, function, formal_indexes)

    # A wrapper macro may call a composing macro and either invoke the
    # resulting function itself or pass that function through to its caller.
    for _round in range(max(1, len(definitions))):
        changed = False
        snapshot = {
            name: tuple(records.values())
            for name, records in result.items()
            if records
        }
        for macro_name, definition in definitions.items():
            body = definition["body"]
            body_mask = [True] * len(body)
            for child_name, child_definition in definitions.items():
                if child_name == macro_name:
                    continue
                child_targets = list(snapshot.get(child_name, ()))
                if (
                    not child_targets
                    and not child_definition["generic_formals"]
                ):
                    continue
                if child_definition["function_like"]:
                    pattern = re.compile(
                        WORD.format(re.escape(child_name)) + r"\s*\("
                    )
                else:
                    pattern = re.compile(
                        WORD.format(re.escape(child_name))
                    )
                for child_match in pattern.finditer(body):
                    if child_definition["function_like"]:
                        child_open = child_match.end() - 1
                        child_close = _close_paren(
                            body, child_open, body_mask
                        )
                        if child_close < 0:
                            continue
                        child_arguments = _arguments(
                            body,
                            child_open + 1,
                            child_close,
                            body_mask,
                        )
                    else:
                        child_close = child_match.end()
                        child_arguments = ()

                    invocation_targets = list(child_targets)
                    for formal_index in child_definition[
                        "generic_formals"
                    ]:
                        if len(child_arguments) <= formal_index:
                            continue
                        argument_start, argument_end = child_arguments[
                            formal_index
                        ]
                        argument_source = body[
                            argument_start:argument_end
                        ].strip()
                        if argument_source in indexes:
                            invocation_targets.append(
                                {
                                    "function": argument_source,
                                    "formal_indexes": None,
                                    "generic": True,
                                }
                            )

                    for child_target in invocation_targets:
                        function = child_target["function"]
                        child_formals = child_target[
                            "formal_indexes"
                        ]
                        if child_formals is not None:
                            selected_spans = tuple(
                                child_arguments[index]
                                for index in child_formals
                                if len(child_arguments) > index
                            )
                            wrapper_formals = mapped_formals(
                                definition,
                                selected_spans,
                            )
                        else:
                            after_child = (
                                child_close + 1
                                if child_definition["function_like"]
                                else child_close
                            )
                            result_open = _next_vex_code_index(
                                body,
                                after_child,
                                body_mask,
                            )
                            if (
                                result_open >= 0
                                and body[result_open] == "("
                            ):
                                result_close = _close_paren(
                                    body,
                                    result_open,
                                    body_mask,
                                )
                                if result_close < 0:
                                    continue
                                result_arguments = _arguments(
                                    body,
                                    result_open + 1,
                                    result_close,
                                    body_mask,
                                )
                                selected_index = indexes[function]
                                selected_spans = (
                                    (result_arguments[selected_index],)
                                    if len(result_arguments)
                                    > selected_index
                                    else ()
                                )
                                wrapper_formals = mapped_formals(
                                    definition,
                                    selected_spans,
                                )
                            else:
                                wrapper_formals = None
                        changed = add_target(
                            macro_name,
                            function,
                            wrapper_formals,
                        ) or changed
                        if (
                            child_target.get("generic")
                            and wrapper_formals is None
                        ):
                            fallback_formals = mapped_formals(
                                definition,
                                child_arguments,
                            )
                            if fallback_formals:
                                changed = add_target(
                                    macro_name,
                                    function,
                                    fallback_formals,
                                ) or changed
        if not changed:
            break

    result = {
        macro_name: {
            "function_like": definitions[macro_name][
                "function_like"
            ],
            "generic_formals": definitions[macro_name][
                "generic_formals"
            ],
            "targets": tuple(records.values()),
        }
        for macro_name, records in result.items()
        if records or definitions[macro_name]["generic_formals"]
    }
    return analysis.store(key, result)


def _vex_macro_generated_overloads(analysis, names):
    """Find allowlisted function declarations produced through macros."""
    key = ("macro_generated_overloads", tuple(names))
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    definitions = {}
    blocked = {}
    for record in analysis.macro_records:
        macro_name = record["name"]
        parameters, body = record["parameters"], record["body"]
        declared_formals = set()
        for function in names:
            declaration = (
                r"\b(?:function\s+)?"
                r"[A-Za-z_][A-Za-z0-9_]*(?:\s*\[\s*\])?"
                r"\s+"
                + re.escape(function)
                + r"\s*\([^)]*\)\s*\{"
            )
            if re.search(declaration, body):
                blocked[function] = (
                    "name is declared or overloaded by macro "
                    "'{0}'".format(macro_name)
                )
        for index, parameter in enumerate(parameters):
            if not re.match(
                r"^[A-Za-z_][A-Za-z0-9_]*$",
                parameter,
            ):
                continue
            declaration = (
                r"\b(?:function\s+)?"
                r"[A-Za-z_][A-Za-z0-9_]*(?:\s*\[\s*\])?"
                r"\s+"
                + re.escape(parameter)
                + r"\s*\([^)]*\)\s*\{"
            )
            if re.search(declaration, body):
                declared_formals.add(index)
        object_target = None
        if not record["function_like"]:
            candidate = body.strip()
            if candidate in names:
                object_target = candidate
        definitions[macro_name] = {
            "function_like": record["function_like"],
            "declared_formals": frozenset(declared_formals),
            "object_target": object_target,
        }

    for macro_name, definition in definitions.items():
        for call_start, arguments, close_paren in _vex_macro_invocations(
            analysis, macro_name
        ):
            object_target = definition["object_target"]
            if (
                object_target
                and _vex_has_typed_declaration_prefix(analysis, call_start)
                and _next_vex_code_character(
                    text, close_paren + 1, code_mask
                )
                == "{"
            ):
                blocked[object_target] = (
                    "name is declared or overloaded by macro "
                    "'{0}'".format(macro_name)
                )

            declaration_name_context = (
                definition["function_like"]
                and _vex_has_typed_declaration_prefix(analysis, call_start)
                and _next_vex_code_character(
                    text, close_paren + 1, code_mask
                )
                == "("
            )
            relevant_indexes = set(definition["declared_formals"])
            if declaration_name_context:
                relevant_indexes.update(range(len(arguments)))
            for index in relevant_indexes:
                if len(arguments) <= index:
                    continue
                start, end = arguments[index]
                function = text[start:end].strip()
                if function in names:
                    blocked[function] = (
                        "name is declared or overloaded by macro "
                        "'{0}'".format(macro_name)
                    )
    return analysis.store(key, blocked)


def _vex_macro_exposed_call_names(analysis, names):
    """Block builtin proof when macro expansion can expose a call name."""
    key = ("macro_exposed_call_names", tuple(names))
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    blocked = {}
    unresolved_declaration = False
    for record in analysis.macro_records:
        macro_name, body = record["name"], record["body"]
        for function in names:
            if re.search(WORD.format(re.escape(function)), body):
                blocked[function] = (
                    "name is exposed to macro expansion by '{0}'".format(
                        macro_name
                    )
                )
        # A macro-supplied ``function`` prefix can place an otherwise
        # ordinary token in declaration position after expansion.  Without
        # preprocessing the source, the declaration target is unknowable.
        if re.search(r"\bfunction\b", body):
            unresolved_declaration = True

    for macro_name, argument_spans, _call_span in _vex_defined_macro_calls(
        analysis
    ):
        for function in names:
            pattern = re.compile(WORD.format(re.escape(function)))
            if any(
                any(
                    _span_is_code(code_mask, token.start(), token.end())
                    for token in pattern.finditer(text, start, end)
                )
                for start, end in argument_spans
            ):
                blocked[function] = (
                    "name is exposed to macro invocation '{0}'".format(
                        macro_name
                    )
                )

    if unresolved_declaration:
        for function in names:
            blocked.setdefault(
                function,
                "authorization is ambiguous after macro-expanded "
                "declaration syntax",
            )
    return analysis.store(key, blocked)


def _vex_has_typed_declaration_prefix(analysis, start):
    """Recognize a return-type prefix immediately before a function name."""
    text, code_mask = analysis.text, analysis.code_mask
    declaration_start = _previous_vex_boundary(
        text, start, code_mask
    )
    declaration_prefix = analysis.executable[declaration_start:start]
    declaration_prefix = re.sub(
        r"\\[ \t]*(?:\r\n|\r|\n)",
        "",
        declaration_prefix,
    )
    declaration_prefix = re.sub(
        r"^[ \t]*#[^\r\n]*(?:\r\n|\r|\n|$)",
        "",
        declaration_prefix,
        flags=re.M,
    ).strip()
    return bool(
        re.match(
            r"^(?:function\s+)?"
            r"[A-Za-z_][A-Za-z0-9_]*(?:\s*\[\s*\])?"
            r"(?:\s+[A-Za-z_][A-Za-z0-9_]*(?:\s*\[\s*\])?)*$",
            declaration_prefix,
        )
    )


def _vex_blocked_call_names(analysis, names):
    """Find allowlisted names replaced by a macro or local VEX overload."""
    if not names:
        return {}
    key = ("blocked_call_names", tuple(names))
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    alternatives = "|".join(re.escape(name) for name in names)
    blocked = {}
    executable = analysis.executable
    preprocessed = analysis.preprocessed
    macro_pattern = re.compile(
        r"^[ \t]*#[ \t]*define[ \t]+("
        + alternatives
        + r")\b",
        re.M,
    )
    for match in macro_pattern.finditer(preprocessed):
        blocked[match.group(1)] = "name is macro-defined"
    blocked.update(
        _vex_macro_generated_overloads(analysis, names)
    )
    blocked.update(
        _vex_macro_exposed_call_names(analysis, names)
    )
    defined_macros = set(
        re.findall(
            r"^[ \t]*#[ \t]*define[ \t]+"
            r"([A-Za-z_][A-Za-z0-9_]*)\b",
            preprocessed,
            re.M,
        )
    )

    for match in re.finditer(
        r"\b(" + alternatives + r")\s*\(", executable
    ):
        name_end = match.start(1) + len(match.group(1))
        open_paren = match.end() - 1
        if (
            not _span_is_code(code_mask, match.start(1), name_end)
            or not code_mask[open_paren]
        ):
            continue
        close = _close_paren(text, open_paren, code_mask)
        if close < 0:
            continue
        next_character = _next_vex_code_character(text, close + 1, code_mask)
        looks_declared = _vex_has_typed_declaration_prefix(
            analysis, match.start()
        )
        next_index = _next_vex_code_index(text, close + 1, code_mask)
        next_token_match = (
            re.match(r"[A-Za-z_][A-Za-z0-9_]*", text[next_index:])
            if next_index >= 0
            else None
        )
        next_token = (
            next_token_match.group(0) if next_token_match else None
        )
        if looks_declared and (
            next_character in ("{", ";")
            or next_token in defined_macros
        ):
            reason = "name is locally declared or overloaded"
            if next_token in defined_macros:
                reason += " with macro-expanded body syntax"
            blocked[match.group(1)] = reason
    return analysis.store(key, blocked)


def _vex_has_external_source_directive(analysis):
    """Detect executable directives that can inject unknown VEX definitions."""
    key = ("external_source_directive",)
    if key in analysis.cache:
        return analysis.cache[key]
    result = bool(
        re.search(
            r"^[ \t]*#[ \t]*(?:include(?:_once)?|import)\b",
            analysis.logical_source,
            re.M,
        )
    )
    return analysis.store(key, result)


def _previous_vex_boundary(text, start, code_mask):
    """Return the first character after the previous executable statement."""
    for index in range(start - 1, -1, -1):
        if code_mask[index] and text[index] in ";{}":
            return index + 1
    return 0


def _next_vex_code_character(text, start, code_mask):
    """Return the next non-space executable character."""
    index = _next_vex_code_index(text, start, code_mask)
    return text[index] if index >= 0 else ""


def _next_vex_code_index(text, start, code_mask):
    """Return the next non-space executable source index."""
    index = max(0, start)
    while index < len(text):
        if not code_mask[index] or text[index].isspace():
            index += 1
            continue
        if text[index] == "\\":
            following = index + 1
            while following < len(text) and text[following] in " \t":
                following += 1
            if following < len(text) and text[following] in "\r\n":
                index = following + 1
                continue
        return index
    return -1


def _vex_call_is_qualified(text, start, code_mask):
    """Reject member, namespace, token-paste, and stringized call syntax."""
    def previous_code_index(index):
        while index >= 0:
            if not code_mask[index] or text[index].isspace():
                index -= 1
                continue
            if text[index] == "\\":
                following = index + 1
                while following < len(text) and text[following] in " \t":
                    following += 1
                if (
                    following < len(text)
                    and text[following] in "\r\n"
                ):
                    index -= 1
                    continue
            break
        return index

    index = previous_code_index(start - 1)
    if index < 0:
        return False
    if text[index] == ".":
        return True
    marker = text[index]
    previous = previous_code_index(index - 1)
    if marker == ":" and previous >= 0 and text[previous] == ":":
        return True
    if marker == ">" and previous >= 0 and text[previous] == "-":
        return True
    if marker == "#":
        return True
    return False


def _vex_argument_mentions_old(analysis, start, end, old):
    """Recognize an exact old-name literal/token/local in one VEX argument."""
    text, code_mask = analysis.text, analysis.code_mask
    value, _quote, _literal_start, _literal_end = _literal(text, start, end)
    if value == old:
        return True
    argument, _argument_span = _vex_argument_identifier(analysis, start, end)
    if argument:
        assignments = _vex_assignments(analysis, argument)
        return any(
            assignment["kind"] == "literal"
            and assignment["value"] == old
            for assignment in assignments
        )
    pattern = re.compile(WORD.format(re.escape(old)))
    return any(
        _span_is_code(code_mask, match.start(), match.end())
        for match in pattern.finditer(text, start, end)
    )


def _vex_alias_uses_are_authorized(
    analysis, name, assignment, authorized_spans
):
    """Require every executable alias token to be one selected call argument."""
    text, code_mask = analysis.text, analysis.code_mask
    if _vex_parameter_binds_name(analysis, name):
        return False
    authorized = set(authorized_spans)
    assignment_target = (
        assignment.get("name_start"),
        assignment.get("name_end"),
    )
    scopes = _vex_scope_paths(analysis)
    declaration_scope = scopes[assignment_target[0]]
    for match in re.finditer(WORD.format(re.escape(name)), text):
        span = (match.start(), match.end())
        if not _span_is_code(code_mask, span[0], span[1]):
            continue
        if span == assignment_target:
            continue
        if (
            span not in authorized
            or scopes[span[0]] != declaration_scope
        ):
            return False
    return True


def _vex_scope_paths(analysis):
    """Record the exact executable brace scope at every source position."""
    key = ("scope_paths",)
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    scopes = [()] * (len(text) + 1)
    stack = []
    for index, character in enumerate(text):
        scopes[index] = tuple(stack)
        if not code_mask[index]:
            continue
        if character == "{":
            stack.append(index)
        elif character == "}" and stack:
            stack.pop()
    scopes[len(text)] = tuple(stack)
    return analysis.store(key, scopes)


def _vex_parameter_binds_name(analysis, name):
    """Conservatively detect a same-named VEX function parameter."""
    key = ("parameter_binds_name", name)
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    executable = analysis.executable
    function_pattern = re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_]*\s*\("
    )
    name_pattern = re.compile(WORD.format(re.escape(name)))
    for match in function_pattern.finditer(executable):
        open_paren = match.end() - 1
        if not code_mask[open_paren]:
            continue
        close = _close_paren(text, open_paren, code_mask)
        if close < 0:
            continue
        if _next_vex_code_character(text, close + 1, code_mask) != "{":
            continue
        if any(
            _span_is_code(code_mask, token.start(), token.end())
            for token in name_pattern.finditer(text, open_paren + 1, close)
        ):
            return analysis.store(key, True)
    return analysis.store(key, False)


def _vex_assignments(analysis, name):
    """Return one unambiguous ``string name = ...`` local declaration."""
    key = ("assignments", name)
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    executable = analysis.executable
    write_pattern = re.compile(
        WORD.format(re.escape(name))
        + r"(?P<array>\s*\[\s*\])?\s*"
        + r"(?P<operator>\+\+|--|"
        r"(?:<<|>>|[+\-*/%&|^])?=(?!=))"
    )
    writes = []
    for match in write_pattern.finditer(executable):
        name_end = match.start() + len(name)
        operator_start = match.start("operator")
        operator_end = match.end("operator")
        if (
            not _span_is_code(code_mask, match.start(), name_end)
            or not _span_is_code(
                code_mask, operator_start, operator_end
            )
        ):
            continue
        operator = match.group("operator")
        declaration_start = _previous_vex_boundary(
            text, match.start(), code_mask
        )
        declaration_prefix = analysis.executable[
            declaration_start : match.start()
        ].strip()
        is_plain_string_declaration = (
            operator == "="
            and match.group("array") is None
            and declaration_prefix == "string"
        )
        if not is_plain_string_declaration:
            writes.append(None)
            continue
        end = _vex_statement_end(text, match.end(), code_mask)
        if end < 0:
            writes.append(None)
            continue

        value, quote, literal_start, literal_end = _literal(
            text, match.end(), end
        )
        if value is not None:
            writes.append(
                {
                    "kind": "literal",
                    "name_start": match.start(),
                    "name_end": match.start() + len(name),
                    "start": literal_start,
                    "end": literal_end,
                    "value": value,
                    "quote": quote,
                    "statement_start": declaration_start,
                    "statement_end": end + 1,
                }
            )
            continue

        argument = text[match.end() : end].strip()
        chs_match = re.match(
            r"^chs\s*\(\s*(['\"])([^'\"]+)\1\s*\)$", argument
        )
        if chs_match:
            writes.append(
                {
                    "kind": "chs",
                    "name_start": match.start(),
                    "name_end": match.start() + len(name),
                    "parm_name": chs_match.group(2),
                    "statement_start": declaration_start,
                    "statement_end": end + 1,
                }
            )
        else:
            writes.append(None)
    result = writes if len(writes) == 1 and writes[0] is not None else []
    return analysis.store(key, result)


def _vex_name_write_spans(analysis, name):
    """Return complete statement spans that assign a possible alias."""
    key = ("name_write_spans", name)
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    executable = analysis.executable
    pattern = re.compile(
        WORD.format(re.escape(name))
        + r"(?:\s*\[\s*\])?\s*"
        + r"(?:\+\+|--|(?:<<|>>|[+\-*/%&|^])?=(?!=))"
    )
    spans = []
    for match in pattern.finditer(executable):
        if not _span_is_code(
            code_mask, match.start(), match.start() + len(name)
        ):
            continue
        start = _previous_vex_boundary(text, match.start(), code_mask)
        end = _vex_statement_end(text, match.end(), code_mask)
        spans.append(
            (
                start,
                end + 1
                if end >= 0
                else _vex_logical_line_end(analysis, match.end()),
            )
        )
    return analysis.store(key, spans)


def _vex_argument_source_spans(analysis, start, end):
    """Bound declarations that feed an explicitly rejected argument."""
    text, code_mask = analysis.text, analysis.code_mask
    identifier_pattern = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
    names = {
        match.group(0)
        for match in identifier_pattern.finditer(text, start, end)
        if _span_is_code(code_mask, match.start(), match.end())
    }
    return _vex_name_dependency_spans(analysis, names)


def _vex_name_dependency_spans(analysis, names):
    """Recursively bound declarations feeding rejected VEX aliases."""
    key = ("name_dependency_spans", tuple(sorted(names)))
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    identifier_pattern = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
    pending = list(names)
    visited = set()
    spans = []
    seen_spans = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        direct_spans = list(
            _vex_name_write_spans(analysis, name)
        )
        direct_spans.extend(
            _vex_macro_definition_spans(analysis, name)
        )
        for span in direct_spans:
            if span not in seen_spans:
                seen_spans.add(span)
                spans.append(span)
            for match in identifier_pattern.finditer(
                text, span[0], span[1]
            ):
                if _span_is_code(
                    code_mask, match.start(), match.end()
                ):
                    dependency = match.group(0)
                    if dependency not in visited:
                        pending.append(dependency)
    return analysis.store(key, spans)


def _vex_spans_contain_exact_string(strings, spans, value):
    """Detect a terminated exact literal inside bounded dependency spans."""
    return any(
        record["terminated"]
        and record["body"] == value
        and any(
            record["start"] < span_end
            and record["end"] > span_start
            for span_start, span_end in spans
        )
        for record in strings
    )


def _vex_macro_definition_spans(analysis, name):
    """Return logical preprocessor lines that define an alias name."""
    key = ("macro_definition_spans", name)
    if key in analysis.cache:
        return analysis.cache[key]
    executable = analysis.executable
    pattern = re.compile(
        r"^[ \t]*#[ \t]*define[ \t]+"
        + re.escape(name)
        + r"\b",
        re.M,
    )
    result = [
        (
            match.start(),
            _vex_logical_line_end(analysis, match.end()),
        )
        for match in pattern.finditer(executable)
    ]
    return analysis.store(key, result)


def _vex_logical_line_end(analysis, start):
    """Return the end of a possibly backslash-continued source line."""
    key = ("logical_line_end", start)
    if key in analysis.cache:
        return analysis.cache[key]
    text, code_mask = analysis.text, analysis.code_mask
    cursor = max(0, start)
    while cursor < len(text):
        line_end = cursor
        while line_end < len(text) and text[line_end] not in "\r\n":
            line_end += 1

        previous = line_end - 1
        while previous >= cursor and (
            not code_mask[previous] or text[previous].isspace()
        ):
            previous -= 1
        continued = previous >= cursor and text[previous] == "\\"

        end = line_end
        if end < len(text) and text[end] == "\r":
            end += 1
        if end < len(text) and text[end] == "\n":
            end += 1
        if not continued:
            return analysis.store(key, end)
        cursor = end
    return analysis.store(key, len(text))


def _vex_argument_identifier(analysis, start, end):
    """Return a sole executable identifier and its token span."""
    text, code_mask = analysis.text, analysis.code_mask
    executable = analysis.executable[start:end]
    identifier = executable.strip()
    if not IDENT.match(identifier):
        return None, None
    pattern = re.compile(WORD.format(re.escape(identifier)))
    for match in pattern.finditer(text, start, end):
        if _span_is_code(code_mask, match.start(), match.end()):
            return identifier, (match.start(), match.end())
    return None, None


def _vex_statement_end(text, start, code_mask):
    """Return the next executable semicolon after a VEX assignment."""
    for index in range(start, len(text)):
        if code_mask[index] and text[index] == ";":
            return index
    return -1


def _lex_vex(text):
    """Return a code mask and records for quoted/C++ raw VEX strings."""
    source = str(text or "")
    code = [True] * len(source)
    strings = []
    index = 0

    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""

        if char == "R" and following == '"':
            start = index
            delimiter_start = index + 2
            opener_end = delimiter_start
            delimiter = None
            while opener_end < len(source):
                current = source[opener_end]
                if current == "(":
                    delimiter = source[delimiter_start:opener_end]
                    break
                if (
                    opener_end - delimiter_start >= 16
                    or current in " ()\\\t\v\f\r\n"
                ):
                    break
                opener_end += 1

            if delimiter is None:
                body_start = len(source)
                body_end = len(source)
                end = len(source)
                terminated = False
            else:
                body_start = opener_end + 1
                terminator = ")" + delimiter + '"'
                body_end = source.find(terminator, body_start)
                terminated = body_end >= 0
                if terminated:
                    end = body_end + len(terminator)
                else:
                    body_end = len(source)
                    end = len(source)

            # Mask the whole literal, including an unterminated tail, so its
            # contents cannot be mistaken for executable VEX.
            code[start:end] = [False] * (end - start)
            strings.append(
                {
                    "start": start,
                    "end": end,
                    "body_start": body_start,
                    "body_end": body_end,
                    "quote": '"',
                    "body": source[body_start:body_end],
                    "terminated": terminated,
                    "raw": True,
                    "prefix": "R",
                    "delimiter": delimiter,
                }
            )
            index = end
            continue

        if char == "/" and following == "/":
            start = index
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            code[start:index] = [False] * (index - start)
            continue

        if char == "/" and following == "*":
            start = index
            index += 2
            while index < len(source):
                if (
                    source[index] == "*"
                    and index + 1 < len(source)
                    and source[index + 1] == "/"
                ):
                    index += 2
                    break
                index += 1
            code[start:index] = [False] * (index - start)
            continue

        if char in "'\"":
            quote = char
            start = index
            index += 1
            body_start = index
            escaped = False
            while index < len(source):
                current = source[index]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    break
                index += 1
            body_end = index
            terminated = index < len(source) and source[index] == quote
            if terminated:
                index += 1
            end = index
            code[start:end] = [False] * (end - start)
            strings.append(
                {
                    "start": start,
                    "end": end,
                    "body_start": body_start,
                    "body_end": body_end,
                    "quote": quote,
                    "body": source[body_start:body_end],
                    "terminated": terminated,
                    "raw": False,
                    "prefix": "",
                    "delimiter": None,
                }
            )
            continue

        index += 1
    return code, tuple(strings)


def _exact_vex_string_replacements(strings, old, new):
    """Plan replacements for exact ordinary or raw string bodies."""
    replacements = []
    for record in strings:
        if not record["terminated"] or record["body"] != old:
            continue
        if record["raw"]:
            delimiter = record["delimiter"]
            replacement = 'R"{0}({1}){0}"'.format(delimiter, new)
        else:
            quote = record["quote"]
            replacement = quote + new + quote
        replacements.append((record["start"], record["end"], replacement))
    return replacements


# ---------------------------------------------------------------------------
# Plain parameter fields and group-owner inference
# ---------------------------------------------------------------------------


def _plain_field_semantics(node, parm, kind):
    """Return explicit name-reference intent and a weaker subject hint."""
    parm_name = re.sub(r"[^a-z0-9]+", "", _parm_name(parm).lower())
    label = re.sub(r"[^a-z0-9]+", " ", _parm_label(parm).lower()).strip()
    label_words = tuple(label.split())
    roles = r"(?:name|names|list|pattern|mask)"
    role_hint = any(word in label_words for word in roles[3:-1].split("|"))
    subjects = r"(?:attrs?|attribs?|attributes?|groups?)"
    values = r"(?:default|values?|data)"
    prefixes = (
        r"(?:(?:in|out|input|output|src|dst|source|dest|destination|point"
        r"|pt|primitive|prim|vertex|vtx|detail|global|edge|any|base|name"
        r"|names|list|pattern|mask|result|custom|setting|parameter|parm))*"
    )
    value_role = bool(
        re.search(
            r"\b" + subjects + r"\b.*\b" + values + r"\b"
            r"|\b" + values + r"\b.*\b" + subjects + r"\b",
            label,
        )
        or re.search(
            subjects + r".*" + values + r"[a-z]*\d*$", parm_name
        )
        or re.match(
            r"^" + prefixes + values + r"[a-z0-9]*" + subjects
            + r"[a-z]*\d*$",
            parm_name,
        )
    )
    if kind == RENAME_KIND_ATTRIBUTE:
        subject_words = frozenset(
            ("attr", "attrs", "attrib", "attribs", "attribute", "attributes")
        )
        subject = r"(?:attr|attrib|attribute)"
        plurals = r"(?:attr|attrs|attrib|attribs|attribute|attributes)"
        owners = r"(?:point|pt|primitive|prim|vertex|vtx|detail|global)"
        node_hint = "{0} {1}".format(
            _node_type_name(node), _node_type_description(node)
        ).lower()
        generic_name = bool(
            re.match(r"^name\d*$", parm_name) or label in ("name", "names")
        ) and ("attrib" in node_hint or "attribute" in node_hint)
    else:
        subject_words = frozenset(("group", "groups"))
        subject = r"group"
        plurals = r"(?:group|groups)"
        owners = r"(?:point|pt|primitive|prim|edge|any|base)"
        generic_name = False
    subject_hint = any(word in subject_words for word in label_words) or bool(
        re.search(subject + r"(?:s|name|names|list|pattern|mask|\d|$)", parm_name)
    )
    role_hint = role_hint or bool(
        re.search(
            subject + r"s?" + roles + r"\d*$|" + roles + subject + r"s?\d*$",
            parm_name,
        )
    )
    directions = r"in|out|input|output|src|dst|source|dest|destination"
    direction = r"(?:" + directions + r")?"
    label_prefix = r"(?:(?:" + directions + r")|" + owners[3:-1] + r")\s+"
    bare_label = bool(
        re.match(r"^(?:" + label_prefix + r"){0,2}" + plurals + r"$", label)
    )
    bare_name = bool(
        re.match(r"^" + direction + owners + r"?" + plurals + r"\d*$", parm_name)
    )
    explicit = bool(
        subject_hint and (role_hint or bare_label or bare_name) or generic_name
    ) and not value_role
    return explicit, subject_hint


def _plain_field_info(node, parm, kind, node_parms=None):
    """Resolve plain-field eligibility and owner metadata for UI and planning."""
    editable = _plain_editable_string_field(parm)
    owner_metadata = _owner_metadata_parameter(parm)
    explicit, hinted = _plain_field_semantics(node, parm, kind)
    owner = None
    ambiguous_owner = False
    if editable and not owner_metadata and explicit:
        owner = _plain_parameter_class(
            node, parm, kind, node_parms=node_parms
        )
        ambiguous_owner = owner is _AMBIGUOUS_OWNER
        if ambiguous_owner:
            owner = None
    return {
        "editable": editable,
        "owner_metadata": owner_metadata,
        "explicit": explicit,
        "hinted": hinted,
        "owner": owner,
        "ambiguous_owner": ambiguous_owner,
    }


def _plain_rewrite(node, parm, text, kind, item_class, old, new):
    """Rewrite concrete tokens only in metadata-supported name fields."""
    try:
        field = _plain_field_info(node, parm, kind)
    except Exception as error:
        if _is_interrupted(error):
            raise
        return text, [], []
    if not field["editable"]:
        return text, [], [
            "plain parameter is not an editable string field"
        ]
    if field["owner_metadata"]:
        return text, [], []

    if kind == RENAME_KIND_GROUP:
        relevant, hinted = field["explicit"], field["hinted"]
        if not relevant:
            return (
                text,
                [],
                (
                    ["plain group field is not an explicit name reference"]
                    if hinted
                    else []
                ),
            )
        parameter_class = field["owner"]
        if field["ambiguous_owner"]:
            return text, [], [
                "group owner metadata is ambiguous or conflicting"
            ]
        if (
            parameter_class == UNSUPPORTED_GROUP_CLASS
            or parameter_class != item_class
        ):
            return text, [], []
    else:
        attribute_relevant = field["explicit"]
        attribute_hint = field["hinted"]
        group_field = None
        if not attribute_hint:
            try:
                group_field = _plain_field_info(
                    node, parm, RENAME_KIND_GROUP
                )
            except Exception as error:
                if _is_interrupted(error):
                    raise
                return text, [], []
        if group_field and group_field["hinted"]:
            group_relevant = group_field["explicit"]
            if not group_relevant:
                return text, [], [
                    "plain group field is not an explicit name reference"
                ]
            parameter_class = group_field["owner"]
            if group_field["ambiguous_owner"]:
                return text, [], [
                    "group owner metadata is ambiguous or conflicting"
                ]
            if parameter_class != item_class:
                return text, [], []
            if _plain_name_occurs_in_pattern(text, old):
                return text, [], [
                    "plain field contains a wildcard or range pattern for "
                    "'{0}'".format(old)
                ]
            value, count = re.subn(
                r"(?<![A-Za-z0-9_])@"
                + re.escape(old)
                + r"(?![A-Za-z0-9_])",
                "@" + new,
                text,
            )
            return (
                value,
                (["group attribute token"] if count else []),
                [],
            )
        relevant = attribute_relevant
        if not relevant:
            return (
                text,
                [],
                (
                    [
                        "plain attribute field is not an explicit "
                        "name reference"
                    ]
                    if attribute_hint
                    else []
                ),
            )
        parameter_class = field["owner"]
        if field["ambiguous_owner"]:
            return text, [], [
                "attribute owner metadata is ambiguous or conflicting"
            ]
        if parameter_class != item_class:
            return text, [], []

    if not relevant:
        return text, [], []
    if (
        kind == RENAME_KIND_ATTRIBUTE
        and _plain_attribute_name_has_nonoperand_use(text, old)
    ):
        return text, [], [
            "plain attribute field does not use '{0}' as an exact list "
            "operand".format(old)
        ]
    if (
        kind == RENAME_KIND_GROUP
        and _plain_group_name_has_nonoperand_use(text, old)
    ):
        return text, [], [
            "plain group field does not use '{0}' as an exact "
            "whitespace-delimited operand".format(old)
        ]

    if kind == RENAME_KIND_GROUP:
        # Concrete operands may carry Houdini's proven exclusion prefix.
        # Generic group fields use whitespace, not commas, between operands.
        pattern = (
            r"(?<!\S)(\^?)"
            + re.escape(old)
            + r"(?=$|\s)"
        )
        value, count = re.subn(
            pattern, lambda match: match.group(1) + new, text
        )
    else:
        pattern = (
            r"(?<![^\s,])(\^?)"
            + re.escape(old)
            + r"(?=$|[\s,])"
        )
        value, count = re.subn(
            pattern, lambda match: match.group(1) + new, text
        )
    return value, (["parameter token"] if count else []), []


def _plain_attribute_name_has_nonoperand_use(text, name):
    """Reject a selected attribute embedded in a non-list operand."""
    name_pattern = re.compile(WORD.format(re.escape(name)))
    exact_operands = frozenset((name, "^" + name))
    return any(
        name_pattern.search(operand) and operand not in exact_operands
        for operand in re.findall(r"[^\s,]+", text)
    )


def _plain_group_name_has_nonoperand_use(text, name):
    """Reject a selected group embedded in a non-whitespace operand."""
    name_pattern = re.compile(WORD.format(re.escape(name)))
    exact_operands = frozenset((name, "^" + name))
    return any(
        name_pattern.search(operand) and operand not in exact_operands
        for operand in re.findall(r"\S+", text)
    )


def _plain_name_occurs_in_pattern(text, name):
    """Detect a selected name inside one non-concrete field operand."""
    name_pattern = re.compile(WORD.format(re.escape(name)))
    pattern_syntax = frozenset("*?[]{}-:")
    for operand in re.findall(r"[^\s,]+", text):
        if (
            any(character in pattern_syntax for character in operand)
            and name_pattern.search(operand)
        ):
            return True
    return False


def _plain_editable_string_field(parm):
    """Require a genuine free-text-capable Houdini string template."""
    try:
        template_type = parm.parmTemplate().type()
    except Exception as error:
        if _is_interrupted(error):
            raise
        return False
    return template_type == getattr(
        getattr(hou, "parmTemplateType", None),
        "String",
        None,
    )


def _owner_metadata_parameter(parm):
    """Exclude class/type selectors from concrete name rewriting."""
    parm_name = re.sub(
        r"[^a-z0-9]+", "", _parm_name(parm).strip().lower()
    )
    label = re.sub(
        r"[^a-z0-9]+", " ", _parm_label(parm).strip().lower()
    ).strip()
    prefix = (
        r"(?:(?:in|out|input|output|src|dst|source|dest|destination))?"
        r"(?:(?:point|pt|primitive|prim|vertex|vtx|detail|global|edge|any))?"
    )
    name_patterns = (
        r"^" + prefix + r"(?:class|attribclass|attributeclass)\d*$",
        r"^"
        + prefix
        + r"(?:grouptype|groupclass|groupentity|entity)\d*$",
    )
    if any(re.match(pattern, parm_name) for pattern in name_patterns):
        return True

    label_prefix = (
        r"(?:(?:in|out|input|output|src|dst|source|dest|destination) )?"
    )
    label_patterns = (
        r"^"
        + label_prefix
        + r"(?:class|attrib class|attribute class)(?: \d+)?$",
        r"^"
        + label_prefix
        + r"(?:group type|group class|group entity|entity)(?: \d+)?$",
    )
    return (
        any(re.match(pattern, label) for pattern in label_patterns)
        or bool(
            re.search(
                r"\b(?:attrib|attribute)\s+class\b"
                r"|\bgroup\s+(?:type|class|entity)\b",
                label,
            )
        )
    )


def _plain_parameter_class(node, parm, kind, node_parms=None):
    """Infer one plain field owner from its descriptor and companion menu."""
    attribute = kind == RENAME_KIND_ATTRIBUTE
    parser = (
        _attribute_classes_from_text if attribute else _group_classes_from_text
    )
    stems = (
        ("class", "attribclass", "attributeclass")
        if attribute
        else ("grouptype", "groupclass", "groupentity", "entity")
    )
    subject = r"(?:name|attrib|attribute)" if attribute else r"(?:group|name)"
    parm_name = _parm_name(parm).lower()
    owners = set(parser("{0} {1}".format(parm_name, _parm_label(parm))))
    if node_parms is None:
        try:
            node_parms = node.parms()
        except Exception:
            if not attribute:
                raise
            node_parms = ()
    by_name = {
        _parm_name(candidate).lower(): candidate
        for candidate in (node_parms or ())
    }
    suffix_match = re.search(r"(\d+)$", parm_name)
    suffix = suffix_match.group(1) if suffix_match else ""
    prefix_match = re.match(
        r"^(in|out|input|output|src|dst|source|dest|destination)" + subject,
        parm_name,
    )
    prefixes = []
    if suffix:
        prefixes.append("")
    if prefix_match:
        prefixes.append(prefix_match.group(1))
    candidate_names = tuple(
        dict.fromkeys(
            prefix + stem + suffix for prefix in prefixes for stem in stems
        )
    ) or stems
    for candidate_name in candidate_names:
        candidate = by_name.get(candidate_name)
        if candidate is None:
            continue
        companion_owners = {
            owner
            for descriptor in _selected_menu_descriptors(candidate)
            for owner in parser(descriptor)
        }
        if len(companion_owners) != 1:
            return _AMBIGUOUS_OWNER
        owners.update(companion_owners)
    return (
        _AMBIGUOUS_OWNER
        if len(owners) > 1
        else next(iter(owners))
        if owners
        else None
    )


def _selected_menu_descriptors(parm):
    """Return only the selected token/label from genuine menu metadata."""
    if parm is None:
        return ()

    def menu_metadata(source):
        result = []
        for method in ("menuItems", "menuLabels"):
            try:
                result.append(tuple(getattr(source, method)()))
            except Exception:
                result.append(())
        return tuple(result)

    menu_items, menu_labels = menu_metadata(parm)
    if not (menu_items or menu_labels):
        try:
            template = parm.parmTemplate()
        except Exception:
            template = None
        if template is not None:
            menu_items, menu_labels = menu_metadata(template)
    if not (menu_items or menu_labels):
        return ()

    descriptors = []
    try:
        value = str(parm.evalAsString())
    except Exception as error:
        if _is_interrupted(error):
            raise
        value = ""
    if value in menu_items:
        index = menu_items.index(value)
        descriptors.append(menu_items[index])
        if index < len(menu_labels):
            descriptors.append(menu_labels[index])
    try:
        index = int(parm.evalAsInt())
    except Exception as error:
        if _is_interrupted(error):
            raise
        index = -1
    if 0 <= index < len(menu_items):
        descriptors.append(menu_items[index])
    if 0 <= index < len(menu_labels):
        descriptors.append(menu_labels[index])
    return tuple(dict.fromkeys(descriptors))


def _selected_attribute_class(parm):
    """Read one selected attribute owner from a menu parameter."""
    descriptors = _selected_menu_descriptors(parm)
    owners = {
        owner
        for descriptor in descriptors
        for owner in _attribute_classes_from_text(descriptor)
    }
    return next(iter(owners)) if len(owners) == 1 else None


def _attribute_classes_from_text(text):
    """Return every bounded attribute-owner term in a descriptor."""
    text = str(text or "").strip().lower()
    mappings = (
        ("vertex", r"\b(?:vertex|vertices|vtx)\b"),
        ("primitive", r"\b(?:primitive|primitives|prim|prims)\b"),
        ("point", r"\b(?:point|points|pt|pts)\b"),
        ("detail", r"\b(?:detail|global|dtl)\b"),
    )
    return {
        owner
        for owner, pattern in mappings
        if re.search(pattern, text)
    }


def _vex_binding_class(node):
    """Infer the owner represented by a VEX ``@`` binding."""
    type_name = _node_type_name(node).lower()
    description = _node_type_description(node).lower()
    if type_name == "pointwrangle" or description == "point wrangle":
        return "point"

    try:
        parms = tuple(node.parms())
    except Exception:
        parms = ()
    owners = []
    for candidate in parms:
        name = _parm_name(candidate).lower()
        label = _parm_label(candidate).lower()
        if (
            "run over" in label
            or name in ("bindclass", "runover", "run_over")
            or ("wrangle" in (type_name + " " + description) and name == "class")
        ):
            owner = _selected_attribute_class(candidate)
            if owner:
                owners.append(owner)
    return owners[0] if owners and len(set(owners)) == 1 else None


def _group_classes_from_text(text):
    """Return every bounded group-owner term in a descriptor."""
    text = str(text or "").strip().lower()
    mappings = (
        (
            UNSUPPORTED_GROUP_CLASS,
            r"\b(?:vertex|vertices|vtx)\b",
        ),
        ("edge", r"\b(?:edge|edges)\b"),
        ("point", r"\b(?:point|points|pt|pts)\b"),
        (
            "primitive",
            r"\b(?:primitive|primitives|prim|prims)\b",
        ),
        (
            ANY_GROUP_CLASS,
            r"\b(?:any|guess|auto|automatic)\b",
        ),
    )
    return {
        owner
        for owner, pattern in mappings
        if re.search(pattern, text)
    }


# ---------------------------------------------------------------------------
# Conservative language classification and metadata helpers
# ---------------------------------------------------------------------------


def _looks_like_python(node, parm, value, language):
    """Recognize Python from explicit metadata or strong HOM syntax."""
    methods = {"addAttrib", "attribValue", "setAttribValue"}
    for names in PY_ATTR.values():
        methods.update(names)
    for names in PY_GROUP.values():
        methods.update(names)
    return (
        _expression_language_kind(language) == "python"
        or "python" in _parm_hint(node, parm)
        or "hou." in (value or "")
        or bool(
            re.search(
                r"\b(?:{0})\s*\(".format(
                    "|".join(re.escape(name) for name in sorted(methods))
                ),
                value or "",
            )
        )
    )


def _looks_like_hscript(text, item_class):
    """Recognize class-correct HScript attribute functions."""
    names = "|".join(
        re.escape(name) for name, _index in HSCRIPT_ATTR[item_class]
    )
    return bool(re.search(r"\b(?:" + names + r")\s*\(", text, re.I))


def _looks_like_vex(node, parm, value):
    """Recognize VEX metadata and strong syntax, including numeric bindings."""
    hint = _parm_hint(node, parm)
    group_functions = "|".join(
        re.escape(name)
        for functions in GROUP_VEX.values()
        for name, _index in functions
    )
    strong_content = bool(
        re.search(
            r"(?:(?<![A-Za-z0-9_])[A-Za-z0-9]?@[A-Za-z_]|"
            r"set(?:point|prim|vertex|detail|edge)"
            r"(?:attrib|group)\s*\(|\b(?:{0})\s*\()".format(
                group_functions
            ),
            value or "",
        )
    )
    return (
        "wrangle" in hint
        or any(marker in hint for marker in ("vex", "snippet", "code"))
        or strong_content
    )


def _hscript_metadata(node, parm, language):
    """Recognize explicit HScript language and parameter metadata."""
    hint = _parm_hint(node, parm)
    return (
        _expression_language_kind(language) == "hscript"
        or "hscript" in hint
        or "h-script" in hint
    )


def _parm_hint(node, parm):
    return "{0} {1} {2}".format(
        _node_type_name(node), _parm_name(parm), _parm_label(parm)
    ).lower()


def _parm_label(parm):
    try:
        return str(parm.parmTemplate().label())
    except Exception:
        return ""


def _node_type_name(node):
    try:
        return str(node.type().name())
    except Exception:
        return ""


def _node_type_description(node):
    try:
        return str(node.type().description())
    except Exception:
        return ""
