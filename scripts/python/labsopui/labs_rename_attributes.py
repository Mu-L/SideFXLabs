"""Interactive Rename Attributes and Groups shelf tool.

The UI discovers references, collects user choices, previews edits, and
reports results. The engine classifies parameters and performs
language-specific planning. Nothing is written until the preview is accepted.
Before each write, the tool resolves and plans the target again, then verifies
the result. Ambiguous references are skipped rather than guessed.

The module is deliberately split into a read-only planning phase and a guarded
application phase. Planning may cook geometry and inspect parameter source, but
it never changes parameter values. Application treats every preview row as a
claim that must still be true: the node and parameter must be the same objects,
the source must have the same form, and replanning must produce the same edit.

This bias toward false negatives is intentional: a missed reference can be
handled manually, while a guessed rewrite can silently change a network. The
same policy guides traversal, parsing, stale checks, and restoration.
"""
import re
from collections import deque

import hou
from hutil.Qt import QtCore, QtWidgets

from . import labs_rename_attributes_engine as rename_engine


# Configuration, supported owner classes, and session keys

TITLE = "Rename Attributes and Groups"
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ATTRS = {
    "primitive": ("Primitive", "primAttribs", "findPrimAttrib"),
    "point": ("Point", "pointAttribs", "findPointAttrib"),
    "vertex": ("Vertex", "vertexAttribs", "findVertexAttrib"),
    "detail": ("Detail", "globalAttribs", "findGlobalAttrib"),
}
GROUPS = {
    "primitive": ("Primitive", "primGroups"),
    "point": ("Point", "pointGroups"),
    "edge": ("Edge", "edgeGroups"),
}
# Houdini exposes vertex attributes but no matching vertex-group API. Do not
# offer edits that the geometry and HOM lookups cannot verify safely.
UNSUPPORTED_GROUP_CLASS = "vertex"

# Stable session names let later runs restore the user's accepted choices.
SESSION_RENAME_KIND_NAME = "_labs_rename_attributes_kind"
SESSION_ATTRIBUTE_NAME = "_labs_select_node_attribute"
SESSION_ATTRIBUTE_CLASS_NAME = "_labs_select_node_attribute_class"
SESSION_GROUP_NAME = "_labs_rename_attributes_group"
SESSION_GROUP_CLASS_NAME = "_labs_rename_attributes_group_class"
_ACCEPTED = getattr(
    QtWidgets.QDialog,
    "Accepted",
    getattr(getattr(QtWidgets.QDialog, "DialogCode", object), "Accepted", 1),
)
_CHECK_STATE = getattr(QtCore.Qt, "CheckState", QtCore.Qt)
_CHECKED = getattr(QtCore.Qt, "Checked", getattr(_CHECK_STATE, "Checked", 2))
_UNCHECKED = getattr(
    QtCore.Qt, "Unchecked", getattr(_CHECK_STATE, "Unchecked", 0))


# Shelf entry and workflow

def run():
    """Run a rename for the current Network Editor selection.

    Discovery and preview are read-only. Parameters change only after the user
    accepts the preview.

    The workflow has four stages:

    1. Read the intended Network Editor selection and optionally expand it
       through editable internal nodes.
    2. Discover names and retain only candidates with a proven reference.
    3. Build a guarded preview in which individual edits can be deselected.
    4. Recheck, write, verify, and report the selected edits in one undo group.

    Cancellation before application leaves the HIP unchanged. The return value
    is true only when at least one parameter was successfully changed.
    """
    # Scanning and planning are read-only, so cancellation here leaves the HIP
    # unchanged.
    try:
        nodes, scope = _nodes()
        if nodes is None:
            return False
        if not nodes:
            _ui("Select one or more nodes first.", warning=True)
            return False

        settings = _options()
        if settings is None:
            return False
        kind, include_inside, rename_vex, rename_python = settings
        nodes, scope, traversal_issues = _scope_nodes(
            nodes, include_inside)

        # Offer only attributes and groups with a safely recognized reference.
        choice = _choose(
            nodes,
            kind,
            discovery_issues=traversal_issues,
            rename_vex=rename_vex,
            rename_python=rename_python,
        )
        if choice is None:
            return False
        kind, item_class, old, discovery_issues = choice

        new = _new_name(kind, item_class, old, nodes)
        if new is None:
            return False

        # Build the preview records without writing parameters. Unsafe or
        # dynamic references are reported as skipped.
        edits, skipped = collect_edits(
            nodes,
            kind,
            item_class,
            old,
            new,
            rename_vex=rename_vex,
            rename_python=rename_python,
        )
    except hou.OperationInterrupted:
        _ui("Scan canceled; no changes were made.")
        return False

    # Show the planned parameter edits and let the user deselect rows.
    preview_issues = (["Discovery: {}".format(issue)
        for issue in discovery_issues] + skipped)
    selected, identities = choose_edits(
        edits, preview_issues, kind, old, new, scope)
    if not selected:
        return False

    # Resolve and plan every selected target again, then write and verify it.
    try:
        applied, failed = apply_edits(
            selected,
            identities,
            kind,
            item_class,
            old,
            new,
            rename_vex=rename_vex,
            rename_python=rename_python,
        )
    except hou.OperationInterrupted:
        _ui("Rename canceled during application.", warning=True)
        return False
    selected_keys = {(edit["node_path"], edit["parm_name"])
        for edit in selected}
    deselected = [
        edit for edit in edits
        if (edit["node_path"], edit["parm_name"]) not in selected_keys]
    details = _report_details(
        applied, deselected, skipped, discovery_issues, failed)
    _ui(
        ("Rename finished: {} applied, {} deselected, {} skipped/discovery, "
         "{} failed.").format(
            len(applied), len(deselected),
            len(skipped) + len(discovery_issues), len(failed)),
        bool(failed), details,
        dialog=True)

    # After a successful rename, seed the next run with the new name. If
    # nothing was written, keep the selected old name.
    if applied:
        _store_item(kind, item_class, new)

    return bool(applied)


# Current Network Editor selection and optional inside-node traversal

def _nodes():
    """Read the selection from the intended visible Network Editor.

    Houdini keeps separate selections in different networks. Using the editor
    context avoids mixing retained selections.

    The editor under the pointer is the strongest indication of user intent.
    Without that signal, all visible current Network Editors must agree on the
    selected paths. Disagreement is treated as ambiguity and fails closed
    instead of combining or arbitrarily choosing retained selections.
    """
    editors = []
    try:
        for pane in hou.ui.paneTabs():
            if (
                pane.type() == hou.paneTabType.NetworkEditor
                and pane.isCurrentTab()
            ):
                editors.append(pane)
    except hou.OperationInterrupted:
        raise
    except Exception as error:
        _ui("The current Network Editor could not be inspected: {0}".format(
            error), warning=True)
        return None, ""

    under_cursor = None
    try:
        pane = hou.ui.paneTabUnderCursor()
        if (
            pane is not None
            and pane.type() == hou.paneTabType.NetworkEditor
        ):
            under_cursor = pane
    except hou.OperationInterrupted:
        raise
    except Exception:
        under_cursor = None

    # Prefer the Network Editor under the pointer. If there is none, proceed
    # only when every visible current editor reports the same selected paths.
    candidates = [under_cursor] if under_cursor is not None else editors
    selections = []
    for editor in candidates:
        try:
            parent = editor.pwd()
            selected = tuple(parent.selectedChildren())
        except hou.OperationInterrupted:
            raise
        except Exception as error:
            _ui("The current Network Editor selection could not be read: {0}".
                format(error), warning=True)
            return None, ""
        if selected:
            selections.append(selected)

    if not selections:
        return [], "Selected Nodes"
    unique = {
        tuple(node.path() for node in selected): selected
        for selected in selections
    }
    if len(unique) != 1:
        _ui(
            "Multiple visible Network Editors have different selections. "
            "Move the pointer over the intended editor and run the tool again.",
            warning=True,
        )
        return None, ""
    return list(next(iter(unique.values()))), "Selected Nodes"


def _scope_nodes(nodes, include_inside):
    """Return selected roots, optionally expanded to editable internal nodes.

    The returned scope label is user-facing and travels through the picker,
    preview, and final report. Traversal problems are returned separately so a
    readable branch can still be scanned while an uncertain branch is skipped.
    Turning Inside Nodes off never inspects children.
    """
    if not include_inside:
        return list(nodes), "Selected Nodes", []
    expanded, issues = _expand_inside_nodes(nodes)
    return expanded, "Selected Nodes + Inside Nodes", issues


def _node_path_for_issue(node, issues=None):
    """Read a node path for diagnostics without swallowing interruption."""
    try:
        return node.path()
    except hou.OperationInterrupted:
        raise
    except Exception as error:
        if issues is not None:
            issues.append(
                "<unknown>/<path>: could not inspect node path: {}".format(
                    error))
        return "<unknown>"


def _inspect_node(
        node, issues, method, issue_name, failure, fallback, transform):
    """Read one node property, reporting errors and failing closed.

    Ordinary inspection failures become diagnostics and return the supplied
    safe fallback. ``hou.OperationInterrupted`` is different: it represents a
    user cancellation and must propagate to the workflow-level handler.
    """
    path = _node_path_for_issue(node, issues)
    try:
        return transform(getattr(node, method)())
    except hou.OperationInterrupted:
        raise
    except Exception as error:
        issues.append("{}/<{}>: {}: {}".format(
            path, issue_name, failure, error))
        return fallback


def _node_children(node, issues):
    """Return inspectable children, or an empty tuple if they cannot be read."""
    return _inspect_node(
        node, issues, "children", "children",
        "could not inspect internal nodes", (),
        lambda children: tuple(child for child in children
                               if child is not None))


def _node_lock_state(node, issues):
    """Return the HDA lock state, or ``None`` when it cannot be determined."""
    return _inspect_node(
        node, issues, "isLockedHDA", "lock",
        "could not inspect asset lock state", None, bool)


def _editable_inside_state(node, issues):
    """Return whether a node is editable inside a locked HDA, or unknown."""
    return _inspect_node(
        node, issues, "isEditableInsideLockedHDA", "editable",
        "could not inspect internal editability", None, bool)


def _editable_islands_below(node, issues):
    """Find editable islands without including hidden locked-HDA nodes.

    Houdini may expose an editable node beneath otherwise locked
    implementation. Hidden descendants must be traversed to find that boundary,
    but they must not themselves enter the rename scope. Once an editable node
    is found, it becomes a normal traversal root and this search does not walk
    through it.

    For example, given ``locked/hidden/editable/child``, the search may inspect
    ``hidden`` to reach ``editable``. It returns ``editable`` only. The outer
    traversal later includes ``editable`` and ``child`` while keeping
    ``hidden`` out of the preview.
    """
    islands = []
    queue = deque(_node_children(node, issues))
    visited = set()
    while queue:
        child = queue.popleft()
        path = _node_path_for_issue(child, issues)
        if path == "<unknown>" or path in visited:
            continue
        visited.add(path)
        editable = _editable_inside_state(child, issues)
        if editable is None:
            continue
        if editable:
            # An editable island is a safe new traversal root. Its hidden
            # locked-HDA siblings remain excluded.
            islands.append(child)
            continue
        queue.extend(_node_children(child, issues))
    return islands


def _expand_inside_nodes(nodes):
    """Include roots and recurse only through safely editable descendants.

    Selected roots are always included. Unlocked roots recurse through their
    children normally. Locked roots contribute only editable islands found
    below their hidden implementation. If lock state or editability cannot be
    determined, that branch stops rather than assuming it is safe.

    Paths are used for deduplication because selected roots can overlap or lead
    to the same internal node through more than one traversal route.
    """
    expanded, issues, visited = [], [], set()
    queue = deque(nodes)
    while queue:
        node = queue.popleft()
        path = _node_path_for_issue(node, issues)
        if path == "<unknown>" or path in visited:
            continue
        visited.add(path)
        expanded.append(node)

        locked = _node_lock_state(node, issues)
        if locked is None:
            continue
        if locked:
            queue.extend(_editable_islands_below(node, issues))
        else:
            queue.extend(_node_children(node, issues))
    return expanded, issues


def collect_edits(
        nodes, kind, item_class, old, new, aggressive=False,
        rename_vex=True, rename_python=True, _progress=None):
    """Plan unique parameter edits and collect skip reasons.

    Picker qualification and the final preview use the same read-only planner,
    so both stages apply the same recognition rules.

    Each edit is a plain data record: it stores paths, names, source values,
    source form, storage type, reasons, and risk, but no live HOM objects. This
    makes preview data safe to retain while the modal dialog is open. Live
    nodes and parameters are resolved again only during guarded application.

    ``rename_vex`` and ``rename_python`` control language planning.
    ``aggressive`` remains for compatibility, but the workflow stays
    conservative. Locked or ambiguous references are reported as skipped.
    """
    edits, skipped, seen = [], [], set()
    for node in _iter_with_progress(
            nodes, "Finding attribute and group references",
            progress=_progress):
        for parm in node.parms():
            key = (node.path(), parm.name())
            # Scope expansion may reach a node by several paths. Deduplicate
            # the scan itself so edits and skipped diagnostics are not repeated.
            if key in seen:
                continue

            seen.add(key)
            edit, _extra, notes = rename_engine.plan_parameter_rewrite(
                node, parm, kind, item_class, old, new,
                rename_vex=rename_vex,
                rename_python=rename_python,
                aggressive_vex=False,
            )
            if edit:
                if parm.isLocked():
                    skipped.append("{}/{}: locked".format(*key))
                else:
                    edits.append(edit)
            skipped.extend(
                "{}/{}: {}".format(
                    note.get("node_path", key[0]),
                    note.get("parm_name", key[1]),
                    note.get("reason", ""),
                )
                for note in notes
            )
    return edits, skipped


# Qt dialogs and preview lifetime

def _target_identity(node, parm):
    """Return the session-local identities of a node and parameter tuple.

    A path and parameter name are not sufficient stale guards. A node can be
    deleted and recreated at the same path, and a spare parameter tuple can be
    replaced under the same name. The node session ID and tuple pointer detect
    both cases within the current Houdini session.
    """
    return int(node.sessionId()), int(parm.tuple()._asVoidPointer())


class _PreviewGuard(object):
    """Expire the preview when a watched target changes.

    The guard uses two complementary protections. Node event callbacks mark the
    preview invalid as soon as Houdini reports a relevant mutation. Validation
    then resolves every target again and compares its recorded node and
    parameter identities. The second check covers replacement and any change
    that did not produce a usable callback event.

    The guard owns its callbacks. It must be closed after the modal dialog on
    every success, cancellation, and exception path so callbacks cannot retain
    Python objects or affect later runs.
    """

    _EVENT_NAMES = (
        "BeingDeleted",
        "NameChanged",
        "SpareParmTemplatesChanged",
        "ParmTupleChanged",
        "ParmTupleAnimated",
        "ParmTupleChannelChanged",
        "ParmTupleLockChanged",
    )

    def __init__(self, edits):
        """Watch target nodes and record their node and parameter identities.

        One callback is installed per distinct node, while identities are kept
        per node/parameter key. Guard setup fails if a target has already
        disappeared or if duplicate preview rows resolve inconsistently.
        """
        owner = getattr(hou, "nodeEventType", None)
        if owner is None:
            raise RuntimeError("Houdini node event metadata is unavailable")
        events = tuple(
            getattr(owner, name)
            for name in self._EVENT_NAMES
            if getattr(owner, name, None) is not None
        )
        if not all(
            getattr(owner, name, None) is not None
            for name in ("BeingDeleted", "NameChanged",
                         "SpareParmTemplatesChanged")
        ):
            raise RuntimeError("required Houdini node events are unavailable")

        self._events = events
        self._watched = []
        self._invalid = ""
        self._closed = False
        self.identities = {}
        try:
            for edit in edits:
                key = (edit["node_path"], edit["parm_name"])
                node = hou.node(key[0])
                parm = node.parm(key[1]) if node is not None else None
                if parm is None:
                    raise RuntimeError(
                        "{}/{} no longer exists".format(*key))
                identity = _target_identity(node, parm)
                previous = self.identities.get(key)
                if previous is not None and previous != identity:
                    raise RuntimeError(
                        "{}/{} changed during preview setup".format(*key))
                self.identities[key] = identity
                if any(record[0] is node for record in self._watched):
                    continue

                # Default arguments freeze this node's guard and path. A direct
                # loop-variable capture would make every callback report the
                # final node.
                def changed(_guard=self, _path=node.path(), **kwargs):
                    if not _guard._closed:
                        _guard._invalid = (
                            "target node '{}' changed while preview was open".
                            format(_path))

                node.addEventCallback(events, changed)
                self._watched.append((node, changed))
        except Exception:
            self.close()
            raise

    def validate(self):
        """Return why the preview expired, or an empty string if it is valid.

        Callback invalidation is checked first. The identity pass then catches
        targets deleted or replaced while the dialog was open. A non-empty
        result prevents every preview row from being applied.
        """
        if self._closed:
            return "preview tracking is no longer active"
        if self._invalid:
            return self._invalid
        for key, expected in self.identities.items():
            node = hou.node(key[0])
            parm = node.parm(key[1]) if node is not None else None
            if parm is None:
                return "{}/{} no longer exists".format(*key)
            if _target_identity(node, parm) != expected:
                return "{}/{} was replaced".format(*key)
        return ""

    def close(self):
        """Remove all callbacks; repeated cleanup is safe.

        Cleanup suppresses callback-removal errors because it may run while
        unwinding a different setup or dialog exception.
        """
        if self._closed:
            return
        self._closed = True
        # Reverse registration order lets partial setup unwind cleanly.
        for node, callback in reversed(self._watched):
            try:
                node.removeEventCallback(self._events, callback)
            except Exception:
                pass
        self._watched = []


def _add_dialog_buttons(
        dialog, layout, accept_text="Accept", leading=()):
    """Add a standard accept-and-cancel footer."""
    row = QtWidgets.QHBoxLayout()
    for button in leading:
        row.addWidget(button)
    row.addStretch(1)
    accept = QtWidgets.QPushButton(accept_text)
    cancel = QtWidgets.QPushButton("Cancel")
    row.addWidget(accept)
    row.addWidget(cancel)
    layout.addLayout(row)
    accept.clicked.connect(dialog.accept)
    cancel.clicked.connect(dialog.reject)


def _exec_dialog(dialog):
    """Open a modal dialog using either supported Qt API."""
    return dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


class _PreviewDialog(QtWidgets.QDialog):
    """Show planned edits with a checkbox for each parameter."""

    def __init__(self, edits, skipped, kind, old, new, scope, parent=None):
        super(_PreviewDialog, self).__init__(parent)
        self.setWindowTitle(TITLE)
        self.setMinimumSize(900, 500)
        self.resize(1050, 500)
        self._edits = tuple(edits)
        layout = QtWidgets.QVBoxLayout(self)
        summary = (
            "Preview: {0} '{1}' \u2192 '{2}' \u00b7 {3} \u00b7 "
            "{4} edit{5} \u00b7 {6} skipped"
        ).format(
            kind,
            old,
            new,
            scope,
            len(edits),
            "" if len(edits) == 1 else "s",
            len(skipped),
        )
        layout.addWidget(QtWidgets.QLabel(summary))
        table = QtWidgets.QTableWidget(len(edits), 5)
        self.table = table
        table.setHorizontalHeaderLabels(
            ("Apply", "Node", "Parameter", "Change", "Reason"))
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        for row, edit in enumerate(edits):
            check = QtWidgets.QTableWidgetItem()
            check.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            check.setCheckState(_CHECKED)
            table.setItem(row, 0, check)
            reason = ", ".join(edit.get("reasons", ())) or "safe"
            values = (
                edit["node_path"],
                edit["parm_name"],
                "{} \u2192 {}".format(
                    edit["old_value"].replace("\n", "\\n"),
                    edit["new_value"].replace("\n", "\\n"),
                ),
                reason,
            )
            for column, value in enumerate(values, 1):
                item = QtWidgets.QTableWidgetItem(
                    value if len(value) <= 180 else value[:177] + "...")
                item.setToolTip(value)
                table.setItem(row, column, item)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 55)
        table.setColumnWidth(1, 260)
        table.setColumnWidth(2, 150)
        table.setColumnWidth(3, 360)
        layout.addWidget(table)

        select_all = QtWidgets.QPushButton("Select All")
        select_none = QtWidgets.QPushButton("Select None")
        _add_dialog_buttons(
            self, layout, leading=(select_all, select_none))
        select_all.clicked.connect(lambda: self._set_all(True))
        select_none.clicked.connect(lambda: self._set_all(False))

    def _set_all(self, checked):
        state = _CHECKED if checked else _UNCHECKED
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(state)

    def selected(self):
        return [
            edit
            for row, edit in enumerate(self._edits)
            if self.table.item(row, 0).checkState() == _CHECKED
        ]


class _OptionsDialog(QtWidgets.QDialog):
    """Choose the rename kind, scope, and enabled code languages."""

    def __init__(self, initial_kind, parent=None):
        super(_OptionsDialog, self).__init__(parent)
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(390)

        layout = QtWidgets.QVBoxLayout(self)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Rename"))
        self.kind_combo = QtWidgets.QComboBox()
        self.kind_combo.addItem("Attributes", "attribute")
        self.kind_combo.addItem("Groups", "group")
        self.kind_combo.setCurrentIndex(
            1 if initial_kind == "group" else 0)
        row.addWidget(self.kind_combo, 1)
        layout.addLayout(row)

        self.inside_check = QtWidgets.QCheckBox("Inside Nodes")
        self.inside_check.setToolTip(
            "Also inspect editable nodes contained by the selection.")
        self.inside_check.setChecked(True)
        layout.addWidget(self.inside_check)

        self.vex_check = QtWidgets.QCheckBox("Rename in VEX")
        self.vex_check.setToolTip(
            "Update direct, safely recognized references in VEX parameters.")
        self.vex_check.setChecked(True)
        layout.addWidget(self.vex_check)

        self.python_check = QtWidgets.QCheckBox("Rename in Python")
        self.python_check.setToolTip(
            "Update direct, safely recognized references in Python parameters.")
        self.python_check.setChecked(True)
        layout.addWidget(self.python_check)

        _add_dialog_buttons(self, layout, accept_text="Next")

    def options(self):
        """Return the rename kind, scope, and code-language settings."""
        return (
            self.kind_combo.currentData(),
            self.inside_check.isChecked(),
            self.vex_check.isChecked(),
            self.python_check.isChecked(),
        )


def _options():
    """Show the start dialog and remember only the rename kind."""
    dialog = _OptionsDialog(_stored_kind(), hou.qt.mainWindow())
    result = _exec_dialog(dialog)
    if result != _ACCEPTED:
        return None
    settings = dialog.options()
    setattr(hou.session, SESSION_RENAME_KIND_NAME, settings[0])
    return settings


class _CandidateDialog(QtWidgets.QDialog):
    """Let the user choose one discovered attribute or group."""

    def __init__(self, labels, kind, default_index=None, parent=None):
        super(_CandidateDialog, self).__init__(parent)
        self.setWindowTitle(TITLE)
        self.setMinimumSize(560, 420)

        layout = QtWidgets.QVBoxLayout(self)
        article = "an" if kind == "attribute" else "a"
        layout.addWidget(QtWidgets.QLabel(
            "Choose {} {} to rename.".format(article, kind)))

        self.list = QtWidgets.QListWidget()
        self.list.addItems(labels)
        self.list.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        layout.addWidget(self.list)

        _add_dialog_buttons(self, layout)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())

        index = default_index if default_index is not None else 0
        if 0 <= index < self.list.count():
            self.list.setCurrentRow(index)

    def selected_index(self):
        """Return the selected row, or ``None`` if nothing is selected."""
        index = self.list.currentRow()
        return index if index >= 0 else None


def choose_edits(edits, skipped, kind, old, new, scope):
    """Preview guarded edits and return the selected rows and identities.

    Guarding begins before the modal dialog opens. If the user cancels, no safe
    edits exist, guard setup fails, or validation detects a scene change, the
    function returns an empty selection and identity map. On success, the
    identity map covers the guarded preview targets and accompanies the rows
    selected for application.

    Callback cleanup lives in ``finally`` so the guard never outlives the
    dialog, regardless of how the dialog exits.
    """
    if not edits:
        _ui(
            "No safe {} references to '{}' were found in {}.".format(
                kind, old, scope), True, "\n".join(skipped))
        return [], {}

    try:
        guard = _PreviewGuard(edits)
    except hou.OperationInterrupted:
        raise
    except Exception as error:
        _ui("The preview could not guard its targets: {}".format(error), True)
        return [], {}

    try:
        dialog = _PreviewDialog(
            edits, skipped, kind, old, new, scope, hou.qt.mainWindow())
        result = _exec_dialog(dialog)
        if result != _ACCEPTED:
            return [], {}
        problem = guard.validate()
        if problem:
            _ui(
                "The preview expired because the scene changed. "
                "Run the tool again.\n\n{}".format(problem),
                True,
            )
            return [], {}
        return dialog.selected(), dict(guard.identities)
    finally:
        # Always detach callbacks when the dialog closes. Leaving them attached
        # would retain Python objects and could invalidate later runs.
        guard.close()


# Rechecking, writing, restoration, and one-step undo

def _expected_source(edit, value_key):
    """Return the exact source state expected before or after a write.

    The tuple order matches ``parameter_source``: value, value kind, expression
    language, and storage type. Comparing all four fields prevents a matching
    string from hiding a change in how Houdini interprets or stores it.
    """
    return (
        edit[value_key],
        edit["value_kind"],
        edit.get("language"),
        edit["storage_type"],
    )


def _restore_after_error(parm, original):
    """Best-effort restore after a setter exception or interruption.

    Restoration runs while handling an existing failure, so another setter
    error is deliberately suppressed. The original failure remains the one
    reported to the user.
    """
    if parm is None or original is None:
        return
    try:
        _set_parm(parm, *original)
    except Exception:
        pass


def apply_edits(
        edits, identities, kind, item_class, old_name, new_name,
        rename_vex=True, rename_python=True):
    """Recheck and apply selected edits as one verified undo batch.

    Every preview row passes the same sequence before it counts as applied:

    1. Resolve the node and parameter again.
    2. Match their session-local identities to the preview snapshot.
    3. Match the exact source value, form, language, and storage type.
    4. Replan the parameter to confirm that the reference still means the same
       thing under its current menu, Run Over class, and parameter template.
    5. Write in the original source form and read the parameter back.
    6. Count the edit only if read-back verification matches the planned state.

    Missing or stale targets are independent failures; they are reported and
    the next safe parameter is attempted. A setter failure restores the
    original source best-effort. User interruption also restores the active
    parameter, records how many earlier edits succeeded, and stops the
    remaining batch. All successful writes share one Houdini undo group.
    """
    applied, failed = [], []
    # Keep successful writes in one undo group. A failure on one parameter is
    # reported without blocking other safe edits.
    with hou.undos.group(TITLE):
        for edit in edits:
            original = None
            parm = None
            target = "{}/{}".format(
                edit["node_path"], edit["parm_name"])
            try:
                node = hou.node(edit["node_path"])
                parm = node.parm(edit["parm_name"]) if node else None
                if parm is None:
                    failed.append(
                        "{}: parameter no longer exists".format(target))
                    continue

                identity_problem = _identity_problem(
                    node, parm, edit, identities)
                if identity_problem:
                    failed.append(
                        "{}: changed since preview ({})".format(
                            target, identity_problem))
                    continue

                current = tuple(rename_engine.parameter_source(parm))
                if current != _expected_source(edit, "old_value"):
                    failed.append(
                        "{}: source changed since preview".format(target))
                    continue

                canonical, _extra, _notes = (
                    rename_engine.plan_parameter_rewrite(
                        node,
                        parm,
                        kind,
                        item_class,
                        old_name,
                        new_name,
                        rename_vex=rename_vex,
                        rename_python=rename_python,
                    )
                )
                if canonical != edit:
                    # Matching text does not prove matching meaning. A changed
                    # menu, Run Over class, or parameter template can change
                    # the reference, so plan it again.
                    failed.append("{}: reference meaning changed since "
                                  "preview".format(target))
                    continue

                original = current[:3]
                _set_parm(
                    parm,
                    edit["new_value"],
                    edit["value_kind"],
                    edit.get("language"),
                )
                written = tuple(rename_engine.parameter_source(parm))
                if written != _expected_source(edit, "new_value"):
                    # A setter may fail silently or coerce storage. Restore the
                    # exact source form before trying another parameter.
                    _set_parm(parm, *original)
                    failed.append(
                        "{}: write verification failed; source restored".
                        format(target))
                    continue
                applied.append(edit)
            except hou.OperationInterrupted:
                _restore_after_error(parm, original)
                failed.append(
                    "Rename interrupted after {} applied edit{}; remaining "
                    "edits were not attempted.".format(
                        len(applied), "" if len(applied) == 1 else "s"))
                break
            except Exception as error:
                _restore_after_error(parm, original)
                failed.append("{}: {}".format(target, error))
    return applied, failed


def _identity_problem(node, parm, edit, identities):
    """Explain why a target no longer matches its preview identity."""
    key = (edit["node_path"], edit["parm_name"])
    expected = identities.get(key)
    if expected is None:
        return "target was not guarded by the preview"
    try:
        current = _target_identity(node, parm)
    except hou.OperationInterrupted:
        raise
    except Exception as error:
        return "identity could not be inspected: {}".format(error)
    return "" if current == expected else "node or parameter was replaced"


def _set_parm(parm, value, kind, language):
    """Write source in its original form: expression or plain value."""
    if kind == "expression":
        parm.setExpression(value, language=language)
    else:
        parm.set(value)


# Candidate discovery and safe-reference filtering

def _choose(
        nodes, kind, discovery_issues=(),
        rename_vex=True, rename_python=True):
    """Ask the user which discovered name to rename.

    Geometry and parameter-only names pass through the final preview's planner,
    so the picker offers only candidates with an actionable reference.
    """
    choices, issues = _discover_geometry(nodes, kind)
    issues[:0] = list(discovery_issues)
    text_choices, text_issues = _discover_text(nodes, kind)
    # A parameter may reference a group that is absent from the cooked output,
    # so supplement geometry discovery with parameter discovery.
    issues.extend(text_issues)
    for choice in text_choices:
        if choice not in choices:
            choices.append(choice)

    choices, locations, filtered_issues = _filter_choices_by_safe_locations(
        nodes,
        kind,
        choices,
        rename_vex=rename_vex,
        rename_python=rename_python,
    )
    issues.extend(
        issue for issue in filtered_issues if issue not in issues)

    if not choices:
        _ui("No {}s with safe parameter references were found in this scope.".
            format(kind), True,
            "\n".join(issues))
        return None
    labels = [
        _choice_label(kind, choice, locations.get(choice))
        for choice in choices]
    stored_name, stored_class = _stored_item(kind)
    default_index = next(
        (index for index, choice in enumerate(choices)
         if choice == (stored_class, stored_name)),
        None)
    dialog = _CandidateDialog(
        labels, kind, default_index, hou.qt.mainWindow())
    result = _exec_dialog(dialog)
    if result != _ACCEPTED:
        return None

    selected = dialog.selected_index()
    if selected is None:
        return None
    item_class, name = choices[selected]
    _store_item(kind, item_class, name)
    return kind, item_class, name, tuple(issues)


def _discover_geometry(nodes, kind):
    """Collect attribute or group names from every SOP output."""
    table = ATTRS if kind == "attribute" else GROUPS
    choices, seen, issues = [], set(), []
    for node in _iter_with_progress(nodes, "Scanning geometry for names"):
        if node.type().category() != hou.sopNodeTypeCategory():
            continue
        # A terminal SOP still has one geometry output to inspect. Inspect every
        # output of a multi-output SOP so valid names are not missed.
        output_count = len(node.outputConnectors()) or 1
        for output_index in range(output_count):
            try:
                # Newer Houdini versions accept an output index. The fallback
                # keeps the first output inspectable on older HOM APIs.
                geo = node.geometry(output_index)
            except TypeError:
                if output_index:
                    issues.append(
                        "{} output {} cannot be inspected".format(
                            node.path(), output_index + 1))
                    continue
                geo = node.geometry()
            except hou.OperationInterrupted:
                raise
            except hou.Error as error:
                issues.append("{} output {}: {}".format(
                    node.path(), output_index + 1, error))
                continue

            if geo is None:
                issues.append("{} output {} returned no geometry".format(
                    node.path(), output_index + 1))
                continue

            for item_class, spec in table.items():
                for item in getattr(geo, spec[1])():
                    name = item.name().strip()
                    # P is Houdini's built-in point-position attribute, not a
                    # normal user-defined rename candidate.
                    hidden = kind == "attribute" and name == "P"
                    if name and not hidden and (item_class, name) not in seen:
                        seen.add((item_class, name))
                        choices.append((item_class, name))
    return choices, issues


def _discover_text(nodes, kind):
    """Collect exact names from metadata-proven parameter fields."""
    if kind not in ("attribute", "group"):
        return [], []
    name_reader = (
        rename_engine._plain_attribute_names
        if kind == "attribute"
        else rename_engine._plain_group_names
    )
    reference_reader = (
        rename_engine._inspect_attribute_reference
        if kind == "attribute"
        else rename_engine._inspect_group_reference
    )
    choices, seen, issues = [], set(), []
    for node in _iter_with_progress(
            nodes, "Scanning {} parameters for names".format(kind)):
        for parm in node.parms():
            try:
                field_kind, _metadata_owner = (
                    rename_engine.inspect_plain_field(node, parm))
            except hou.OperationInterrupted:
                raise
            except hou.Error as error:
                issues.append(
                    "{}/{}: could not inspect {} metadata: {}".format(
                        node.path(), parm.name(), kind, error))
                continue
            if field_kind != kind:
                continue

            try:
                text, _kind, _language, _storage = (
                    rename_engine.parameter_source(parm))
            except hou.OperationInterrupted:
                raise
            except hou.Error as error:
                issues.append(
                    "{}/{}: could not inspect {} value: {}".format(
                        node.path(), parm.name(), kind, error))
                continue
            if not text:
                continue

            for name in name_reader(text):
                if kind == "attribute" and name == "P":
                    continue
                try:
                    item_class, problem = reference_reader(node, parm, name)
                except hou.OperationInterrupted:
                    raise
                except hou.Error as error:
                    item_class = None
                    problem = "could not inspect {} owner: {}".format(
                        kind, error)
                if item_class is None:
                    issue = "{}/{}: {}".format(
                        node.path(), parm.name(),
                        problem or "{} owner is not proven".format(kind))
                    if issue not in issues:
                        issues.append(issue)
                    continue
                if kind == "group" and item_class == UNSUPPORTED_GROUP_CLASS:
                    issue = "{}/{}: vertex groups are not supported".format(
                        node.path(), parm.name())
                    if issue not in issues:
                        issues.append(issue)
                    continue
                pair = (item_class, name)
                if pair not in seen:
                    seen.add(pair)
                    choices.append(pair)
    return choices, issues


def _filter_choices_by_safe_locations(
        nodes, kind, choices, rename_vex=True, rename_python=True):
    """Keep candidates with at least one safely plannable reference.

    Reusing the read-only ``collect_edits`` planner keeps picker eligibility
    aligned with the final preview.
    """
    nodes, choices = list(nodes), list(choices)
    offered, locations, issues = [], {}, []
    for item_class, old in choices:
        choice = (item_class, old)
        edits, skipped = collect_edits(
            nodes, kind, item_class, old,
            _rename_location_probe_name(old),
            rename_vex=rename_vex,
            rename_python=rename_python,
        )
        locations[choice] = tuple(edits)
        if edits:
            offered.append(choice)
        else:
            issues.extend(item for item in skipped if item not in issues)
    return offered, locations, issues


def _rename_location_probe_name(old):
    """Return a harmless replacement used only to find editable locations."""
    probe = "__labs_rename_location_probe__"
    return probe + "new" if probe == old else probe


def _choice_label(kind, choice, locations=None):
    """Build a picker label with the number of editable matches."""
    item_class, name = choice
    label = "{}: {}".format(_class_label(kind, item_class), name)
    if locations is None:
        return label
    count = len(locations)
    return "{} ({} match{})".format(
        label, count, "" if count == 1 else "es")


def _class_label(kind, item_class):
    """Return the owner-class label shown in the picker."""
    return (ATTRS if kind == "attribute" else GROUPS)[item_class][0]


# Session defaults, name validation, and reporting

def _stored_kind():
    """Load a valid last-used rename kind."""
    # Session data may outlive this tool version, so validate stored values.
    kind = getattr(hou.session, SESSION_RENAME_KIND_NAME, "attribute")
    kind = str(kind or "").strip().lower()
    return kind if kind in ("attribute", "group") else "attribute"


def _stored_item(kind):
    """Load a valid last-used name and owner class.

    Invalid or obsolete session values fall back to supported defaults.
    """
    if kind == "group":
        name_key, class_key = SESSION_GROUP_NAME, SESSION_GROUP_CLASS_NAME
        default_name, valid_classes = "group1", set(GROUPS)
    else:
        name_key, class_key = (
            SESSION_ATTRIBUTE_NAME, SESSION_ATTRIBUTE_CLASS_NAME)
        default_name, valid_classes = "selectnode", set(ATTRS)
    name = getattr(hou.session, name_key, default_name)
    name = name.strip() if isinstance(name, str) else default_name
    item_class = getattr(hou.session, class_key, "primitive")
    item_class = str(item_class or "").strip().lower()
    return (
        name or default_name,
        (item_class if item_class in valid_classes else "primitive"))


def _store_item(kind, item_class, name):
    """Remember the chosen name and owner class for the next run."""
    if kind == "group":
        setattr(hou.session, SESSION_GROUP_NAME, name)
        setattr(hou.session, SESSION_GROUP_CLASS_NAME, item_class)
    else:
        setattr(hou.session, SESSION_ATTRIBUTE_NAME, name)
        setattr(hou.session, SESSION_ATTRIBUTE_CLASS_NAME, item_class)


def _new_name(kind, item_class, old, nodes):
    """Ask for and validate a replacement name in the scanned scope.

    Names must be identifiers and must differ from the original. Discovery is
    repeated after input so collision advice reflects the current scene.
    """
    initial = old
    while True:
        button, entered = hou.ui.readInput(
            "Rename {} '{}' to:".format(kind, old),
            buttons=("Preview", "Cancel"),
            close_choice=1, title=TITLE, initial_contents=initial)
        if button:
            return None
        name = entered.strip()
        if IDENT.match(name) and name != old:
            break
        if name == old:
            problem = "Enter a name different from '{}'.".format(old)
        else:
            problem = (
                "Enter an identifier beginning with a letter or underscore "
                "and containing only letters, numbers, and underscores.")
        _ui(problem, warning=True)
        # Keep invalid text in the field so the user can correct it in place.
        initial = entered

    # Discover again because cooking or callbacks may have changed the scene
    # while the input dialog was open. Merging with an existing name is allowed
    # only after the user explicitly accepts the collision.
    choices, _issues = _discover_geometry(nodes, kind)
    text_choices, _text_issues = _discover_text(nodes, kind)
    choices.extend(choice for choice in text_choices if choice not in choices)
    collision = any(
        choice_name == name and (
            choice_class == item_class)
        for choice_class, choice_name in choices)
    if collision:
        answer = hou.ui.displayMessage(
            "A {} named '{}' already exists in the scanned scope. Continue?".
            format(kind, name),
            buttons=("Continue", "Cancel"),
            default_choice=1,
            close_choice=1,
            title=TITLE,
            severity=hou.severityType.Warning)
        if answer:
            return None
    return name


def _label(edit):
    """Format an edit as a compact preview or report row."""
    old = edit["old_value"].replace("\n", "\\n")[:90]
    new = edit["new_value"].replace("\n", "\\n")[:90]
    reason = ", ".join(edit.get("reasons", ())) or "safe"
    return "{}/{}  [{}]  {} -> {}".format(
        edit["node_path"], edit["parm_name"], reason,
        old, new)


def _report_details(applied, deselected, skipped, discovery_issues, failed):
    """Build the complete sectioned report shown by Houdini.

    Counts stay visible even for empty sections; populated sections then list
    every outcome so partial batches remain auditable.
    """
    sections = [
        ("Applied", applied, _label),
        ("Deselected", deselected, _label),
        ("Skipped during rewrite", skipped, str),
        ("Discovery issues", discovery_issues, str),
        ("Failed/stale", failed, str),
    ]
    lines = ["{}: {}".format(title, len(items))
        for title, items, _formatter in sections]
    for title, items, formatter in sections:
        if not items:
            continue
        lines.extend(("", "{} items:".format(title)))
        lines.extend("- " + formatter(item) for item in items)
    return "\n".join(lines)


def _iter_with_progress(items, title, progress=None):
    """Yield a materialized sequence and optionally report progress."""
    # These small selected-node scans stay in the Qt workflow to avoid
    # overlapping native Houdini dialogs. Tests and non-UI callers can still
    # receive progress through the optional callback.
    items = list(items)
    total = max(len(items), 1)
    for index, item in enumerate(items):
        if progress is not None:
            progress(float(index) / total)
        yield item
    if progress is not None:
        progress(1.0)


def _ui(message, warning=False, details=None, dialog=False):
    """Post a status message and open a dialog for warnings or reports."""
    severity = (
        hou.severityType.Warning if warning else hou.severityType.Message)
    # Use the status bar for routine results. Open a dialog for warnings and
    # the final itemized report.
    hou.ui.setStatusMessage(message, severity=severity)
    if warning or dialog:
        hou.ui.displayMessage(
            message, severity=severity, title=TITLE, details=details or "")
