"""Pure-Python VEX, Python, and HScript name rewriters.

These functions operate on source strings without importing Houdini or Qt.
Each one returns a ``RewriteResult``:

    from labsopui import labs_rename_attributes_rewriters as rewriters

    vex_result = rewriters.rewrite_vex(
        'f@Cd = point(0, "Cd", 0);',
        "attribute", "point", "Cd", "color",
        run_over_class="point",
    )
    python_result = rewriters.rewrite_python(
        'hou.pwd().geometry().findPointAttrib("Cd")',
        "attribute", "point", "Cd", "color",
    )
    hscript_result = rewriters.rewrite_hscript(
        'point("../OUT", 0, "Cd", 0)',
        "attribute", "point", "Cd", "color",
    )

A rewrite follows the same conservative pipeline in every language:

1. Validate the rename kind, owner, and both identifiers.
2. Parse the language or mask comments and strings so code-like text inside
   them cannot be mistaken for a reference.
3. Find only constructs whose meaning is established by an owner-specific
   allowlist or an equally strict syntax rule.
4. Replace recorded spans right to left, preserving unrelated formatting.

Attribute owners are ``point``, ``primitive``, ``vertex``, and ``detail``;
group owners are ``point``, ``primitive``, and ``edge``.  The same name can
legitimately exist on several geometry classes, so owner is part of the request.

A name is changed only when the source establishes both its meaning and owner.
Dynamic names, aliases, ambiguous owners, comments, unsupported syntax, and
indirect references remain unchanged and are reported through
``RewriteResult.skipped``.  These diagnostics describe recognized candidates;
they are not an inventory of every textual occurrence of the old name.
"""

import ast
from dataclasses import dataclass
import re


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VALID_OWNERS = {
    "attribute": frozenset(("point", "primitive", "vertex", "detail")),
    "group": frozenset(("point", "primitive", "edge")),
}


# Results and request validation

@dataclass(frozen=True)
class RewriteResult:
    """Immutable result returned by every language-specific rewriter.

    ``text`` is the complete rewritten source, ``changed`` compares it with
    the input, ``reasons`` lists the rules that produced edits, and ``skipped``
    explains candidate references that could not be rewritten safely.

    A result may contain both edits and skipped candidates.  For example, one
    direct literal can be renamed while an alias in the same source is reported
    but left alone.  Treat ``skipped`` as context, not as a failure flag.
    """

    text: str
    changed: bool
    reasons: tuple
    skipped: tuple


def validate_request(rename_kind, item_class, old_name, new_name):
    """Validate and normalize the common rename arguments.

    The rename kind and owner are stripped and lowercased.  Names are converted
    to strings but otherwise kept exact; both must be distinct identifiers.
    """
    kind = str(rename_kind or "").strip().lower()
    owner = str(item_class or "").strip().lower()
    old = str(old_name or "")
    new = str(new_name or "")
    if kind not in VALID_OWNERS:
        raise ValueError("rename_kind must be 'attribute' or 'group'")
    if owner not in VALID_OWNERS[kind]:
        raise ValueError("unsupported {} class: {}".format(
            kind, owner or "<empty>"))
    if not IDENTIFIER.match(old):
        raise ValueError("old_name must be a non-empty identifier")
    if not IDENTIFIER.match(new):
        raise ValueError("new_name must be a non-empty identifier")
    if old == new:
        raise ValueError("old_name and new_name must be different")
    return kind, owner, old, new


def make_result(source, text, reasons=(), skipped=()):
    """Build one result while deduplicating reasons in discovery order."""
    reasons = tuple(dict.fromkeys(reason for reason in reasons if reason))
    skipped = tuple(dict.fromkeys(reason for reason in skipped if reason))
    return RewriteResult(
        text=text,
        changed=text != source,
        reasons=reasons,
        skipped=skipped,
    )


# C/VEX lexical masking

def lex_c_like(text):
    """Return an executable-code mask and C/VEX-style string records.

    Each mask entry corresponds to one source character.  Comments and string
    literals are false so later searches ignore code-like text inside them.
    String records preserve exact source offsets and whether the literal was
    raw or terminated.

    The mask and recorded spans use Python character offsets.  A string record
    includes full-literal and body spans, quote and prefix information, and
    ``raw`` and ``terminated`` flags.

    This is deliberately a small lexer rather than a complete VEX parser.  It
    recognizes the comments and string forms needed by the rewriters.  When a
    raw-string opener is malformed or unterminated, the remainder is masked;
    hiding uncertain text is safer than treating its contents as executable.
    """
    source = str(text or "")
    code = [True] * len(source)
    strings = []
    index = 0

    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""

        if char == "R" and following == '"':
            # VEX raw strings use C++-style R"delimiter(body)delimiter".
            # The delimiter may contain up to 16 characters, excluding
            # whitespace, parentheses, and backslashes.
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

            code[start:end] = [False] * (end - start)
            strings.append({
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
            })
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
            strings.append({
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
            })
            continue

        index += 1

    return code, tuple(strings)


def span_is_code(code_mask, start, end):
    """Return whether a source span is valid and entirely executable code."""
    if start < 0 or end < start or end > len(code_mask):
        return False
    return all(code_mask[start:end])


def _close_paren(text, start, mask):
    """Return the close matching ``text[start]``, ignoring masked regions."""
    depth, quote, index = 0, None, start
    while index < len(text):
        if mask is not None and not mask[index]:
            index += 1
            continue
        char = text[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if not depth:
                return index
        index += 1
    return -1


def _arguments(text, start, end, mask):
    """Split one call's top-level arguments into trimmed source spans."""
    spans, begin, depth, quote, index = [], start, 0, None, start
    while index < end:
        if mask is not None and not mask[index]:
            index += 1
            continue
        char = text[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and not depth:
            # Nested calls, containers, and subscripts keep their commas
            # inside the current argument.
            spans.append((begin, index))
            begin = index + 1
        index += 1
    spans.append((begin, end))
    return [
        (
            start + len(text[start:stop]) - len(text[start:stop].lstrip()),
            stop - len(text[start:stop]) + len(text[start:stop].rstrip()),
        )
        for start, stop in spans
    ]


# Allowlisted calls and literals

def find_calls(
        text, table, case_sensitive=False, code_mask=None, blocked_names=()):
    """Locate allowlisted calls and return their name-argument source spans.

    Skips qualified calls, token-pasted names, explicitly blocked functions,
    masked text, and calls without a matching closing parenthesis.  ``table``
    maps each function to the zero-based argument containing the attribute or
    group name.

    Each result is ``(function_name, (start, end))`` in the original source.
    Argument splitting honors nested parentheses, lists, and dictionaries;
    delimiters inside masked comments or strings are ignored.
    """
    if not table:
        return []
    if code_mask is None:
        code_mask, _strings = lex_c_like(text)
    names = "|".join(re.escape(name) for name, _index in table)
    indexes = dict(table)
    flags = 0 if case_sensitive else re.I
    result = []
    for match in re.finditer(r"\b(" + names + r")\s*\(", text, flags):
        if not span_is_code(code_mask, match.start(), match.end()):
            continue
        function = match.group(1) if case_sensitive else match.group(1).lower()
        if function in blocked_names:
            continue
        prefix = text[max(0, match.start() - 2):match.start()]
        if prefix.endswith((".", ":")) or prefix == "##":
            continue
        close = _close_paren(text, match.end() - 1, code_mask)
        if close < 0:
            continue
        arguments = _arguments(text, match.end(), close, code_mask)
        index = indexes[function]
        if len(arguments) > index:
            result.append((function, arguments[index]))
    return result


def literal_argument(text, start, end):
    """Return a sole quoted literal and its exact source span.

    Whitespace and comments may surround the literal.  Concatenation,
    operators, multiple literals, or another executable expression make it
    dynamic.  Thus ``"Cd"`` and ``/* note */ "Cd"`` are eligible, while
    ``prefix + "Cd"`` and ``chs("name")`` are not.
    """
    raw = text[start:end]
    matches = list(re.finditer(r"(['\"])(.*?)\1", raw, re.S))
    if len(matches) != 1:
        return None, None, None, None
    match = matches[0]

    def only_spacing_and_comments(fragment):
        """Return whether a fragment contains no executable expression."""
        fragment = re.sub(
            r"/\*.*?\*/|//[^\n]*(?:\n|$)|#[^\n]*(?:\n|$)",
            "",
            fragment,
            flags=re.S,
        )
        return not fragment.strip()

    if not (
        only_spacing_and_comments(raw[:match.start()])
        and only_spacing_and_comments(raw[match.end():])
    ):
        return None, None, None, None
    return (
        match.group(2),
        match.group(1),
        start + match.start(),
        start + match.end(),
    )


def replace_spans(text, replacements):
    """Apply valid non-overlapping replacements from right to left.

    Reverse source order keeps every earlier offset stable.  Invalid or
    overlapping spans are ignored.
    """
    used = []
    for start, end, value in sorted(replacements, reverse=True):
        if (
            start < 0
            or end < start
            or any(start < prior_end and end > prior_start
                   for prior_start, prior_end in used)
        ):
            continue
        text = text[:start] + value + text[end:]
        used.append((start, end))
    return text


# Entries pair a case-insensitive HScript function with the zero-based
# argument containing the attribute name.
HSCRIPT_ATTRIBUTE_FUNCTIONS = {
    "point": (("point", 2), ("haspointattrib", 1)),
    "primitive": (
        ("prim", 2), ("primuv", 2), ("hasprimattrib", 1)),
    "vertex": (("vertex", 3), ("hasvertexattrib", 1)),
    "detail": (
        ("detail", 1), ("details", 1), ("hasdetailattrib", 1)),
}


# HScript rewriting

def rewrite_hscript(source, rename_kind, item_class, old_name, new_name):
    """Rewrite allowlisted literal HScript references in source text.

    HScript function names are matched case-insensitively, but only the
    owner-specific argument declared in ``HSCRIPT_ATTRIBUTE_FUNCTIONS`` is
    considered.  A direct literal is eligible:

        point("../OUT", 0, "Cd", 0)

    The same spelling elsewhere is not.  Indirection and calculated names are
    reported without being followed:

        point("../OUT", 0, chs("attribute_name"), 0)
        point("../OUT", 0, strcat("C", "d"), 0)

    Groups are unsupported because HScript has no equivalent class-specific
    syntax that establishes their owner.  Executable ``#`` starts a comment;
    a hash inside a quoted string remains part of that string.
    """
    text = str(source if source is not None else "")
    kind, owner, old, new = validate_request(
        rename_kind, item_class, old_name, new_name)
    if kind != "attribute":
        return make_result(
            text,
            text,
            skipped=("HScript group references are not supported",),
        )

    code_mask = _hscript_code_mask(text)
    replacements, skipped, reasons = [], [], []
    for function, (start, end) in find_calls(
            text, HSCRIPT_ATTRIBUTE_FUNCTIONS[owner], code_mask=code_mask):
        value, quote, literal_start, literal_end = literal_argument(
            text, start, end)
        if value == old:
            replacements.append((
                literal_start, literal_end, quote + new + quote))
            reasons.append("HScript {} literal".format(function))
            continue

        argument = text[start:end].strip()
        if re.match(r"(?i)^chs\s*\(", argument):
            skipped.append(
                "HScript {} uses indirect chs(); target unchanged".format(
                    function))
        elif old in argument:
            skipped.append(
                "HScript {} uses a dynamic name".format(function))

    updated = replace_spans(text, replacements)
    return make_result(text, updated, reasons, skipped)


# HScript comment masking

def _hscript_code_mask(text):
    """Return a C-like code mask extended with HScript ``#`` comments."""
    code, _strings = lex_c_like(text)
    index = 0
    while index < len(text):
        if code[index] and text[index] == "#":
            # Only executable ``#`` starts a comment; hashes already inside a
            # quoted string are false in the shared mask and remain untouched.
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            code[index:end] = [False] * (end - index)
            index = end
        else:
            index += 1
    return code


# Each allowlist is owner-specific.  Selecting an owner therefore determines
# both which HOM methods are valid and what the receiver must prove.
PYTHON_ATTRIBUTE_METHODS = {
    "point": (
        "findPointAttrib", "deletePointAttrib", "pointFloatAttribValues",
        "pointIntAttribValues", "pointStringAttribValues",
        "setPointFloatAttribValues", "setPointIntAttribValues",
        "setPointStringAttribValues"),
    "primitive": (
        "findPrimAttrib", "deletePrimAttrib",
        "primFloatAttribValues", "primIntAttribValues",
        "primStringAttribValues", "setPrimFloatAttribValues",
        "setPrimIntAttribValues", "setPrimStringAttribValues"),
    "vertex": (
        "findVertexAttrib", "deleteVertexAttrib",
        "vertexFloatAttribValues", "vertexIntAttribValues",
        "vertexStringAttribValues", "setVertexFloatAttribValues",
        "setVertexIntAttribValues", "setVertexStringAttribValues"),
    "detail": (
        "findGlobalAttrib", "deleteGlobalAttrib", "setGlobalAttribValue"),
}
PYTHON_GROUP_METHODS = {
    "point": (
        "findPointGroup", "createPointGroup", "deletePointGroup",
        "destroyPointGroup"),
    "primitive": (
        "findPrimGroup", "createPrimGroup", "deletePrimGroup",
        "destroyPrimGroup"),
    "edge": (
        "findEdgeGroup", "createEdgeGroup", "deleteEdgeGroup",
        "destroyEdgeGroup"),
}


# Python rewriting

def rewrite_python(source, rename_kind, item_class, old_name, new_name):
    """Rewrite direct literals on ``hou`` receiver chains established by AST.

    Invalid Python returns an unchanged result with a parse diagnostic.
    If ``hou`` may be rebound or mutated, the source is left unchanged because
    receiver inference is no longer reliable.

    Geometry methods require a direct receiver such as:

        hou.pwd().geometry().findPointAttrib("Cd")
        hou.node("/obj/geo1").geometry().findPointGroup("selection")

    Storing the geometry in ``geo`` is rejected because syntax no longer proves
    what it refers to.  The name must also be a direct positional string
    literal; aliases and computed expressions remain unchanged.

    ``attribValue`` and ``setAttribValue`` are accepted only on a direct point,
    primitive, vertex, or geometry lookup that proves the selected owner.
    ``addAttrib`` instead proves its owner through an explicit matching
    ``hou.attribType`` enum.  These checks prevent an attribute with the same
    name on another geometry class from being changed accidentally.
    """
    text = str(source if source is not None else "")
    kind, owner, old, new = validate_request(
        rename_kind, item_class, old_name, new_name)
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return make_result(
            text,
            text,
            skipped=("Python could not be parsed: {}".format(error),),
        )

    if _hou_is_ambiguous(tree):
        return make_result(
            text,
            text,
            skipped=("Python hou binding or namespace is ambiguous",),
        )

    methods = (
        PYTHON_ATTRIBUTE_METHODS if kind == "attribute" else PYTHON_GROUP_METHODS
    )[owner]
    replacements, skipped = [], []
    for call in (
            candidate for candidate in ast.walk(tree)
            if isinstance(candidate, ast.Call)):
        name = _call_name(call)
        if not isinstance(call.func, ast.Attribute):
            continue
        receiver = call.func.value

        if kind == "attribute" and name == "addAttrib":
            if (
                not _direct_hou_geometry(receiver)
                or _add_attrib_class(call) != owner
            ):
                if old in (ast.get_source_segment(text, call) or ""):
                    skipped.append(
                        "Python addAttrib owner or receiver is not proven")
                continue
            index = 1
        elif kind == "attribute" and name in (
                "attribValue", "setAttribValue"):
            if _direct_hou_element_class(receiver) != owner:
                if old in (ast.get_source_segment(text, call) or ""):
                    skipped.append(
                        "Python {} receiver is not proven".format(name))
                continue
            index = 0
        else:
            index = 0

        if name not in methods and not (
                kind == "attribute"
                and name in ("addAttrib", "attribValue", "setAttribValue")):
            continue
        if name not in ("attribValue", "setAttribValue") and (
                not _direct_hou_geometry(receiver)):
            if old in (ast.get_source_segment(text, call) or ""):
                skipped.append(
                    "Python {} receiver is not a direct hou chain".format(
                        name))
            continue
        if len(call.args) <= index:
            continue

        argument = call.args[index]
        if isinstance(argument, ast.Constant) and argument.value == old:
            # Replace the literal's exact source span rather than regenerating
            # the AST, preserving comments and unrelated formatting.
            span = _node_span(text, argument)
            if span:
                replacements.append((
                    span[0],
                    span[1],
                    _quoted_like(text[span[0]:span[1]], new),
                ))
        elif old in (
            ast.get_source_segment(text, argument)
            if ast.get_source_segment(text, argument)
            else False
        ):
            skipped.append(
                "Python {} uses an alias or dynamic name".format(name))

    updated = replace_spans(text, replacements)
    reasons = ("Python HOM method",) if replacements else ()
    return make_result(text, updated, reasons, skipped)


# ``hou`` namespace checks and direct receiver inference

def _hou_is_ambiguous(tree):
    """Reject a source that can rebind or dynamically mutate trusted ``hou``.

    The check applies to the whole source.  Modeling runtime control flow,
    closures, ``eval``, or ``exec`` is out of scope, so any namespace
    ambiguity disables rewriting.

    Ambiguity includes assigning to or deleting ``hou``, shadowing it through
    an import or local binding, and writing through a ``hou`` attribute.
    ``eval``, ``exec``, ``setattr``, and ``delattr`` can make similar changes.
    One such operation disables every Python rewrite rather than guessing
    which control-flow path reaches a candidate.

    For example, the call looks direct but cannot be trusted after rebinding:

        hou = proxy
        hou.pwd().geometry().findPointAttrib("Cd")
    """
    match_as = getattr(ast, "MatchAs", ())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
                (alias.asname or alias.name.split(".")[0]) == "hou"
                and alias.name != "hou"
                for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and (
                node.module != "hou"
                or any(alias.name == "*" for alias in node.names)):
            if any(alias.name == "hou" or alias.name == "*"
                   for alias in node.names):
                return True
        if isinstance(node, ast.Name) and node.id == "hou" and isinstance(
                node.ctx, (ast.Store, ast.Del)):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if getattr(node, "name", None) == "hou":
                return True
            arguments = (
                list(getattr(node.args, "posonlyargs", ()))
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            )
            if any(argument.arg == "hou" for argument in arguments):
                return True
        if isinstance(node, ast.ExceptHandler) and node.name == "hou":
            return True
        if match_as and isinstance(node, match_as) and node.name == "hou":
            return True
        if isinstance(node, ast.Call):
            called = _call_name(node)
            if called in ("eval", "exec"):
                return True
            if called in ("setattr", "delattr") and node.args and (
                    isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "hou"):
                return True
        if isinstance(node, ast.Attribute) and isinstance(
                node.ctx, (ast.Store, ast.Del)) and _root_name(node) == "hou":
            return True
    return False


def _root_name(node):
    """Return the leftmost name of an attribute/call receiver chain."""
    while isinstance(node, (ast.Attribute, ast.Call)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else ""


def _direct_hou_geometry(node):
    """Return whether a node is exactly ``hou.pwd/node(...).geometry()``."""
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "geometry"
    ):
        return False
    owner = node.func.value
    return (
        isinstance(owner, ast.Call)
        and isinstance(owner.func, ast.Attribute)
        and isinstance(owner.func.value, ast.Name)
        and owner.func.value.id == "hou"
        and owner.func.attr in ("pwd", "node")
    )


def _direct_hou_element_class(node):
    """Infer an element owner from a direct geometry element lookup."""
    if _direct_hou_geometry(node):
        return "detail"
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and _direct_hou_geometry(node.func.value)
    ):
        return None
    return {
        "point": "point",
        "prim": "primitive",
        "vertex": "vertex",
    }.get(node.func.attr)


# AST source offsets and literal preservation

def _node_span(source, node):
    """Translate an AST node's UTF-8 positions into character offsets.

    CPython reports AST columns as UTF-8 byte offsets, while slicing a Python
    string uses character indexes.  Converting both endpoints keeps later
    replacements aligned when non-ASCII text appears earlier on the line.
    """
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
        start = line_offsets[start_line] + _utf8_column_to_character_index(
            lines[start_line], node.col_offset)
        end = line_offsets[end_line] + _utf8_column_to_character_index(
            lines[end_line], node.end_col_offset)
    except (IndexError, TypeError, ValueError):
        return None
    if start < 0 or end < start or end > len(source):
        return None
    return start, end


def _utf8_column_to_character_index(line, byte_column):
    """Convert CPython's UTF-8 byte column to a safe character index."""
    if byte_column <= 0:
        return 0
    encoded = line.encode("utf-8")
    byte_column = min(int(byte_column), len(encoded))
    while byte_column > 0:
        try:
            return len(encoded[:byte_column].decode("utf-8"))
        except UnicodeDecodeError:
            # A mid-codepoint offset backs up to the nearest preceding
            # complete character.
            byte_column -= 1
    return 0


def _quoted_like(source, new):
    """Quote ``new`` using the original literal prefix and delimiter.

    Recognized prefixes and single, double, or triple quotes are preserved.
    Unrecognized literal forms fall back to ``repr``.
    """
    match = re.match(
        r"^(?P<prefix>[rRuUbB]*)(?P<quote>'''|\"\"\"|'|\")"
        r"(?P<body>.*)(?P=quote)$",
        source,
        re.S,
    )
    if not match:
        return repr(new)
    prefix, quote = match.group("prefix"), match.group("quote")
    escaped = new.replace("\\", "\\\\").replace(quote, "\\" + quote)
    return prefix + quote + escaped + quote


def _call_name(call):
    """Return the terminal callable name for a simple AST call."""
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _add_attrib_class(call):
    """Return the owner from an explicit ``hou.attribType`` enum argument."""
    if not call.args:
        return None
    owner = call.args[0]
    if not isinstance(owner, ast.Attribute):
        return None
    container = owner.value
    # Similar local enums or aliases are not accepted; the receiver must be
    # the literal, unshadowed ``hou.attribType`` chain.
    if not (
        isinstance(container, ast.Attribute)
        and isinstance(container.value, ast.Name)
        and container.value.id == "hou"
        and container.attr == "attribType"
    ):
        return None
    return {
        "Point": "point",
        "Prim": "primitive",
        "Vertex": "vertex",
        "Global": "detail",
    }.get(owner.attr)


# Function entries pair a case-sensitive VEX name with the zero-based argument
# that contains the attribute or group name.
VEX_ATTRIBUTE_FUNCTIONS = {
    "point": (
        ("setpointattrib", 1), ("point", 1), ("pointattrib", 1),
        ("haspointattrib", 1), ("pointattribtype", 1), ("pointattribsize", 1)),
    "primitive": (
        ("setprimattrib", 1), ("prim", 1), ("primattrib", 1),
        ("hasprimattrib", 1), ("primattribtype", 1), ("primattribsize", 1)),
    "vertex": (
        ("setvertexattrib", 1), ("vertex", 1), ("vertexattrib", 1),
        ("hasvertexattrib", 1), ("vertexattribtype", 1),
        ("vertexattribsize", 1)),
    "detail": (
        ("setdetailattrib", 1), ("detail", 1), ("detailattrib", 1),
        ("hasdetailattrib", 1), ("detailattribtype", 1),
        ("detailattribsize", 1)),
}
VEX_GROUP_FUNCTIONS = {
    "point": (
        ("setpointgroup", 1), ("inpointgroup", 1),
        ("expandpointgroup", 1), ("npointsgroup", 1)),
    "primitive": (
        ("setprimgroup", 1), ("inprimgroup", 1),
        ("expandprimgroup", 1), ("nprimitivesgroup", 1)),
    "edge": (
        ("setedgegroup", 1), ("inedgegroup", 1), ("expandedgegroup", 1),
        ("nedgesgroup", 1)),
}


# VEX rewriting

def rewrite_vex(
        source,
        rename_kind,
        item_class,
        old_name,
        new_name,
        run_over_class=None):
    """Rewrite direct VEX bindings and allowlisted literal call arguments.

    ``run_over_class`` is optional but must equal the requested owner before
    an ``@`` binding is changed.  Allowlisted function calls establish their
    owner from the owner-specific table and do not require Run Over metadata.

    There are two independent authorization paths.  An owner-specific function
    such as ``point(0, "Cd", @ptnum)`` identifies a point attribute through its
    allowlist entry, so its direct literal can be changed without Run Over
    metadata.  A binding such as ``f@Cd`` or ``i@group_selected`` carries no
    complete owner information; it is changed only when ``run_over_class``
    matches the requested owner.  Type prefixes such as ``f@`` and ``v@`` are
    preserved.

    Aliases, calculated strings, and ``chs()`` indirection are reported but not
    followed:

        string name = "Cd"; vector value = point(0, name, 0);
        vector value = point(0, chs("attribute_name"), 0);

    Comments, string bodies, preprocessor directives, qualified calls, and
    token-pasted names cannot authorize a match.  A macro or local function
    that shadows an allowlisted built-in blocks that function name throughout
    the source, because resolving overload and macro scope would require a full
    compiler rather than this focused source rewriter.
    """
    text = str(source if source is not None else "")
    kind, owner, old, new = validate_request(
        rename_kind, item_class, old_name, new_name)
    run_over = (
        str(run_over_class).strip().lower()
        if run_over_class is not None
        else None
    )
    table = (
        VEX_ATTRIBUTE_FUNCTIONS if kind == "attribute" else VEX_GROUP_FUNCTIONS
    )[owner]
    code_mask, _strings = lex_c_like(text)
    # Mask directives before searching for calls; macro text does not
    # establish a runtime call to the built-in function.
    code_mask = _vex_mask_directives(text, code_mask)
    replacements, skipped, reasons = [], [], []
    blocked = _vex_blocked_functions(text, table, code_mask)

    for function, (start, end) in find_calls(
            text,
            table,
            case_sensitive=True,
            code_mask=code_mask,
            blocked_names=blocked):
        value, quote, literal_start, literal_end = literal_argument(
            text, start, end)
        if value == old:
            replacements.append((
                literal_start, literal_end, quote + new + quote))
            reasons.append("VEX {} literal".format(function))
            continue

        argument = text[start:end].strip()
        if re.match(r"^chs\s*\(", argument):
            skipped.append(
                "VEX {} uses indirect chs(); target unchanged".format(
                    function))
        elif IDENTIFIER.match(argument):
            skipped.append(
                "VEX {} uses an alias; direct literals only".format(function))
        elif old in argument:
            skipped.append(
                "VEX {} uses a dynamic name".format(function))

    binding = r"(?<![A-Za-z0-9_])([A-Za-z0-9]?)@" + (
        "group_" if kind == "group" else "") + re.escape(old) + (
        r"(?![A-Za-z0-9_])")
    owner_note_added = False
    for match in re.finditer(binding, text):
        if not span_is_code(code_mask, match.start(), match.end()):
            continue
        if run_over != owner:
            if not owner_note_added:
                skipped.append(
                    "VEX binding owner is not proven by Run Over")
                owner_note_added = True
            continue
        prefix = match.group(1) + "@" + (
            "group_" if kind == "group" else "")
        replacements.append((match.start(), match.end(), prefix + new))
        reasons.append("VEX @ binding")

    updated = replace_spans(text, replacements)
    return make_result(text, updated, reasons, skipped)


# VEX preprocessor and local-function exclusions

def _vex_mask_directives(text, code_mask):
    """Mask preprocessor directives, including backslash continuations."""
    mask = list(code_mask)
    offset = 0
    directive = False
    for line in text.splitlines(True):
        stripped = line.lstrip()
        if not directive:
            directive = stripped.startswith("#")
        if directive:
            mask[offset:offset + len(line)] = [False] * len(line)
        directive = directive and line.rstrip("\r\n").endswith("\\")
        offset += len(line)
    return mask


def _vex_blocked_functions(text, table, code_mask):
    """Return allowlisted names shadowed by macros, pasting, or overloads.

    Blocking is source-wide.  Once an allowlisted name can refer to a macro,
    token-pasted symbol, or local overload, no call with that name is assumed
    to reach the built-in function, even if some individual calls look valid.
    This deliberate false negative avoids making edits that depend on VEX
    preprocessing or overload resolution.
    """
    names = {name for name, _index in table}
    blocked = set()
    logical = re.sub(r"\\\r?\n", " ", text)
    for line in logical.splitlines():
        directive = re.match(
            r"\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)", line)
        if directive and directive.group(1) in names:
            blocked.add(directive.group(1))
        if "##" in line:
            # Token pasting can manufacture an allowlisted function name; a
            # textual match in that macro does not prove the runtime callee.
            blocked.update(name for name in names if name in line)

    for name in names:
        # A same-source declaration shadows the built-in name.  Calls to the
        # local overload are deliberately excluded even when signatures look
        # compatible with the built-in function.
        declaration = re.compile(
            r"(?m)^[ \t]*(?:export[ \t]+)?"
            r"(?:[A-Za-z_][A-Za-z0-9_<>\[\]]*[ \t]+)+"
            + re.escape(name)
            + r"[ \t]*\("
        )
        for match in declaration.finditer(text):
            if span_is_code(code_mask, match.start(), match.end()):
                blocked.add(name)
                break
    return blocked


__all__ = (
    "RewriteResult",
    "rewrite_vex",
    "rewrite_python",
    "rewrite_hscript",
)
