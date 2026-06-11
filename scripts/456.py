import hou

# Removes the Preferences option from Labs toolset in H 22 and above set in the labs_toolset.shelf file
# This keeps the shelf tool for earlier versions to retain compatability
if hou.applicationVersion()[0] >= 22:
    shelf = hou.shelves.shelves().get("labs_toolset")
    if shelf:
        tools = list(shelf.tools())
        tools = [t for t in tools if t.name() != "labs::preferences"]
        shelf.setTools(tools)