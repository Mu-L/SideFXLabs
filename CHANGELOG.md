# SideFX Labs Changelog


### Production Release [21.0.700](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.700) - Apr 29, 2026


**MAJOR UPDATES**
- [21.0.673](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.673) **Labs Exoside QuadRemesher SOP 1.4** - Updated to 1.4 version.


**MINOR UPDATES**
- [21.0.693](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.693) **Labs Cable Generator SOP 2.1** created to add cosh function to psuedo-gravity alongside the original quadratic function.
- [21.0.682](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.682) **Labs Toon Shader VOP 1.2** - Updated to version 1.2, which is compatible with Houdini versions 20.0 and 21.5 with using OpenGL viewports. Note, this node is not compatible with Vulkan viewports.
- [21.0.682](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.682) **Labs Toon Shader VOP 1.1** - Updated to version 1.1, which is compatible with Houdini versions 19.0 and 19.5. Note, this node is not compatible with Vulkan viewports.
- [21.0.678](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.678) **Labs Biome Plant Scatter SOP 1.2** - Added an optional output integer for 'shrub'. If shrub = 1 it is a shrub type. If shrub = 0, it is a tree type.
- [21.0.674](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.674) **Labs Quick Material SOP 2.2** - The node is unhidden until COP Preview Material SOP supports MatCap preview.
- [21.0.672](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.672) **ML CV ROP Synthetic Data TOP 1.1** - Updated python venv library versions.


**BUG FIXES**
- [21.0.687](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.687) **Labs Biome Configure Multibiomes SOP** - Replaced heightfield paint cache with mask by geometry nodes to reduce file size significantly.