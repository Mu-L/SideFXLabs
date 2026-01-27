# SideFX Labs Changelog


### Production Release [21.0.596](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.596) - Jan 15, 2026


**MAJOR UPDATES**
- [21.0.589](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.589) **SideFX Labs Unreal Plugin 5.7** - Updated the Labs Plugin to 5.7.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Symmetrize SOP** - Replaced with *Mirror SOP* alias. To be removed in Houdini 23.0.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Split Primitives by Normal SOP** - Cleaned up the network, refined the UI, set an internal group code, set the version to 1.0.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Sweep Geometry SOP** - Replaced by *Sweep SOP*. To be removed in Houdini 23.0.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Dem Bones Skinning Converter SOP** - Added a comment that the node is replaced by *Dem Bones Skinning Converter SOP* and is going to be removed in Houdini 23.0.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Group Attribute Borders SOP**, **Labs Group by Color SOP**, **Labs Group Edge Loop SOP**, **Labs Group UV Borders SOP**, **Labs Mark Seams SOP**, **Labs Niagara Impacts SOP**, **Labs Niagara Interpolate SOP**, **Labs Niagara RBD SOP**, **Labs Split Pyro SOP**, **Labs Preview RBD SOP**, **Labs Director RBD SOP**, **Labs Fracture RBD SOP**, **Labs Solver RC SOP**, **Labs RC Register Images SOP**, **Labs RC Texture Model**, **Labs Simple RBD SOP**, **Labs UV Stack SOP**, **Labs Volume Detail Attributes SOP** - Removed otls, help files, and icons of tools that were deprecated before Houdini 19.0.


**MINOR UPDATES** 
- [21.0.595](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.595) **Labs Attribute Import COP2**, **Labs Normal Combine COP2**, **Labs Normal Invert COP2**, **Labs Normal From Grayscale COP2**, **Labs Normalize Normal COP2**, **Labs Normal Rotate COP2** - Added comments for the corresponding replacement nodes in Copernicus for those tools.
- [21.0.595](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.595) **Labs Instant Meshes SOP** - This tool's functionality is replaced by the *Quad Remesh SOP*. To be removed in Houdini 23.0.
- [21.0.594](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.594) **Labs Radial Sort SOP 1.1** - Added options to sort indices, and guides to visualize the direction of the vectors.
- [21.0.594](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.594) **Labs Biome Attributes To Terrain SOP 1.1** - Removed the embedded *Labs Biome Define SOP* from the node network.
- [21.0.593](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.593) **Labs Mandelbulb Generator SOP 1.1** - Removed 'Generator' from the label.
- [21.0.593](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.593) **Labs Houdini Icon SOP 1.1** - Made minor UI changes.
- [21.0.593](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.593) **Labs Attribute Normalize Float SOP**, **Labs Attribute Normalize Vector SOP**, **Labs Biome Attributes to Terrain SOP 1.1**, **Labs Calculate Thickness SOP**, **Labs Cluster Refine SOP**, **Labs Connect Polygon Neighbours SOP**, **Labs Fast Gaussian Curvature SOP**, **Labs Fast Group Unshared SOP**, **Labs Houdini Icon SOP**, **Labs Instance Attributes SOP**, **Labs Instant Meshes SOP 2.0**, **Labs Instant Meshes SOP**, **Labs Mandelbulb Generator SOP 1.1**, **Labs Quick Basic Tree SOP**, **Labs Quick Material SOP 2.2**, **Labs Quick Material SOP 2.1**, **Labs Quick Material SOP 2.0**, **Labs Spectral Feature Extract SOP**, **Labs Substance Material SOP**, **Labs Test Geometry: Luiz SOP**, **Labs Test Geometry: Paul SOP** - Added help files and fixed the paths so they display correctly.
- [21.0.590](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.590) **Labs Biome Define SOP** Added SetViewFlag function to python module so it will work with the after data applied script on the multibiome recipe. *Labs Biome Configure SOP Recipe* and *Labs Biome Configure Multibiomes SOP Recipe* fixed -1 outputs so visualizations will appear by default.
- [21.0.589](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.589) **Labs Biome Plant Define SOP 1.2** has plant radii that appear at the object level, not just a guide any more.
- [21.0.587](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.587) **Labs AutoUV SOP**, **Labs Calculate UV Distortion SOP**, **Labs Inside Face UVs SOP**, **Labs Merge Small Islands SOP**, **Labs Remove UV Distortion SOP**, **Labs UV Unwrap Cylinder SOP**, **Labs UV Visualize SOP 1.2** - Added Groups and UV Attribute drop down selection menus.
- [21.0.587](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.587) **Labs UV Unitize SOP 1.1** - Updated the algorithm to only use the UV space instead of @P, added dropdown menu to select prim groups and UV attribute, added Preserve Ratio, Center In Unit, and Preserve UDIM parameters for the UV Islands mode.
- [21.0.569](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.569) **Labs Building from Patterns SOP 1.1**, **Labs Building Generator SOP 4.0**, **Labs Building Generator Utility SOP 2.0**, **Labs Cable Generator SOP 2.0**, **Labs Calculate Thickness SOP**, **Labs Curve Resample by Density SOP**, **Labs Instance Attributes SOP**, **Labs Min Max Average SOP**, **Labs Tree Branch Placer SOP**, **Labs Unreal Spline SOP**, **Labs UV Unwrap Cylinder SOP** - Rewrote the help files.
- [21.0.568](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.568) **Labs Boxcutter SOP** - Updated the help file.
- [21.0.567](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.567) **Labs Box Clip SOP** - Rewrote the help file, cleaned up the network, set parameters to disable whenever there is a second input.
- [21.0.567](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.567) **Labs Boolean Curve SOP** - Rewrote the help file, renamed parameters, cleaned up the network, and set an HDA code for internal attributes and groups.
- [21.0.567](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.567) **Labs Auto UV** - Rewrote the help file, and renamed the parameters.
- [21.0.567](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.567) **Labs Attribute Value Replace** - Updated the documentation to clarify the node only works with point attributes of string type.
- [21.0.567](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.567) **Labs Attribute Value Replace SOP** - Rewrote the help file, and updated the UI.
- [21.0.566](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.566) **Labs Biome Configure**, **Labs Biome Configure Multibiomes** - Changed the icon from Beta to the Labs Default.
- [21.0.566](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.566) **OPcustomize** - Restored hidden operators to avoid error messages.
- [21.0.562](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.562) **Labs Biome Attributes Evolve**, **Labs Biome Attributes to Terrain**, **Labs Biome Configure**, **Labs Biome Configure Multiobiomes**, **Labs Biome Curve Label**, **Labs Biome Define**, **Labs Biome Definitions File**, **Labs Biome Plant Define**, **Labs Biome Plant Scatter**, **Labs Biome Region Assign**, **Labs Pathfinding Global**, **Labs PCG Export**, **Labs Settlement Connections**, **Labs Terrain Analysis**, **Labs Unreal Spline** - Removed (Beta) from the label.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Quadrangulate SOP 2.0** - Replaced the *Dissolve SOP* internally with version 2.0 to make it compilable, set internal group code, cleaned up the network and removed the nested networks.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Impostor Camera Rig OBJ** - Fixed the *Labs Impostor Texture* links in the help file.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Labs Delete Small Parts SOP** - Made it compilable, and added the option to set a custom piece attribute.
- [21.0.561](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.561) **Triangulate** - Restored the alias.


**BUG FIXES**
- [21.0.595](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.595) **Labs Instant Meshes SOP** no more overlapping geometry of the input and the output geometry on top of each other. Only the output of the algorithm is output from the tool. The output file and input file default filenames were also swapped.
- [21.0.587](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.587) **Labs Quad Sphere SOP 1.1** - Fixed a minor UV layout issue when adding UVs.