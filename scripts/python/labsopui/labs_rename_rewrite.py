"""Pure rewrite helpers for Rename Attributes and Groups.

This module deliberately has no Houdini dependency so its offset-sensitive
rewrites can be covered by ordinary Python unit tests.
"""


def vex_lex(source):
    """Return a code mask and string literal records for VEX-like source."""
    source = str(source or "")
    code_mask = [True] * len(source)
    strings = []
    index = 0

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if char == "/" and next_char == "/":
            start = index
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            for offset in range(start, index):
                code_mask[offset] = False
            continue

        if char == "/" and next_char == "*":
            start = index
            index += 2
            while index < len(source):
                if source[index] == "*" and index + 1 < len(source) and source[index + 1] == "/":
                    index += 2
                    break
                index += 1
            for offset in range(start, index):
                code_mask[offset] = False
            continue

        if char in ("'", '"'):
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
            for offset in range(start, end):
                code_mask[offset] = False
            strings.append({
                "start": start,
                "end": end,
                "body_start": body_start,
                "body_end": body_end,
                "quote": quote,
                "body": source[body_start:body_end],
                "terminated": terminated,
            })
            continue

        index += 1

    return code_mask, tuple(strings)


def vex_code_mask(source):
    return vex_lex(source)[0]


def span_is_code(code_mask, start, end):
    if start < 0 or end < start or end > len(code_mask):
        return False
    return all(code_mask[index] for index in range(start, end))


def vex_exact_string_replacements(source, old_name, new_name):
    """Return aggressive replacements for exact VEX string literals."""
    replacements = []
    _code_mask, strings = vex_lex(source)
    for record in strings:
        if not record["terminated"] or record["body"] != old_name:
            continue
        quote = record["quote"]
        replacements.append({
            "start": record["start"],
            "end": record["end"],
            "text": "{0}{1}{0}".format(quote, new_name),
        })
    return replacements


def utf8_column_to_character_index(line, byte_column):
    """Translate CPython AST's UTF-8 byte column into a string index."""
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


def python_ast_node_span(source, node):
    """Return character offsets for an AST node, including non-ASCII lines."""
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return None

    lines = source.splitlines(True)
    if not lines:
        lines = [""]
    offsets = []
    total = 0
    for line in lines:
        offsets.append(total)
        total += len(line)

    try:
        start_line = lines[node.lineno - 1]
        end_line = lines[node.end_lineno - 1]
        start = offsets[node.lineno - 1] + utf8_column_to_character_index(start_line, node.col_offset)
        end = offsets[node.end_lineno - 1] + utf8_column_to_character_index(end_line, node.end_col_offset)
    except (IndexError, TypeError, ValueError):
        return None

    if start < 0 or end < start or end > len(source):
        return None
    return start, end
