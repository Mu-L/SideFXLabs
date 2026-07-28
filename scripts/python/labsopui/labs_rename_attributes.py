"""Interactive Houdini workflow for renaming attributes and groups safely.

This module owns scope discovery, the rich Qt workflow, previews, guarded
application, undo, and reporting.  ``labs_rename_attributes_engine`` owns the
read-only language-aware rewrite decisions for individual parameters.

Discovery and preview never mutate parameters.  Application resolves every
node and parameter again, verifies that its source still matches the preview,
and records all successful writes in one Houdini undo group.
"""

import importlib
import re
from collections import deque
from contextlib import contextmanager

import hou

from . import labs_rename_attributes_engine as rename_engine

# Reload the planner with the shelf module so both sides of the public
# boundary stay synchronized after Houdini refreshes shelf code.
rename_engine = importlib.reload(rename_engine)


# ---------------------------------------------------------------------------
# Configuration, owner classes, scope identifiers, and session keys
# ---------------------------------------------------------------------------

RENAME_TITLE = "Rename Attributes and Groups"
DEFAULT_ATTRIBUTE = "selectnode"
DEFAULT_ATTRIBUTE_CLASS = "primitive"
DEFAULT_GROUP_CLASS = "primitive"
RENAME_KIND_ATTRIBUTE = "attribute"
RENAME_KIND_GROUP = "group"
RENAME_KIND_ITEMS = (
    (RENAME_KIND_ATTRIBUTE, "Attributes"),
    (RENAME_KIND_GROUP, "Groups"),
)
SESSION_RENAME_KIND_NAME = "_labs_rename_attributes_kind"
SESSION_ATTRIBUTE_NAME = "_labs_select_node_attribute"
SESSION_ATTRIBUTE_CLASS_NAME = "_labs_select_node_attribute_class"
SESSION_GROUP_NAME = "_labs_rename_attributes_group"
SESSION_GROUP_CLASS_NAME = "_labs_rename_attributes_group_class"
SESSION_SCOPE_OPTIONS_NAME = "_labs_rename_attributes_scope_options"
SESSION_SCOPE_DIALOG_NAME = "_labs_rename_attributes_scope_dialog"
SESSION_ITEM_DIALOG_NAME = "_labs_rename_attributes_item_dialog"
SESSION_AGGRESSIVE_VEX_NAME = "_labs_rename_attributes_aggressive_vex"
HIDDEN_RENAME_ATTRIBUTES = set(["P"])
ATTRIBUTE_CLASS_PRIMITIVE = "primitive"
ATTRIBUTE_CLASS_POINT = "point"
ATTRIBUTE_CLASS_VERTEX = "vertex"
ATTRIBUTE_CLASS_DETAIL = "detail"
ATTRIBUTE_CLASS_ITEMS = (
    (ATTRIBUTE_CLASS_PRIMITIVE, "Primitive"),
    (ATTRIBUTE_CLASS_POINT, "Point"),
    (ATTRIBUTE_CLASS_VERTEX, "Vertex"),
    (ATTRIBUTE_CLASS_DETAIL, "Detail"),
)
GROUP_CLASS_POINT = "point"
GROUP_CLASS_PRIMITIVE = "primitive"
GROUP_CLASS_EDGE = "edge"
GROUP_CLASS_ANY = "any"
GROUP_CLASS_UNSUPPORTED_VERTEX = "vertex"
GROUP_CLASS_ITEMS = (
    (GROUP_CLASS_POINT, "Point"),
    (GROUP_CLASS_PRIMITIVE, "Primitive"),
    (GROUP_CLASS_EDGE, "Edge"),
)
SCOPE_TARGET_SELECTED_NODES = "selected_nodes"
SCOPE_TARGET_WHOLE_HIP = "whole_hip"
SCOPE_ALL_NODES_LABEL = "All Nodes"
SCOPE_TARGET_ITEMS = (
    (SCOPE_TARGET_SELECTED_NODES, "Selected Nodes"),
    (SCOPE_TARGET_WHOLE_HIP, SCOPE_ALL_NODES_LABEL),
)


# ---------------------------------------------------------------------------
# Status reporting and persisted user selections
# ---------------------------------------------------------------------------


def _show_status(message, severity=hou.severityType.Message):
    try:
        hou.ui.setStatusMessage(message, severity=severity)
        return
    except Exception:
        pass

    try:
        hou.ui.displayMessage(message, severity=severity)
        return
    except Exception:
        pass

    print(message)


def _append_discovery_issue(issues, node_path, source_name, reason):
    """Append one stable discovery problem without repeating it."""
    if issues is None:
        return

    issue = {
        "node_path": str(node_path or ""),
        "parm_name": str(source_name or "<discovery>"),
        "reason": str(reason or "could not inspect source"),
    }
    key = (issue["node_path"], issue["parm_name"], issue["reason"])
    for existing in issues:
        existing_key = (
            str(existing.get("node_path", "")),
            str(existing.get("parm_name", "")),
            str(existing.get("reason", "")),
        )
        if existing_key == key:
            return
    issues.append(issue)


def _operation_interrupted(error):
    return error.__class__.__name__ == "OperationInterrupted"


def _append_rename_issue(records, node_path, parm_name, reason):
    records.append({
        "node_path": node_path,
        "parm_name": parm_name,
        "reason": reason,
    })


def _normalize_rename_kind(rename_kind):
    rename_kind = str(rename_kind or RENAME_KIND_ATTRIBUTE).strip().lower()
    if rename_kind not in dict(RENAME_KIND_ITEMS):
        return RENAME_KIND_ATTRIBUTE
    return rename_kind


def _rename_kind():
    rename_kind = getattr(hou.session, SESSION_RENAME_KIND_NAME, RENAME_KIND_ATTRIBUTE)
    rename_kind = _normalize_rename_kind(rename_kind)
    setattr(hou.session, SESSION_RENAME_KIND_NAME, rename_kind)
    return rename_kind


def _set_rename_kind(rename_kind):
    rename_kind = _normalize_rename_kind(rename_kind)
    setattr(hou.session, SESSION_RENAME_KIND_NAME, rename_kind)
    return True


def _rename_kind_label(rename_kind=None):
    rename_kind = _normalize_rename_kind(rename_kind or _rename_kind())
    for value, label in RENAME_KIND_ITEMS:
        if value == rename_kind:
            return label
    return "Attributes"


def _rename_kind_label_singular(rename_kind=None):
    rename_kind = _normalize_rename_kind(rename_kind or _rename_kind())
    if rename_kind == RENAME_KIND_GROUP:
        return "group"
    return "attribute"


def _rename_kind_indefinite_label(rename_kind=None):
    """Return the singular rename kind with its natural English article."""
    if _normalize_rename_kind(rename_kind or _rename_kind()) == RENAME_KIND_GROUP:
        return "a group"
    return "an attribute"


def _rename_kind_label_plural_lower(rename_kind=None):
    rename_kind = _normalize_rename_kind(rename_kind or _rename_kind())
    if rename_kind == RENAME_KIND_GROUP:
        return "groups"
    return "attributes"


def _normalize_attribute_class(attr_class):
    attr_class = str(attr_class).strip().lower()
    if attr_class not in dict(ATTRIBUTE_CLASS_ITEMS):
        return DEFAULT_ATTRIBUTE_CLASS
    return attr_class

def _attribute_class():
    attr_class = getattr(hou.session, SESSION_ATTRIBUTE_CLASS_NAME, DEFAULT_ATTRIBUTE_CLASS)
    attr_class = _normalize_attribute_class(attr_class)
    setattr(hou.session, SESSION_ATTRIBUTE_CLASS_NAME, attr_class)
    return attr_class

def _attribute_class_label(attr_class=None):
    attr_class = _normalize_attribute_class(attr_class or _attribute_class())
    for value, label in ATTRIBUTE_CLASS_ITEMS:
        if value == attr_class:
            return label
    return "Primitive"


def _set_matching_attribute(attr_name):
    attr_name = str(attr_name).strip()
    if not attr_name:
        _show_status("Matching attribute cannot be empty.", hou.severityType.Warning)
        return False

    setattr(hou.session, SESSION_ATTRIBUTE_NAME, attr_name)
    return True


def _set_attribute_class(attr_class):
    attr_class = _normalize_attribute_class(attr_class)
    setattr(hou.session, SESSION_ATTRIBUTE_CLASS_NAME, attr_class)
    return True

def _normalize_group_class(group_class):
    group_class = str(group_class or DEFAULT_GROUP_CLASS).strip().lower()
    if group_class == GROUP_CLASS_ANY:
        return GROUP_CLASS_ANY
    if group_class not in dict(GROUP_CLASS_ITEMS):
        return DEFAULT_GROUP_CLASS
    return group_class


def _group_class():
    group_class = getattr(hou.session, SESSION_GROUP_CLASS_NAME, DEFAULT_GROUP_CLASS)
    group_class = _normalize_group_class(group_class)
    setattr(hou.session, SESSION_GROUP_CLASS_NAME, group_class)
    return group_class


def _group_class_label(group_class=None):
    group_class = _normalize_group_class(group_class or _group_class())
    if group_class == GROUP_CLASS_ANY:
        return "Any Class"
    for value, label in GROUP_CLASS_ITEMS:
        if value == group_class:
            return label
    return "Primitive"


def _set_group_class(group_class):
    group_class = _normalize_group_class(group_class)
    setattr(hou.session, SESSION_GROUP_CLASS_NAME, group_class)
    return True


def _set_matching_group(group_name):
    group_name = str(group_name).strip()
    if not group_name:
        _show_status("Matching group cannot be empty.", hou.severityType.Warning)
        return False

    setattr(hou.session, SESSION_GROUP_NAME, group_name)
    return True


def _item_class_label(rename_kind, item_class):
    if _normalize_rename_kind(rename_kind) == RENAME_KIND_GROUP:
        return _group_class_label(item_class)
    return _attribute_class_label(item_class)


def _item_class_label_lower(rename_kind, item_class):
    return _item_class_label(rename_kind, item_class).lower()


def _set_matching_item(rename_kind, item_class, item_name):
    if _normalize_rename_kind(rename_kind) == RENAME_KIND_GROUP:
        _set_group_class(item_class)
        return _set_matching_group(item_name)
    _set_attribute_class(item_class)
    return _set_matching_attribute(item_name)


# ---------------------------------------------------------------------------
# Geometry, parameter, and rename-candidate discovery
# ---------------------------------------------------------------------------


def _displayed_sop_and_geometry(scene_viewer=None, cook_geometry=True):
    """Return the displayed SOP and optionally cook its current geometry."""
    try:
        viewer = scene_viewer or hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewer is None:
            return None, None

        pwd = viewer.pwd()
        if pwd is None:
            return None, None

        sop = pwd.displayNode()
        if sop is None:
            return None, None

        geo = sop.geometry() if cook_geometry else None
    except Exception:
        return None, None

    return sop, geo

def _geometry_attributes(geo, attr_class, discovery_issues=None, source_key=""):
    if geo is None:
        return []

    method_names = {
        ATTRIBUTE_CLASS_PRIMITIVE: "primAttribs",
        ATTRIBUTE_CLASS_POINT: "pointAttribs",
        ATTRIBUTE_CLASS_VERTEX: "vertexAttribs",
        ATTRIBUTE_CLASS_DETAIL: "globalAttribs",
    }
    method_name = method_names.get(_normalize_attribute_class(attr_class))
    if not method_name:
        return []

    try:
        method = getattr(geo, method_name)
        return list(method())
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            source_key,
            "<{0} attributes>".format(_normalize_attribute_class(attr_class)),
            "could not inspect attributes: {0}".format(exc),
        )
        return []

def _find_geometry_attribute(geo, attr_class, attr_name):
    if geo is None:
        return None

    attr_name = str(attr_name).strip()
    if not attr_name:
        return None

    method_names = {
        ATTRIBUTE_CLASS_PRIMITIVE: "findPrimAttrib",
        ATTRIBUTE_CLASS_POINT: "findPointAttrib",
        ATTRIBUTE_CLASS_VERTEX: "findVertexAttrib",
        ATTRIBUTE_CLASS_DETAIL: "findGlobalAttrib",
    }
    method_name = method_names.get(_normalize_attribute_class(attr_class))
    if not method_name:
        return None

    try:
        method = getattr(geo, method_name)
        return method(attr_name)
    except Exception:
        return None

def _attribute_names_from_geo(geo, attr_class, discovery_issues=None, source_key=""):
    names = []
    for attrib in _geometry_attributes(
        geo,
        attr_class,
        discovery_issues=discovery_issues,
        source_key=source_key,
    ):
        try:
            name = attrib.name().strip()
        except Exception as exc:
            _append_discovery_issue(
                discovery_issues,
                source_key,
                "<{0} attribute>".format(_normalize_attribute_class(attr_class)),
                "could not inspect attribute name: {0}".format(exc),
            )
            name = ""

        if name and name not in HIDDEN_RENAME_ATTRIBUTES:
            names.append(name)

    return sorted(set(names))

def _node_inputs(node, discovery_issues=None):
    try:
        return [input_node for input_node in node.inputs() if input_node is not None]
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<inputs>",
            "could not inspect input connections: {0}".format(exc),
        )
        return []

def _selected_nodes_in_current_network(selected):
    selected = [node for node in selected or () if node is not None]
    if not selected:
        return []

    try:
        current_parent_path = _node_path(selected[-1].parent())
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        current_parent_path = ""
    if not current_parent_path:
        return selected[-1:]

    current_network_selection = []
    for node in selected:
        try:
            parent_path = _node_path(node.parent())
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            parent_path = ""
        if parent_path == current_parent_path:
            current_network_selection.append(node)
    return current_network_selection


def _network_editor_selected_nodes(global_selected):
    """Return the selection owned by the visible Network Editor, when known."""
    if not hasattr(hou, "ui"):
        return None, None

    try:
        pane_tabs = tuple(hou.ui.paneTabs())
        network_editor_type = hou.paneTabType.NetworkEditor
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        return [], (
            "Could not inspect the visible Network Editors: {0}. "
            "No previous selection was kept."
        ).format(exc)

    pane_under_cursor_failed = False
    try:
        pane_under_cursor = hou.ui.paneTabUnderCursor()
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        pane_under_cursor = None
        pane_under_cursor_failed = True

    inspected_editors = []
    visible_editor_count = 0
    inspected_editor_count = 0
    failed_editor_count = 0
    for editor in pane_tabs:
        try:
            if editor.type() != network_editor_type:
                continue
            if not editor.isCurrentTab():
                continue
            visible_editor_count += 1
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            failed_editor_count += 1
            continue

        try:
            network = editor.pwd()
            if network is None:
                failed_editor_count += 1
                continue

            selected = list(network.selectedChildren())
            if not selected:
                current = editor.currentNode()
                if (
                    current is not None
                    and current.isSelected()
                    and _node_path(current.parent()) == _node_path(network)
                ):
                    selected = [current]

            network_path = _node_path(network)
            selected = _unique_nodes(
                node
                for node in selected
                if node is not None
                and _node_path(node.parent()) == network_path
            )
            inspected_editor_count += 1
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            failed_editor_count += 1
            continue

        inspected_editors.append((editor, network_path, selected))

    if not visible_editor_count:
        if pane_under_cursor_failed:
            return [], (
                "Could not inspect the pane under the cursor while resolving "
                "the Network Editor selection. No previous selection was kept."
            )
        if failed_editor_count:
            return [], (
                "Could not inspect every visible pane while resolving the "
                "Network Editor selection. No previous selection was kept."
            )
        return None, None

    for editor, _network_path, selected in inspected_editors:
        try:
            if editor == pane_under_cursor:
                if not selected:
                    return [], (
                        "No nodes are selected in the current Network Editor."
                    )
                return selected, None
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            pass

    if pane_under_cursor_failed:
        return [], (
            "Could not inspect the pane under the cursor while resolving the "
            "Network Editor selection. No previous selection was kept."
        )

    if failed_editor_count:
        return [], (
            "Could not inspect every visible Network Editor. "
            "Make the intended Network Editor active, then refresh."
        )

    if not inspected_editor_count:
        return [], (
            "Could not inspect the visible Network Editors. "
            "No previous selection was kept."
        )

    candidates = []
    seen_signatures = set()
    for _editor, network_path, selected in inspected_editors:
        if not selected:
            continue
        signature = (
            network_path,
            tuple(_node_path(node) for node in selected),
        )
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        candidates.append(selected)

    if not candidates:
        return [], "No nodes are selected in the current Network Editor."
    if len(candidates) == 1:
        return candidates[0], None

    return [], (
        "Selected nodes exist in more than one visible Network Editor. "
        "Make the intended node current or clear the other selection, then refresh."
    )


def _selected_nodes_with_warning():
    try:
        selected = hou.selectedNodes()
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        selected = []

    editor_selected, warning = _network_editor_selected_nodes(selected)
    if editor_selected is not None:
        return editor_selected, warning

    selected = _selected_nodes_in_current_network(selected)
    if selected:
        return selected, None
    return [], "No nodes are selected in the current network."


def _node_output_indices(node, discovery_issues=None):
    """Return every inspectable SOP output, falling back to output zero."""
    method = getattr(node, "outputConnectors", None)
    if method is None:
        return (0,)

    try:
        connectors = tuple(method())
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<outputs>",
            "could not inspect output connectors; output 1 was used: {0}".format(exc),
        )
        return (0,)
    return tuple(range(len(connectors))) or (0,)


def _node_geometry_for_discovery(node, output_index, discovery_issues=None):
    """Cook one output while converting local failures into reportable issues."""
    node_path = _node_path(node)
    source_name = "<output {0}>".format(output_index + 1)
    try:
        geo = node.geometry(output_index)
    except TypeError as exc:
        if output_index != 0:
            _append_discovery_issue(
                discovery_issues,
                node_path,
                source_name,
                "could not inspect indexed geometry output: {0}".format(exc),
            )
            return None
        try:
            geo = node.geometry()
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            _append_discovery_issue(
                discovery_issues,
                node_path,
                source_name,
                "could not cook geometry: {0}".format(exc),
            )
            return None
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            node_path,
            source_name,
            "could not cook geometry: {0}".format(exc),
        )
        return None

    if geo is None:
        _append_discovery_issue(
            discovery_issues,
            node_path,
            source_name,
            "no cooked geometry was returned",
        )
        return None
    try:
        is_valid = getattr(geo, "isValid", None)
        if is_valid is not None and not is_valid():
            _append_discovery_issue(
                discovery_issues,
                node_path,
                source_name,
                "cooked geometry is invalid",
            )
            return None
    except Exception as exc:
        _append_discovery_issue(
            discovery_issues,
            node_path,
            source_name,
            "could not validate cooked geometry: {0}".format(exc),
        )
        return None
    return geo


def _node_is_sop(node):
    if node is None:
        return False

    try:
        return node.type().category() == hou.sopNodeTypeCategory()
    except Exception:
        return False


@contextmanager
def _interruptable_scan(title):
    """Yield a Houdini progress operation when the host can create one."""
    try:
        operation = hou.InterruptableOperation(
            title,
            open_interrupt_dialog=True,
        )
    except Exception:
        yield None
        return

    with operation:
        yield operation


def _iter_nodes_with_progress(nodes, title, progress_callback=None):
    """Yield unique nodes while maintaining one monotonic progress stream."""
    unique_nodes = _unique_nodes(nodes or ())
    total = max(len(unique_nodes), 1)
    if progress_callback is not None:
        for index, node in enumerate(unique_nodes):
            progress_callback(index, total)
            yield node
        progress_callback(total, total)
        return

    with _interruptable_scan(title) as operation:
        for index, node in enumerate(unique_nodes):
            if operation is not None:
                operation.updateProgress(float(index) / total)
            yield node
        if operation is not None:
            operation.updateProgress(1.0)


def _discover_geometry_items_from_nodes(nodes):
    """Collect valid geometry from every SOP output without aborting the scan."""
    geometry_items = []
    discovery_issues = []
    seen_sources = set()
    sop_nodes = [node for node in _unique_nodes(nodes or []) if _node_is_sop(node)]

    with _interruptable_scan("Scanning geometry for renameable items") as operation:
        total = max(len(sop_nodes), 1)
        for index, node in enumerate(sop_nodes):
            if operation is not None:
                operation.updateProgress(float(index) / total)

            node_path = _node_path(node)
            if not node_path:
                continue

            for output_index in _node_output_indices(node, discovery_issues):
                source_key = (
                    node_path
                    if output_index == 0
                    else "{0} [output {1}]".format(node_path, output_index + 1)
                )
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)
                geo = _node_geometry_for_discovery(
                    node,
                    output_index,
                    discovery_issues,
                )
                if geo is not None:
                    geometry_items.append((source_key, geo))

        if operation is not None:
            operation.updateProgress(1.0)

    return geometry_items, discovery_issues


def _geometry_groups(geo, group_class, discovery_issues=None, source_key=""):
    """Read one group owner class while isolating geometry inspection failures."""
    if geo is None:
        return []

    group_class = _normalize_group_class(group_class)
    if group_class == GROUP_CLASS_ANY:
        groups = []
        for concrete_class, _label in GROUP_CLASS_ITEMS:
            groups.extend(
                _geometry_groups(
                    geo,
                    concrete_class,
                    discovery_issues=discovery_issues,
                    source_key=source_key,
                )
            )
        return groups

    method_names = {
        GROUP_CLASS_POINT: "pointGroups",
        GROUP_CLASS_PRIMITIVE: "primGroups",
        GROUP_CLASS_EDGE: "edgeGroups",
    }
    method_name = method_names.get(group_class)
    if not method_name:
        return []

    try:
        method = getattr(geo, method_name)
        return list(method())
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            source_key,
            "<{0} groups>".format(group_class),
            "could not inspect groups: {0}".format(exc),
        )
        return []


def _group_names_from_geo(geo, group_class, discovery_issues=None, source_key=""):
    names = []
    for group in _geometry_groups(
        geo,
        group_class,
        discovery_issues=discovery_issues,
        source_key=source_key,
    ):
        try:
            name = group.name().strip()
        except Exception as exc:
            _append_discovery_issue(
                discovery_issues,
                source_key,
                "<{0} group>".format(_normalize_group_class(group_class)),
                "could not inspect group name: {0}".format(exc),
            )
            name = ""
        if name:
            names.append(name)
    return sorted(set(names))


def _geometry_has_item(geo, rename_kind, item_class, item_name):
    item_name = str(item_name or "").strip()
    if not item_name:
        return False

    if _normalize_rename_kind(rename_kind) == RENAME_KIND_GROUP:
        return item_name in _group_names_from_geo(geo, item_class)
    return _find_geometry_attribute(geo, item_class, item_name) is not None


def _choice_dict(rename_kind, item_class, item_name, sources):
    sources = tuple(str(source) for source in sources if source)
    return {
        "kind": _normalize_rename_kind(rename_kind),
        "class": item_class,
        "name": item_name,
        "source_count": len(sources),
        "sources": sources,
    }


def _item_choices_from_geometry_items(
    rename_kind,
    geometry_items,
    discovery_issues=None,
):
    """Merge discovered names and retain every geometry source for each choice."""
    rename_kind = _normalize_rename_kind(rename_kind)
    choices = []
    source_paths = {}
    seen_source_choices = set()

    if rename_kind == RENAME_KIND_GROUP:
        class_items = GROUP_CLASS_ITEMS
        names_from_geo = _group_names_from_geo
    else:
        class_items = ATTRIBUTE_CLASS_ITEMS
        names_from_geo = _attribute_names_from_geo

    for source_key, geo in geometry_items:
        if geo is None:
            continue

        source_key = str(source_key or id(geo))
        for item_class, _label in class_items:
            for item_name in names_from_geo(
                geo,
                item_class,
                discovery_issues=discovery_issues,
                source_key=source_key,
            ):
                choice_key = (item_class, item_name)
                source_choice = (source_key, choice_key)
                if source_choice in seen_source_choices:
                    continue

                seen_source_choices.add(source_choice)
                if choice_key not in source_paths:
                    source_paths[choice_key] = []
                    choices.append(choice_key)
                source_paths[choice_key].append(source_key)

    return [
        _choice_dict(rename_kind, item_class, item_name, source_paths.get((item_class, item_name), ()))
        for item_class, item_name in choices
    ]


def _merge_item_choices(primary_choices, extra_choices):
    merged = []
    sources_by_key = {}

    for choice in list(primary_choices or ()) + list(extra_choices or ()):
        rename_kind, item_class, item_name, _source_count, sources = _item_choice_parts(choice)
        key = (rename_kind, item_class, item_name)
        if key not in sources_by_key:
            sources_by_key[key] = []
            merged.append(key)
        for source in sources:
            source = str(source or "")
            if source and source not in sources_by_key[key]:
                sources_by_key[key].append(source)

    return [
        _choice_dict(rename_kind, item_class, item_name, sources_by_key.get((rename_kind, item_class, item_name), ()))
        for rename_kind, item_class, item_name in merged
    ]


def _group_names_from_parameter_value(value):
    names = []
    seen = set()
    for token in re.split(r"[\s,]+", str(value or "")):
        token = token.strip()
        if not token or token in ("*", "^*"):
            continue
        if token.startswith("^"):
            token = token[1:].strip()
        if not _attribute_name_is_safe(token):
            continue
        if token not in seen:
            seen.add(token)
            names.append(token)
    return names


def _group_choices_from_node_parameters(nodes):
    """Discover concrete group names from class-aware parameter fields."""
    choices = []
    source_paths = {}
    seen_sources = set()
    skipped = []

    for node in _iter_nodes_with_progress(
        nodes,
        "Scanning group parameter sources",
    ):
        node_path = _node_path(node)
        if not node_path:
            continue
        try:
            parms = node.parms()
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            _append_discovery_issue(
                skipped,
                node_path,
                "<parms>",
                "could not inspect group parameters: {0}".format(exc),
            )
            parms = []
        for parm in parms:
            field = rename_engine._plain_field_info(
                node,
                parm,
                rename_engine.RENAME_KIND_GROUP,
                node_parms=parms,
            )
            if (
                not field["editable"]
                or field["owner_metadata"]
                or not field["explicit"]
            ):
                continue
            value = _parm_string_value(parm)
            if value is None:
                _append_discovery_issue(
                    skipped,
                    node_path,
                    _parm_name(parm),
                    "could not inspect group parameter value",
                )
                continue
            parm_name = _parm_name(parm)
            source_key = "{0}/{1}".format(node_path, parm_name) if parm_name else node_path
            group_names = _group_names_from_parameter_value(value)
            if not group_names:
                continue
            group_class = (
                None if field["ambiguous_owner"] else field["owner"]
            )
            if group_class == GROUP_CLASS_UNSUPPORTED_VERTEX:
                _append_discovery_issue(
                    skipped,
                    node_path,
                    parm_name,
                    "vertex groups are not supported",
                )
                continue
            if group_class is None:
                group_class = GROUP_CLASS_ANY
            for group_name in group_names:
                choice_key = (group_class, group_name)
                source_choice = (source_key, choice_key)
                if source_choice in seen_sources:
                    continue
                seen_sources.add(source_choice)
                if choice_key not in source_paths:
                    source_paths[choice_key] = []
                    choices.append(choice_key)
                source_paths[choice_key].append(source_key)

    return [
        _choice_dict(RENAME_KIND_GROUP, group_class, group_name, source_paths.get((group_class, group_name), ()))
        for group_class, group_name in choices
    ], skipped


def _geometry_discovery_for_scope(displayed_geo=None, nodes=None, displayed_sop=None):
    """Merge displayed and scoped geometry without reporting a source twice."""
    geometry_items = []
    discovery_issues = []
    displayed_path = _node_path(displayed_sop)
    scoped_paths = set(_node_path(node) for node in _unique_nodes(nodes or ()))
    scoped_paths.discard("")
    displayed_geometry_added = (
        displayed_geo is not None and displayed_path in scoped_paths
    )

    if displayed_geometry_added:
        geometry_items.append((displayed_path or "<displayed>", displayed_geo))

    discovered_items, node_issues = _discover_geometry_items_from_nodes(nodes)
    discovery_issues.extend(node_issues)
    for source_key, geo in discovered_items:
        if displayed_geometry_added and source_key == displayed_path:
            continue
        geometry_items.append((source_key, geo))

    return geometry_items, discovery_issues


def _available_item_choices(rename_kind, displayed_geo=None, nodes=None, displayed_sop=None):
    """Discover rename candidates and the sources that exposed each name."""
    rename_kind = _normalize_rename_kind(rename_kind)
    geometry_items, discovery_issues = _geometry_discovery_for_scope(
        displayed_geo,
        nodes=nodes,
        displayed_sop=displayed_sop,
    )
    choices = _item_choices_from_geometry_items(
        rename_kind,
        geometry_items,
        discovery_issues=discovery_issues,
    )
    if rename_kind == RENAME_KIND_GROUP:
        parameter_choices, parameter_issues = _group_choices_from_node_parameters(nodes)
        discovery_issues.extend(parameter_issues)
        choices = _merge_item_choices(choices, parameter_choices)
    return choices, len(geometry_items), geometry_items, discovery_issues


def _target_item_exists(rename_kind, item_class, item_name, geometry_items, item_choices=None):
    """Check collisions only in compatible owner-class contexts."""
    for _source_key, geo in geometry_items or []:
        if _geometry_has_item(geo, rename_kind, item_class, item_name):
            return True
    normalized_kind = _normalize_rename_kind(rename_kind)
    for choice in item_choices or ():
        choice_kind, choice_class, choice_name, _source_count, _sources = _item_choice_parts(choice)
        class_matches = choice_class == item_class
        if normalized_kind == RENAME_KIND_GROUP:
            class_matches = class_matches or choice_class == GROUP_CLASS_ANY or item_class == GROUP_CLASS_ANY
        if (
            choice_kind == normalized_kind
            and class_matches
            and choice_name == item_name
        ):
            return True
    return False

def _item_choice_parts(choice):
    if isinstance(choice, dict):
        rename_kind = _normalize_rename_kind(choice.get("kind", RENAME_KIND_ATTRIBUTE))
        item_class = choice.get("class", DEFAULT_ATTRIBUTE_CLASS)
        item_name = choice.get("name", DEFAULT_ATTRIBUTE)
        try:
            source_count = int(choice.get("source_count", 1))
        except Exception:
            source_count = 1
        sources = tuple(choice.get("sources", ()))
        return rename_kind, item_class, item_name, max(source_count, 1), sources

    try:
        if len(choice) >= 5:
            rename_kind = _normalize_rename_kind(choice[0])
            return rename_kind, choice[1], choice[2], max(int(choice[3]), 1), tuple(choice[4] or ())
    except Exception:
        pass

    try:
        item_class = choice[0]
        item_name = choice[1]
    except Exception:
        return RENAME_KIND_ATTRIBUTE, DEFAULT_ATTRIBUTE_CLASS, DEFAULT_ATTRIBUTE, 1, ()

    try:
        source_count = int(choice[2])
    except Exception:
        source_count = 1

    return RENAME_KIND_ATTRIBUTE, item_class, item_name, max(source_count, 1), ()


def _item_choice_key(choice):
    rename_kind, item_class, item_name, _source_count, _sources = _item_choice_parts(choice)
    return rename_kind, item_class, item_name


def _choice_matches_attribute_search(choice, search_text):
    search_text = str(search_text or "").strip().lower()
    if not search_text:
        return True

    _rename_kind, _item_class, item_name, _source_count, _sources = _item_choice_parts(choice)
    return search_text in str(item_name).lower()


# ---------------------------------------------------------------------------
# PySide compatibility helpers
# ---------------------------------------------------------------------------


def _qt_enum(owner, enum_name, member_name):
    value = getattr(owner, member_name, None)
    if value is None:
        value = getattr(getattr(owner, enum_name), member_name)
    return value


def _configure_qt_dialog(dialog, QtCore, nonmodal=False):
    if nonmodal:
        dialog.setModal(False)
        try:
            dialog.setWindowModality(
                _qt_enum(QtCore.Qt, "WindowModality", "NonModal")
            )
        except Exception:
            pass
    try:
        dialog.setWindowFlags(
            dialog.windowFlags()
            ^ _qt_enum(
                QtCore.Qt,
                "WindowType",
                "WindowContextHelpButtonHint",
            )
        )
    except Exception:
        pass


def _qt_main_window():
    try:
        return hou.qt.mainWindow()
    except Exception:
        return None


def _focus_qt_dialog(dialog):
    for method_name in ("raise_", "activateWindow"):
        try:
            getattr(dialog, method_name)()
        except Exception:
            pass


def _show_qt_dialog(dialog):
    dialog.show()
    _focus_qt_dialog(dialog)


def _delete_qt_later(dialog):
    try:
        dialog.deleteLater()
    except Exception:
        pass


def _resize_qt_dialog(dialog, QtWidgets, width, height):
    maximum_width = None
    maximum_height = None
    screens = []
    try:
        screens.append(dialog.screen())
    except Exception:
        pass
    try:
        screens.append(QtWidgets.QApplication.primaryScreen())
    except Exception:
        pass

    for screen in screens:
        if screen is None:
            continue
        try:
            geometry = screen.availableGeometry()
            available_width = int(geometry.width())
            available_height = int(geometry.height())
        except Exception:
            continue
        if available_width > 0 and available_height > 0:
            maximum_width = max(int(available_width * 0.9), 1)
            maximum_height = max(int(available_height * 0.9), 1)
            break

    try:
        minimum_width = max(int(dialog.minimumWidth()), 0)
    except Exception:
        minimum_width = 0
    try:
        minimum_height = max(int(dialog.minimumHeight()), 0)
    except Exception:
        minimum_height = 0

    target_width = int(width)
    target_height = int(height)
    if maximum_width is not None:
        target_width = min(target_width, maximum_width)
    if maximum_height is not None:
        target_height = min(target_height, maximum_height)
    target_width = max(target_width, minimum_width)
    target_height = max(target_height, minimum_height)
    try:
        dialog.resize(target_width, target_height)
    except Exception:
        pass


def _configure_readonly_table(
    table,
    QtCore,
    QtWidgets,
    selection_mode="ExtendedSelection",
    vertical_scroll=True,
):
    table.setWordWrap(False)
    table.setTextElideMode(
        _qt_enum(QtCore.Qt, "TextElideMode", "ElideNone")
    )
    scrollbar_policy = _qt_enum(
        QtCore.Qt, "ScrollBarPolicy", "ScrollBarAsNeeded"
    )
    table.setHorizontalScrollBarPolicy(scrollbar_policy)
    if vertical_scroll:
        table.setVerticalScrollBarPolicy(scrollbar_policy)
    view = QtWidgets.QAbstractItemView
    table.setSelectionBehavior(
        _qt_enum(view, "SelectionBehavior", "SelectRows")
    )
    table.setSelectionMode(
        _qt_enum(view, "SelectionMode", selection_mode)
    )
    table.setEditTriggers(
        _qt_enum(view, "EditTrigger", "NoEditTriggers")
    )


# ---------------------------------------------------------------------------
# Scope graph traversal and locked-asset boundaries
# ---------------------------------------------------------------------------


def _node_path(node):
    if node is None:
        return ""

    try:
        return node.path()
    except Exception:
        return ""

def _node_type_name(node):
    try:
        return node.type().name().lower()
    except Exception:
        return ""

def _node_is_wrangle_wrapper(node):
    return "wrangle" in _node_type_name(node)

def _nearest_wrangle_origin_node(node):
    """Map an internal wrangle implementation node to its visible wrapper."""
    current = node
    seen_paths = set()

    while current is not None:
        current_path = _node_path(current)
        if current_path:
            if current_path in seen_paths:
                break
            seen_paths.add(current_path)

        if _node_is_wrangle_wrapper(current):
            return current

        try:
            current = current.parent()
        except Exception:
            break

    return None

def _canonical_origin_node(node):
    """Return the stable user-facing node used for scope traversal."""
    wrangle_node = _nearest_wrangle_origin_node(node)
    if wrangle_node is not None:
        return wrangle_node
    return node

def _origin_traversal_nodes(node):
    """Return concrete dataflow nodes represented by one visible origin."""
    if node is None:
        return []

    node = _canonical_origin_node(node)
    if node is None:
        return []
    return [node]

def _origin_dataflow_inputs(node, discovery_issues=None):
    """Collect unique inputs across a visible node and its implementation."""
    node = _canonical_origin_node(node)
    if node is None:
        return []

    raw_inputs = _node_inputs(node, discovery_issues)

    inputs = []
    seen_paths = set()
    for input_node in raw_inputs:
        for traversal_node in _origin_traversal_nodes(input_node):
            node_path = _node_path(traversal_node)
            if not node_path or node_path in seen_paths:
                continue
            seen_paths.add(node_path)
            inputs.append(traversal_node)
    return inputs

def _iter_upstream_nodes_with_depth(source_sop, discovery_issues=None):
    """Traverse upstream breadth-first while retaining deterministic depth."""
    if source_sop is None:
        return []

    seen_paths = set()
    order = 0
    queue = deque()
    for node in _origin_traversal_nodes(source_sop):
        queue.append((node, 0, order))
        order += 1
    upstream_nodes = []

    while queue:
        node, depth, visit_order = queue.popleft()
        node = _canonical_origin_node(node)
        node_path = _node_path(node)
        if not node_path or node_path in seen_paths:
            continue

        seen_paths.add(node_path)
        upstream_nodes.append((node, depth, visit_order, node_path))

        for input_node in _origin_dataflow_inputs(node, discovery_issues):
            queue.append((input_node, depth + 1, order))
            order += 1

    return upstream_nodes

def _node_outputs(node, discovery_issues=None):
    if node is None:
        return []

    for method_name in ("outputsFollowingInputs", "outputs"):
        method = getattr(node, method_name, None)
        if method is None:
            continue

        try:
            return [output_node for output_node in method() if output_node is not None]
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            _append_discovery_issue(
                discovery_issues,
                _node_path(node),
                "<outputs>",
                "could not inspect output connections with {0}: {1}".format(
                    method_name,
                    exc,
                ),
            )
            continue

    return []

def _iter_downstream_nodes_with_depth(source_sop, discovery_issues=None):
    """Traverse downstream breadth-first through visible dataflow origins."""
    if source_sop is None:
        return []

    seen_paths = set()
    order = 0
    queue = deque([(source_sop, 0, order)])
    downstream_nodes = []

    while queue:
        node, depth, visit_order = queue.popleft()
        node_path = _node_path(node)
        if not node_path or node_path in seen_paths:
            continue

        seen_paths.add(node_path)
        downstream_nodes.append((node, depth, visit_order, node_path))

        for output_node in _node_outputs(node, discovery_issues):
            order += 1
            queue.append((output_node, depth + 1, order))

    return downstream_nodes

def _node_children(node, discovery_issues=None):
    if node is None:
        return []

    try:
        return [child for child in node.children() if child is not None]
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<children>",
            "could not inspect internal nodes: {0}".format(exc),
        )
        return []

def _node_allows_internal_scan(node, discovery_issues=None):
    if node is None:
        return None

    method = getattr(node, "isLockedHDA", None)
    if method is None:
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<internals>",
            "could not verify whether node internals are locked; internals were not entered",
        )
        return None

    try:
        if method():
            return False
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<internals>",
            "could not verify whether node internals are locked; internals were not entered: {0}".format(
                exc
            ),
        )
        return None

    return True


def _node_is_editable_inside_locked_hda(node, discovery_issues=None):
    if node is None:
        return None

    method = getattr(node, "isEditableInsideLockedHDA", None)
    if method is None:
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<internals>",
            "could not verify whether locked-asset internals are editable; "
            "this branch was not entered",
        )
        return None
    try:
        return bool(method())
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<internals>",
            "could not verify whether locked-asset internals are editable; "
            "this branch was not entered: {0}".format(exc),
        )
        return None


def _editable_descendants_of_locked_hda(node, discovery_issues=None):
    """Return only editable islands exposed inside a locked asset."""
    editable = []
    seen_paths = set()
    queue = deque(_node_children(node, discovery_issues))
    while queue:
        child = queue.popleft()
        child_path = _node_path(child)
        if not child_path or child_path in seen_paths:
            continue
        seen_paths.add(child_path)
        editable_state = _node_is_editable_inside_locked_hda(
            child,
            discovery_issues,
        )
        if editable_state is True:
            editable.append(child)
            continue
        if editable_state is None:
            continue
        queue.extend(_node_children(child, discovery_issues))
    return editable

def _unique_nodes(nodes):
    unique_nodes = []
    seen_paths = set()
    for node in nodes:
        node_path = _node_path(node)
        if not node_path or node_path in seen_paths:
            continue
        seen_paths.add(node_path)
        unique_nodes.append(node)
    return unique_nodes

def _expand_nodes_with_internals(nodes, discovery_issues=None):
    """Expand scope through editable internals without entering locked details."""
    expanded = []
    seen_paths = set()
    queue = deque(nodes)

    while queue:
        node = queue.popleft()
        node_path = _node_path(node)
        if not node_path or node_path in seen_paths:
            continue

        seen_paths.add(node_path)
        expanded.append(node)

        internal_scan_state = _node_allows_internal_scan(
            node,
            discovery_issues,
        )
        if internal_scan_state is None:
            continue
        if internal_scan_state is False:
            queue.extend(
                _editable_descendants_of_locked_hda(
                    node,
                    discovery_issues,
                )
            )
            continue

        queue.extend(_node_children(node, discovery_issues))

    return expanded

def _nodes_from_tuples(node_tuples):
    return _unique_nodes(item[0] for item in node_tuples if item)


def _whole_hip_surface_nodes(discovery_issues=None):
    """Collect the editable node surface of the current Houdini scene."""
    try:
        root = hou.node("/")
    except Exception as exc:
        if _operation_interrupted(exc):
            raise
        _append_discovery_issue(
            discovery_issues,
            "/",
            "<root>",
            "could not inspect the HIP root: {0}".format(exc),
        )
        return []
    if root is None:
        _append_discovery_issue(
            discovery_issues,
            "/",
            "<root>",
            "could not find the HIP root",
        )
        return []

    nodes = []
    for context_node in _node_children(root, discovery_issues):
        children = _node_children(context_node, discovery_issues)
        if children:
            nodes.extend(children)
        else:
            nodes.append(context_node)
    return _unique_nodes(nodes)

# ---------------------------------------------------------------------------
# Scope options and non-modal dialog state
# ---------------------------------------------------------------------------


def _default_rename_scope_options():
    return {
        "target": SCOPE_TARGET_SELECTED_NODES,
        "rename_kind": _rename_kind(),
        "include_internals": False,
        "include_upstream": False,
        "include_downstream": False,
        "rename_vex": True,
        "rename_python": True,
        "aggressive_vex": bool(
            getattr(hou.session, SESSION_AGGRESSIVE_VEX_NAME, False)
        ),
    }


def _normalize_rename_scope_options(scope):
    """Normalize persisted scope settings into one complete option mapping."""
    options = _default_rename_scope_options()
    scope = scope if isinstance(scope, dict) else {}
    target = scope.get("target", options["target"])
    if target not in {value for value, _label in SCOPE_TARGET_ITEMS}:
        target = options["target"]

    options["target"] = target
    options["rename_kind"] = _normalize_rename_kind(
        scope.get("rename_kind", options["rename_kind"])
    )
    options["include_internals"] = bool(scope.get("include_internals", False))
    options["include_upstream"] = bool(scope.get("include_upstream", False))
    options["include_downstream"] = bool(scope.get("include_downstream", False))
    options["rename_vex"] = bool(scope.get("rename_vex", True))
    options["rename_python"] = bool(scope.get("rename_python", True))
    options["aggressive_vex"] = bool(scope.get("aggressive_vex", False))
    if not options["rename_vex"]:
        options["aggressive_vex"] = False
    if target == SCOPE_TARGET_WHOLE_HIP:
        options["include_internals"] = True
        options["include_upstream"] = False
        options["include_downstream"] = False
    return options


def _stored_rename_scope_options():
    options = getattr(hou.session, SESSION_SCOPE_OPTIONS_NAME, None)
    if isinstance(options, dict):
        return _normalize_rename_scope_options(options)
    return _normalize_rename_scope_options(_default_rename_scope_options())


def _set_stored_rename_scope_options(options):
    normalized = _normalize_rename_scope_options(options)
    setattr(hou.session, SESSION_SCOPE_OPTIONS_NAME, normalized)
    setattr(
        hou.session,
        SESSION_AGGRESSIVE_VEX_NAME,
        bool(normalized.get("aggressive_vex", False)),
    )


def _scope_label(scope):
    options = _normalize_rename_scope_options(scope)
    target = options.get("target", SCOPE_TARGET_SELECTED_NODES)
    if target == SCOPE_TARGET_WHOLE_HIP:
        return SCOPE_ALL_NODES_LABEL

    parts = []
    if options.get("include_upstream"):
        parts.append("Upstream")
    if options.get("include_downstream"):
        parts.append("Downstream")
    if options.get("include_internals"):
        parts.append("Inside")

    label = "Selected Nodes"
    if parts:
        label = "{0} ({1})".format(label, " + ".join(parts))
    return label


def _stored_rename_scope_dialog():
    return getattr(hou.session, SESSION_SCOPE_DIALOG_NAME, None)


def _set_stored_rename_scope_dialog(dialog):
    setattr(hou.session, SESSION_SCOPE_DIALOG_NAME, dialog)


def _clear_stored_rename_scope_dialog(dialog=None):
    current_dialog = _stored_rename_scope_dialog()
    if dialog is not None and current_dialog is not dialog:
        return
    setattr(hou.session, SESSION_SCOPE_DIALOG_NAME, None)


def _focus_existing_rename_scope_dialog():
    dialog = _stored_rename_scope_dialog()
    if dialog is None:
        return False

    try:
        visible = dialog.isVisible()
    except Exception:
        _clear_stored_rename_scope_dialog(dialog)
        return False

    if not visible:
        _clear_stored_rename_scope_dialog(dialog)
        return False

    _focus_qt_dialog(dialog)
    return True


def _open_rename_scope_dialog(on_accept):
    """Show the reusable non-modal scope dialog and continue through a callback."""
    if _focus_existing_rename_scope_dialog():
        return True

    from hutil.Qt import QtCore, QtWidgets

    class RenameScopeDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(RenameScopeDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            _configure_qt_dialog(self, QtCore, nonmodal=True)

            layout = QtWidgets.QVBoxLayout()

            kind_layout = QtWidgets.QHBoxLayout()
            kind_label = QtWidgets.QLabel("Rename")
            self.kind_combo = QtWidgets.QComboBox()
            for _value, label in RENAME_KIND_ITEMS:
                self.kind_combo.addItem(label)
            kind_layout.addWidget(kind_label)
            kind_layout.addWidget(self.kind_combo, 1)
            layout.addLayout(kind_layout)

            target_layout = QtWidgets.QHBoxLayout()
            target_label = QtWidgets.QLabel("Search")
            self.target_combo = QtWidgets.QComboBox()
            for _value, label in SCOPE_TARGET_ITEMS:
                self.target_combo.addItem(label)
            target_layout.addWidget(target_label)
            target_layout.addWidget(self.target_combo, 1)
            layout.addLayout(target_layout)

            self.selected_nodes_group = QtWidgets.QGroupBox("Selected Nodes")
            selected_nodes_layout = QtWidgets.QVBoxLayout()
            self.upstream_check = QtWidgets.QCheckBox("Upstream")
            self.downstream_check = QtWidgets.QCheckBox("Downstream")
            self.include_internals_check = QtWidgets.QCheckBox("Inside Nodes")
            selected_nodes_layout.addWidget(self.upstream_check)
            selected_nodes_layout.addWidget(self.downstream_check)
            selected_nodes_layout.addWidget(self.include_internals_check)
            self.selected_nodes_group.setLayout(selected_nodes_layout)
            layout.addWidget(self.selected_nodes_group)

            self.code_group = QtWidgets.QGroupBox("Code Parameters")
            code_layout = QtWidgets.QVBoxLayout()
            self.rename_vex_check = QtWidgets.QCheckBox("Rename in VEX")
            self.rename_python_check = QtWidgets.QCheckBox("Rename in Python")
            self.aggressive_vex_check = QtWidgets.QCheckBox("Aggressive VEX Strings")
            self.aggressive_vex_check.setToolTip(
                "Also rename exact matching VEX string literals outside known attribute or group functions."
            )
            self.rename_vex_check.setChecked(True)
            self.rename_python_check.setChecked(True)
            code_layout.addWidget(self.rename_vex_check)
            code_layout.addWidget(self.rename_python_check)
            code_layout.addWidget(self.aggressive_vex_check)
            self.code_group.setLayout(code_layout)
            layout.addWidget(self.code_group)

            ok_button = getattr(QtWidgets.QDialogButtonBox, "Ok", None)
            cancel_button = getattr(QtWidgets.QDialogButtonBox, "Cancel", None)
            if ok_button is None:
                ok_button = QtWidgets.QDialogButtonBox.StandardButton.Ok
            if cancel_button is None:
                cancel_button = QtWidgets.QDialogButtonBox.StandardButton.Cancel

            buttons = QtWidgets.QDialogButtonBox(ok_button | cancel_button)
            try:
                next_button = buttons.button(ok_button)
                if next_button is not None:
                    next_button.setText("Next")
            except Exception:
                pass
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

            self._apply_initial_options(_stored_rename_scope_options())
            self.setLayout(layout)
            self.setMinimumWidth(390)
            _resize_qt_dialog(self, QtWidgets, 520, 400)
            self.target_combo.currentIndexChanged.connect(self._update_scope_controls)
            self.rename_vex_check.toggled.connect(self._update_code_controls)
            self._update_scope_controls()
            self._update_code_controls()

        def _target(self):
            index = self.target_combo.currentIndex()
            if index < 0 or index >= len(SCOPE_TARGET_ITEMS):
                return SCOPE_TARGET_SELECTED_NODES
            return SCOPE_TARGET_ITEMS[index][0]

        def _rename_kind(self):
            index = self.kind_combo.currentIndex()
            if index < 0 or index >= len(RENAME_KIND_ITEMS):
                return RENAME_KIND_ATTRIBUTE
            return RENAME_KIND_ITEMS[index][0]

        def _apply_initial_options(self, options):
            options = _normalize_rename_scope_options(options)
            target = options.get("target", SCOPE_TARGET_SELECTED_NODES)
            rename_kind = _normalize_rename_kind(options.get("rename_kind", RENAME_KIND_ATTRIBUTE))
            try:
                target_index = tuple(
                    value for value, _label in SCOPE_TARGET_ITEMS
                ).index(target)
            except ValueError:
                target_index = 0
            try:
                kind_index = tuple(
                    value for value, _label in RENAME_KIND_ITEMS
                ).index(rename_kind)
            except ValueError:
                kind_index = 0

            self.kind_combo.setCurrentIndex(kind_index)
            self.target_combo.setCurrentIndex(target_index)
            self.upstream_check.setChecked(bool(options.get("include_upstream", False)))
            self.downstream_check.setChecked(bool(options.get("include_downstream", False)))
            self.include_internals_check.setChecked(bool(options.get("include_internals", False)))
            self.rename_vex_check.setChecked(bool(options.get("rename_vex", True)))
            self.rename_python_check.setChecked(bool(options.get("rename_python", True)))
            self.aggressive_vex_check.setChecked(bool(options.get("aggressive_vex", False)))
            if target == SCOPE_TARGET_WHOLE_HIP:
                self.include_internals_check.setChecked(True)

        def _update_scope_controls(self):
            is_selected_nodes = self._target() == SCOPE_TARGET_SELECTED_NODES
            self.selected_nodes_group.setVisible(is_selected_nodes)
            self.selected_nodes_group.setEnabled(is_selected_nodes)
            if not is_selected_nodes:
                self.upstream_check.setChecked(False)
                self.downstream_check.setChecked(False)
                self.include_internals_check.setChecked(True)

        def _update_code_controls(self, *_args):
            enabled = self.rename_vex_check.isChecked()
            self.aggressive_vex_check.setEnabled(enabled)
            if not enabled:
                self.aggressive_vex_check.setChecked(False)

        def scope_options(self):
            target = self._target()
            return _normalize_rename_scope_options({
                "target": target,
                "rename_kind": self._rename_kind(),
                "include_internals": self.include_internals_check.isChecked(),
                "include_upstream": self.upstream_check.isChecked(),
                "include_downstream": self.downstream_check.isChecked(),
                "rename_vex": self.rename_vex_check.isChecked(),
                "rename_python": self.rename_python_check.isChecked(),
                "aggressive_vex": self.aggressive_vex_check.isChecked(),
            })

    dialog = RenameScopeDialog(_qt_main_window())
    # The session reference keeps the non-modal dialog alive until its
    # finished callback releases it.
    _set_stored_rename_scope_dialog(dialog)

    def _finished(_result=None):
        _clear_stored_rename_scope_dialog(dialog)
        _delete_qt_later(dialog)

    def _accepted():
        scope_options = dialog.scope_options()
        _set_stored_rename_scope_options(scope_options)
        _set_rename_kind(scope_options.get("rename_kind", RENAME_KIND_ATTRIBUTE))
        _clear_stored_rename_scope_dialog(dialog)
        try:
            on_accept(scope_options)
        except Exception as exc:
            _show_attribute_rename_warning(
                "Rename failed: {0}".format(exc)
            )

    dialog.accepted.connect(_accepted)
    dialog.finished.connect(_finished)
    _show_qt_dialog(dialog)
    return True


def _choose_rename_scope_fallback():
    labels = [label for _value, label in SCOPE_TARGET_ITEMS]
    try:
        selection = hou.ui.selectFromList(
            labels,
            default_choices=(0,),
            exclusive=True,
            message="Choose where to search for references to rename.",
            title=RENAME_TITLE,
            column_header="Rename Scope",
            clear_on_cancel=True,
            sort=False,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open rename scope picker: {0}".format(exc)
        )
        return None

    if not selection:
        return None

    index = selection[0]
    if index < 0 or index >= len(SCOPE_TARGET_ITEMS):
        _show_attribute_rename_warning("Rename scope selection is out of range.")
        return None

    return _normalize_rename_scope_options({
        "target": SCOPE_TARGET_ITEMS[index][0],
    })


def _choose_rename_scope():
    scope_options = _choose_rename_scope_fallback()
    if scope_options is not None:
        _set_stored_rename_scope_options(scope_options)
        _set_rename_kind(scope_options.get("rename_kind", RENAME_KIND_ATTRIBUTE))
    return scope_options


def _nodes_from_selected_scope_nodes(
    base_nodes,
    include_upstream=False,
    include_downstream=False,
    discovery_issues=None,
):
    """Expand selected nodes through the requested dataflow directions."""
    nodes = list(base_nodes)
    if include_upstream:
        for node in base_nodes:
            nodes.extend(
                _nodes_from_tuples(
                    _iter_upstream_nodes_with_depth(node, discovery_issues)
                )
            )
    if include_downstream:
        for node in base_nodes:
            nodes.extend(
                _nodes_from_tuples(
                    _iter_downstream_nodes_with_depth(node, discovery_issues)
                )
            )
    return _unique_nodes(nodes)


def _nodes_for_rename_scope_with_issues(scope, source_sop=None, scene_viewer=None):
    """Resolve one scope while preserving recoverable traversal problems."""
    options = _normalize_rename_scope_options(scope)
    target = options.get("target", SCOPE_TARGET_SELECTED_NODES)
    discovery_issues = []

    if target == SCOPE_TARGET_SELECTED_NODES:
        selected_nodes, selection_warning = _selected_nodes_with_warning()
        if selection_warning:
            return [], selection_warning, discovery_issues
        nodes = _nodes_from_selected_scope_nodes(
            selected_nodes,
            include_upstream=options.get("include_upstream", False),
            include_downstream=options.get("include_downstream", False),
            discovery_issues=discovery_issues,
        )
    elif target == SCOPE_TARGET_WHOLE_HIP:
        nodes = _whole_hip_surface_nodes(discovery_issues)
    else:
        return [], "Unknown rename scope: {0}".format(target), discovery_issues

    if options.get("include_internals"):
        nodes = _expand_nodes_with_internals(nodes, discovery_issues)
    return _unique_nodes(nodes), None, discovery_issues


def _stored_item_dialog():
    return getattr(hou.session, SESSION_ITEM_DIALOG_NAME, None)


def _set_stored_item_dialog(dialog):
    setattr(hou.session, SESSION_ITEM_DIALOG_NAME, dialog)


def _clear_stored_item_dialog(dialog=None):
    current_dialog = _stored_item_dialog()
    if dialog is not None and current_dialog is not dialog:
        return
    setattr(hou.session, SESSION_ITEM_DIALOG_NAME, None)


def _retire_stored_item_dialog():
    """Close an earlier browser without relying on its reloaded class."""
    dialog = _stored_item_dialog()
    if dialog is None:
        return

    _clear_stored_item_dialog(dialog)
    try:
        close_locations = getattr(dialog, "_close_locations_dialog", None)
        if close_locations is not None:
            close_locations()
    except Exception:
        pass

    for method_name in ("reject", "close", "hide"):
        try:
            getattr(dialog, method_name)()
            break
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Rename context, location cache, and item browser
# ---------------------------------------------------------------------------


def _build_rename_context(scope, scene_viewer=None):
    """Build the immutable inputs and stable metadata used by item browsing."""
    source_sop, geo = _displayed_sop_and_geometry(
        scene_viewer,
        cook_geometry=False,
    )
    nodes, scope_warning, scope_issues = _nodes_for_rename_scope_with_issues(
        scope,
        source_sop,
        scene_viewer,
    )
    if scope_warning:
        return {"warning": scope_warning}

    rename_kind = _normalize_rename_kind(scope.get("rename_kind", RENAME_KIND_ATTRIBUTE))
    try:
        choices, geometry_source_count, geometry_items, discovery_issues = _available_item_choices(
            rename_kind,
            geo,
            nodes=nodes,
            displayed_sop=source_sop,
        )
        discovery_issues = list(scope_issues) + list(discovery_issues)
    except Exception as exc:
        if _operation_interrupted(exc):
            return {"warning": "Rename scan canceled; no parameters were changed."}
        raise
    return {
        "scope": scope,
        "nodes": nodes,
        "choices": choices,
        "geometry_source_count": geometry_source_count,
        "geometry_items": geometry_items,
        "discovery_issues": discovery_issues,
        "scope_label": _scope_label(scope),
        "rename_kind": rename_kind,
    }


def _empty_rename_context(scope):
    scope = _normalize_rename_scope_options(scope)
    return {
        "scope": scope,
        "nodes": (),
        "choices": (),
        "geometry_source_count": 0,
        "geometry_items": (),
        "discovery_issues": (),
        "scope_label": _scope_label(scope),
        "rename_kind": scope["rename_kind"],
    }


def _rename_location_count_label(result):
    if result is None:
        return "Not scanned"
    count = len(result.get("locations", ()))
    return "{0} node{1}".format(count, "" if count == 1 else "s")


def _rename_location_result_is_zero(result):
    return result is not None and not bool(result.get("locations", ()))


def _rename_choice_is_hidden_by_location_cache(choice, location_cache):
    result = (location_cache or {}).get(_item_choice_key(choice))
    return _rename_location_result_is_zero(result)


def _rename_location_cache_is_complete(choices, location_cache):
    location_cache = location_cache or {}
    return all(_item_choice_key(choice) in location_cache for choice in choices or ())


def _zero_rename_locations_status(choice, result):
    rename_kind, item_class, item_name, _source_count, _sources = (
        _item_choice_parts(choice)
    )
    message = "No safe rename locations were found for {0} {1} '{2}'.".format(
        _item_class_label(rename_kind, item_class),
        _rename_kind_label_singular(rename_kind),
        item_name,
    )
    skipped_count = len((result or {}).get("skipped", ()))
    if skipped_count:
        message += " {0} reference{1} {2} skipped by safety checks.".format(
            skipped_count,
            "" if skipped_count == 1 else "s",
            "was" if skipped_count == 1 else "were",
        )
    return message


def _no_safe_rename_locations_message(rename_kind, scope_label, can_refresh):
    message = "No {0} with safe rename locations were found in {1}.".format(
        _rename_kind_label_plural_lower(rename_kind),
        scope_label or "the selected scope",
    )
    if can_refresh:
        message += " Select different nodes and click Refresh From Current Selection."
    else:
        message += " Go Back to choose a different scope."
    return message


def _open_rename_locations_dialog(parent, choice, result):
    """Show stable node paths from a completed read-only location scan."""
    from hutil.Qt import QtCore, QtWidgets

    rename_kind, item_class, item_name, _source_count, _sources = _item_choice_parts(choice)
    locations = list(result.get("locations", ()))
    skipped = list(result.get("skipped", ()))
    discovery_issues = list(result.get("discovery_issues", ()))
    edit_count = sum(int(location.get("edit_count", 0)) for location in locations)

    class RenameLocationsDialog(QtWidgets.QDialog):
        def __init__(self, dialog_parent=None):
            super(RenameLocationsDialog, self).__init__(dialog_parent)
            self.setWindowTitle("{0} Rename Locations".format(
                _rename_kind_label_singular(rename_kind).title()
            ))
            _configure_qt_dialog(self, QtCore, nonmodal=True)

            layout = QtWidgets.QVBoxLayout()
            summary = QtWidgets.QLabel(
                "Potential rename locations for {0} {1} '{2}': "
                "{3} matching node{4}, {5} parameter edit{6}.".format(
                    _item_class_label(rename_kind, item_class),
                    _rename_kind_label_singular(rename_kind),
                    item_name,
                    len(locations),
                    "" if len(locations) == 1 else "s",
                    edit_count,
                    "" if edit_count == 1 else "s",
                )
            )
            summary.setWordWrap(True)
            layout.addWidget(summary)

            self.table = QtWidgets.QTableWidget(len(locations), 3)
            self.table.setHorizontalHeaderLabels(("Node", "Parameters", "Find"))
            _configure_readonly_table(self.table, QtCore, QtWidgets)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 470)
            self.table.setColumnWidth(1, 290)
            self.table.setColumnWidth(2, 72)

            for row, location in enumerate(locations):
                node_path = str(location.get("node_path", ""))
                parm_names = ", ".join(location.get("parm_names", ()))
                self.table.setItem(row, 0, _make_table_item(QtWidgets, node_path, node_path))
                self.table.setItem(row, 1, _make_table_item(QtWidgets, parm_names, parm_names))

                find_button = QtWidgets.QPushButton("Find")
                find_button.setToolTip("Select and focus this node in the Network Editor.")
                find_button.clicked.connect(
                    lambda _checked=False, path=node_path: _focus_rename_node_paths((path,))
                )
                self.table.setCellWidget(row, 2, find_button)

            self.table.cellDoubleClicked.connect(self._find_row)
            if locations:
                self.table.selectRow(0)
            layout.addWidget(self.table, 1)

            status_text = ""
            if not locations:
                status_text = "No safe rename locations were found with the current options."
            elif skipped:
                if len(skipped) == 1:
                    status_text = "1 reference was skipped by safety checks."
                else:
                    status_text = "{0} references were skipped by safety checks.".format(
                        len(skipped)
                    )
            if discovery_issues:
                issue_text = "{0} discovery issue{1} occurred while building this list.".format(
                    len(discovery_issues),
                    "" if len(discovery_issues) == 1 else "s",
                )
                status_text = "{0} {1}".format(status_text, issue_text).strip()
            self.status_label = QtWidgets.QLabel(status_text)
            self.status_label.setWordWrap(True)
            self.status_label.setVisible(bool(status_text))
            layout.addWidget(self.status_label)

            button_layout = QtWidgets.QHBoxLayout()
            self.select_and_frame_button = QtWidgets.QPushButton("Select and Frame")
            self.select_and_frame_button.setEnabled(bool(locations))
            self.close_button = QtWidgets.QPushButton("Close")
            button_layout.addWidget(self.select_and_frame_button)
            button_layout.addStretch(1)
            button_layout.addWidget(self.close_button)
            layout.addLayout(button_layout)

            self.select_and_frame_button.clicked.connect(self._select_and_frame)
            self.close_button.clicked.connect(self.close)
            self.setLayout(layout)
            self.setMinimumSize(820, 390)
            _resize_qt_dialog(self, QtWidgets, 1050, 600)

        def _selected_paths(self):
            rows = []
            try:
                selection_model = self.table.selectionModel()
                if selection_model is not None:
                    rows = sorted(index.row() for index in selection_model.selectedRows())
            except Exception:
                rows = []
            if not rows and self.table.currentRow() >= 0:
                rows = [self.table.currentRow()]
            return tuple(
                locations[row].get("node_path", "")
                for row in rows
                if 0 <= row < len(locations)
            )

        def _select_and_frame(self):
            paths = self._selected_paths()
            if not paths:
                self.status_label.setText("Select one or more matching nodes.")
                self.status_label.show()
                return
            _focus_rename_node_paths(paths)

        def _find_row(self, row, _column):
            if 0 <= row < len(locations):
                _focus_rename_node_paths((locations[row].get("node_path", ""),))

    dialog = RenameLocationsDialog(parent)
    _show_qt_dialog(dialog)
    return dialog


# ---------------------------------------------------------------------------
# Searchable item selection and replacement-name validation
# ---------------------------------------------------------------------------


def _open_item_choice_dialog(scope, scene_viewer, on_choose, on_back, initial_context=None):
    """Show the searchable candidate browser without blocking viewport work."""
    _retire_stored_item_dialog()

    from hutil.Qt import QtCore, QtWidgets

    refresh_from_current_selection = (
        _normalize_rename_scope_options(scope).get("target")
        == SCOPE_TARGET_SELECTED_NODES
    )

    class ItemChoiceDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(ItemChoiceDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            _configure_qt_dialog(self, QtCore, nonmodal=True)

            self._context = None
            self._choices = []
            self._visible_indexes = []
            self._location_cache = {}
            self._locations_dialog = None
            self._user_role = _qt_enum(
                QtCore.Qt, "ItemDataRole", "UserRole"
            )

            layout = QtWidgets.QVBoxLayout()
            self.message_label = QtWidgets.QLabel("")
            self.message_label.setWordWrap(True)
            layout.addWidget(self.message_label)

            search_layout = QtWidgets.QHBoxLayout()
            self.search_edit = QtWidgets.QLineEdit()
            self.search_edit.setPlaceholderText("Name")
            self.search_button = QtWidgets.QPushButton("Search")
            self.refresh_button = QtWidgets.QPushButton("Refresh From Current Selection")
            self.refresh_button.setVisible(refresh_from_current_selection)
            search_layout.addWidget(self.search_edit, 1)
            search_layout.addWidget(self.search_button)
            search_layout.addWidget(self.refresh_button)
            layout.addLayout(search_layout)

            self.table = QtWidgets.QTableWidget(0, 3)
            self.table.setHorizontalHeaderLabels(("Name", "Matching Nodes", "Locations"))
            _configure_readonly_table(
                self.table,
                QtCore,
                QtWidgets,
                selection_mode="SingleSelection",
                vertical_scroll=False,
            )
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 360)
            self.table.setColumnWidth(1, 130)
            self.table.setColumnWidth(2, 190)
            layout.addWidget(self.table, 1)

            self.status_label = QtWidgets.QLabel("")
            self.status_label.setWordWrap(True)
            self.status_label.setStyleSheet("color: #ff9a9a;")
            self.status_label.hide()
            layout.addWidget(self.status_label)

            button_layout = QtWidgets.QHBoxLayout()
            self.back_button = QtWidgets.QPushButton("Back")
            button_layout.addWidget(self.back_button)
            button_layout.addStretch(1)
            self.choose_button = QtWidgets.QPushButton("Choose")
            self.cancel_button = QtWidgets.QPushButton("Cancel")
            self.choose_button.setDefault(True)
            button_layout.addWidget(self.choose_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            self.setLayout(layout)
            self.setMinimumSize(820, 460)
            _resize_qt_dialog(self, QtWidgets, 1050, 650)

            self.search_button.clicked.connect(self._apply_filter)
            self.search_edit.returnPressed.connect(self._apply_filter)
            self.refresh_button.clicked.connect(self._refresh_from_scope)
            self.choose_button.clicked.connect(self._choose)
            self.cancel_button.clicked.connect(self.reject)
            self.back_button.clicked.connect(self._back)
            self.table.cellDoubleClicked.connect(lambda _row, _col: self._choose())
            if initial_context:
                location_cache = dict(initial_context.get("location_cache", {}))
                self._set_context(initial_context, location_cache)
            else:
                self._refresh_from_scope()

        def _show_status(self, message):
            self.status_label.setText(message)
            self.status_label.show()

        def _clear_status(self):
            self.status_label.clear()
            self.status_label.hide()

        def _close_locations_dialog(self):
            dialog = self._locations_dialog
            self._locations_dialog = None
            if dialog is None:
                return
            try:
                dialog.close()
            except Exception:
                pass

        def _set_context(self, context, location_cache):
            self._close_locations_dialog()
            self._context = context
            self._choices = list(context.get("choices", ()))
            # Location caches keep paths and parameter names only, so a dialog
            # cannot prolong the lifetime of mutable HOM objects.
            self._location_cache = dict(location_cache or {})
            context["location_cache"] = dict(self._location_cache)
            self.message_label.setText(
                "Choose {0} to rename in {1}.".format(
                    _rename_kind_indefinite_label(
                        context.get("rename_kind", RENAME_KIND_ATTRIBUTE)
                    ),
                    context.get("scope_label", "selected scope"),
                )
            )
            self._populate_table()

        def _scan_and_set_context(self, context):
            try:
                location_cache = _collect_item_rename_location_cache(
                    context,
                    context.get("choices", ()),
                )
            except Exception as exc:
                canceled = _operation_interrupted(exc)
                # A refresh always belongs to the newly sampled scope.  Keeping
                # an earlier cache here would leave stale rows actionable.
                self._set_context(context, {})
                if canceled:
                    message = (
                        "Automatic rename-location scan canceled. "
                        "Use Find Rename Locations to scan individual names."
                    )
                else:
                    message = (
                        "Could not automatically scan rename locations: {0}. "
                        "Use Find Rename Locations to scan individual names."
                    ).format(exc)
                self._show_status(message)
                return False

            self._set_context(context, location_cache)
            return True

        def _refresh_from_scope(self):
            try:
                context = _build_rename_context(scope, scene_viewer)
            except Exception as exc:
                canceled = _operation_interrupted(exc)
                message = (
                    "Rename refresh canceled; previous results were cleared."
                    if canceled
                    else (
                        "Could not refresh the rename scope: {0}. "
                        "Previous results were cleared."
                    ).format(exc)
                )
                self._set_context(_empty_rename_context(scope), {})
                self._show_status(message)
                return
            if context.get("warning"):
                warning = context.get("warning")
                self._set_context(_empty_rename_context(scope), {})
                self._show_status(warning)
                return
            self._scan_and_set_context(context)

        def _choice_matches(self, choice):
            return _choice_matches_attribute_search(choice, self.search_edit.text())

        def _populate_table(self, selected_key=None):
            self.table.setRowCount(0)
            self._visible_indexes = []
            selected_row = -1
            matching_choice_count = 0
            hidden_zero_count = 0
            for index, choice in enumerate(self._choices):
                if not self._choice_matches(choice):
                    continue
                matching_choice_count += 1
                choice_key = _item_choice_key(choice)
                location_result = self._location_cache.get(choice_key)
                if _rename_choice_is_hidden_by_location_cache(
                    choice,
                    self._location_cache,
                ):
                    hidden_zero_count += 1
                    continue
                row = self.table.rowCount()
                self.table.insertRow(row)
                self._visible_indexes.append(index)
                rename_kind, item_class, item_name, _source_count, _sources = _item_choice_parts(choice)
                if choice_key == selected_key:
                    selected_row = row
                item = QtWidgets.QTableWidgetItem("{0}: {1}".format(_item_class_label(rename_kind, item_class), item_name))
                item.setData(self._user_role, index)
                self.table.setItem(row, 0, item)
                self.table.setItem(
                    row,
                    1,
                    QtWidgets.QTableWidgetItem(_rename_location_count_label(location_result)),
                )
                if location_result is None:
                    locations_button = QtWidgets.QPushButton("Find Rename Locations")
                    locations_button.setToolTip(
                        "Find nodes with potential safe edits for this name."
                    )
                else:
                    locations_button = QtWidgets.QPushButton("View Rename Locations")
                    locations_button.setToolTip(
                        "View nodes with potential safe edits for this name."
                    )
                locations_button.clicked.connect(
                    lambda _checked=False, item_choice=choice: self._find_rename_locations(item_choice)
                )
                self.table.setCellWidget(row, 2, locations_button)

            self.choose_button.setEnabled(bool(self._visible_indexes))
            if not self._visible_indexes:
                if hidden_zero_count and hidden_zero_count == matching_choice_count:
                    all_choices_scanned = _rename_location_cache_is_complete(
                        self._choices,
                        self._location_cache,
                    )
                    if (
                        not self.search_edit.text().strip()
                        and hidden_zero_count == len(self._choices)
                        and all_choices_scanned
                    ):
                        message = _no_safe_rename_locations_message(
                            scope.get("rename_kind", RENAME_KIND_ATTRIBUTE),
                            (self._context or {}).get(
                                "scope_label",
                                "the selected scope",
                            ),
                            refresh_from_current_selection,
                        )
                    else:
                        message = (
                            "All scanned {0} matching this search had 0 safe "
                            "rename locations."
                        ).format(
                            _rename_kind_label_plural_lower(
                                scope.get("rename_kind", RENAME_KIND_ATTRIBUTE)
                            )
                        )
                    self._show_status(message)
                elif self._choices:
                    self._show_status("No matching {0} found.".format(_rename_kind_label_plural_lower(scope.get("rename_kind", RENAME_KIND_ATTRIBUTE))))
                elif self._context and self._context.get("geometry_source_count", 0) > 0:
                    message = "No {0} were found in {1}.".format(
                        _rename_kind_label_plural_lower(scope.get("rename_kind", RENAME_KIND_ATTRIBUTE)),
                        self._context.get("scope_label", "selected scope"),
                    )
                    if refresh_from_current_selection:
                        message += " Select different nodes and click Refresh From Current Selection."
                    self._show_status(message)
                else:
                    rename_kind = _normalize_rename_kind(scope.get("rename_kind", RENAME_KIND_ATTRIBUTE))
                    if self._context.get("discovery_issues"):
                        self._show_status(
                            "No renameable items were found, and some sources could not be inspected."
                        )
                    elif rename_kind == RENAME_KIND_GROUP:
                        message = "No inspectable geometry or group-name parameters were found."
                        if refresh_from_current_selection:
                            message += " Select nodes and click Refresh From Current Selection."
                        self._show_status(message)
                    else:
                        message = "No inspectable geometry was found."
                        if refresh_from_current_selection:
                            message += " Select nodes and click Refresh From Current Selection."
                        self._show_status(message)

                discovery_issues = list(
                    (self._context or {}).get("discovery_issues", ())
                )
                if discovery_issues:
                    first_issue = _short_preview(
                        _rename_skip_label(discovery_issues[0]),
                        limit=160,
                    )
                    issue_summary = (
                        "{0} discovery issue{1}. First issue: {2}"
                    ).format(
                        len(discovery_issues),
                        "" if len(discovery_issues) == 1 else "s",
                        first_issue,
                    )
                    remaining = len(discovery_issues) - 1
                    if remaining:
                        issue_summary += " {0} more.".format(remaining)
                    current_status = str(self.status_label.text() or "").strip()
                    self._show_status(
                        "{0} {1}".format(
                            current_status,
                            issue_summary,
                        ).strip()
                    )
                return

            self._clear_status()
            self.table.selectRow(selected_row if selected_row >= 0 else 0)

        def _find_rename_locations(self, choice):
            if not self._context:
                self._show_status("No rename scope is available to scan.")
                return

            choice_key = _item_choice_key(choice)
            result = self._location_cache.get(choice_key)
            if result is None:
                self._show_status("Finding potential rename locations...")
                try:
                    result = _collect_item_rename_locations(self._context, choice)
                except Exception as exc:
                    if _operation_interrupted(exc):
                        self._show_status("Rename location scan canceled.")
                    else:
                        self._show_status(
                            "Could not find rename locations: {0}".format(exc)
                        )
                    return
                self._location_cache[choice_key] = result
                self._context["location_cache"] = dict(self._location_cache)
                self._populate_table(selected_key=choice_key)

            if _rename_location_result_is_zero(result):
                self._close_locations_dialog()
                self._show_status(_zero_rename_locations_status(choice, result))
                return

            self._close_locations_dialog()
            dialog = _open_rename_locations_dialog(self, choice, result)
            self._locations_dialog = dialog

            def _locations_finished(_result=None):
                if self._locations_dialog is dialog:
                    self._locations_dialog = None
                _delete_qt_later(dialog)

            dialog.finished.connect(_locations_finished)

        def _apply_filter(self):
            self._populate_table()

        def _selected_choice(self):
            row = self.table.currentRow()
            if row < 0 or row >= len(self._visible_indexes):
                return None
            index = self._visible_indexes[row]
            if index < 0 or index >= len(self._choices):
                return None
            return self._choices[index]

        def _choose(self):
            choice = self._selected_choice()
            if choice is None:
                self._show_status("Choose an item or press Cancel.")
                return
            self._close_locations_dialog()
            _clear_stored_item_dialog(self)
            self.hide()
            on_choose(self._context, choice)
            self.close()

        def _back(self):
            self._close_locations_dialog()
            _clear_stored_item_dialog(self)
            self.hide()
            on_back()
            self.close()

    dialog = ItemChoiceDialog(_qt_main_window())
    # Keep a strong reference while viewport interaction returns control to
    # Houdini; the finished callback clears it.
    _set_stored_item_dialog(dialog)

    def _finished(_result=None):
        _clear_stored_item_dialog(dialog)
        _delete_qt_later(dialog)

    dialog.finished.connect(_finished)
    _show_qt_dialog(dialog)
    return True


def _show_attribute_rename_warning(message, details=None):
    _show_status(message, hou.severityType.Warning)
    try:
        if details:
            hou.ui.displayMessage(
                message,
                severity=hou.severityType.Warning,
                title=RENAME_TITLE,
                details=details,
                details_expanded=False,
            )
        else:
            hou.ui.displayMessage(
                message,
                severity=hou.severityType.Warning,
                title=RENAME_TITLE,
            )
    except Exception:
        pass

def _attribute_name_is_safe(attr_name):
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", attr_name) is not None

DIALOG_BACK = "__labs_rename_attributes_back__"


def _new_item_name_error(rename_kind, new_name, old_name):
    item_label = _rename_kind_label_singular(rename_kind)
    new_name = str(new_name).strip()
    if not new_name:
        return "New {0} name cannot be empty.".format(item_label)

    if new_name == old_name:
        return "New {0} name is the same as the current {0}.".format(item_label)

    if not _attribute_name_is_safe(new_name):
        return "New {0} name must start with a letter or underscore and contain only letters, numbers, and underscores.".format(item_label)

    return None


def _prompt_new_item_name_dialog(
    old_name,
    item_class,
    rename_kind,
    geometry_items=None,
    initial_name=None,
    item_choices=None,
):
    """Prompt for a valid replacement and require confirmation on collisions."""
    from hutil.Qt import QtCore, QtWidgets

    rename_kind = _normalize_rename_kind(rename_kind)
    item_label = _rename_kind_label_singular(rename_kind)
    class_label = _item_class_label_lower(rename_kind, item_class)

    class NewItemNameDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(NewItemNameDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            self._result = None
            self._collision_confirmed_for = None
            _configure_qt_dialog(self, QtCore)

            layout = QtWidgets.QVBoxLayout()

            label = QtWidgets.QLabel(
                "Rename {0} {1} '{2}' to:".format(
                    class_label,
                    item_label,
                    old_name,
                )
            )
            label.setWordWrap(True)
            layout.addWidget(label)

            self.name_edit = QtWidgets.QLineEdit()
            self.name_edit.setText(initial_name or old_name)
            layout.addWidget(self.name_edit)

            self.error_label = QtWidgets.QLabel("")
            self.error_label.setWordWrap(True)
            self.error_label.setStyleSheet("color: #ff9a9a;")
            self.error_label.hide()
            layout.addWidget(self.error_label)

            button_layout = QtWidgets.QHBoxLayout()
            self.back_button = QtWidgets.QPushButton("Back")
            button_layout.addWidget(self.back_button)
            button_layout.addStretch(1)
            self.preview_button = QtWidgets.QPushButton("Preview")
            self.cancel_button = QtWidgets.QPushButton("Cancel")
            self.preview_button.setDefault(True)
            button_layout.addWidget(self.preview_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            self.setLayout(layout)
            self.setMinimumWidth(390)

            self.preview_button.clicked.connect(self.accept)
            self.cancel_button.clicked.connect(self.reject)
            self.back_button.clicked.connect(self._back)
            self.name_edit.returnPressed.connect(self.accept)
            self.name_edit.textChanged.connect(self._clear_error)
            self.name_edit.selectAll()
            self.name_edit.setFocus()

        def _clear_error(self, *_args):
            self.error_label.clear()
            self.error_label.hide()
            self._collision_confirmed_for = None

        def _show_error(self, message):
            self.error_label.setText(message)
            self.error_label.show()
            self.name_edit.setFocus()

        def new_item_name(self):
            return str(self.name_edit.text()).strip()

        def _back(self):
            self._result = DIALOG_BACK
            super(NewItemNameDialog, self).accept()

        def accept(self):
            new_name = self.new_item_name()
            error = _new_item_name_error(rename_kind, new_name, old_name)
            if error:
                self._show_error(error)
                return

            if (
                _target_item_exists(
                    rename_kind,
                    item_class,
                    new_name,
                    geometry_items,
                    item_choices=item_choices,
                )
                and self._collision_confirmed_for != new_name
            ):
                self._collision_confirmed_for = new_name
                self._show_error(
                    "A {0} {1} named '{2}' already exists in the scanned scope. Press Preview again to continue."
                    .format(class_label, item_label, new_name)
                )
                return

            self._result = new_name
            super(NewItemNameDialog, self).accept()

        def result_value(self):
            return self._result

    dialog = NewItemNameDialog(_qt_main_window())
    exec_method = getattr(dialog, "exec", None)
    if exec_method is None:
        exec_method = getattr(dialog, "exec_")

    if exec_method() != _qt_enum(QtWidgets.QDialog, "DialogCode", "Accepted"):
        return None
    return dialog.result_value()


def _prompt_new_item_name_fallback(
    old_name,
    item_class,
    rename_kind,
    geometry_items=None,
    initial_name=None,
    item_choices=None,
):
    """Validate a replacement name through Houdini's native input dialog."""
    rename_kind = _normalize_rename_kind(rename_kind)
    item_label = _rename_kind_label_singular(rename_kind)
    try:
        button_index, text = hou.ui.readInput(
            "Rename {0} {1} '{2}' to:".format(
                _item_class_label_lower(rename_kind, item_class),
                item_label,
                old_name,
            ),
            buttons=("Preview", "Back", "Cancel"),
            close_choice=2,
            title=RENAME_TITLE,
            initial_contents=initial_name or old_name,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open {0} rename prompt: {1}".format(item_label, exc)
        )
        return None

    if button_index == 1:
        return DIALOG_BACK
    if button_index != 0:
        return None

    new_name = str(text).strip()
    error = _new_item_name_error(rename_kind, new_name, old_name)
    if error:
        _show_attribute_rename_warning(error)
        return None

    if _target_item_exists(
        rename_kind,
        item_class,
        new_name,
        geometry_items,
        item_choices=item_choices,
    ):
        try:
            choice = hou.ui.displayMessage(
                "A {0} {1} named '{2}' already exists in the scanned scope. Continue?".format(
                    _item_class_label_lower(rename_kind, item_class),
                    item_label,
                    new_name,
                ),
                buttons=("Continue", "Cancel"),
                default_choice=1,
                close_choice=1,
                severity=hou.severityType.Warning,
                title=RENAME_TITLE,
            )
        except Exception:
            choice = 1
        if choice != 0:
            return None

    return new_name


def _prompt_new_item_name(
    old_name,
    item_class,
    rename_kind,
    geometry_items=None,
    initial_name=None,
    item_choices=None,
):
    try:
        return _prompt_new_item_name_dialog(
            old_name,
            item_class,
            rename_kind,
            geometry_items=geometry_items,
            initial_name=initial_name,
            item_choices=item_choices,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open rename dialog: {0}. Falling back to simple prompt.".format(exc)
        )
        return _prompt_new_item_name_fallback(
            old_name,
            item_class,
            rename_kind,
            geometry_items=geometry_items,
            initial_name=initial_name,
            item_choices=item_choices,
        )


# ---------------------------------------------------------------------------
# Parameter-source metadata and edit presentation
# ---------------------------------------------------------------------------


def _parm_name(parm):
    try:
        return parm.name()
    except Exception:
        return ""

def _parm_string_value(parm):
    try:
        return parm.unexpandedString()
    except Exception:
        pass

    try:
        return parm.evalAsString()
    except Exception:
        return None

def _short_preview(value, limit=72):
    value = str(value).replace("\r", "\\r").replace("\n", "\\n")
    if len(value) <= limit:
        return value
    return value[:limit - 3] + "..."

def _rename_edit_label(edit):
    reason_text = ", ".join(edit.get("reasons", ()))
    language_label = edit.get("language_label", "")
    if edit.get("value_kind") == "expression" and language_label:
        reason_text = "{0}; {1}".format(language_label, reason_text)

    return "{0}/{1}: {2} -> {3} [{4}]".format(
        edit.get("node_path", ""),
        edit.get("parm_name", ""),
        _short_preview(edit.get("old_value", "")),
        _short_preview(edit.get("new_value", "")),
        reason_text,
    )

def _rename_skip_label(skip):
    return "{0}/{1}: {2}".format(
        skip.get("node_path", ""),
        skip.get("parm_name", ""),
        skip.get("reason", ""),
    )

def _append_unique_rename_edit(edits, edit, edit_index=None):
    """Merge identical plans and reject conflicting plans for one parameter."""
    key = (edit.get("node_path", ""), edit.get("parm_name", ""))
    if edit_index is not None:
        existing = edit_index.get(key)
        existing_items = (existing,) if existing is not None else ()
    else:
        existing_items = (
            existing
            for existing in edits
            if (existing.get("node_path", ""), existing.get("parm_name", "")) == key
        )

    for existing in existing_items:

        if existing.get("old_value") != edit.get("old_value"):
            return False

        if existing.get("new_value") == edit.get("new_value"):
            reasons = list(existing.get("reasons", ()))
            for reason in edit.get("reasons", ()):
                if reason not in reasons:
                    reasons.append(reason)
            existing["reasons"] = tuple(reasons)
            return True

        return False

    edits.append(edit)
    if edit_index is not None:
        edit_index[key] = edit
    return True


def _edit_code_type(edit):
    language_label = str(edit.get("language_label", ""))
    reasons = " ".join(edit.get("reasons", ()))
    text = "{0} {1}".format(language_label, reasons).lower()
    if "python" in text:
        return "Python"
    if "vex" in text or "@" in text or "setpoint" in text or "setprim" in text or "setedge" in text:
        return "VEX"
    if "hscript" in text:
        return "HScript"
    return "Plain"


def _edit_risk(edit):
    reasons = " ".join(edit.get("reasons", ())).lower()
    if "aggressive vex" in reasons:
        return "High"
    code_type = _edit_code_type(edit)
    if edit.get("value_kind") == "expression":
        return "Expression"
    if code_type != "Plain":
        return "Code"
    return "Plain"


def _annotate_rename_edit(edit):
    edit["code_type"] = _edit_code_type(edit)
    edit["risk"] = _edit_risk(edit)
    return edit


# ---------------------------------------------------------------------------
# Engine delegation and stable location planning
# ---------------------------------------------------------------------------


class _RenamePreviewTargetGuard:
    """Track the exact HOM targets authorized by one final preview.

    Planner records deliberately contain only stable, public data.  This
    preview-lifetime guard keeps volatile node identity and event callbacks
    beside those records, then releases them as soon as the preview/apply
    workflow finishes.
    """

    _STRUCTURAL_EVENT_NAMES = (
        "BeingDeleted",
        "NameChanged",
        "SpareParmTemplatesChanged",
    )
    _PARM_EVENT_NAMES = (
        "ParmTupleChanged",
        "ParmTupleAnimated",
        "ParmTupleChannelChanged",
        "ParmTupleLockChanged",
    )

    def __init__(self):
        self._targets = {}
        self._scan_targets = {}
        self._nodes = {}
        self._writing_targets = set()
        self._pending_writes = {}
        self._closed = False

        event_owner = getattr(hou, "nodeEventType", None)
        if event_owner is None:
            raise RuntimeError("Houdini node event metadata is unavailable")

        structural_events = []
        for event_name in self._STRUCTURAL_EVENT_NAMES:
            event_type = getattr(event_owner, event_name, None)
            if event_type is None:
                raise RuntimeError(
                    "required Houdini node event is unavailable: {0}".format(
                        event_name
                    )
                )
            structural_events.append(event_type)

        parm_events = [
            getattr(event_owner, event_name, None)
            for event_name in self._PARM_EVENT_NAMES
        ]
        self._structural_events = tuple(structural_events)
        self._parm_events = tuple(
            event_type for event_type in parm_events if event_type is not None
        )
        self._event_types = self._structural_events + self._parm_events

    @staticmethod
    def _target_key(edit):
        return (
            str(edit.get("node_path", "")),
            str(edit.get("parm_name", "")),
        )

    @staticmethod
    def _node_session_id(node):
        try:
            return int(node.sessionId())
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            raise RuntimeError(
                "could not inspect node identity: {0}".format(exc)
            )

    @staticmethod
    def _parm_tuple_id(parm):
        try:
            return int(parm.tuple()._asVoidPointer())
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            raise RuntimeError(
                "could not inspect parameter tuple identity: {0}".format(exc)
            )

    @staticmethod
    def _node_modification_id(node):
        try:
            method = getattr(node, "_OpNode__modificationTime", None)
            if method is not None:
                return method()
            return node.modificationTime()
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            raise RuntimeError(
                "could not inspect node modification state: {0}".format(exc)
            )

    def _invalidate_node(self, node_path, event_type, parm_tuple=None):
        if self._closed:
            return
        node_record = self._nodes.get(node_path)
        if node_record is None or node_record.get("invalid_reason"):
            return

        if event_type in self._parm_events and parm_tuple is not None:
            try:
                event_parm_names = {
                    _parm_name(event_parm)
                    for event_parm in parm_tuple
                }
            except Exception:
                event_parm_names = set()
            if any(
                writing_path == node_path
                and writing_parm in event_parm_names
                for writing_path, writing_parm in self._writing_targets
            ):
                return

        if event_type == getattr(hou.nodeEventType, "BeingDeleted", None):
            reason = "preview target node was deleted"
        elif event_type == getattr(hou.nodeEventType, "NameChanged", None):
            reason = "preview target node was renamed"
        elif event_type == getattr(
            hou.nodeEventType, "SpareParmTemplatesChanged", None
        ):
            reason = "preview target parameter layout changed"
        else:
            reason = "preview target node parameters changed"
        node_record["invalid_reason"] = reason

    def _watch_node(self, node):
        node_path = _node_path(node)
        if not node_path:
            raise RuntimeError("preview target node path is unavailable")
        session_id = self._node_session_id(node)

        existing = self._nodes.get(node_path)
        if existing is not None:
            if existing.get("session_id") != session_id:
                raise RuntimeError(
                    "preview target node was replaced during the final scan"
                )
            return existing

        def _node_event_callback(
            _guard=self,
            _node_path_value=node_path,
            **kwargs
        ):
            _guard._invalidate_node(
                _node_path_value,
                kwargs.get("event_type"),
                parm_tuple=kwargs.get("parm_tuple"),
            )

        try:
            node.addEventCallback(self._event_types, _node_event_callback)
        except Exception as exc:
            # Treat registration as potentially partial and make a best-effort
            # removal before propagating either cancellation or failure.
            try:
                node.removeEventCallback(
                    self._event_types,
                    _node_event_callback,
                )
            except Exception:
                pass
            if _operation_interrupted(exc):
                raise
            raise RuntimeError(
                "could not guard preview target node '{0}': {1}".format(
                    node_path,
                    exc,
                )
            )

        try:
            modification_id = self._node_modification_id(node)
        except Exception:
            # Registration and baseline capture form one operation.  If the
            # latter fails, leave no callback behind on an untracked node.
            try:
                node.removeEventCallback(
                    self._event_types,
                    _node_event_callback,
                )
            except Exception:
                pass
            raise

        node_record = {
            "node": node,
            "session_id": session_id,
            "modification_id": modification_id,
            "callback": _node_event_callback,
            "invalid_reason": "",
        }
        self._nodes[node_path] = node_record
        return node_record

    def watch_scan_node(self, node):
        """Begin event tracking before any parameter on a node is planned."""
        if self._closed:
            raise RuntimeError("preview target guard is already closed")
        self._watch_node(node)

    def watch_scan_parm(self, node, parm):
        """Capture native tuple identity before the planner reads a parameter."""
        if self._closed:
            raise RuntimeError("preview target guard is already closed")
        node_path = _node_path(node)
        parm_name = _parm_name(parm)
        if not node_path or not parm_name:
            raise RuntimeError("preview scan target path is incomplete")
        node_record = self._watch_node(node)
        if node_record.get("invalid_reason"):
            raise RuntimeError(node_record.get("invalid_reason"))
        if (
            self._node_modification_id(node)
            != node_record.get("modification_id")
        ):
            raise RuntimeError(
                "preview target node changed during the final scan"
            )
        key = (node_path, parm_name)
        parm_tuple_id = self._parm_tuple_id(parm)
        try:
            current_parm = node.parm(parm_name)
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            raise RuntimeError(
                "could not resolve current preview scan parameter: {0}".format(
                    exc
                )
            )
        if (
            current_parm is None
            or self._parm_tuple_id(current_parm) != parm_tuple_id
        ):
            raise RuntimeError(
                "preview target parameter was replaced during the final scan"
            )
        existing = self._scan_targets.get(key)
        if existing is not None and existing != parm_tuple_id:
            raise RuntimeError(
                "preview target parameter was replaced during the final scan"
            )
        self._scan_targets[key] = parm_tuple_id

    def watch(self, edit, node=None, parm=None):
        """Attach one planner record to its exact live node and parameter."""
        if self._closed:
            raise RuntimeError("preview target guard is already closed")

        node_path, parm_name = self._target_key(edit)
        if not node_path or not parm_name:
            raise RuntimeError("preview target path is incomplete")

        if node is None:
            try:
                node = hou.node(node_path)
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                raise RuntimeError(
                    "could not resolve preview target node: {0}".format(exc)
                )
        if node is None or _node_path(node) != node_path:
            raise RuntimeError("preview target node no longer exists")

        if parm is None:
            try:
                parm = node.parm(parm_name)
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                raise RuntimeError(
                    "could not resolve preview target parameter: {0}".format(
                        exc
                    )
                )
        if parm is None or _parm_name(parm) != parm_name:
            raise RuntimeError("preview target parameter no longer exists")

        try:
            current_parm = node.parm(parm_name)
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            raise RuntimeError(
                "could not resolve current preview target parameter: {0}".format(
                    exc
                )
            )
        if current_parm is None or _parm_name(current_parm) != parm_name:
            raise RuntimeError("preview target parameter no longer exists")

        node_record = self._watch_node(node)
        if node_record.get("invalid_reason"):
            raise RuntimeError(node_record.get("invalid_reason"))
        if (
            self._node_modification_id(node)
            != node_record.get("modification_id")
        ):
            raise RuntimeError(
                "preview target node changed during the final scan"
            )
        key = (node_path, parm_name)
        parm_tuple_id = self._parm_tuple_id(parm)
        current_parm_tuple_id = self._parm_tuple_id(current_parm)
        if current_parm_tuple_id != parm_tuple_id:
            raise RuntimeError(
                "preview target parameter was replaced during the final scan"
            )
        scan_tuple_id = self._scan_targets.get(key)
        if (
            scan_tuple_id is not None
            and scan_tuple_id != current_parm_tuple_id
        ):
            raise RuntimeError(
                "preview target parameter was replaced during the final scan"
            )
        existing = self._targets.get(key)
        if existing is not None:
            if (
                existing.get("session_id") != node_record.get("session_id")
                or existing.get("parm_tuple_id") != current_parm_tuple_id
            ):
                raise RuntimeError(
                    "preview target was replaced during the final scan"
                )
            return
        self._targets[key] = {
            "session_id": node_record.get("session_id"),
            "parm_tuple_id": current_parm_tuple_id,
        }

    def validate_identity(self, edit, node=None, parm=None):
        """Validate target identity without considering later node changes."""
        if self._closed:
            return "preview target guard is no longer active"
        node_path, parm_name = self._target_key(edit)
        target_record = self._targets.get((node_path, parm_name))
        if target_record is None:
            return "parameter was not guarded by the final preview"
        try:
            current_node = hou.node(node_path)
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            return "could not resolve guarded node: {0}".format(exc)
        if current_node is None:
            return "preview target node no longer exists"
        if (
            self._node_session_id(current_node)
            != target_record.get("session_id")
        ):
            return "preview target node was replaced"
        if node is not None and (
            self._node_session_id(node)
            != target_record.get("session_id")
        ):
            return "resolved parameter belongs to a different node"
        try:
            current_parm = current_node.parm(parm_name)
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            return "could not resolve guarded parameter: {0}".format(exc)
        if current_parm is None:
            return "preview target parameter no longer exists"
        if (
            self._parm_tuple_id(current_parm)
            != target_record.get("parm_tuple_id")
        ):
            return "preview target parameter was replaced"
        if parm is not None:
            if _parm_name(parm) != parm_name:
                return "resolved parameter does not match the preview target"
            if (
                self._parm_tuple_id(parm)
                != target_record.get("parm_tuple_id")
            ):
                return "resolved parameter was replaced"
        return ""

    def validate(
        self,
        edit,
        node=None,
        parm=None,
        allow_pending_write=False,
    ):
        """Return an explanation when a watched target is no longer exact."""
        node_path, parm_name = self._target_key(edit)
        node_record = self._nodes.get(node_path)
        if node_record is None:
            return "preview target node was not guarded"
        if node_record.get("invalid_reason"):
            return node_record.get("invalid_reason")
        try:
            callback_node = hou.node(node_path)
            callbacks = (
                tuple(callback_node.eventCallbacks())
                if callback_node is not None
                else ()
            )
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            return "could not verify preview target tracking: {0}".format(exc)
        expected_callback = node_record.get("callback")
        callback_registered = any(
            len(callback_record) >= 2
            and callback_record[1] is expected_callback
            and frozenset(callback_record[0]) == frozenset(self._event_types)
            for callback_record in callbacks
        )
        if not callback_registered:
            return "preview target tracking callback was removed"

        identity_reason = self.validate_identity(
            edit,
            node=node,
            parm=parm,
        )
        if identity_reason:
            return identity_reason

        try:
            current_node = hou.node(node_path)
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            return "could not resolve guarded node: {0}".format(exc)
        if current_node is None:
            return "preview target node no longer exists"

        try:
            current_session_id = self._node_session_id(current_node)
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            return str(exc)
        current_modification_id = self._node_modification_id(current_node)
        expected_modification_id = node_record.get("modification_id")
        if allow_pending_write:
            expected_modification_id = self._pending_writes.get(
                (node_path, parm_name),
                expected_modification_id,
            )
        if current_modification_id != expected_modification_id:
            return "preview target node changed"

        if node is not None:
            try:
                if self._node_session_id(node) != current_session_id:
                    return "resolved parameter belongs to a different node"
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                return str(exc)

        return ""

    def accept_write(self, edit, node=None):
        """Advance the node baseline only after an own write is verified."""
        node_path, parm_name = self._target_key(edit)
        key = (node_path, parm_name)
        node_record = self._nodes.get(node_path)
        if node_record is None:
            raise RuntimeError("preview target node was not guarded")
        pending_modification_id = self._pending_writes.get(key)
        if pending_modification_id is None:
            raise RuntimeError("guarded write has no pending modification state")
        if node is None:
            node = hou.node(node_path)
        if node is None:
            raise RuntimeError("preview target node no longer exists")
        identity_reason = self.validate_identity(edit, node=node)
        if identity_reason:
            raise RuntimeError(identity_reason)
        if self._node_modification_id(node) != pending_modification_id:
            raise RuntimeError("preview target node changed after the write")
        self._pending_writes.pop(key, None)
        node_record["modification_id"] = pending_modification_id

    def validate_all(self):
        """Validate every watched target before the preview becomes actionable."""
        for node_path, parm_name in tuple(self._targets):
            reason = self.validate({
                "node_path": node_path,
                "parm_name": parm_name,
            })
            if reason:
                return "{0}/{1}: {2}".format(node_path, parm_name, reason)
        return ""

    @contextmanager
    def writing(self, edit):
        """Ignore only synchronous value events caused by this guarded write."""
        key = self._target_key(edit)
        self._writing_targets.add(key)
        try:
            yield
        finally:
            self._writing_targets.discard(key)
            node_path, _parm_name_value = key
            node_record = self._nodes.get(node_path)
            if node_record is not None:
                try:
                    self._pending_writes[key] = self._node_modification_id(
                        node_record["node"]
                    )
                except Exception as exc:
                    self._pending_writes.pop(key, None)
                    if _operation_interrupted(exc):
                        raise
                    if not node_record.get("invalid_reason"):
                        node_record["invalid_reason"] = (
                            "could not capture node modification state after "
                            "the guarded write: {0}"
                        ).format(exc)

    def close(self):
        """Remove callbacks and release every preview-lifetime HOM reference."""
        if self._closed:
            return
        self._closed = True
        for node_record in tuple(self._nodes.values()):
            try:
                node_record["node"].removeEventCallback(
                    self._event_types,
                    node_record["callback"],
                )
            except Exception:
                pass
        self._writing_targets.clear()
        self._nodes.clear()
        self._targets.clear()
        self._scan_targets.clear()
        self._pending_writes.clear()


def _create_rename_preview_target_guard(edits=None):
    """Create a fail-closed guard without adding data to planner records."""
    guard = _RenamePreviewTargetGuard()
    try:
        for edit in edits or ():
            guard.watch(edit)
    except Exception:
        guard.close()
        raise
    return guard


def _collect_item_rename_edits(
    rename_kind,
    nodes,
    old_name,
    new_name,
    item_class,
    rename_vex=True,
    rename_python=True,
    aggressive_vex=False,
    progress_callback=None,
    target_guard=None,
):
    """Collect safe parameter edits using the standalone rewrite engine.

    The UI owns scope, progress, preview, application, undo, and reporting.
    The engine owns only the read-only language-aware decision for one
    parameter.  Keeping iteration here preserves per-node and per-parameter
    error isolation and ensures cached edit records contain stable paths rather
    than live HOM objects.
    """
    rename_kind = _normalize_rename_kind(rename_kind)
    if rename_kind == RENAME_KIND_GROUP:
        item_class = _normalize_group_class(item_class)
        progress_title = "Finding group references"
    else:
        item_class = _normalize_attribute_class(item_class)
        progress_title = "Finding attribute references"

    edits = []
    skipped = []
    seen_parms = set()
    edit_index = {}

    for node in _iter_nodes_with_progress(
        nodes,
        progress_title,
        progress_callback=progress_callback,
    ):
        node_path = _node_path(node)
        if not node_path:
            continue

        if target_guard is not None:
            target_guard.watch_scan_node(node)

        try:
            parms = node.parms()
        except Exception as exc:
            if _operation_interrupted(exc):
                raise
            _append_rename_issue(
                skipped,
                node_path,
                "<parms>",
                "could not inspect parameters: {0}".format(exc),
            )
            continue

        for parm in parms:
            try:
                parm_name = parm.name()
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                _append_rename_issue(
                    skipped,
                    node_path,
                    "<unknown>",
                    "could not inspect parameter name: {0}".format(exc),
                )
                continue

            if not parm_name:
                continue
            parm_key = (node_path, parm_name)
            if parm_key in seen_parms:
                continue
            seen_parms.add(parm_key)

            if target_guard is not None:
                target_guard.watch_scan_parm(node, parm)

            try:
                # The planner only reads HOM state and returns path-based
                # records for preview and later stale-value validation.
                edit, _, extra_skips = (
                    rename_engine.plan_parameter_rewrite(
                        node,
                        parm,
                        rename_kind,
                        item_class,
                        old_name,
                        new_name,
                        rename_vex=rename_vex,
                        rename_python=rename_python,
                        aggressive_vex=aggressive_vex,
                    )
                )
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                _append_rename_issue(
                    skipped,
                    node_path,
                    parm_name,
                    "could not inspect parameter: {0}".format(exc),
                )
                continue

            skipped.extend(extra_skips or ())

            if edit is not None:
                try:
                    parameter_is_locked = bool(parm.isLocked())
                except Exception as exc:
                    if _operation_interrupted(exc):
                        raise
                    _append_rename_issue(
                        skipped,
                        node_path,
                        parm_name,
                        "could not inspect parameter lock state: {0}".format(exc),
                    )
                    parameter_is_locked = None

                if parameter_is_locked is True:
                    _append_rename_issue(
                        skipped, node_path, parm_name, "parameter is locked"
                    )
                elif parameter_is_locked is False:
                    edit_added = _append_unique_rename_edit(
                        edits,
                        edit,
                        edit_index=edit_index,
                    )
                    if not edit_added:
                        _append_rename_issue(
                            skipped,
                            node_path,
                            parm_name,
                            "multiple rename edits conflict for this parameter",
                        )
                    elif target_guard is not None:
                        target_guard.watch(edit, node=node, parm=parm)

    for edit in edits:
        _annotate_rename_edit(edit)
    return edits, skipped


def _rename_location_probe_name(old_name):
    probe_name = "__labs_rename_location_probe__"
    if probe_name == str(old_name or ""):
        probe_name += "new"
    return probe_name


def _rename_location_rows(edits):
    rows = []
    rows_by_path = {}
    for edit in edits or ():
        node_path = str(edit.get("node_path", ""))
        if not node_path:
            continue

        row = rows_by_path.get(node_path)
        if row is None:
            row = {
                "node_path": node_path,
                "parm_names": [],
                "edit_count": 0,
            }
            rows_by_path[node_path] = row
            rows.append(row)

        parm_name = str(edit.get("parm_name", ""))
        if parm_name and parm_name not in row["parm_names"]:
            row["parm_names"].append(parm_name)
        row["edit_count"] += 1

    return tuple({
        "node_path": row["node_path"],
        "parm_names": tuple(row["parm_names"]),
        "edit_count": row["edit_count"],
    } for row in rows)


def _collect_item_rename_locations(context, choice, progress_callback=None):
    """Probe one candidate with a temporary name and return stable locations."""
    context = context or {}
    scope = context.get("scope") or {}
    if not isinstance(scope, dict):
        scope = {}

    rename_kind, item_class, old_name, _source_count, _sources = _item_choice_parts(choice)
    edits, skipped = _collect_item_rename_edits(
        rename_kind,
        context.get("nodes") or (),
        old_name,
        _rename_location_probe_name(old_name),
        item_class,
        rename_vex=scope.get("rename_vex", True),
        rename_python=scope.get("rename_python", True),
        aggressive_vex=scope.get("aggressive_vex", False),
        progress_callback=progress_callback,
    )
    return {
        "locations": _rename_location_rows(edits),
        "skipped": tuple(skipped),
        "discovery_issues": tuple(context.get("discovery_issues", ())),
    }


def _rename_batch_progress_callback(operation, choice_index, choice_count):
    choice_count = max(int(choice_count), 1)

    def _update(completed_nodes, total_nodes):
        if operation is None:
            return
        total_nodes = max(int(total_nodes), 1)
        within_choice = min(max(float(completed_nodes) / total_nodes, 0.0), 1.0)
        progress = (float(choice_index) + within_choice) / choice_count
        operation.updateProgress(min(max(progress, 0.0), 1.0))

    return _update


def _collect_item_rename_location_cache(context, choices):
    """Build an all-or-nothing location result for every visible candidate."""
    choices = list(choices or ())
    if not choices:
        return {}

    location_cache = {}
    with _interruptable_scan("Finding rename locations") as operation:
        choice_count = len(choices)
        for choice_index, choice in enumerate(choices):
            progress_callback = _rename_batch_progress_callback(
                operation,
                choice_index,
                choice_count,
            )
            location_cache[_item_choice_key(choice)] = (
                _collect_item_rename_locations(
                    context,
                    choice,
                    progress_callback=progress_callback,
                )
            )
        if operation is not None:
            operation.updateProgress(1.0)
    return location_cache


def _rename_edit_reason_text(edit):
    reason_text = ", ".join(edit.get("reasons", ()))
    language_label = edit.get("language_label", "")
    if edit.get("value_kind") == "expression" and language_label:
        reason_text = "{0}; {1}".format(language_label, reason_text)
    return reason_text


def _rename_edit_change_preview(edit):
    return "{0} -> {1}".format(
        _short_preview(edit.get("old_value", "")),
        _short_preview(edit.get("new_value", "")),
    )


# ---------------------------------------------------------------------------
# Network focus and edit preview
# ---------------------------------------------------------------------------


def _focus_rename_node_paths(node_paths):
    """Resolve stable paths, select their nodes, and frame them in the editor."""
    paths = []
    for node_path in node_paths or ():
        node_path = str(node_path or "")
        if node_path and node_path not in paths:
            paths.append(node_path)

    if not paths:
        _show_attribute_rename_warning("No node paths were selected to find.")
        return False

    nodes = []
    missing_paths = []
    for node_path in paths:
        try:
            node = hou.node(node_path)
        except Exception:
            node = None
        if node is None:
            missing_paths.append(node_path)
        else:
            nodes.append(node)

    if not nodes:
        if len(paths) == 1:
            message = "Could not find node '{0}'. It may have been deleted or renamed.".format(
                paths[0]
            )
        else:
            message = "Could not find the selected nodes. They may have been deleted or renamed."
        _show_attribute_rename_warning(
            message,
            details="\n".join(missing_paths),
        )
        return False

    for index, node in enumerate(nodes):
        try:
            node.setSelected(True, clear_all_selected=(index == 0))
        except Exception:
            pass

    first_node = nodes[0]
    try:
        first_node.setCurrent(True, clear_all_selected=False)
    except Exception:
        pass

    try:
        network_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    except Exception:
        network_editor = None

    first_parent = None
    try:
        first_parent = first_node.parent()
    except Exception:
        pass

    framed_count = len(nodes)
    if first_parent is not None:
        framed_count = 0
        for node in nodes:
            try:
                if node.parent() == first_parent:
                    framed_count += 1
            except Exception:
                pass

    if network_editor is not None:
        if first_parent is not None:
            try:
                network_editor.setPwd(first_parent)
            except Exception:
                pass

        try:
            network_editor.setCurrentNode(first_node)
        except Exception:
            pass

        for method_name in ("homeToSelection", "frameSelection"):
            try:
                method = getattr(network_editor, method_name, None)
                if method is not None:
                    method()
                    break
            except Exception:
                pass

    if len(nodes) == 1:
        message = "Selected and framed node {0}.".format(_node_path(first_node))
    elif framed_count == len(nodes):
        message = "Selected and framed {0} nodes.".format(len(nodes))
    else:
        parent_path = _node_path(first_parent) or "the first node's network"
        message = "Selected {0} nodes and framed {1} in {2}.".format(
            len(nodes),
            framed_count,
            parent_path,
        )

    if missing_paths:
        if len(missing_paths) == 1:
            message += " 1 missing node path was skipped."
        else:
            message += " {0} missing node paths were skipped.".format(
                len(missing_paths)
            )
    _show_status(
        message,
        hou.severityType.Warning if missing_paths else hou.severityType.Message,
    )
    return True


def _focus_rename_edit_node(edit):
    node_path = str(edit.get("node_path", ""))
    if not node_path:
        _show_attribute_rename_warning("This planned edit does not have a node path to find.")
        return False
    return _focus_rename_node_paths((node_path,))


def _make_table_item(QtWidgets, text, tooltip=None):
    item = QtWidgets.QTableWidgetItem(str(text))
    if tooltip is not None:
        item.setToolTip(str(tooltip))
    return item


def _rename_item_preview_text(rename_kind, item_class, old_name, new_name):
    return "{0} {1} '{2}' to '{3}'".format(
        _item_class_label_lower(rename_kind, item_class),
        _rename_kind_label_singular(rename_kind),
        old_name,
        new_name,
    )


def _choose_attribute_rename_edits_message(
    edits,
    skipped,
    old_attr,
    new_attr,
    attr_class,
    scope_label,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    discovery_issues=None,
):
    edit_count = len(edits)
    issue_count = len(discovery_issues or ())
    return "Preview: {0} · {1} · {2} edit{3} · {4} skipped · {5} issue{6}".format(
        "{0} {1} '{2}' → '{3}'".format(
            _item_class_label_lower(rename_kind, attr_class),
            _rename_kind_label_singular(rename_kind),
            old_attr,
            new_attr,
        ),
        scope_label,
        edit_count,
        "" if edit_count == 1 else "s",
        len(skipped),
        issue_count,
        "" if issue_count == 1 else "s",
    )


def _edit_filter_text(edit):
    return " ".join([
        str(edit.get("node_path", "")),
        str(edit.get("parm_name", "")),
        str(edit.get("old_value", "")),
        str(edit.get("new_value", "")),
        str(edit.get("language_label", "")),
        " ".join(str(reason) for reason in edit.get("reasons", ())),
        _edit_code_type(edit),
        _edit_risk(edit),
    ]).lower()


def _choose_attribute_rename_edits_dialog(
    edits,
    skipped,
    old_attr,
    new_attr,
    attr_class,
    scope_label,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    nodes=None,
    discovery_issues=None,
):
    """Preview risks and let the user select the exact edits to apply."""
    from hutil.Qt import QtCore, QtWidgets

    class PlannedEditsDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(PlannedEditsDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            _configure_qt_dialog(self, QtCore)

            self._edits = [_annotate_rename_edit(dict(edit)) for edit in edits]
            self._checked = _qt_enum(
                QtCore.Qt, "CheckState", "Checked"
            )
            self._unchecked = _qt_enum(
                QtCore.Qt, "CheckState", "Unchecked"
            )
            self._checked_indexes = set(range(len(self._edits)))
            self._row_edit_indexes = list(range(len(self._edits)))
            self._edit_index_to_row = {
                edit_index: row
                for row, edit_index in enumerate(self._row_edit_indexes)
            }
            self._selected_edits = None
            self._result = None
            self._updating_checks = False
            self._pressed_check_indexes = set()
            self._filter_timer = QtCore.QTimer(self)
            self._filter_timer.setSingleShot(True)
            self._filter_timer.setInterval(150)

            layout = QtWidgets.QVBoxLayout()

            label = QtWidgets.QLabel(
                _choose_attribute_rename_edits_message(
                    self._edits,
                    skipped,
                    old_attr,
                    new_attr,
                    attr_class,
                    scope_label,
                    rename_kind=rename_kind,
                    discovery_issues=discovery_issues,
                )
            )
            label.setWordWrap(True)
            layout.addWidget(label)

            filter_layout = QtWidgets.QHBoxLayout()
            self.search_edit = QtWidgets.QLineEdit()
            self.search_edit.setPlaceholderText("Filter planned edits")
            self.search_button = QtWidgets.QPushButton("Search")
            filter_layout.addWidget(self.search_edit, 1)
            filter_layout.addWidget(self.search_button)
            layout.addLayout(filter_layout)

            self.table = QtWidgets.QTableWidget(0, 6)
            self.table.setHorizontalHeaderLabels((
                "Apply",
                "Node",
                "Find",
                "Parameter",
                "Change",
                "Reason",
            ))
            _configure_readonly_table(self.table, QtCore, QtWidgets)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 64)
            self.table.setColumnWidth(1, 430)
            self.table.setColumnWidth(2, 72)
            self.table.setColumnWidth(3, 170)
            self.table.setColumnWidth(4, 340)
            self.table.setColumnWidth(5, 260)
            try:
                self.table.viewport().installEventFilter(self)
            except Exception:
                pass
            layout.addWidget(self.table, 1)

            button_layout = QtWidgets.QHBoxLayout()
            self.back_button = QtWidgets.QPushButton("Back")
            self.select_all_button = QtWidgets.QPushButton("Select All")
            self.select_none_button = QtWidgets.QPushButton("Select None")
            button_layout.addWidget(self.back_button)
            button_layout.addWidget(self.select_all_button)
            button_layout.addWidget(self.select_none_button)
            button_layout.addStretch(1)
            self.accept_button = QtWidgets.QPushButton("Accept")
            self.cancel_button = QtWidgets.QPushButton("Cancel")
            self.accept_button.setDefault(True)
            button_layout.addWidget(self.accept_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            self.setLayout(layout)
            self.setMinimumSize(1080, 610)
            _resize_qt_dialog(self, QtWidgets, 1440, 800)

            self.table.itemChanged.connect(self._apply_check_to_selected_rows)
            self.search_button.clicked.connect(self._apply_filter)
            self.search_edit.returnPressed.connect(self._apply_filter)
            self.search_edit.textChanged.connect(self._schedule_filter)
            self._filter_timer.timeout.connect(self._apply_filter)
            self.select_all_button.clicked.connect(lambda: self._set_all_checks(self._checked))
            self.select_none_button.clicked.connect(lambda: self._set_all_checks(self._unchecked))
            self.accept_button.clicked.connect(self.accept)
            self.cancel_button.clicked.connect(self.reject)
            self.back_button.clicked.connect(self._back)
            self._build_table()
            self._apply_filter()

        def _schedule_filter(self, *_args):
            self._filter_timer.start()

        def _edit_is_visible(self, edit):
            search_text = str(self.search_edit.text() or "").strip().lower()
            return not search_text or search_text in _edit_filter_text(edit)

        def _build_table(self):
            self._updating_checks = True
            try:
                self.table.setRowCount(len(self._row_edit_indexes))
                for row, edit_index in enumerate(self._row_edit_indexes):
                    edit = self._edits[edit_index]

                    apply_item = QtWidgets.QTableWidgetItem("")
                    apply_item.setCheckState(self._checked if edit_index in self._checked_indexes else self._unchecked)
                    self.table.setItem(row, 0, apply_item)

                    node_path = edit.get("node_path", "")
                    self.table.setItem(row, 1, _make_table_item(QtWidgets, node_path, node_path))

                    find_button = QtWidgets.QPushButton("Find")
                    find_button.setToolTip("Select and focus this node in the Network Editor.")
                    find_button.clicked.connect(
                        lambda _checked=False, planned_edit=edit: _focus_rename_edit_node(planned_edit)
                    )
                    self.table.setCellWidget(row, 2, find_button)

                    parm_name = edit.get("parm_name", "")
                    self.table.setItem(row, 3, _make_table_item(QtWidgets, parm_name, parm_name))

                    change_preview = _rename_edit_change_preview(edit)
                    full_change = "{0} -> {1}".format(edit.get("old_value", ""), edit.get("new_value", ""))
                    self.table.setItem(row, 4, _make_table_item(QtWidgets, change_preview, full_change))

                    reason_text = _rename_edit_reason_text(edit)
                    self.table.setItem(row, 5, _make_table_item(QtWidgets, reason_text, reason_text))
                self.table.resizeRowsToContents()
            finally:
                self._updating_checks = False
                self._pressed_check_indexes = set()

        def _apply_filter(self, *_args):
            for row, edit_index in enumerate(self._row_edit_indexes):
                self.table.setRowHidden(
                    row,
                    not self._edit_is_visible(self._edits[edit_index]),
                )

        def _selected_edit_indexes(self):
            indexes = set()
            try:
                selection_model = self.table.selectionModel()
                if selection_model is not None:
                    for row_index in selection_model.selectedRows():
                        row = row_index.row()
                        if 0 <= row < len(self._row_edit_indexes):
                            indexes.add(self._row_edit_indexes[row])
            except Exception:
                pass
            return indexes

        def eventFilter(self, obj, event):
            try:
                if (
                    obj is self.table.viewport()
                    and event.type()
                    == _qt_enum(QtCore.QEvent, "Type", "MouseButtonPress")
                ):
                    index = self.table.indexAt(event.pos())
                    if index.isValid() and index.column() == 0:
                        row = index.row()
                        if 0 <= row < len(self._row_edit_indexes):
                            edit_index = self._row_edit_indexes[row]
                            selected = self._selected_edit_indexes()
                            if edit_index in selected and len(selected) > 1:
                                self._pressed_check_indexes = selected
            except Exception:
                pass
            return super(PlannedEditsDialog, self).eventFilter(obj, event)

        def _apply_check_to_selected_rows(self, item):
            if self._updating_checks or item is None or item.column() != 0:
                return
            row = item.row()
            if row < 0 or row >= len(self._row_edit_indexes):
                return
            edit_index = self._row_edit_indexes[row]
            state = item.checkState()
            target_indexes = self._pressed_check_indexes or self._selected_edit_indexes()
            self._pressed_check_indexes = set()
            if edit_index not in target_indexes or len(target_indexes) <= 1:
                target_indexes = {edit_index}

            if state == self._checked:
                self._checked_indexes.update(target_indexes)
            else:
                self._checked_indexes.difference_update(target_indexes)

            if len(target_indexes) > 1:
                self._updating_checks = True
                try:
                    for target_index in target_indexes:
                        target_row = self._edit_index_to_row.get(target_index)
                        if target_row is None:
                            continue
                        target_item = self.table.item(target_row, 0)
                        if target_item is not None and target_item.checkState() != state:
                            target_item.setCheckState(state)
                finally:
                    self._updating_checks = False

        def _set_all_checks(self, state):
            if state == self._checked:
                self._checked_indexes = set(range(len(self._edits)))
            else:
                self._checked_indexes = set()
            self._updating_checks = True
            try:
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, 0)
                    if item is not None and item.checkState() != state:
                        item.setCheckState(state)
            finally:
                self._updating_checks = False

        def _back(self):
            self._result = DIALOG_BACK
            super(PlannedEditsDialog, self).accept()

        def accept(self):
            self._selected_edits = [
                edit for index, edit in enumerate(self._edits)
                if index in self._checked_indexes
            ]
            self._result = self._selected_edits
            super(PlannedEditsDialog, self).accept()

        def result_value(self):
            if self._result == DIALOG_BACK:
                return DIALOG_BACK
            return self._selected_edits or []

    dialog = PlannedEditsDialog(_qt_main_window())
    exec_method = getattr(dialog, "exec", None)
    if exec_method is None:
        exec_method = getattr(dialog, "exec_")

    if exec_method() != _qt_enum(QtWidgets.QDialog, "DialogCode", "Accepted"):
        return []
    return dialog.result_value()


def _choose_attribute_rename_edits_fallback(
    edits,
    skipped,
    old_attr,
    new_attr,
    attr_class,
    scope_label,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    discovery_issues=None,
):
    """Offer the same edit selection through Houdini's native list UI."""
    labels = [_rename_edit_label(edit) for edit in edits]
    try:
        selection = hou.ui.selectFromList(
            labels,
            default_choices=tuple(range(len(labels))),
            exclusive=False,
            message=_choose_attribute_rename_edits_message(
                edits,
                skipped,
                old_attr,
                new_attr,
                attr_class,
                scope_label,
                rename_kind=rename_kind,
                discovery_issues=discovery_issues,
            ),
            title=RENAME_TITLE,
            column_header="Planned Edits",
            clear_on_cancel=True,
            sort=False,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open rename preview: {0}".format(exc)
        )
        return None

    if not selection:
        return []

    selected_edits = []
    for index in selection:
        if index < 0 or index >= len(edits):
            _show_attribute_rename_warning("Rename selection is out of range.")
            return []
        selected_edits.append(edits[index])

    return selected_edits


def _choose_attribute_rename_edits(
    edits,
    skipped,
    old_attr,
    new_attr,
    attr_class,
    scope_label=None,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    nodes=None,
    discovery_issues=None,
):
    """Return selected plans while preserving Back and cancel semantics."""
    rename_kind = _normalize_rename_kind(rename_kind)
    if rename_kind == RENAME_KIND_GROUP:
        attr_class = _normalize_group_class(attr_class)
    else:
        attr_class = _normalize_attribute_class(attr_class)
    scope_label = scope_label or "selected scope"
    if not edits:
        detail_sections = []
        if skipped:
            detail_sections.append(
                "Skipped:\n{0}".format(
                    "\n".join(_rename_skip_label(skip) for skip in skipped)
                )
            )
        if discovery_issues:
            detail_sections.append(
                "Discovery Issues:\n{0}".format(
                    "\n".join(
                        _rename_skip_label(issue)
                        for issue in discovery_issues
                    )
                )
            )
        details = "\n\n".join(detail_sections)
        _show_attribute_rename_warning(
            "No safe edits were found in {0} for renaming {1}.".format(
                scope_label,
                _rename_item_preview_text(rename_kind, attr_class, old_attr, new_attr),
            ),
            details=details or None,
        )
        return []

    try:
        return _choose_attribute_rename_edits_dialog(
            edits,
            skipped,
            old_attr,
            new_attr,
            attr_class,
            scope_label,
            rename_kind=rename_kind,
            nodes=nodes,
            discovery_issues=discovery_issues,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open table-based rename preview: {0}. Falling back to simple preview.".format(exc)
        )
        return _choose_attribute_rename_edits_fallback(
            edits,
            skipped,
            old_attr,
            new_attr,
            attr_class,
            scope_label,
            rename_kind=rename_kind,
            discovery_issues=discovery_issues,
        )

# ---------------------------------------------------------------------------
# Reporting, guarded application, and one-step undo
# ---------------------------------------------------------------------------


def _rename_report_text(
    applied,
    skipped,
    failed,
    old_name,
    new_name,
    item_class,
    rename_kind,
    discovery_issues=None,
):
    """Build one complete report for applied, skipped, and failed work."""
    message = "Renamed {0} in {1} parameter edits.".format(
        _rename_item_preview_text(rename_kind, item_class, old_name, new_name),
        len(applied),
    )
    lines = [message]
    if applied:
        lines.append("")
        lines.append("Applied:")
        lines.extend(_rename_edit_label(edit) for edit in applied)
    if skipped:
        lines.append("")
        lines.append("Skipped:")
        lines.extend(_rename_skip_label(skip) for skip in skipped)
    if failed:
        lines.append("")
        lines.append("Failed:")
        lines.extend(_rename_skip_label(fail) for fail in failed)
    if discovery_issues:
        lines.append("")
        lines.append("Discovery Issues:")
        lines.extend(_rename_skip_label(issue) for issue in discovery_issues)
    return "\n".join(lines)


def _show_rename_report_dialog(report_text):
    """Display a copyable report without hiding fallback status output."""
    try:
        from hutil.Qt import QtCore, QtWidgets
    except Exception:
        _show_attribute_rename_warning("Rename report", details=report_text)
        return

    class RenameReportDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(RenameReportDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            _configure_qt_dialog(self, QtCore)

            layout = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel("Rename report")
            layout.addWidget(label)
            self.text_edit = QtWidgets.QTextEdit()
            self.text_edit.setPlainText(report_text)
            self.text_edit.setReadOnly(True)
            layout.addWidget(self.text_edit, 1)

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.addStretch(1)
            self.copy_button = QtWidgets.QPushButton("Copy Report")
            self.close_button = QtWidgets.QPushButton("Close")
            button_layout.addWidget(self.copy_button)
            button_layout.addWidget(self.close_button)
            layout.addLayout(button_layout)
            self.setLayout(layout)
            self.setMinimumSize(720, 420)
            _resize_qt_dialog(self, QtWidgets, 900, 600)
            self.copy_button.clicked.connect(self._copy_report)
            self.close_button.clicked.connect(self.accept)

        def _copy_report(self):
            try:
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(self.text_edit.toPlainText())
                _show_status("Rename report copied.", hou.severityType.Message)
            except Exception as exc:
                _show_attribute_rename_warning("Could not copy rename report: {0}".format(exc))

    try:
        dialog = RenameReportDialog(_qt_main_window())
        exec_method = getattr(dialog, "exec", None)
        if exec_method is None:
            exec_method = getattr(dialog, "exec_")
        exec_method()
    except Exception:
        _show_attribute_rename_warning("Rename report", details=report_text)


def _show_attribute_rename_report(
    applied,
    skipped,
    failed,
    old_attr,
    new_attr,
    attr_class,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    discovery_issues=None,
):
    """Publish the final report even when only part of a batch succeeded."""
    report_text = _rename_report_text(
        applied,
        skipped,
        failed,
        old_attr,
        new_attr,
        attr_class,
        rename_kind,
        discovery_issues=discovery_issues,
    )
    first_line = report_text.splitlines()[0] if report_text else "Rename finished."
    _show_status(first_line, hou.severityType.Message)
    if applied or skipped or failed or discovery_issues:
        _show_rename_report_dialog(report_text)

def _rename_parm_storage_type(parm):
    """Return the supported HOM storage kind without evaluating the parameter."""
    data_type = parm.parmTemplate().dataType()
    storage_types = (
        ("string", getattr(hou.parmData, "String", None)),
        ("int", getattr(hou.parmData, "Int", None)),
        ("float", getattr(hou.parmData, "Float", None)),
    )
    for storage_name, hom_type in storage_types:
        if hom_type is not None and data_type == hom_type:
            return storage_name
    raise RuntimeError("unsupported parameter storage")


def _rename_edit_current_source(parm):
    """Return the exact, unevaluated storage snapshot used by stale checks."""
    storage_type = _rename_parm_storage_type(parm)
    try:
        expression = parm.expression()
    except Exception as exc:
        operation_failed = getattr(hou, "OperationFailed", None)
        if operation_failed is None or not isinstance(exc, operation_failed):
            raise
    else:
        if expression is None:
            raise RuntimeError("expression source is unavailable")
        try:
            language = parm.expressionLanguage()
        except Exception as exc:
            raise RuntimeError(
                "expression language metadata is unavailable: {0}".format(exc)
            )
        if language is None:
            raise RuntimeError("expression language metadata is unavailable")
        return {
            "value_kind": "expression",
            "source": expression,
            "language": language,
            "storage_type": storage_type,
        }

    if storage_type != "string":
        raise RuntimeError("unsupported non-string parameter storage")
    if parm.keyframes():
        raise RuntimeError("keyframed string parameter storage is unsupported")

    return {
        "value_kind": "value",
        "source": parm.unexpandedString(),
        "language": None,
        "storage_type": storage_type,
    }


def _rename_edit_planned_storage_type(edit):
    """Normalize storage metadata while supporting legacy raw string records."""
    value_kind = edit.get("value_kind")
    if "storage_type" not in edit:
        if value_kind == "value":
            return "string", ""
        return None, "preview is missing expression storage metadata"

    storage_type = str(edit.get("storage_type") or "").strip().lower()
    if storage_type not in ("string", "int", "float"):
        return None, "preview has unsupported parameter storage metadata"
    if value_kind == "value" and storage_type != "string":
        return None, "preview storage metadata is inconsistent"
    return storage_type, ""


def _rename_edit_stale_reason(current_source, edit):
    """Explain any mismatch between a preview record and current HOM source."""
    planned_kind = edit.get("value_kind")
    if planned_kind not in ("value", "expression"):
        return "preview has unsupported parameter storage"

    if current_source.get("value_kind") != planned_kind:
        return "parameter storage changed since preview"

    planned_storage, storage_error = _rename_edit_planned_storage_type(edit)
    if storage_error:
        return storage_error
    if current_source.get("storage_type") != planned_storage:
        return "parameter storage type changed since preview"

    if current_source.get("source") != edit.get("old_value", ""):
        return "parameter source changed since preview"

    if planned_kind == "expression":
        if "language" not in edit or edit.get("language") is None:
            return "preview is missing expression language metadata"
        if current_source.get("language") != edit.get("language"):
            return "expression language changed since preview"
    elif edit.get("language") is not None:
        return "preview storage metadata is inconsistent"

    return ""


def _rename_edit_canonical_signature(edit):
    """Return the authorization-sensitive fields of one planner record."""
    storage_type, storage_error = _rename_edit_planned_storage_type(edit)
    if storage_error:
        return None, storage_error

    code_type = edit.get("code_type")
    if not code_type:
        code_type = _edit_code_type(edit)
    risk = edit.get("risk")
    if not risk:
        risk = _edit_risk(edit)
    return (
        edit.get("old_value", ""),
        edit.get("new_value", ""),
        tuple(edit.get("reasons", ())),
        edit.get("value_kind"),
        edit.get("language"),
        code_type,
        risk,
        storage_type,
    ), ""


def _rename_edit_reauthorization_reason(
    node,
    parm,
    edit,
    rename_kind,
    item_class,
    old_name,
    new_name,
):
    """Replan one row so changed owner metadata cannot reuse an old preview."""
    aggressive_vex = (
        "aggressive VEX exact string" in tuple(edit.get("reasons", ()))
    )
    current_edit, _, _skipped = (
        rename_engine.plan_parameter_rewrite(
            node,
            parm,
            rename_kind,
            item_class,
            old_name,
            new_name,
            rename_vex=True,
            rename_python=True,
            aggressive_vex=aggressive_vex,
        )
    )
    if current_edit is None:
        return "rename ownership or authorization changed since preview"

    preview_signature, preview_error = _rename_edit_canonical_signature(edit)
    if preview_error:
        return preview_error
    current_signature, current_error = _rename_edit_canonical_signature(
        current_edit
    )
    if current_error:
        return "current rename plan is incomplete: {0}".format(current_error)
    if current_signature != preview_signature:
        return "rename ownership or authorization changed since preview"
    return ""


def _rename_edit_written_reason(parm, edit):
    """Verify that a setter produced the exact planned source and storage."""
    current_source = _rename_edit_current_source(parm)
    planned_storage, storage_error = _rename_edit_planned_storage_type(edit)
    if storage_error:
        return storage_error
    if current_source.get("value_kind") != edit.get("value_kind"):
        return "parameter write changed the source storage kind"
    if current_source.get("storage_type") != planned_storage:
        return "parameter write changed the storage type"
    if current_source.get("source") != edit.get("new_value", ""):
        return "parameter write did not produce the planned source"
    if (
        edit.get("value_kind") == "expression"
        and current_source.get("language") != edit.get("language")
    ):
        return "parameter write changed the expression language"
    return ""


def _apply_rename_edit_value(parm, edit):
    """Write a plan without changing its expression/value storage kind."""
    new_value = edit.get("new_value", "")
    if edit.get("value_kind") == "expression":
        language = edit.get("language")
        parm.setExpression(new_value, language=language, replace_expression=True)
        return

    parm.set(new_value)


def _restore_rename_edit_source(parm, edit, target_guard=None):
    """Restore a setter's preview source after write verification fails."""
    if target_guard is not None:
        identity_reason = target_guard.validate_identity(
            edit,
            parm=parm,
        )
        if identity_reason:
            return (
                "preview source was not restored because target identity "
                "is unsafe: {0}"
            ).format(identity_reason)

    # A setter can fail before it writes, so avoid a second write when the
    # exact preview source is already present.
    current_source = _rename_edit_current_source(parm)
    if not _rename_edit_stale_reason(current_source, edit):
        return ""

    restore_edit = dict(edit)
    restore_edit["new_value"] = edit.get("old_value", "")
    if target_guard is None:
        _apply_rename_edit_value(parm, restore_edit)
    else:
        with target_guard.writing(edit):
            _apply_rename_edit_value(parm, restore_edit)
        identity_reason = target_guard.validate_identity(
            edit,
            parm=parm,
        )
        if identity_reason:
            return (
                "preview source restoration could not be verified because "
                "target identity is unsafe: {0}"
            ).format(identity_reason)
    current_source = _rename_edit_current_source(parm)
    restore_reason = _rename_edit_stale_reason(current_source, edit)
    if not restore_reason and target_guard is not None:
        target_guard.accept_write(edit)
    return restore_reason


def _record_write_restore(
    failed,
    node_path,
    parm_name,
    parm,
    edit,
    target_guard,
    reason,
    reraise_interruption=False,
):
    """Restore a post-set edit and record one guarded failure outcome."""
    try:
        restore_reason = _restore_rename_edit_source(
            parm,
            edit,
            target_guard=target_guard,
        )
    except Exception as restore_exc:
        restore_reason = "could not restore preview source: {0}".format(
            restore_exc
        )
        _append_rename_issue(
            failed, node_path, parm_name, "{0}; {1}".format(reason, restore_reason)
        )
        if reraise_interruption and _operation_interrupted(restore_exc):
            raise
        return

    if restore_reason:
        reason = "{0}; {1}".format(reason, restore_reason)
    else:
        reason += "; preview source was restored"
    _append_rename_issue(failed, node_path, parm_name, reason)


def _apply_attribute_rename_edits(
    edits,
    skipped,
    old_attr,
    new_attr,
    attr_class,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    discovery_issues=None,
    target_guard=None,
):
    """Apply still-current plans independently inside one Houdini undo group."""
    rename_kind = _normalize_rename_kind(rename_kind)
    if rename_kind == RENAME_KIND_GROUP:
        attr_class = _normalize_group_class(attr_class)
    else:
        attr_class = _normalize_attribute_class(attr_class)
    applied = []
    failed = []
    interrupted = None

    def _apply_selected_edits():
        for edit in edits:
            node_path = edit.get("node_path", "")
            parm_name = edit.get("parm_name", "")
            # Resolve at apply time instead of retaining live parameters from
            # discovery or preview.
            try:
                node = hou.node(node_path) if node_path else None
                parm = (
                    node.parm(parm_name)
                    if node is not None and parm_name
                    else None
                )
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                _append_rename_issue(
                    failed,
                    node_path,
                    parm_name,
                    "could not resolve parameter: {0}".format(exc),
                )
                continue

            if parm is None:
                _append_rename_issue(
                    failed, node_path, parm_name, "parameter no longer exists"
                )
                continue

            try:
                current_source = _rename_edit_current_source(parm)
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                _append_rename_issue(
                    failed,
                    node_path,
                    parm_name,
                    "could not read current parameter source: {0}".format(exc),
                )
                continue

            # A preview is a snapshot.  Never overwrite source that changed
            # while the user was reviewing the batch.
            try:
                stale_reason = _rename_edit_stale_reason(current_source, edit)
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                _append_rename_issue(
                    failed,
                    node_path,
                    parm_name,
                    "could not compare parameter with preview: {0}".format(exc),
                )
                continue
            if stale_reason:
                _append_rename_issue(
                    failed, node_path, parm_name, stale_reason
                )
                continue

            try:
                authorization_reason = _rename_edit_reauthorization_reason(
                    node,
                    parm,
                    edit,
                    rename_kind,
                    attr_class,
                    old_attr,
                    new_attr,
                )
            except Exception as exc:
                if _operation_interrupted(exc):
                    raise
                _append_rename_issue(
                    failed,
                    node_path,
                    parm_name,
                    "could not revalidate rename authorization: {0}".format(exc),
                )
                continue
            if authorization_reason:
                _append_rename_issue(
                    failed, node_path, parm_name, authorization_reason
                )
                continue

            if target_guard is not None:
                try:
                    target_reason = target_guard.validate(
                        edit,
                        node=node,
                        parm=parm,
                    )
                except Exception as exc:
                    if _operation_interrupted(exc):
                        raise
                    target_reason = (
                        "could not revalidate preview target identity: {0}"
                    ).format(exc)
                if target_reason:
                    _append_rename_issue(
                        failed, node_path, parm_name, target_reason
                    )
                    continue

            try:
                if target_guard is None:
                    _apply_rename_edit_value(parm, edit)
                else:
                    with target_guard.writing(edit):
                        _apply_rename_edit_value(parm, edit)
            except Exception as exc:
                if _operation_interrupted(exc):
                    interrupted = exc
                    _record_write_restore(
                        failed,
                        node_path,
                        parm_name,
                        parm,
                        edit,
                        target_guard,
                        "rename was interrupted while setting the parameter",
                    )
                    raise interrupted
                _record_write_restore(
                    failed,
                    node_path,
                    parm_name,
                    parm,
                    edit,
                    target_guard,
                    "could not set parameter: {0}".format(exc),
                    reraise_interruption=True,
                )
                continue

            if target_guard is not None:
                try:
                    target_reason = target_guard.validate(
                        edit,
                        node=node,
                        parm=parm,
                        allow_pending_write=True,
                    )
                except Exception as exc:
                    if _operation_interrupted(exc):
                        interrupted = exc
                        _record_write_restore(
                            failed,
                            node_path,
                            parm_name,
                            parm,
                            edit,
                            target_guard,
                            "rename was interrupted during post-write target validation",
                        )
                        raise interrupted
                    target_reason = (
                        "could not verify preview target identity after write: {0}"
                    ).format(exc)
                if target_reason:
                    _record_write_restore(
                        failed,
                        node_path,
                        parm_name,
                        parm,
                        edit,
                        target_guard,
                        target_reason,
                        reraise_interruption=True,
                    )
                    continue

            try:
                written_reason = _rename_edit_written_reason(parm, edit)
            except Exception as exc:
                if _operation_interrupted(exc):
                    interrupted = exc
                    _record_write_restore(
                        failed,
                        node_path,
                        parm_name,
                        parm,
                        edit,
                        target_guard,
                        "rename was interrupted during parameter write verification",
                    )
                    raise interrupted
                written_reason = "could not verify parameter write: {0}".format(
                    exc
                )
            if not written_reason and target_guard is not None:
                try:
                    target_guard.accept_write(edit, node=node)
                except Exception as exc:
                    if _operation_interrupted(exc):
                        interrupted = exc
                        _record_write_restore(
                            failed,
                            node_path,
                            parm_name,
                            parm,
                            edit,
                            target_guard,
                            "rename was interrupted while accepting verified write state",
                        )
                        raise interrupted
                    written_reason = (
                        "could not accept verified guarded write state: {0}"
                    ).format(exc)
            if written_reason:
                _record_write_restore(
                    failed,
                    node_path,
                    parm_name,
                    parm,
                    edit,
                    target_guard,
                    written_reason,
                    reraise_interruption=True,
                )
                continue
            applied.append(edit)

    undo_label = "Rename {0}: {1} to {2}".format(_rename_kind_label(rename_kind), old_attr, new_attr)
    try:
        # Individual failures are recorded and skipped, while every successful
        # write remains part of the same user-visible undo action.
        with hou.undos.group(undo_label):
            _apply_selected_edits()
    except Exception as exc:
        interrupted = (
            exc
            if _operation_interrupted(exc)
            else None
        )
        _append_rename_issue(
            failed,
            "",
            "<undo group>",
            "{0}: {1}".format(
                (
                    "rename batch was interrupted"
                    if interrupted is not None
                    else "rename batch failed"
                ),
                exc,
            ),
        )

    if applied:
        try:
            _set_matching_item(rename_kind, attr_class, new_attr)
            _set_rename_kind(rename_kind)
        except Exception as exc:
            _append_rename_issue(
                failed,
                "",
                "<session state>",
                "rename applied but session defaults could not be updated: {0}".format(
                    exc
                ),
            )

    # Reporting remains outside the write loop so partial batches always
    # receive a complete outcome summary.
    try:
        _show_attribute_rename_report(
            applied,
            skipped,
            failed,
            old_attr,
            new_attr,
            attr_class,
            rename_kind=rename_kind,
            discovery_issues=discovery_issues,
        )
    finally:
        if interrupted is not None:
            raise interrupted
    return bool(applied)

def _attribute_rename_needs_apply_confirmation(selected_edits, scope_label):
    """Require a final warning for broad, large, or high-risk batches."""
    return (
        len(selected_edits) >= 10
        or scope_label == SCOPE_ALL_NODES_LABEL
        or any(_edit_risk(edit) == "High" for edit in selected_edits)
    )


def _confirm_any_class_group_rename(old_group, new_group, scope_label):
    """Confirm edits across owner classes when discovery cannot prove one."""
    message = (
        "The class of group '{0}' could not be determined.\n\n"
        "Rename references from '{0}' to '{1}' across Point, Primitive, "
        "and Edge group contexts in {2}?\n\n"
        "The planned edits preview will still appear before anything changes."
    ).format(old_group, new_group, scope_label)
    try:
        choice = hou.ui.displayMessage(
            message,
            buttons=("Continue", "Back", "Cancel"),
            default_choice=0,
            close_choice=2,
            severity=hou.severityType.Warning,
            title=RENAME_TITLE,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open Any Class confirmation: {0}".format(exc)
        )
        return None

    if choice == 0:
        return True
    if choice == 1:
        return DIALOG_BACK
    return None


def _confirm_attribute_rename_apply(selected_edits, old_attr, new_attr, attr_class, scope_label, rename_kind=RENAME_KIND_ATTRIBUTE):
    """Request final approval when the selected batch crosses a risk threshold."""
    if not _attribute_rename_needs_apply_confirmation(selected_edits, scope_label):
        return True

    message = (
        "Apply {0} selected parameter edits?\n\n"
        "Rename {1} in {2}.\n\n"
        "Ctrl+Z will undo this rename batch as one action."
    ).format(
        len(selected_edits),
        _rename_item_preview_text(rename_kind, attr_class, old_attr, new_attr),
        scope_label,
    )
    if any(_edit_risk(edit) == "High" for edit in selected_edits):
        message += "\n\nThis batch includes aggressive VEX string edits."

    try:
        choice = hou.ui.displayMessage(
            message,
            buttons=("Apply", "Cancel"),
            default_choice=0,
            close_choice=1,
            severity=hou.severityType.Warning,
            title=RENAME_TITLE,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open apply confirmation: {0}".format(exc)
        )
        return False

    return choice == 0


def _defer_apply_attribute_rename_edits(
    edits,
    skipped,
    old_attr,
    new_attr,
    attr_class,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    discovery_issues=None,
    target_guard=None,
):
    """Schedule application after the active dialog callback has returned."""
    # Freeze the preview snapshot before Qt releases its dialog-owned data.
    edits = tuple(dict(edit) for edit in edits)
    skipped = tuple(dict(skip) for skip in skipped)
    discovery_issues = tuple(dict(issue) for issue in discovery_issues or ())
    old_attr = str(old_attr)
    new_attr = str(new_attr)
    rename_kind = _normalize_rename_kind(rename_kind)
    attr_class = _normalize_group_class(attr_class) if rename_kind == RENAME_KIND_GROUP else _normalize_attribute_class(attr_class)

    def _deferred_apply():
        try:
            _apply_attribute_rename_edits(
                edits,
                skipped,
                old_attr,
                new_attr,
                attr_class,
                rename_kind=rename_kind,
                discovery_issues=discovery_issues,
                target_guard=target_guard,
            )
        except Exception as exc:
            if _operation_interrupted(exc):
                _show_status(
                    "Rename canceled; partial results are listed in the rename report.",
                    hou.severityType.Warning,
                )
            else:
                _show_attribute_rename_warning(
                    "Rename failed: {0}".format(exc)
                )
        finally:
            if target_guard is not None:
                target_guard.close()

    try:
        import hdefereval
        hdefereval.executeDeferred(_deferred_apply)
        return True
    except Exception as exc:
        if target_guard is not None:
            target_guard.close()
        _show_attribute_rename_warning(
            "Could not defer rename: {0}".format(exc)
        )
        return False

# ---------------------------------------------------------------------------
# End-to-end shelf workflow
# ---------------------------------------------------------------------------


def _open_item_stage_for_scope(scope, scene_viewer=None, initial_context=None):
    """Open the searchable candidate stage for one normalized scope."""
    def _on_choose(context, choice):
        return _continue_rename_from_item_choice(context, choice, scene_viewer)

    def _on_back():
        return _rename_attribute_from_popup(scene_viewer)

    try:
        return _open_item_choice_dialog(scope, scene_viewer, _on_choose, _on_back, initial_context=initial_context)
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open searchable rename picker: {0}".format(exc)
        )
        return False


def _continue_rename_from_item_choice(context, choice, scene_viewer=None):
    """Drive naming, preview, confirmation, and deferred application."""
    context = context or {}
    scope = context.get("scope") or _default_rename_scope_options()
    scope_label = context.get("scope_label") or _scope_label(scope)
    nodes = context.get("nodes") or []
    geometry_items = context.get("geometry_items") or []
    discovery_issues = list(context.get("discovery_issues", ()))
    rename_kind, item_class, old_name, _source_count, _sources = _item_choice_parts(choice)
    rename_kind = _normalize_rename_kind(rename_kind)

    if not nodes:
        _show_attribute_rename_warning(
            "No nodes were found in {0} for {1} rename.".format(
                scope_label,
                _rename_kind_label_singular(rename_kind),
            )
        )
        return False

    _set_rename_kind(rename_kind)
    _set_matching_item(rename_kind, item_class, old_name)

    initial_new_name = old_name
    while True:
        new_name = _prompt_new_item_name(
            old_name,
            item_class,
            rename_kind,
            geometry_items=geometry_items,
            initial_name=initial_new_name,
            item_choices=context.get("choices", ()),
        )
        if new_name == DIALOG_BACK:
            return _open_item_stage_for_scope(scope, scene_viewer, initial_context=context)
        if new_name is None:
            return True

        if rename_kind == RENAME_KIND_GROUP and item_class == GROUP_CLASS_ANY:
            any_class_choice = _confirm_any_class_group_rename(
                old_name,
                new_name,
                scope_label,
            )
            if any_class_choice == DIALOG_BACK:
                initial_new_name = new_name
                continue
            if any_class_choice is not True:
                _show_status(
                    "Rename canceled; no parameters were changed.",
                    hou.severityType.Message,
                )
                return True

        target_guard = None
        target_guard_transferred = False
        try:
            try:
                target_guard = _create_rename_preview_target_guard()
                edits, skipped = _collect_item_rename_edits(
                    rename_kind,
                    nodes,
                    old_name,
                    new_name,
                    item_class,
                    rename_vex=scope.get("rename_vex", True),
                    rename_python=scope.get("rename_python", True),
                    aggressive_vex=scope.get("aggressive_vex", False),
                    target_guard=target_guard,
                )
                guard_reason = target_guard.validate_all()
            except Exception as exc:
                if _operation_interrupted(exc):
                    _show_status(
                        "Rename scan canceled; no parameters were changed.",
                        hou.severityType.Message,
                    )
                    return _open_item_stage_for_scope(
                        scope,
                        scene_viewer,
                    )
                _show_attribute_rename_warning(
                    "Could not safely guard rename targets: {0}".format(exc)
                )
                return False

            if guard_reason:
                _show_attribute_rename_warning(
                    "Rename targets changed during the final scan. "
                    "Refresh the scope and try again.",
                    details=guard_reason,
                )
                return _open_item_stage_for_scope(scope, scene_viewer)

            selected_edits = _choose_attribute_rename_edits(
                edits,
                skipped,
                old_name,
                new_name,
                item_class,
                scope_label=scope_label,
                rename_kind=rename_kind,
                nodes=nodes,
                discovery_issues=discovery_issues,
            )
            if selected_edits == DIALOG_BACK:
                initial_new_name = new_name
                continue
            if selected_edits is None:
                return False

            if not selected_edits:
                if edits:
                    _show_status(
                        "Rename canceled; no parameters were changed.",
                        hou.severityType.Message,
                    )
                return True

            if not _confirm_attribute_rename_apply(
                selected_edits,
                old_name,
                new_name,
                item_class,
                scope_label,
                rename_kind=rename_kind,
            ):
                _show_status(
                    "Rename canceled; no parameters were changed.",
                    hou.severityType.Message,
                )
                return True

            deferred = _defer_apply_attribute_rename_edits(
                selected_edits,
                skipped,
                old_name,
                new_name,
                item_class,
                rename_kind=rename_kind,
                discovery_issues=discovery_issues,
                target_guard=target_guard,
            )
            target_guard_transferred = bool(deferred)
            return deferred
        finally:
            if (
                target_guard is not None
                and not target_guard_transferred
            ):
                target_guard.close()


def _rename_attribute_from_popup(scene_viewer=None):
    """Start the non-modal workflow and retain a native fallback."""
    def _continue_from_scope(scope):
        return _open_item_stage_for_scope(scope, scene_viewer)

    try:
        return _open_rename_scope_dialog(_continue_from_scope)
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open non-modal rename scope dialog: {0}. Falling back to simple scope picker.".format(exc)
        )

    scope = _choose_rename_scope()
    if scope is None:
        return True

    return _open_item_stage_for_scope(scope, scene_viewer)


def run():
    """Shelf entry point for the rename workflow."""
    _rename_attribute_from_popup()
