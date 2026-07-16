import ast
import importlib
import re
from collections import deque
from contextlib import contextmanager

import hou

from labsopui import labs_rename_rewrite

labs_rename_rewrite = importlib.reload(labs_rename_rewrite)

RENAME_TITLE = "Rename Attributes and Groups"
DEFAULT_ATTRIBUTE = "selectnode"
DEFAULT_ATTRIBUTE_CLASS = "primitive"
DEFAULT_GROUP = "group1"
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
SCOPE_SELECTED_NODES = SCOPE_TARGET_SELECTED_NODES
SCOPE_SELECTED_NODES_INTERNALS = "selected_nodes_internals"
SCOPE_UPSTREAM_DISPLAYED = "upstream_displayed"
SCOPE_CURRENT_NETWORK = "current_network"
SCOPE_CURRENT_NETWORK_INTERNALS = "current_network_internals"
SCOPE_WHOLE_HIP = SCOPE_TARGET_WHOLE_HIP
SCOPE_WHOLE_HIP_INTERNALS = "whole_hip_internals"
SCOPE_DOWNSTREAM_DISPLAYED = "downstream_displayed"
SCOPE_ITEMS = (
    (SCOPE_SELECTED_NODES, "Selected Nodes"),
    (SCOPE_WHOLE_HIP, SCOPE_ALL_NODES_LABEL),
)

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

def _valid_rename_kinds():
    return [item[0] for item in RENAME_KIND_ITEMS]


def _normalize_rename_kind(rename_kind):
    rename_kind = str(rename_kind or RENAME_KIND_ATTRIBUTE).strip().lower()
    if rename_kind not in _valid_rename_kinds():
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


def _rename_kind_label_plural_lower(rename_kind=None):
    rename_kind = _normalize_rename_kind(rename_kind or _rename_kind())
    if rename_kind == RENAME_KIND_GROUP:
        return "groups"
    return "attributes"


def _matching_attribute():
    attr_name = getattr(hou.session, SESSION_ATTRIBUTE_NAME, DEFAULT_ATTRIBUTE)
    if not isinstance(attr_name, str):
        attr_name = DEFAULT_ATTRIBUTE

    attr_name = attr_name.strip()
    if not attr_name:
        attr_name = DEFAULT_ATTRIBUTE

    setattr(hou.session, SESSION_ATTRIBUTE_NAME, attr_name)
    return attr_name

def _valid_attribute_classes():
    return [item[0] for item in ATTRIBUTE_CLASS_ITEMS]

def _normalize_attribute_class(attr_class):
    attr_class = str(attr_class).strip().lower()
    if attr_class not in _valid_attribute_classes():
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

def _attribute_class_label_lower(attr_class=None):
    return _attribute_class_label(attr_class).lower()

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

def _valid_group_classes():
    return [item[0] for item in GROUP_CLASS_ITEMS]


def _normalize_group_class(group_class):
    group_class = str(group_class or DEFAULT_GROUP_CLASS).strip().lower()
    if group_class == GROUP_CLASS_ANY:
        return GROUP_CLASS_ANY
    if group_class not in _valid_group_classes():
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


def _group_class_label_lower(group_class=None):
    return _group_class_label(group_class).lower()


def _set_group_class(group_class):
    group_class = _normalize_group_class(group_class)
    setattr(hou.session, SESSION_GROUP_CLASS_NAME, group_class)
    return True


def _matching_group():
    group_name = getattr(hou.session, SESSION_GROUP_NAME, DEFAULT_GROUP)
    if not isinstance(group_name, str):
        group_name = DEFAULT_GROUP

    group_name = group_name.strip()
    if not group_name:
        group_name = DEFAULT_GROUP

    setattr(hou.session, SESSION_GROUP_NAME, group_name)
    return group_name


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


def _matching_item_name(rename_kind):
    if _normalize_rename_kind(rename_kind) == RENAME_KIND_GROUP:
        return _matching_group()
    return _matching_attribute()


def _set_matching_item(rename_kind, item_class, item_name):
    if _normalize_rename_kind(rename_kind) == RENAME_KIND_GROUP:
        _set_group_class(item_class)
        return _set_matching_group(item_name)
    _set_attribute_class(item_class)
    return _set_matching_attribute(item_name)


def _displayed_sop_and_geometry(scene_viewer=None, cook_geometry=True):
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
        if exc.__class__.__name__ == "OperationInterrupted":
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
        if exc.__class__.__name__ == "OperationInterrupted":
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
    except Exception:
        current_parent_path = ""
    if not current_parent_path:
        return selected[-1:]

    current_network_selection = []
    for node in selected:
        try:
            parent_path = _node_path(node.parent())
        except Exception:
            parent_path = ""
        if parent_path == current_parent_path:
            current_network_selection.append(node)
    return current_network_selection


def _selected_nodes():
    try:
        selected = hou.selectedNodes()
    except Exception:
        return []
    return _selected_nodes_in_current_network(selected)

def _node_geometry(node, output_index=0):
    if node is None:
        return None

    if not _node_is_sop(node):
        return None

    try:
        return node.geometry(output_index)
    except TypeError:
        if output_index != 0:
            return None
        try:
            return node.geometry()
        except Exception as exc:
            if exc.__class__.__name__ == "OperationInterrupted":
                raise
            return None
    except Exception as exc:
        if exc.__class__.__name__ == "OperationInterrupted":
            raise
        return None


def _node_output_indices(node, discovery_issues=None):
    method = getattr(node, "outputConnectors", None)
    if method is None:
        return (0,)

    try:
        connectors = tuple(method())
    except Exception as exc:
        if exc.__class__.__name__ == "OperationInterrupted":
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
            if exc.__class__.__name__ == "OperationInterrupted":
                raise
            _append_discovery_issue(
                discovery_issues,
                node_path,
                source_name,
                "could not cook geometry: {0}".format(exc),
            )
            return None
    except Exception as exc:
        if exc.__class__.__name__ == "OperationInterrupted":
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

def _selected_sop_geometries():
    geometries = []
    for node in _selected_nodes():
        geo = _node_geometry(node)
        if geo is not None:
            geometries.append(geo)
    return geometries

def _attribute_choices_from_geometry_items(geometry_items):
    choices = []
    source_counts = {}
    seen_source_choices = set()

    for source_key, geo in geometry_items:
        if geo is None:
            continue

        source_key = str(source_key or id(geo))
        for attr_class, _label in ATTRIBUTE_CLASS_ITEMS:
            for attr_name in _attribute_names_from_geo(geo, attr_class):
                choice = (attr_class, attr_name)
                source_choice = (source_key, choice)
                if source_choice in seen_source_choices:
                    continue

                seen_source_choices.add(source_choice)
                if choice not in source_counts:
                    source_counts[choice] = 0
                    choices.append(choice)
                source_counts[choice] += 1

    return [
        (attr_class, attr_name, source_counts.get((attr_class, attr_name), 1))
        for attr_class, attr_name in choices
    ]

def _attribute_choices_from_geometries(geometries):
    geometry_items = [
        ("geometry:{0}".format(index), geo)
        for index, geo in enumerate(geometries)
    ]
    return _attribute_choices_from_geometry_items(geometry_items)

def _discover_geometry_items_from_nodes(nodes):
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


def _geometry_items_from_nodes(nodes):
    geometry_items, _discovery_issues = _discover_geometry_items_from_nodes(nodes)
    return geometry_items

def _available_attribute_choices(displayed_geo=None, nodes=None, displayed_sop=None):
    geometry_items = []
    displayed_path = _node_path(displayed_sop)

    if displayed_geo is not None:
        geometry_items.append((displayed_path or "<displayed>", displayed_geo))

    for node_path, geo in _geometry_items_from_nodes(nodes):
        if displayed_path and node_path == displayed_path:
            continue
        geometry_items.append((node_path, geo))

    return _attribute_choices_from_geometry_items(geometry_items), len(geometry_items)


def _geometry_groups(geo, group_class, discovery_issues=None, source_key=""):
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
        if exc.__class__.__name__ == "OperationInterrupted":
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


def _group_class_from_text(value):
    text = str(value or "").strip().lower()
    if not text:
        return None
    if "vertex" in text or "vertices" in text:
        return GROUP_CLASS_UNSUPPORTED_VERTEX
    if "edge" in text:
        return GROUP_CLASS_EDGE
    if "point" in text:
        return GROUP_CLASS_POINT
    if "prim" in text or "primitive" in text:
        return GROUP_CLASS_PRIMITIVE
    if text in ("any", "guess", "auto", "automatic"):
        return GROUP_CLASS_ANY
    return None


def _parm_is_named_for_groups(parm):
    parm_name = _parm_name(parm).strip().lower()
    parm_label = _parm_label(parm).strip().lower()
    search_text = "{0} {1}".format(parm_name, parm_label)
    return "group" in search_text


def _parm_value_descriptors(parm):
    descriptors = []
    try:
        descriptors.append(parm.evalAsString())
    except Exception:
        pass

    try:
        template = parm.parmTemplate()
        menu_items = tuple(template.menuItems())
        menu_labels = tuple(template.menuLabels())
        index = int(parm.evalAsInt())
        if 0 <= index < len(menu_items):
            descriptors.append(menu_items[index])
        if 0 <= index < len(menu_labels):
            descriptors.append(menu_labels[index])
    except Exception:
        pass
    return descriptors


def _parm_group_discovery_class(node, parm, node_parms=None):
    parm_name = _parm_name(parm).strip().lower()
    parm_label = _parm_label(parm).strip().lower()
    search_text = "{0} {1}".format(parm_name, parm_label)

    explicit_class = _group_class_from_text(search_text)
    if explicit_class is not None:
        return explicit_class

    suffix_match = re.search(r"(\d+)$", parm_name)
    suffix = suffix_match.group(1) if suffix_match else ""
    numbered_companion_names = (
        "grouptype{0}".format(suffix),
        "groupclass{0}".format(suffix),
        "groupentity{0}".format(suffix),
        "entity{0}".format(suffix),
    ) if suffix else ()
    generic_companion_names = (
        "grouptype",
        "groupclass",
        "groupentity",
    )

    if node_parms is None:
        try:
            node_parms = node.parms()
        except Exception:
            node_parms = ()

    parms_by_name = {}
    for candidate in node_parms or ():
        candidate_name = _parm_name(candidate).strip().lower()
        if candidate_name and candidate_name not in parms_by_name:
            parms_by_name[candidate_name] = candidate

    ranked_companions = []
    seen_companion_names = set()
    for candidate_name in numbered_companion_names + generic_companion_names:
        candidate = parms_by_name.get(candidate_name)
        if candidate is None or candidate_name in seen_companion_names:
            continue
        seen_companion_names.add(candidate_name)
        ranked_companions.append(candidate)

    for candidate in node_parms or ():
        candidate_name = _parm_name(candidate).strip().lower()
        candidate_label = _parm_label(candidate).strip().lower()
        candidate_text = "{0} {1}".format(candidate_name, candidate_label)
        if candidate_name in seen_companion_names:
            continue
        candidate_suffix_match = re.search(r"(\d+)$", candidate_name)
        candidate_suffix = candidate_suffix_match.group(1) if candidate_suffix_match else ""
        compatible_suffix = not suffix or not candidate_suffix or candidate_suffix == suffix
        if compatible_suffix and (
            "group type" in candidate_text
            or "group class" in candidate_text
        ):
            seen_companion_names.add(candidate_name)
            ranked_companions.append(candidate)

    seen_names = set()
    for candidate in ranked_companions:
        candidate_name = _parm_name(candidate)
        if candidate_name in seen_names:
            continue
        seen_names.add(candidate_name)
        for descriptor in _parm_value_descriptors(candidate):
            group_class = _group_class_from_text(descriptor)
            if group_class is not None:
                return group_class

    try:
        node_type_text = "{0} {1}".format(_node_type_name(node), node.type().description())
    except Exception:
        node_type_text = _node_type_name(node)
    return _group_class_from_text(node_type_text)


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
            if exc.__class__.__name__ == "OperationInterrupted":
                raise
            _append_discovery_issue(
                skipped,
                node_path,
                "<parms>",
                "could not inspect group parameters: {0}".format(exc),
            )
            parms = []
        for parm in parms:
            if not _parm_is_string_like(parm):
                continue
            if not _parm_is_named_for_groups(parm):
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
            group_class = _parm_group_discovery_class(node, parm, node_parms=parms)
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
    geometry_items = []
    discovery_issues = []
    displayed_path = _node_path(displayed_sop)
    scoped_paths = set(_node_path(node) for node in _unique_nodes(nodes or ()))
    scoped_paths.discard("")

    if displayed_geo is not None and displayed_path in scoped_paths:
        geometry_items.append((displayed_path or "<displayed>", displayed_geo))

    discovered_items, node_issues = _discover_geometry_items_from_nodes(nodes)
    discovery_issues.extend(node_issues)
    for source_key, geo in discovered_items:
        if displayed_path and source_key == displayed_path:
            continue
        geometry_items.append((source_key, geo))

    return geometry_items, discovery_issues


def _geometry_items_for_scope(displayed_geo=None, nodes=None, displayed_sop=None):
    geometry_items, _discovery_issues = _geometry_discovery_for_scope(
        displayed_geo,
        nodes=nodes,
        displayed_sop=displayed_sop,
    )
    return geometry_items


def _available_item_choices(rename_kind, displayed_geo=None, nodes=None, displayed_sop=None):
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


def _attribute_choice_parts(choice):
    _rename_kind, attr_class, attr_name, source_count, _sources = _item_choice_parts(choice)
    return attr_class, attr_name, source_count


def _item_choice_label(choice):
    rename_kind, item_class, item_name, source_count, _sources = _item_choice_parts(choice)
    suffix = " ({0} found)".format(source_count)
    return "{0}: {1}{2}".format(_item_class_label(rename_kind, item_class), item_name, suffix)


def _attribute_choice_label(choice):
    return _item_choice_label(choice)


def _default_attribute_choice_index(choices):
    current_attr = _matching_attribute()
    current_class = _attribute_class()
    for index, choice in enumerate(choices):
        attr_class, attr_name, _source_count = _attribute_choice_parts(choice)
        if (attr_class, attr_name) == (current_class, current_attr):
            return index

    default_choice = (DEFAULT_ATTRIBUTE_CLASS, DEFAULT_ATTRIBUTE)
    for index, choice in enumerate(choices):
        attr_class, attr_name, _source_count = _attribute_choice_parts(choice)
        if (attr_class, attr_name) == default_choice:
            return index

    return 0


def _choice_matches_attribute_search(choice, search_text):
    search_text = str(search_text or "").strip().lower()
    if not search_text:
        return True

    _rename_kind, _item_class, item_name, _source_count, _sources = _item_choice_parts(choice)
    return search_text in str(item_name).lower()


def _qt_user_role(QtCore):
    role = getattr(QtCore.Qt, "UserRole", None)
    if role is not None:
        return role
    return QtCore.Qt.ItemDataRole.UserRole


def _qt_checked_state(QtCore):
    state = getattr(QtCore.Qt, "Checked", None)
    if state is not None:
        return state
    return QtCore.Qt.CheckState.Checked


def _qt_unchecked_state(QtCore):
    state = getattr(QtCore.Qt, "Unchecked", None)
    if state is not None:
        return state
    return QtCore.Qt.CheckState.Unchecked


def _qt_scrollbar_as_needed(QtCore):
    policy = getattr(QtCore.Qt, "ScrollBarAsNeeded", None)
    if policy is not None:
        return policy
    return QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded


def _qt_elide_none(QtCore):
    elide = getattr(QtCore.Qt, "ElideNone", None)
    if elide is not None:
        return elide
    return QtCore.Qt.TextElideMode.ElideNone


def _qt_select_rows(QtWidgets):
    behavior = getattr(QtWidgets.QAbstractItemView, "SelectRows", None)
    if behavior is not None:
        return behavior
    return QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows


def _qt_extended_selection(QtWidgets):
    mode = getattr(QtWidgets.QAbstractItemView, "ExtendedSelection", None)
    if mode is not None:
        return mode
    return QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection


def _qt_no_edit_triggers(QtWidgets):
    triggers = getattr(QtWidgets.QAbstractItemView, "NoEditTriggers", None)
    if triggers is not None:
        return triggers
    return QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers


def _qt_resize_to_contents(QtWidgets):
    mode = getattr(QtWidgets.QHeaderView, "ResizeToContents", None)
    if mode is not None:
        return mode
    return QtWidgets.QHeaderView.ResizeMode.ResizeToContents


def _qt_non_modal(QtCore):
    modality = getattr(QtCore.Qt, "NonModal", None)
    if modality is not None:
        return modality
    return QtCore.Qt.WindowModality.NonModal


def _qt_mouse_button_press(QtCore):
    event_type = getattr(QtCore.QEvent, "MouseButtonPress", None)
    if event_type is not None:
        return event_type
    return QtCore.QEvent.Type.MouseButtonPress


def _choose_attribute_to_rename_dialog(choices):
    from hutil.Qt import QtCore, QtWidgets

    class AttributeChoiceDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(AttributeChoiceDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            try:
                self.setWindowFlags(
                    self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
                )
            except Exception:
                pass

            self._choices = list(choices)
            self._selected_index = None
            self._user_role = _qt_user_role(QtCore)
            self._default_index = _default_attribute_choice_index(self._choices)

            layout = QtWidgets.QVBoxLayout()

            label = QtWidgets.QLabel("Choose an attribute to rename.")
            label.setWordWrap(True)
            layout.addWidget(label)

            search_layout = QtWidgets.QHBoxLayout()
            self.search_edit = QtWidgets.QLineEdit()
            self.search_edit.setPlaceholderText("Attribute name")
            self.search_button = QtWidgets.QPushButton("Search")
            search_layout.addWidget(self.search_edit, 1)
            search_layout.addWidget(self.search_button)
            layout.addLayout(search_layout)

            self.list_widget = QtWidgets.QListWidget()
            single_selection = getattr(QtWidgets.QAbstractItemView, "SingleSelection", None)
            if single_selection is None:
                single_selection = QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
            self.list_widget.setSelectionMode(single_selection)
            layout.addWidget(self.list_widget)

            self.status_label = QtWidgets.QLabel("")
            self.status_label.setWordWrap(True)
            self.status_label.setStyleSheet("color: #ff9a9a;")
            self.status_label.hide()
            layout.addWidget(self.status_label)

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.addStretch(1)
            self.choose_button = QtWidgets.QPushButton("Choose")
            self.cancel_button = QtWidgets.QPushButton("Cancel")
            self.choose_button.setDefault(True)
            button_layout.addWidget(self.choose_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            self.setLayout(layout)
            self.setMinimumSize(520, 420)

            self.search_button.clicked.connect(self._apply_filter)
            self.search_edit.returnPressed.connect(self._apply_filter)
            self.choose_button.clicked.connect(self.accept)
            self.cancel_button.clicked.connect(self.reject)
            self.list_widget.itemDoubleClicked.connect(self._accept_item)

            self._populate_list("")

        def _show_status(self, message):
            self.status_label.setText(message)
            self.status_label.show()

        def _clear_status(self):
            self.status_label.clear()
            self.status_label.hide()

        def _populate_list(self, search_text):
            self.list_widget.clear()
            matched_default_item = None
            first_item = None

            for index, choice in enumerate(self._choices):
                if not _choice_matches_attribute_search(choice, search_text):
                    continue

                item = QtWidgets.QListWidgetItem(_attribute_choice_label(choice))
                item.setData(self._user_role, index)
                self.list_widget.addItem(item)
                if first_item is None:
                    first_item = item
                if index == self._default_index:
                    matched_default_item = item

            if self.list_widget.count() == 0:
                self._show_status("No matching attributes found.")
                return

            self._clear_status()
            item_to_select = matched_default_item or first_item
            if item_to_select is not None:
                self.list_widget.setCurrentItem(item_to_select)

        def _apply_filter(self):
            self._populate_list(self.search_edit.text())

        def _selected_choice_index(self):
            item = self.list_widget.currentItem()
            if item is None:
                return None
            try:
                return int(item.data(self._user_role))
            except Exception:
                return None

        def _accept_item(self, item):
            if item is not None:
                self.list_widget.setCurrentItem(item)
            self.accept()

        def accept(self):
            index = self._selected_choice_index()
            if index is None or index < 0 or index >= len(self._choices):
                self._show_status("Choose an attribute or press Cancel.")
                return

            self._selected_index = index
            super(AttributeChoiceDialog, self).accept()

        def selected_choice(self):
            if self._selected_index is None:
                return None
            return self._choices[self._selected_index]

    parent = None
    try:
        parent = hou.qt.mainWindow()
    except Exception:
        pass

    dialog = AttributeChoiceDialog(parent)
    exec_method = getattr(dialog, "exec", None)
    if exec_method is None:
        exec_method = getattr(dialog, "exec_")

    accepted = getattr(QtWidgets.QDialog, "Accepted", None)
    if accepted is None:
        accepted = QtWidgets.QDialog.DialogCode.Accepted

    if exec_method() != accepted:
        return None
    return dialog.selected_choice()


def _choose_attribute_to_rename_fallback(choices):
    labels = [_attribute_choice_label(choice) for choice in choices]
    default_index = _default_attribute_choice_index(choices)
    try:
        selection = hou.ui.selectFromList(
            labels,
            default_choices=(default_index,),
            exclusive=True,
            message="Choose an attribute to rename.",
            title=RENAME_TITLE,
            column_header="Attribute",
            clear_on_cancel=True,
            sort=False,
        )
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open attribute rename picker: {0}".format(exc)
        )
        return None

    if not selection:
        return None

    index = selection[0]
    if index < 0 or index >= len(choices):
        _show_attribute_rename_warning("Attribute rename selection is out of range.")
        return None

    return choices[index]


def _choose_attribute_to_rename(displayed_geo=None, nodes=None, displayed_sop=None, scope_label=None):
    choices, geometry_source_count = _available_attribute_choices(
        displayed_geo,
        nodes=nodes,
        displayed_sop=displayed_sop,
    )
    if not choices:
        if geometry_source_count > 0:
            _show_attribute_rename_warning(
                "No attributes were found in {0} to rename.".format(
                    scope_label or "the selected scope"
                )
            )
            return None

        _show_attribute_rename_warning(
            "No inspectable geometry was found. Select nodes and use Refresh From Current Selection."
        )
        return None

    try:
        choice = _choose_attribute_to_rename_dialog(choices)
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not open searchable attribute picker: {0}. Falling back to simple picker.".format(exc)
        )
        choice = _choose_attribute_to_rename_fallback(choices)

    if choice is None:
        return None

    attr_class, old_attr, _source_count = _attribute_choice_parts(choice)
    _set_attribute_class(attr_class)
    _set_matching_attribute(old_attr)
    return attr_class, old_attr

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
    wrangle_node = _nearest_wrangle_origin_node(node)
    if wrangle_node is not None:
        return wrangle_node
    return node

def _origin_traversal_nodes(node):
    if node is None:
        return []

    node = _canonical_origin_node(node)
    if node is None:
        return []
    return [node]

def _origin_dataflow_inputs(node, discovery_issues=None):
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
            if exc.__class__.__name__ == "OperationInterrupted":
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
        if exc.__class__.__name__ == "OperationInterrupted":
            raise
        _append_discovery_issue(
            discovery_issues,
            _node_path(node),
            "<children>",
            "could not inspect internal nodes: {0}".format(exc),
        )
        return []

def _node_allows_internal_scan(node):
    if node is None:
        return False

    method = getattr(node, "isLockedHDA", None)
    if method is not None:
        try:
            if method():
                return False
        except Exception:
            pass

    return True


def _node_is_editable_inside_locked_hda(node):
    if node is None:
        return False

    method = getattr(node, "isEditableInsideLockedHDA", None)
    if method is None:
        return False
    try:
        return bool(method())
    except Exception:
        return False


def _editable_descendants_of_locked_hda(node, discovery_issues=None):
    editable = []
    seen_paths = set()
    queue = deque(_node_children(node, discovery_issues))
    while queue:
        child = queue.popleft()
        child_path = _node_path(child)
        if not child_path or child_path in seen_paths:
            continue
        seen_paths.add(child_path)
        if _node_is_editable_inside_locked_hda(child):
            editable.append(child)
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

        if not _node_allows_internal_scan(node):
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

def _current_network_node(scene_viewer=None):
    try:
        viewer = scene_viewer or hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    except Exception:
        viewer = None

    if viewer is not None:
        try:
            pwd = viewer.pwd()
            if pwd is not None:
                return pwd
        except Exception:
            pass

    try:
        network_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    except Exception:
        network_editor = None

    if network_editor is not None:
        try:
            pwd = network_editor.pwd()
            if pwd is not None:
                return pwd
        except Exception:
            pass

    return None

def _whole_hip_surface_nodes(discovery_issues=None):
    try:
        root = hou.node("/")
    except Exception as exc:
        if exc.__class__.__name__ == "OperationInterrupted":
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


def _valid_scope_targets():
    return [value for value, _label in SCOPE_TARGET_ITEMS]


def _normalize_rename_scope_options(scope):
    options = _default_rename_scope_options()

    if isinstance(scope, dict):
        target = scope.get("target", options["target"])
        if target not in _valid_scope_targets():
            target = options["target"]

        options["target"] = target
        options["rename_kind"] = _normalize_rename_kind(scope.get("rename_kind", options.get("rename_kind", RENAME_KIND_ATTRIBUTE)))
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

    scope = scope or SCOPE_SELECTED_NODES
    if scope == SCOPE_SELECTED_NODES_INTERNALS:
        options["include_internals"] = True
    elif scope == SCOPE_UPSTREAM_DISPLAYED:
        options["include_upstream"] = True
    elif scope == SCOPE_DOWNSTREAM_DISPLAYED:
        options["include_downstream"] = True
    elif scope == SCOPE_CURRENT_NETWORK_INTERNALS:
        options["include_internals"] = True
    elif scope in (SCOPE_WHOLE_HIP, SCOPE_WHOLE_HIP_INTERNALS):
        options["target"] = SCOPE_TARGET_WHOLE_HIP
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


def _scope_target_label(target):
    for value, label in SCOPE_TARGET_ITEMS:
        if value == target:
            return label
    return "Selected Nodes"


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

    try:
        dialog.raise_()
    except Exception:
        pass
    try:
        dialog.activateWindow()
    except Exception:
        pass
    return True


def _open_rename_scope_dialog(on_accept):
    if _focus_existing_rename_scope_dialog():
        return True

    from hutil.Qt import QtCore, QtWidgets

    class RenameScopeDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(RenameScopeDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            self.setModal(False)
            try:
                self.setWindowModality(_qt_non_modal(QtCore))
            except Exception:
                pass
            try:
                self.setWindowFlags(
                    self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
                )
            except Exception:
                pass

            layout = QtWidgets.QVBoxLayout()

            message = QtWidgets.QLabel(
                "Choose what to rename and where to search. You can select nodes while this window is open."
            )
            message.setWordWrap(True)
            layout.addWidget(message)

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
                target_index = _valid_scope_targets().index(target)
            except ValueError:
                target_index = 0
            try:
                kind_index = _valid_rename_kinds().index(rename_kind)
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
            try:
                self.adjustSize()
            except Exception:
                pass

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

    parent = None
    try:
        parent = hou.qt.mainWindow()
    except Exception:
        pass

    dialog = RenameScopeDialog(parent)
    _set_stored_rename_scope_dialog(dialog)

    def _finished(_result=None):
        _clear_stored_rename_scope_dialog(dialog)
        try:
            dialog.deleteLater()
        except Exception:
            pass

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
    dialog.show()
    try:
        dialog.raise_()
    except Exception:
        pass
    try:
        dialog.activateWindow()
    except Exception:
        pass
    return True


def _choose_rename_scope_fallback():
    labels = [label for _value, label in SCOPE_ITEMS]
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
    if index < 0 or index >= len(SCOPE_ITEMS):
        _show_attribute_rename_warning("Rename scope selection is out of range.")
        return None

    return _normalize_rename_scope_options(SCOPE_ITEMS[index][0])


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
    options = _normalize_rename_scope_options(scope)
    target = options.get("target", SCOPE_TARGET_SELECTED_NODES)
    discovery_issues = []

    if target == SCOPE_TARGET_SELECTED_NODES:
        nodes = _nodes_from_selected_scope_nodes(
            _selected_nodes(),
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


def _nodes_for_rename_scope(scope, source_sop=None, scene_viewer=None):
    nodes, warning, _discovery_issues = _nodes_for_rename_scope_with_issues(
        scope,
        source_sop,
        scene_viewer,
    )
    return nodes, warning


def _stored_item_dialog():
    return getattr(hou.session, SESSION_ITEM_DIALOG_NAME, None)


def _set_stored_item_dialog(dialog):
    setattr(hou.session, SESSION_ITEM_DIALOG_NAME, dialog)


def _clear_stored_item_dialog(dialog=None):
    current_dialog = _stored_item_dialog()
    if dialog is not None and current_dialog is not dialog:
        return
    setattr(hou.session, SESSION_ITEM_DIALOG_NAME, None)


def _build_rename_context(scope, scene_viewer=None):
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
        if exc.__class__.__name__ == "OperationInterrupted":
            return {"warning": "Rename scan canceled; no parameters were changed."}
        raise
    return {
        "scope": scope,
        "source_sop": source_sop,
        "displayed_geo": geo,
        "nodes": nodes,
        "choices": choices,
        "geometry_source_count": geometry_source_count,
        "geometry_items": geometry_items,
        "discovery_issues": discovery_issues,
        "scope_label": _scope_label(scope),
        "rename_kind": rename_kind,
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
            self.setModal(False)
            try:
                self.setWindowModality(_qt_non_modal(QtCore))
            except Exception:
                pass
            try:
                self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
            except Exception:
                pass

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
            self.table.setWordWrap(False)
            self.table.setTextElideMode(_qt_elide_none(QtCore))
            self.table.setHorizontalScrollBarPolicy(_qt_scrollbar_as_needed(QtCore))
            self.table.setVerticalScrollBarPolicy(_qt_scrollbar_as_needed(QtCore))
            self.table.setSelectionBehavior(_qt_select_rows(QtWidgets))
            self.table.setSelectionMode(_qt_extended_selection(QtWidgets))
            self.table.setEditTriggers(_qt_no_edit_triggers(QtWidgets))
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
    dialog.show()
    try:
        dialog.raise_()
        dialog.activateWindow()
    except Exception:
        pass
    return dialog


def _show_discovery_issues(issues):
    issues = tuple(issues or ())
    if not issues:
        return
    message = "{0} discovery issue{1} occurred while scanning rename sources.".format(
        len(issues),
        "" if len(issues) == 1 else "s",
    )
    details = "\n".join(_rename_skip_label(item) for item in issues)
    try:
        hou.ui.displayMessage(
            message,
            severity=hou.severityType.Warning,
            title="Rename Discovery Issues",
            details=details,
            details_expanded=True,
        )
    except Exception:
        print("{0}\n{1}".format(message, details))


def _open_item_choice_dialog(scope, scene_viewer, on_choose, on_back, initial_context=None):
    existing = _stored_item_dialog()
    if existing is not None:
        try:
            if existing.isVisible():
                existing.raise_()
                existing.activateWindow()
                return True
        except Exception:
            _clear_stored_item_dialog(existing)

    from hutil.Qt import QtCore, QtWidgets

    refresh_from_current_selection = (
        _normalize_rename_scope_options(scope).get("target")
        == SCOPE_TARGET_SELECTED_NODES
    )

    class ItemChoiceDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(ItemChoiceDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            self.setModal(False)
            try:
                self.setWindowModality(_qt_non_modal(QtCore))
            except Exception:
                pass
            try:
                self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
            except Exception:
                pass

            self._context = None
            self._choices = []
            self._visible_indexes = []
            self._location_cache = {}
            self._locations_dialog = None
            self._user_role = _qt_user_role(QtCore)

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
            self.skipped_sources_button = QtWidgets.QPushButton("View Discovery Issues")
            self.skipped_sources_button.hide()
            search_layout.addWidget(self.search_edit, 1)
            search_layout.addWidget(self.search_button)
            search_layout.addWidget(self.refresh_button)
            search_layout.addWidget(self.skipped_sources_button)
            layout.addLayout(search_layout)

            self.table = QtWidgets.QTableWidget(0, 3)
            self.table.setHorizontalHeaderLabels(("Name", "Matching Nodes", "Locations"))
            self.table.setWordWrap(False)
            self.table.setTextElideMode(_qt_elide_none(QtCore))
            self.table.setHorizontalScrollBarPolicy(_qt_scrollbar_as_needed(QtCore))
            self.table.setSelectionBehavior(_qt_select_rows(QtWidgets))
            single_selection = getattr(QtWidgets.QAbstractItemView, "SingleSelection", None)
            if single_selection is None:
                single_selection = QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
            self.table.setSelectionMode(single_selection)
            self.table.setEditTriggers(_qt_no_edit_triggers(QtWidgets))
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

            self.search_button.clicked.connect(self._apply_filter)
            self.search_edit.returnPressed.connect(self._apply_filter)
            self.refresh_button.clicked.connect(self._refresh_from_scope)
            self.skipped_sources_button.clicked.connect(self._show_discovery_issues)
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
            self._location_cache = dict(location_cache or {})
            context["location_cache"] = dict(self._location_cache)
            self._update_discovery_issues()
            self.message_label.setText(
                "Choose a {0} to rename in {1}.".format(
                    _rename_kind_label_singular(
                        context.get("rename_kind", RENAME_KIND_ATTRIBUTE)
                    ),
                    context.get("scope_label", "selected scope"),
                )
            )
            self._populate_table()

        def _scan_and_set_context(self, context, keep_existing_on_failure):
            try:
                location_cache = _collect_item_rename_location_cache(
                    context,
                    context.get("choices", ()),
                )
            except Exception as exc:
                canceled = exc.__class__.__name__ == "OperationInterrupted"
                if keep_existing_on_failure and self._context is not None:
                    if canceled:
                        message = (
                            "Automatic rename-location refresh canceled; "
                            "previous results were kept."
                        )
                    else:
                        message = (
                            "Could not refresh rename locations; previous results "
                            "were kept: {0}"
                        ).format(exc)
                    self._show_status(message)
                    return False

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
            context = _build_rename_context(scope, scene_viewer)
            if context.get("warning"):
                self._show_status(context.get("warning"))
                return
            self._scan_and_set_context(
                context,
                keep_existing_on_failure=self._context is not None,
            )

        def _update_discovery_issues(self):
            issues = list((self._context or {}).get("discovery_issues", ()))
            self.skipped_sources_button.setVisible(bool(issues))
            if issues:
                self.skipped_sources_button.setText(
                    "View Discovery Issues ({0})".format(len(issues))
                )

        def _show_discovery_issues(self):
            _show_discovery_issues((self._context or {}).get("discovery_issues", ()))

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
                            "No renameable items were found, and some sources could not be inspected. View Discovery Issues for details."
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
                    if exc.__class__.__name__ == "OperationInterrupted":
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
                try:
                    dialog.deleteLater()
                except Exception:
                    pass

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

    parent = None
    try:
        parent = hou.qt.mainWindow()
    except Exception:
        pass

    dialog = ItemChoiceDialog(parent)
    _set_stored_item_dialog(dialog)

    def _finished(_result=None):
        _clear_stored_item_dialog(dialog)
        try:
            dialog.deleteLater()
        except Exception:
            pass

    dialog.finished.connect(_finished)
    dialog.show()
    try:
        dialog.raise_()
    except Exception:
        pass
    try:
        dialog.activateWindow()
    except Exception:
        pass
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


def _new_attribute_name_error(new_attr, old_attr):
    return _new_item_name_error(RENAME_KIND_ATTRIBUTE, new_attr, old_attr)


def _prompt_new_item_name_dialog(
    old_name,
    item_class,
    rename_kind,
    geometry_items=None,
    initial_name=None,
    item_choices=None,
):
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
            try:
                self.setWindowFlags(
                    self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
                )
            except Exception:
                pass

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

    parent = None
    try:
        parent = hou.qt.mainWindow()
    except Exception:
        pass

    dialog = NewItemNameDialog(parent)
    exec_method = getattr(dialog, "exec", None)
    if exec_method is None:
        exec_method = getattr(dialog, "exec_")

    accepted = getattr(QtWidgets.QDialog, "Accepted", None)
    if accepted is None:
        accepted = QtWidgets.QDialog.DialogCode.Accepted

    if exec_method() != accepted:
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


def _prompt_new_attribute_name_dialog(old_attr, attr_class):
    return _prompt_new_item_name_dialog(old_attr, attr_class, RENAME_KIND_ATTRIBUTE)


def _prompt_new_attribute_name_fallback(old_attr, attr_class):
    return _prompt_new_item_name_fallback(old_attr, attr_class, RENAME_KIND_ATTRIBUTE)


def _prompt_new_attribute_name(old_attr, attr_class):
    return _prompt_new_item_name(old_attr, attr_class, RENAME_KIND_ATTRIBUTE)

def _parm_label(parm):
    try:
        return parm.parmTemplate().label()
    except Exception:
        return ""

def _parm_name(parm):
    try:
        return parm.name()
    except Exception:
        return ""

def _parm_is_string_like(parm):
    try:
        data_type = parm.parmTemplate().dataType()
        if data_type == hou.parmData.String:
            return True
        return False
    except Exception:
        pass

    try:
        parm.evalAsString()
        return True
    except Exception:
        return False

def _parm_string_value(parm):
    try:
        return parm.unexpandedString()
    except Exception:
        pass

    try:
        return parm.evalAsString()
    except Exception:
        return None

def _parm_expression_data(parm):
    try:
        expression = parm.expression()
        language = parm.expressionLanguage()
    except Exception:
        return None

    if expression is None:
        return None

    return {
        "kind": "expression",
        "value": expression,
        "language": language,
        "language_kind": _expression_language_kind(language),
        "language_label": _expression_language_label(language),
    }

def _expression_language_kind(language):
    try:
        expr_language = hou.exprLanguage
    except Exception:
        expr_language = None

    if expr_language is not None:
        try:
            if language == getattr(expr_language, "Python", None):
                return "python"
        except Exception:
            pass

        try:
            if language == getattr(expr_language, "Hscript", None):
                return "hscript"
        except Exception:
            pass

    language_text = str(language).lower()
    if "python" in language_text:
        return "python"
    if "hscript" in language_text or "h-script" in language_text:
        return "hscript"
    return ""

def _expression_language_label(language):
    kind = _expression_language_kind(language)
    if kind == "python":
        return "Python expression"
    if kind == "hscript":
        return "HScript expression"
    return "Expression"

def _parm_rename_source(parm):
    expression_data = _parm_expression_data(parm)
    if expression_data is not None:
        return expression_data

    if not _parm_is_string_like(parm):
        return None

    value = _parm_string_value(parm)
    if value is None:
        return None

    return {
        "kind": "value",
        "value": value,
        "language": None,
        "language_kind": "",
        "language_label": "Parameter value",
    }

def _parm_has_keyframes_or_expression(parm):
    try:
        return bool(parm.keyframes())
    except Exception:
        return False

def _text_looks_like_vex_code(value):
    text = value or ""
    return (
        "@" in text
        or re.search(r"\bset(?:point|prim|vertex|detail)attrib\s*\(", text) is not None
    )

def _parm_is_vex_code_parameter(parm, value):
    parm_name = _parm_name(parm).lower()
    label = _parm_label(parm).lower()
    search_text = "{0} {1}".format(parm_name, label)

    if any(token in search_text for token in ("snippet", "vex", "code")):
        return True

    if any(token in search_text for token in ("expr", "expression")):
        return _text_looks_like_vex_code(value)

    return False

def _parm_should_skip_expression_state(node, parm, value):
    return (
        _parm_has_keyframes_or_expression(parm)
        and not _parm_is_vex_code_parameter(parm, value)
    )

def _parm_is_locked(parm):
    try:
        return bool(parm.isLocked())
    except Exception:
        return False

def _parm_looks_like_vex_code(node, parm, value):
    parm_name = _parm_name(parm).lower()
    label = _parm_label(parm).lower()
    node_type = _node_type_name(node)
    text = value or ""

    if "wrangle" in node_type:
        return True

    if any(token in parm_name for token in ("snippet", "vex", "code", "expr")):
        return True

    if any(token in label for token in ("snippet", "vex", "code", "expression")):
        return True

    return _text_looks_like_vex_code(text)

def _text_looks_like_python_attribute_code(value):
    text = value or ""
    return (
        "hou." in text
        or re.search(
            r"\b(?:find(?:Point|Prim|Vertex|Global)Attrib|(?:point|prim|vertex)(?:Float|Int|String)AttribValues|attribValue|setAttribValue|setGlobalAttribValue|addAttrib)\s*\(",
            text,
        ) is not None
    )

def _parm_looks_like_python_code(node, parm, value):
    parm_name = _parm_name(parm).lower()
    label = _parm_label(parm).lower()
    node_type = _node_type_name(node)
    search_text = "{0} {1} {2}".format(node_type, parm_name, label)

    if "python" in search_text:
        return True

    return _text_looks_like_python_attribute_code(value)

def _text_looks_like_hscript_attribute_code(value):
    text = value or ""
    return re.search(
        r"\b(?:point|prim|primuv|vertex|detail|details|has(?:point|prim|vertex|detail)attrib)\s*\(",
        text,
        re.IGNORECASE,
    ) is not None

def _parm_looks_like_hscript_code(node, parm, value):
    parm_name = _parm_name(parm).lower()
    label = _parm_label(parm).lower()
    search_text = "{0} {1}".format(parm_name, label)

    if "hscript" in search_text or "h-script" in search_text:
        return True

    return _text_looks_like_hscript_attribute_code(value)

def _parm_is_attribute_like(parm, value, old_attr):
    value = value or ""
    if value.strip() == old_attr:
        return True

    parm_name = _parm_name(parm)
    label = _parm_label(parm)
    search_text = "{0} {1}".format(parm_name, label).lower()
    if any(keyword in search_text for keyword in ("attrib", "attribute", "attr", "group")):
        return True

    if (
        parm_name.lower().startswith("name")
        or label.strip().lower() == "name"
    ):
        token_pattern = re.compile(
            r"(?<![A-Za-z0-9_]){0}(?![A-Za-z0-9_])".format(
                re.escape(old_attr)
            )
        )
        return token_pattern.search(value) is not None

    return False

def _matching_close_paren(text, open_index, code_mask=None):
    depth = 0
    quote = ""
    escape = False

    for index in range(open_index, len(text)):
        char = text[index]

        if code_mask is not None and not code_mask[index]:
            continue

        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = ""
            continue

        if char in ("'", '"'):
            quote = char
            continue

        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index

    return -1

def _trim_arg_span(text, start, end, base_offset):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return text[start:end], base_offset + start, base_offset + end

def _split_top_level_args(arg_text, base_offset):
    args = []
    depth = 0
    quote = ""
    escape = False
    start = 0

    code_mask = labs_rename_rewrite.vex_code_mask(arg_text)
    for index, char in enumerate(arg_text):
        if not code_mask[index]:
            continue
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = ""
            continue

        if char in ("'", '"'):
            quote = char
            continue

        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            args.append(_trim_arg_span(arg_text, start, index, base_offset))
            start = index + 1

    args.append(_trim_arg_span(arg_text, start, len(arg_text), base_offset))
    return args

def _setattrib_function_for_class(attr_class):
    return {
        ATTRIBUTE_CLASS_POINT: "setpointattrib",
        ATTRIBUTE_CLASS_PRIMITIVE: "setprimattrib",
        ATTRIBUTE_CLASS_VERTEX: "setvertexattrib",
        ATTRIBUTE_CLASS_DETAIL: "setdetailattrib",
    }.get(_normalize_attribute_class(attr_class), "setprimattrib")

def _setattrib_attribute_args(value):
    calls = []
    code_mask = labs_rename_rewrite.vex_code_mask(value)
    pattern = re.compile(r"\b(?P<function>set(?:point|prim|vertex|detail)attrib)\s*\(")
    for match in pattern.finditer(value):
        if not labs_rename_rewrite.span_is_code(code_mask, match.start(), match.end()):
            continue
        open_index = match.end() - 1
        close_index = _matching_close_paren(value, open_index, code_mask=code_mask)
        if close_index < 0:
            continue

        args = _split_top_level_args(
            value[open_index + 1:close_index],
            open_index + 1,
        )
        if len(args) < 2:
            continue

        arg_text, start, end = args[1]
        calls.append({
            "function": match.group("function"),
            "text": arg_text.strip(),
            "start": start,
            "end": end,
        })

    return calls

def _span_overlaps(start, end, spans):
    return any(not (end <= span_start or start >= span_end) for span_start, span_end in spans)

def _string_literal_value(text):
    match = re.match(r"^([\"'])(.*)\1$", text.strip(), re.DOTALL)
    if match:
        return match.group(2), match.group(1)
    return None, ""

def _is_simple_identifier(text):
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", text.strip()) is not None

def _chs_reference(text):
    match = re.match(r"^chs\(\s*([\"'])([^\"']+)\1\s*\)$", text.strip())
    if match:
        return match.group(2)
    return ""

def _local_string_assignments(value, identifier):
    escaped_identifier = re.escape(identifier)
    literal_pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?:string\s+)?{0}\s*=\s*(?P<literal>(?P<quote>[\"'])(?P<value>[^\"']*)(?P=quote))\s*;".format(
            escaped_identifier
        )
    )
    chs_pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?:string\s+)?{0}\s*=\s*chs\(\s*(?P<quote>[\"'])(?P<parm>[^\"']+)(?P=quote)\s*\)\s*;".format(
            escaped_identifier
        )
    )

    assignments = []
    for match in literal_pattern.finditer(value):
        assignments.append({
            "kind": "literal",
            "start": match.start("literal"),
            "end": match.end("literal"),
            "value": match.group("value"),
            "quote": match.group("quote"),
        })

    for match in chs_pattern.finditer(value):
        assignments.append({
            "kind": "chs",
            "parm_name": match.group("parm"),
        })

    return assignments

def _replace_spans(value, replacements):
    if not replacements:
        return value

    new_value = value
    used_ranges = []
    for replacement in sorted(replacements, key=lambda item: item["start"], reverse=True):
        start = replacement["start"]
        end = replacement["end"]
        if start < 0 or end < start or end > len(value):
            continue

        overlaps = any(not (end <= used_start or start >= used_end) for used_start, used_end in used_ranges)
        if overlaps:
            continue

        new_value = new_value[:start] + replacement["text"] + new_value[end:]
        used_ranges.append((start, end))

    return new_value

def _ast_node_span(value, node):
    return labs_rename_rewrite.python_ast_node_span(value, node)

def _python_string_literal_replacement(source_text, new_attr):
    match = re.match(
        r"^(?P<prefix>[rRuUbB]*)(?P<quote>'''|\"\"\"|'|\")(?P<body>.*)(?P=quote)$",
        source_text,
        re.DOTALL,
    )
    if not match:
        return repr(new_attr)

    prefix = match.group("prefix") or ""
    quote = match.group("quote")
    escaped = str(new_attr).replace("\\", "\\\\")
    if quote in ("'", '"'):
        escaped = escaped.replace(quote, "\\" + quote)
    else:
        escaped = escaped.replace(quote[:1] * 3, "\\" + quote[:1] * 3)
    return "{0}{1}{2}{1}".format(prefix, quote, escaped)

def _python_literal_replacement(value, node, new_attr):
    span = _ast_node_span(value, node)
    if span is None:
        return None

    start, end = span
    return {
        "start": start,
        "end": end,
        "text": _python_string_literal_replacement(value[start:end], new_attr),
    }

def _python_call_name(call):
    try:
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        if isinstance(call.func, ast.Name):
            return call.func.id
    except Exception:
        pass
    return ""

def _python_attribute_method_arg_indexes(method_name, attr_class):
    attr_class = _normalize_attribute_class(attr_class)
    class_methods = {
        ATTRIBUTE_CLASS_POINT: {
            "findPointAttrib",
            "deletePointAttrib",
            "pointFloatAttribValues",
            "pointIntAttribValues",
            "pointStringAttribValues",
            "setPointFloatAttribValues",
            "setPointIntAttribValues",
            "setPointStringAttribValues",
        },
        ATTRIBUTE_CLASS_PRIMITIVE: {
            "findPrimAttrib",
            "deletePrimAttrib",
            "primFloatAttribValues",
            "primIntAttribValues",
            "primStringAttribValues",
            "setPrimFloatAttribValues",
            "setPrimIntAttribValues",
            "setPrimStringAttribValues",
        },
        ATTRIBUTE_CLASS_VERTEX: {
            "findVertexAttrib",
            "deleteVertexAttrib",
            "vertexFloatAttribValues",
            "vertexIntAttribValues",
            "vertexStringAttribValues",
            "setVertexFloatAttribValues",
            "setVertexIntAttribValues",
            "setVertexStringAttribValues",
        },
        ATTRIBUTE_CLASS_DETAIL: {
            "findGlobalAttrib",
            "deleteGlobalAttrib",
            "attribValue",
            "setGlobalAttribValue",
        },
    }

    if method_name in class_methods.get(attr_class, set()):
        return (0,)

    if method_name in ("attribValue", "setAttribValue"):
        return (0,)

    if method_name == "addAttrib":
        return (1,)

    return ()

def _python_string_assignments(tree, old_attr):
    assignments = {}
    blocked = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value_node = node.value
        else:
            continue

        for target in targets:
            if not isinstance(target, ast.Name):
                continue

            if (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, str)
                and value_node.value == old_attr
            ):
                assignments.setdefault(target.id, []).append(value_node)
            else:
                blocked.add(target.id)

    for name in blocked:
        if name in assignments:
            assignments.setdefault(name, [])
            assignments[name].append(None)
    return assignments

def _python_attribute_replacements(value, old_attr, new_attr, attr_class, node_path, parm_name):
    replacements = []
    reasons = []
    skipped = []

    try:
        try:
            tree = ast.parse(value, mode="eval")
        except SyntaxError:
            tree = ast.parse(value, mode="exec")
    except SyntaxError as exc:
        if old_attr in value:
            skipped.append({
                "node_path": node_path,
                "parm_name": parm_name,
                "reason": "Python expression could not be parsed: {0}".format(exc),
            })
        return replacements, reasons, skipped

    assignments = _python_string_assignments(tree, old_attr)

    for call in [node for node in ast.walk(tree) if isinstance(node, ast.Call)]:
        method_name = _python_call_name(call)
        arg_indexes = _python_attribute_method_arg_indexes(method_name, attr_class)
        if not arg_indexes:
            continue

        for arg_index in arg_indexes:
            if arg_index >= len(call.args):
                continue

            arg = call.args[arg_index]
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value == old_attr
            ):
                replacement = _python_literal_replacement(value, arg, new_attr)
                if replacement:
                    replacements.append(replacement)
                    reasons.append("Python {0} attribute".format(method_name))
                continue

            if isinstance(arg, ast.Name):
                assigned_literals = assignments.get(arg.id)
                if assigned_literals is None:
                    continue
                if len(assigned_literals) == 1 and assigned_literals[0] is not None:
                    replacement = _python_literal_replacement(value, assigned_literals[0], new_attr)
                    if replacement:
                        replacements.append(replacement)
                        reasons.append("Python {0} local string reference".format(method_name))
                    continue

                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "Python {0} reference '{1}' has ambiguous local assignments".format(
                        method_name,
                        arg.id,
                    ),
                })
                continue

            arg_span = _ast_node_span(value, arg)
            arg_text = value[arg_span[0]:arg_span[1]] if arg_span else ""
            if old_attr in arg_text:
                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "Python {0} attribute name is generated by an unsupported expression".format(
                        method_name
                    ),
                })

    if replacements:
        reasons.append("Python attribute reference")
    return replacements, reasons, skipped

def _hscript_attribute_function_arg_indexes(function_name, attr_class):
    function_name = str(function_name).lower()
    attr_class = _normalize_attribute_class(attr_class)
    function_args = {
        ATTRIBUTE_CLASS_POINT: {
            "point": 2,
            "haspointattrib": 1,
        },
        ATTRIBUTE_CLASS_PRIMITIVE: {
            "prim": 2,
            "primuv": 2,
            "hasprimattrib": 1,
        },
        ATTRIBUTE_CLASS_VERTEX: {
            "vertex": 3,
            "hasvertexattrib": 1,
        },
        ATTRIBUTE_CLASS_DETAIL: {
            "detail": 1,
            "details": 1,
            "hasdetailattrib": 1,
        },
    }
    arg_index = function_args.get(attr_class, {}).get(function_name)
    if arg_index is None:
        return ()
    return (arg_index,)

def _hscript_attribute_args(value, attr_class):
    calls = []
    code_mask = labs_rename_rewrite.vex_code_mask(value)
    pattern = re.compile(
        r"\b(?P<function>point|primuv|prim|vertex|details|detail|haspointattrib|hasprimattrib|hasvertexattrib|hasdetailattrib)\s*\(",
        re.IGNORECASE,
    )
    for match in pattern.finditer(value):
        if not labs_rename_rewrite.span_is_code(code_mask, match.start(), match.end()):
            continue
        function_name = match.group("function")
        arg_indexes = _hscript_attribute_function_arg_indexes(function_name, attr_class)
        if not arg_indexes:
            continue

        open_index = match.end() - 1
        close_index = _matching_close_paren(value, open_index, code_mask=code_mask)
        if close_index < 0:
            continue

        args = _split_top_level_args(
            value[open_index + 1:close_index],
            open_index + 1,
        )
        for arg_index in arg_indexes:
            if arg_index >= len(args):
                continue
            arg_text, start, end = args[arg_index]
            calls.append({
                "function": function_name,
                "text": arg_text.strip(),
                "start": start,
                "end": end,
            })

    return calls

def _make_rename_edit(
    node_path,
    parm_name,
    old_value,
    new_value,
    reasons,
    value_kind="value",
    language=None,
    language_label="",
):
    edit = {
        "node_path": node_path,
        "parm_name": parm_name,
        "old_value": old_value,
        "new_value": new_value,
        "reasons": tuple(reasons),
        "value_kind": value_kind,
    }
    if language is not None:
        edit["language"] = language
    if language_label:
        edit["language_label"] = language_label
    return edit

def _referenced_string_parm_edit(
    node,
    node_path,
    source_parm_name,
    parm_name,
    old_attr,
    new_attr,
    function_name,
):
    if not parm_name or "/" in parm_name or "\\" in parm_name:
        return None, {
            "node_path": node_path,
            "parm_name": source_parm_name,
            "reason": "{0} chs() reference is not a simple local parameter".format(function_name),
        }

    parm = node.parm(parm_name) if node is not None else None
    if parm is None:
        return None, {
            "node_path": node_path,
            "parm_name": source_parm_name,
            "reason": "{0} chs() parameter '{1}' was not found".format(
                function_name,
                parm_name,
            ),
        }

    value = _parm_string_value(parm)
    if value != old_attr:
        return None, None

    if _parm_is_locked(parm):
        return None, {
            "node_path": node_path,
            "parm_name": parm_name,
            "reason": "referenced parameter is locked",
        }

    if _parm_should_skip_expression_state(node, parm, value):
        return None, {
            "node_path": node_path,
            "parm_name": parm_name,
            "reason": "referenced non-code parameter has keyframes or an expression",
        }

    return _make_rename_edit(
        node_path,
        parm_name,
        value,
        new_attr,
        ("{0} chs() reference".format(function_name),),
    ), None

def _rename_attribute_value(
    node,
    parm,
    value,
    old_attr,
    new_attr,
    attr_class,
    attr_like,
    vex_like,
    python_like=False,
    hscript_like=False,
    aggressive_vex=False,
):
    node_path = _node_path(node)
    parm_name = _parm_name(parm)
    replacements = []
    reasons = []
    extra_edits = []
    skipped = []
    escaped_old = re.escape(old_attr)

    if python_like:
        python_replacements, python_reasons, python_skips = _python_attribute_replacements(
            value,
            old_attr,
            new_attr,
            attr_class,
            node_path,
            parm_name,
        )
        replacements.extend(python_replacements)
        reasons.extend(python_reasons)
        skipped.extend(python_skips)

    if hscript_like:
        for call in _hscript_attribute_args(value, attr_class):
            function_name = call.get("function", "")
            arg_text = call.get("text", "")
            literal_value, quote = _string_literal_value(arg_text)
            if literal_value is not None:
                if literal_value == old_attr:
                    replacements.append({
                        "start": call["start"],
                        "end": call["end"],
                        "text": "{0}{1}{0}".format(quote, new_attr),
                    })
                    reasons.append("HScript {0} attribute".format(function_name))
                continue

            chs_parm = _chs_reference(arg_text)
            if chs_parm:
                edit, skip = _referenced_string_parm_edit(
                    node,
                    node_path,
                    parm_name,
                    chs_parm,
                    old_attr,
                    new_attr,
                    "HScript {0}".format(function_name),
                )
                if edit:
                    extra_edits.append(edit)
                if skip:
                    skipped.append(skip)
                continue

            if old_attr in arg_text:
                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "HScript {0} attribute name is generated by an unsupported expression".format(
                        function_name
                    ),
                })

    if vex_like:
        vex_code_mask = labs_rename_rewrite.vex_code_mask(value)
        target_function = _setattrib_function_for_class(attr_class)
        setattrib_calls = _setattrib_attribute_args(value)
        for call in setattrib_calls:
            function_name = call.get("function", "")
            if function_name != target_function:
                continue

            arg_text = call["text"]
            literal_value, quote = _string_literal_value(arg_text)
            if literal_value is not None:
                if literal_value == old_attr:
                    replacements.append({
                        "start": call["start"],
                        "end": call["end"],
                        "text": "{0}{1}{0}".format(quote, new_attr),
                    })
                    reasons.append("{0} literal".format(function_name))
                continue

            chs_parm = _chs_reference(arg_text)
            if chs_parm:
                edit, skip = _referenced_string_parm_edit(
                    node,
                    node_path,
                    parm_name,
                    chs_parm,
                    old_attr,
                    new_attr,
                    function_name,
                )
                if edit:
                    extra_edits.append(edit)
                if skip:
                    skipped.append(skip)
                continue

            if _is_simple_identifier(arg_text):
                assignments = _local_string_assignments(value, arg_text)
                if not assignments:
                    skipped.append({
                        "node_path": node_path,
                        "parm_name": parm_name,
                        "reason": "{0} reference '{1}' is not a simple local string or chs() value".format(
                            function_name,
                            arg_text,
                        ),
                    })
                    continue

                if len(assignments) > 1:
                    skipped.append({
                        "node_path": node_path,
                        "parm_name": parm_name,
                        "reason": "{0} reference '{1}' has ambiguous local assignments".format(
                            function_name,
                            arg_text,
                        ),
                    })
                    continue

                assignment = assignments[0]
                if assignment["kind"] == "literal":
                    if assignment.get("value") == old_attr:
                        replacements.append({
                            "start": assignment["start"],
                            "end": assignment["end"],
                            "text": "{0}{1}{0}".format(assignment.get("quote", '"'), new_attr),
                        })
                        reasons.append("{0} local string reference".format(function_name))
                    continue

                if assignment["kind"] == "chs":
                    edit, skip = _referenced_string_parm_edit(
                        node,
                        node_path,
                        parm_name,
                        assignment.get("parm_name", ""),
                        old_attr,
                        new_attr,
                        function_name,
                    )
                    if edit:
                        extra_edits.append(edit)
                    if skip:
                        skipped.append(skip)
                    continue

            skipped.append({
                "node_path": node_path,
                "parm_name": parm_name,
                "reason": "{0} attribute name is generated by an unsupported expression".format(function_name),
            })

        typed_binding_pattern = re.compile(
            r"(?<![A-Za-z0-9_])([A-Za-z]?)@{0}(?![A-Za-z0-9_])".format(escaped_old)
        )
        typed_binding_replacements = []
        for match in typed_binding_pattern.finditer(value):
            if not labs_rename_rewrite.span_is_code(
                vex_code_mask, match.start(), match.end()
            ):
                continue
            typed_binding_replacements.append({
                "start": match.start(),
                "end": match.end(),
                "text": "{0}@{1}".format(match.group(1), new_attr),
            })
        if typed_binding_replacements:
            replacements.extend(typed_binding_replacements)
            reasons.append("VEX @ binding")

        if aggressive_vex:
            aggressive_replacements = labs_rename_rewrite.vex_exact_string_replacements(
                value, old_attr, new_attr
            )
            aggressive_replacements = [
                replacement
                for replacement in aggressive_replacements
                if not _span_overlaps(
                    replacement["start"],
                    replacement["end"],
                    ((item["start"], item["end"]) for item in replacements),
                )
            ]
            if aggressive_replacements:
                replacements.extend(aggressive_replacements)
                reasons.append("Aggressive VEX string")

    value_after_replacements = _replace_spans(value, replacements)

    if (
        attr_like
        and not python_like
        and not hscript_like
        and not _parm_is_vex_code_parameter(parm, value)
    ):
        token_pattern = re.compile(
            r"(?<![A-Za-z0-9_]){0}(?![A-Za-z0-9_])".format(escaped_old)
        )
        value_after_replacements, count = token_pattern.subn(new_attr, value_after_replacements)
        if count:
            reasons.append("attribute token")

    unique_reasons = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)

    return value_after_replacements, tuple(unique_reasons), extra_edits, skipped

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


def _collect_attribute_rename_edits(
    nodes,
    old_attr,
    new_attr,
    attr_class,
    rename_vex=True,
    rename_python=True,
    aggressive_vex=False,
    progress_callback=None,
):
    attr_class = _normalize_attribute_class(attr_class)
    edits = []
    skipped = []
    seen_parms = set()
    edit_index = {}

    for node in _iter_nodes_with_progress(
        nodes,
        "Finding attribute references",
        progress_callback=progress_callback,
    ):
        node_path = _node_path(node)
        if not node_path:
            continue

        try:
            parms = node.parms()
        except Exception as exc:
            skipped.append({
                "node_path": node_path,
                "parm_name": "<parms>",
                "reason": "could not inspect parameters: {0}".format(exc),
            })
            continue

        for parm in parms:
            parm_name = _parm_name(parm)
            if not parm_name:
                continue

            parm_key = (node_path, parm_name)
            if parm_key in seen_parms:
                continue
            seen_parms.add(parm_key)

            source = _parm_rename_source(parm)
            if source is None:
                continue

            value = source.get("value")
            if old_attr not in str(value or "") and "chs(" not in str(value or ""):
                continue
            value_kind = source.get("kind", "value")
            language = source.get("language")
            language_kind = source.get("language_kind", "")
            language_label = source.get("language_label", "")
            attr_like = _parm_is_attribute_like(parm, value, old_attr)
            python_like = (
                language_kind == "python"
                or (
                    value_kind != "expression"
                    and _parm_looks_like_python_code(node, parm, value)
                )
            )
            hscript_like = (
                language_kind == "hscript"
                or (
                    value_kind != "expression"
                    and _parm_looks_like_hscript_code(node, parm, value)
                )
            )
            vex_like = (
                not python_like
                and not hscript_like
                and language_kind != "hscript"
                and _parm_looks_like_vex_code(node, parm, value)
            )

            if python_like and not rename_python:
                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "Python rename disabled",
                })
                continue

            if vex_like and not rename_vex:
                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "VEX rename disabled",
                })
                continue

            new_value, reasons, extra_edits, extra_skips = _rename_attribute_value(
                node,
                parm,
                value,
                old_attr,
                new_attr,
                attr_class,
                attr_like,
                vex_like,
                python_like=python_like,
                hscript_like=hscript_like,
                aggressive_vex=aggressive_vex,
            )
            skipped.extend(extra_skips)

            if new_value != value:
                edit = _make_rename_edit(
                    node_path,
                    parm_name,
                    value,
                    new_value,
                    reasons,
                    value_kind=value_kind,
                    language=language,
                    language_label=language_label,
                )

                if _parm_is_locked(parm):
                    edit["reason"] = "parameter is locked"
                    skipped.append(edit)
                    continue

                if (
                    value_kind != "expression"
                    and _parm_should_skip_expression_state(node, parm, value)
                ):
                    edit["reason"] = "non-code parameter has keyframes or an expression"
                    skipped.append(edit)
                    continue

                if not _append_unique_rename_edit(edits, edit, edit_index=edit_index):
                    skipped.append({
                        "node_path": node_path,
                        "parm_name": parm_name,
                        "reason": "multiple rename edits conflict for this parameter",
                    })

            for extra_edit in extra_edits:
                if not _append_unique_rename_edit(edits, extra_edit, edit_index=edit_index):
                    skipped.append({
                        "node_path": extra_edit.get("node_path", ""),
                        "parm_name": extra_edit.get("parm_name", ""),
                        "reason": "multiple rename edits conflict for this referenced parameter",
                    })

    return edits, skipped

def _group_vex_function_names(group_class):
    group_class = _normalize_group_class(group_class)
    if group_class == GROUP_CLASS_ANY:
        names = set()
        for concrete_class, _label in GROUP_CLASS_ITEMS:
            names.update(_group_vex_function_names(concrete_class))
        return names
    if group_class == GROUP_CLASS_POINT:
        return {
            "setpointgroup",
            "inpointgroup",
            "expandpointgroup",
            "npointsgroup",
        }
    if group_class == GROUP_CLASS_EDGE:
        return {
            "setedgegroup",
            "inedgegroup",
            "expandedgegroup",
            "nedgesgroup",
        }
    return {
        "setprimgroup",
        "inprimgroup",
        "expandprimgroup",
        "nprimitivesgroup",
    }


def _vex_group_args(value, group_class):
    calls = []
    code_mask = labs_rename_rewrite.vex_code_mask(value)
    names = _group_vex_function_names(group_class)
    pattern = re.compile(
        r"\b(?P<function>setpointgroup|setprimgroup|setedgegroup|inpointgroup|inprimgroup|inedgegroup|expandpointgroup|expandprimgroup|expandedgegroup|npointsgroup|nprimitivesgroup|nedgesgroup)\s*\(",
        re.IGNORECASE,
    )
    for match in pattern.finditer(value):
        if not labs_rename_rewrite.span_is_code(code_mask, match.start(), match.end()):
            continue
        function_name = match.group("function").lower()
        if function_name not in names:
            continue

        open_index = match.end() - 1
        close_index = _matching_close_paren(value, open_index, code_mask=code_mask)
        if close_index < 0:
            continue

        args = _split_top_level_args(
            value[open_index + 1:close_index],
            open_index + 1,
        )
        if len(args) < 2:
            continue

        arg_text, start, end = args[1]
        calls.append({
            "function": function_name,
            "text": arg_text.strip(),
            "start": start,
            "end": end,
        })

    return calls


def _python_group_method_names(group_class):
    group_class = _normalize_group_class(group_class)
    if group_class == GROUP_CLASS_ANY:
        names = set()
        for concrete_class, _label in GROUP_CLASS_ITEMS:
            names.update(_python_group_method_names(concrete_class))
        return names
    if group_class == GROUP_CLASS_POINT:
        return {
            "findPointGroup",
            "createPointGroup",
            "deletePointGroup",
            "destroyPointGroup",
        }
    if group_class == GROUP_CLASS_EDGE:
        return {
            "findEdgeGroup",
            "createEdgeGroup",
            "deleteEdgeGroup",
            "destroyEdgeGroup",
        }
    return {
        "findPrimGroup",
        "createPrimGroup",
        "deletePrimGroup",
        "destroyPrimGroup",
    }


def _python_group_replacements(value, old_group, new_group, group_class, node_path, parm_name):
    replacements = []
    reasons = []
    skipped = []

    try:
        try:
            tree = ast.parse(value, mode="eval")
        except SyntaxError:
            tree = ast.parse(value, mode="exec")
    except SyntaxError as exc:
        if old_group in value:
            skipped.append({
                "node_path": node_path,
                "parm_name": parm_name,
                "reason": "Python expression could not be parsed: {0}".format(exc),
            })
        return replacements, reasons, skipped

    assignments = _python_string_assignments(tree, old_group)
    group_methods = _python_group_method_names(group_class)

    for call in [node for node in ast.walk(tree) if isinstance(node, ast.Call)]:
        method_name = _python_call_name(call)
        if method_name not in group_methods or not call.args:
            continue

        arg = call.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value == old_group:
            replacement = _python_literal_replacement(value, arg, new_group)
            if replacement:
                replacements.append(replacement)
                reasons.append("Python {0} group".format(method_name))
            continue

        if isinstance(arg, ast.Name):
            assigned_literals = assignments.get(arg.id)
            if assigned_literals is None:
                continue
            if len(assigned_literals) == 1 and assigned_literals[0] is not None:
                replacement = _python_literal_replacement(value, assigned_literals[0], new_group)
                if replacement:
                    replacements.append(replacement)
                    reasons.append("Python {0} local string reference".format(method_name))
                continue

            skipped.append({
                "node_path": node_path,
                "parm_name": parm_name,
                "reason": "Python {0} group reference '{1}' has ambiguous local assignments".format(
                    method_name,
                    arg.id,
                ),
            })
            continue

        arg_span = _ast_node_span(value, arg)
        arg_text = value[arg_span[0]:arg_span[1]] if arg_span else ""
        if old_group in arg_text:
            skipped.append({
                "node_path": node_path,
                "parm_name": parm_name,
                "reason": "Python {0} group name is generated by an unsupported expression".format(method_name),
            })

    if replacements:
        reasons.append("Python group reference")
    return replacements, reasons, skipped


def _parm_is_group_like(node, parm):
    if _parm_is_named_for_groups(parm):
        return True

    node_type = _node_type_name(node)
    parm_name = _parm_name(parm).strip().lower()
    return "group" in node_type and parm_name in {
        "name",
        "name1",
        "newname",
        "rename",
    }


def _rename_group_value(
    node,
    parm,
    value,
    old_group,
    new_group,
    group_class,
    group_like,
    vex_like,
    python_like=False,
    hscript_like=False,
    aggressive_vex=False,
):
    node_path = _node_path(node)
    parm_name = _parm_name(parm)
    replacements = []
    reasons = []
    extra_edits = []
    skipped = []
    escaped_old = re.escape(old_group)

    if python_like:
        python_replacements, python_reasons, python_skips = _python_group_replacements(
            value,
            old_group,
            new_group,
            group_class,
            node_path,
            parm_name,
        )
        replacements.extend(python_replacements)
        reasons.extend(python_reasons)
        skipped.extend(python_skips)

    if vex_like:
        vex_code_mask = labs_rename_rewrite.vex_code_mask(value)
        group_calls = _vex_group_args(value, group_class)
        for call in group_calls:
            function_name = call.get("function", "")
            arg_text = call.get("text", "")
            literal_value, quote = _string_literal_value(arg_text)
            if literal_value is not None:
                if literal_value == old_group:
                    replacements.append({
                        "start": call["start"],
                        "end": call["end"],
                        "text": "{0}{1}{0}".format(quote, new_group),
                    })
                    reasons.append("{0} literal".format(function_name))
                continue

            chs_parm = _chs_reference(arg_text)
            if chs_parm:
                edit, skip = _referenced_string_parm_edit(
                    node,
                    node_path,
                    parm_name,
                    chs_parm,
                    old_group,
                    new_group,
                    function_name,
                )
                if edit:
                    extra_edits.append(edit)
                if skip:
                    skipped.append(skip)
                continue

            if old_group in arg_text:
                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "{0} group name is generated by an unsupported expression".format(function_name),
                })

        group_binding_pattern = re.compile(
            r"(?<![A-Za-z0-9_])([A-Za-z]?)@group_{0}(?![A-Za-z0-9_])".format(escaped_old)
        )
        for match in group_binding_pattern.finditer(value):
            if not labs_rename_rewrite.span_is_code(
                vex_code_mask, match.start(), match.end()
            ):
                continue
            replacements.append({
                "start": match.start(),
                "end": match.end(),
                "text": "{0}@group_{1}".format(match.group(1), new_group),
            })
        if replacements:
            reasons.append("VEX group reference")

        if aggressive_vex:
            aggressive_replacements = labs_rename_rewrite.vex_exact_string_replacements(
                value, old_group, new_group
            )
            aggressive_replacements = [
                replacement
                for replacement in aggressive_replacements
                if not _span_overlaps(
                    replacement["start"],
                    replacement["end"],
                    ((item["start"], item["end"]) for item in replacements),
                )
            ]
            if aggressive_replacements:
                replacements.extend(aggressive_replacements)
                reasons.append("Aggressive VEX string")

    value_after_replacements = _replace_spans(value, replacements)

    if group_like and not python_like and not hscript_like and not _parm_is_vex_code_parameter(parm, value):
        token_pattern = re.compile(
            r"(?<![A-Za-z0-9_]){0}(?![A-Za-z0-9_])".format(escaped_old)
        )
        value_after_replacements, count = token_pattern.subn(new_group, value_after_replacements)
        if count:
            reasons.append("group token")

    unique_reasons = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)

    return value_after_replacements, tuple(unique_reasons), extra_edits, skipped


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


def _collect_group_rename_edits(
    nodes,
    old_group,
    new_group,
    group_class,
    rename_vex=True,
    rename_python=True,
    aggressive_vex=False,
    progress_callback=None,
):
    group_class = _normalize_group_class(group_class)
    edits = []
    skipped = []
    seen_parms = set()
    edit_index = {}

    for node in _iter_nodes_with_progress(
        nodes,
        "Finding group references",
        progress_callback=progress_callback,
    ):
        node_path = _node_path(node)
        if not node_path:
            continue

        try:
            parms = node.parms()
        except Exception as exc:
            skipped.append({
                "node_path": node_path,
                "parm_name": "<parms>",
                "reason": "could not inspect parameters: {0}".format(exc),
            })
            continue

        for parm in parms:
            parm_name = _parm_name(parm)
            if not parm_name:
                continue

            parm_key = (node_path, parm_name)
            if parm_key in seen_parms:
                continue
            seen_parms.add(parm_key)

            source = _parm_rename_source(parm)
            if source is None:
                continue

            value = source.get("value")
            if old_group not in str(value or "") and "chs(" not in str(value or ""):
                continue
            value_kind = source.get("kind", "value")
            language = source.get("language")
            language_kind = source.get("language_kind", "")
            language_label = source.get("language_label", "")
            group_like = _parm_is_group_like(node, parm)
            python_like = (
                language_kind == "python"
                or (
                    value_kind != "expression"
                    and _parm_looks_like_python_code(node, parm, value)
                )
            )
            hscript_like = (
                language_kind == "hscript"
                or (
                    value_kind != "expression"
                    and _parm_looks_like_hscript_code(node, parm, value)
                )
            )
            vex_like = (
                not python_like
                and not hscript_like
                and language_kind != "hscript"
                and _parm_looks_like_vex_code(node, parm, value)
            )

            if python_like and not rename_python:
                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "Python rename disabled",
                })
                continue

            if vex_like and not rename_vex:
                skipped.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "VEX rename disabled",
                })
                continue

            new_value, reasons, extra_edits, extra_skips = _rename_group_value(
                node,
                parm,
                value,
                old_group,
                new_group,
                group_class,
                group_like,
                vex_like,
                python_like=python_like,
                hscript_like=hscript_like,
                aggressive_vex=aggressive_vex,
            )
            skipped.extend(extra_skips)

            if new_value != value:
                edit = _make_rename_edit(
                    node_path,
                    parm_name,
                    value,
                    new_value,
                    reasons,
                    value_kind=value_kind,
                    language=language,
                    language_label=language_label,
                )
                _annotate_rename_edit(edit)

                if _parm_is_locked(parm):
                    edit["reason"] = "parameter is locked"
                    skipped.append(edit)
                    continue

                if value_kind != "expression" and _parm_should_skip_expression_state(node, parm, value):
                    edit["reason"] = "non-code parameter has keyframes or an expression"
                    skipped.append(edit)
                    continue

                if not _append_unique_rename_edit(edits, edit, edit_index=edit_index):
                    skipped.append({
                        "node_path": node_path,
                        "parm_name": parm_name,
                        "reason": "multiple rename edits conflict for this parameter",
                    })

            for extra_edit in extra_edits:
                _annotate_rename_edit(extra_edit)
                if not _append_unique_rename_edit(edits, extra_edit, edit_index=edit_index):
                    skipped.append({
                        "node_path": extra_edit.get("node_path", ""),
                        "parm_name": extra_edit.get("parm_name", ""),
                        "reason": "multiple rename edits conflict for this referenced parameter",
                    })

    return edits, skipped


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
):
    if _normalize_rename_kind(rename_kind) == RENAME_KIND_GROUP:
        edits, skipped = _collect_group_rename_edits(
            nodes,
            old_name,
            new_name,
            item_class,
            rename_vex=rename_vex,
            rename_python=rename_python,
            aggressive_vex=aggressive_vex,
            progress_callback=progress_callback,
        )
    else:
        edits, skipped = _collect_attribute_rename_edits(
            nodes,
            old_name,
            new_name,
            item_class,
            rename_vex=rename_vex,
            rename_python=rename_python,
            aggressive_vex=aggressive_vex,
            progress_callback=progress_callback,
        )
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


def _collect_upstream_attribute_rename_edits(source_sop, old_attr, new_attr, attr_class):
    nodes = _nodes_from_tuples(_iter_upstream_nodes_with_depth(source_sop))
    return _collect_attribute_rename_edits(nodes, old_attr, new_attr, attr_class)

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


def _focus_rename_node_paths(node_paths):
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
    return (
        "Preview rename {0} in {1}. Select parameter edits to apply. "
        "{2} safe edits, {3} skipped, {4} discovery issues."
    ).format(
        _rename_item_preview_text(rename_kind, attr_class, old_attr, new_attr),
        scope_label,
        len(edits),
        len(skipped),
        len(discovery_issues or ()),
    )


def _rename_risk_summary(nodes, edits, skipped, discovery_issues=None):
    scanned_nodes = len(_unique_nodes(nodes or []))
    edit_nodes = sorted(set(edit.get("node_path", "") for edit in edits if edit.get("node_path", "")))
    vex_edits = sum(1 for edit in edits if _edit_code_type(edit) == "VEX")
    python_edits = sum(1 for edit in edits if _edit_code_type(edit) == "Python")
    plain_edits = sum(1 for edit in edits if _edit_code_type(edit) == "Plain")
    locked_skips = sum(1 for skip in skipped if "locked" in str(skip.get("reason", "")).lower())
    conflict_skips = sum(1 for skip in skipped if "conflict" in str(skip.get("reason", "")).lower())
    high_risk_edits = sum(1 for edit in edits if _edit_risk(edit) == "High")
    return (
        "Scanned {0} nodes. Editable matches on {1} nodes. "
        "Plain {2}, VEX {3}, Python {4}. High risk {5}. "
        "Skipped {6}, Locked {7}, Conflicts {8}. Discovery Issues {9}."
    ).format(
        scanned_nodes,
        len(edit_nodes),
        plain_edits,
        vex_edits,
        python_edits,
        high_risk_edits,
        len(skipped),
        locked_skips,
        conflict_skips,
        len(discovery_issues or ()),
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
    from hutil.Qt import QtCore, QtWidgets

    class PlannedEditsDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(PlannedEditsDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            try:
                self.setWindowFlags(
                    self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
                )
            except Exception:
                pass

            self._edits = [_annotate_rename_edit(dict(edit)) for edit in edits]
            self._checked = _qt_checked_state(QtCore)
            self._unchecked = _qt_unchecked_state(QtCore)
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

            summary_label = QtWidgets.QLabel(
                _rename_risk_summary(
                    nodes,
                    self._edits,
                    skipped,
                    discovery_issues=discovery_issues,
                )
            )
            summary_label.setWordWrap(True)
            layout.addWidget(summary_label)

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
            self.table.setWordWrap(False)
            self.table.setTextElideMode(_qt_elide_none(QtCore))
            self.table.setHorizontalScrollBarPolicy(_qt_scrollbar_as_needed(QtCore))
            self.table.setVerticalScrollBarPolicy(_qt_scrollbar_as_needed(QtCore))
            self.table.setSelectionBehavior(_qt_select_rows(QtWidgets))
            self.table.setSelectionMode(_qt_extended_selection(QtWidgets))
            self.table.setEditTriggers(_qt_no_edit_triggers(QtWidgets))
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
            self.discovery_issues_button = QtWidgets.QPushButton(
                "View Discovery Issues ({0})".format(len(discovery_issues or ()))
            )
            self.discovery_issues_button.setVisible(bool(discovery_issues))
            button_layout.addWidget(self.back_button)
            button_layout.addWidget(self.select_all_button)
            button_layout.addWidget(self.select_none_button)
            button_layout.addWidget(self.discovery_issues_button)
            button_layout.addStretch(1)
            self.accept_button = QtWidgets.QPushButton("Accept")
            self.cancel_button = QtWidgets.QPushButton("Cancel")
            self.accept_button.setDefault(True)
            button_layout.addWidget(self.accept_button)
            button_layout.addWidget(self.cancel_button)
            layout.addLayout(button_layout)

            self.setLayout(layout)
            self.setMinimumSize(1080, 610)
            try:
                self.resize(1360, 720)
            except Exception:
                pass

            self.table.itemChanged.connect(self._apply_check_to_selected_rows)
            self.search_button.clicked.connect(self._apply_filter)
            self.search_edit.returnPressed.connect(self._apply_filter)
            self.search_edit.textChanged.connect(self._schedule_filter)
            self._filter_timer.timeout.connect(self._apply_filter)
            self.select_all_button.clicked.connect(lambda: self._set_all_checks(self._checked))
            self.select_none_button.clicked.connect(lambda: self._set_all_checks(self._unchecked))
            self.discovery_issues_button.clicked.connect(
                lambda: _show_discovery_issues(discovery_issues)
            )
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
                if obj is self.table.viewport() and event.type() == _qt_mouse_button_press(QtCore):
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

    parent = None
    try:
        parent = hou.qt.mainWindow()
    except Exception:
        pass

    dialog = PlannedEditsDialog(parent)
    exec_method = getattr(dialog, "exec", None)
    if exec_method is None:
        exec_method = getattr(dialog, "exec_")

    accepted = getattr(QtWidgets.QDialog, "Accepted", None)
    if accepted is None:
        accepted = QtWidgets.QDialog.DialogCode.Accepted

    if exec_method() != accepted:
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
    try:
        from hutil.Qt import QtCore, QtWidgets
    except Exception:
        _show_attribute_rename_warning("Rename report", details=report_text)
        return

    class RenameReportDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(RenameReportDialog, self).__init__(parent)
            self.setWindowTitle(RENAME_TITLE)
            try:
                self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
            except Exception:
                pass

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
            self.copy_button.clicked.connect(self._copy_report)
            self.close_button.clicked.connect(self.accept)

        def _copy_report(self):
            try:
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(self.text_edit.toPlainText())
                _show_status("Rename report copied.", hou.severityType.Message)
            except Exception as exc:
                _show_attribute_rename_warning("Could not copy rename report: {0}".format(exc))

    parent = None
    try:
        parent = hou.qt.mainWindow()
    except Exception:
        pass
    dialog = RenameReportDialog(parent)
    exec_method = getattr(dialog, "exec", None)
    if exec_method is None:
        exec_method = getattr(dialog, "exec_")
    exec_method()


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

def _rename_edit_current_value(parm, edit):
    if edit.get("value_kind") == "expression":
        expression_data = _parm_expression_data(parm)
        if expression_data is None:
            return None
        return expression_data.get("value")

    return _parm_string_value(parm)

def _apply_rename_edit_value(parm, edit):
    new_value = edit.get("new_value", "")
    if edit.get("value_kind") == "expression":
        language = edit.get("language")
        parm.setExpression(new_value, language=language, replace_expression=True)
        return

    parm.set(new_value)

def _apply_attribute_rename_edits(
    edits,
    skipped,
    old_attr,
    new_attr,
    attr_class,
    rename_kind=RENAME_KIND_ATTRIBUTE,
    discovery_issues=None,
):
    rename_kind = _normalize_rename_kind(rename_kind)
    if rename_kind == RENAME_KIND_GROUP:
        attr_class = _normalize_group_class(attr_class)
    else:
        attr_class = _normalize_attribute_class(attr_class)
    applied = []
    failed = []

    def _apply_selected_edits():
        for edit in edits:
            node_path = edit.get("node_path", "")
            parm_name = edit.get("parm_name", "")
            node = hou.node(node_path) if node_path else None
            parm = node.parm(parm_name) if node is not None and parm_name else None
            if parm is None:
                failed.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "parameter no longer exists",
                })
                continue

            current_value = _rename_edit_current_value(parm, edit)
            if current_value != edit.get("old_value", ""):
                failed.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "parameter changed since preview",
                })
                continue

            try:
                _apply_rename_edit_value(parm, edit)
                applied.append(edit)
            except Exception as exc:
                failed.append({
                    "node_path": node_path,
                    "parm_name": parm_name,
                    "reason": "could not set parameter: {0}".format(exc),
                })

    undo_label = "Rename {0}: {1} to {2}".format(_rename_kind_label(rename_kind), old_attr, new_attr)
    with hou.undos.group(undo_label):
        _apply_selected_edits()

    if applied:
        _set_matching_item(rename_kind, attr_class, new_attr)
        _set_rename_kind(rename_kind)

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
    return bool(applied)

def _attribute_rename_needs_apply_confirmation(selected_edits, scope_label):
    return (
        len(selected_edits) >= 10
        or scope_label == SCOPE_ALL_NODES_LABEL
        or any(_edit_risk(edit) == "High" for edit in selected_edits)
    )


def _confirm_any_class_group_rename(old_group, new_group, scope_label):
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
):
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
            )
        except Exception as exc:
            _show_attribute_rename_warning(
                "Rename failed: {0}".format(exc)
            )

    try:
        import hdefereval
        hdefereval.executeDeferred(_deferred_apply)
        return True
    except Exception as exc:
        _show_attribute_rename_warning(
            "Could not defer rename: {0}".format(exc)
        )
        return False

def _open_item_stage_for_scope(scope, scene_viewer=None, initial_context=None):
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

        try:
            edits, skipped = _collect_item_rename_edits(
                rename_kind,
                nodes,
                old_name,
                new_name,
                item_class,
                rename_vex=scope.get("rename_vex", True),
                rename_python=scope.get("rename_python", True),
                aggressive_vex=scope.get("aggressive_vex", False),
            )
        except Exception as exc:
            if exc.__class__.__name__ == "OperationInterrupted":
                _show_status(
                    "Rename scan canceled; no parameters were changed.",
                    hou.severityType.Message,
                )
                return _open_item_stage_for_scope(
                    scope,
                    scene_viewer,
                    initial_context=context,
                )
            _show_attribute_rename_warning(
                "Could not scan rename references: {0}".format(exc)
            )
            return False
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

        return _defer_apply_attribute_rename_edits(
            selected_edits,
            skipped,
            old_name,
            new_name,
            item_class,
            rename_kind=rename_kind,
            discovery_issues=discovery_issues,
        )


def _continue_rename_attribute_from_scope(scope, scene_viewer=None):
    return _open_item_stage_for_scope(scope, scene_viewer)


def _rename_attribute_from_popup(scene_viewer=None):
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


def _rename_attribute_upstream_from_popup(scene_viewer=None):
    return _rename_attribute_from_popup(scene_viewer)


def run():
    _rename_attribute_from_popup()
