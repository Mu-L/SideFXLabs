import hou, labutils


# Hide GSplat nodes in Houdini versions before 22.0, as they are not compatible
if hou.applicationVersion()[0] < 22:
    try:
        hou.hscript("ophide Lop labs::relight_gsplats::1.0")
        hou.hscript("ophide Sop labs::delight_gsplats::1.0")
        hou.hscript("ophide Sop labs::normals_from_gsplats::1.0")
    except hou.Error:
        pass


# Deprecating Labs OCIO ACES Profile and Labs Alternative Grey Background for Houdini Versions 20 - 21
labutils.deprecate_settings_warnings()

