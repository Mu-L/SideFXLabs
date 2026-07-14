import hou

if hou.applicationVersion()[0] < 22:
    try:
        hou.hscript("ophide Lop labs::relight_gsplats::1.0")
        hou.hscript("ophide Sop labs::delight_gsplats::1.0")
        hou.hscript("ophide Sop labs::normals_from_gsplats::1.0")
    except hou.Error:
        pass

