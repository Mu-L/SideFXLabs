# SideFX Labs Changelog


### Production Release [21.0.631](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.631) - Feb 18, 2026


**MAJOR UPDATES**
- [21.0.631](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.631) **Labs AV Analyze Images SOP 7.0**, **Labs AV Depth Map SOP 7.0**, **Labs AV Initialize SOP 7.0**, **Labs AV Meshing SOP 7.0**, **Labs AV Photogrammetry SOP 7.0**, **Labs AV Structure from Motion SOP 7.0**, **Labs AV Texturing SOP 7.0**, - Upgraded to 7.0 version which works with the latest AliceVision binaries, version 2025.1.0.
- [21.0.608](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.608) **QuadSpinner Canyon SOP 1.1**, **QuadSpinner Craterfield SOP 1.1**, **QuadSpinner Crumble SOP 1.1**, **QuadSpinner Erosion SOP 1.1**, **QuadSpinner Erosion2 SOP 1.1**, **QuadSpinner Flowmap SOP 1.1**, **QuadSpinner FractalTerraces SOP 1.1**, **QuadSpinner Gaea Core SOP 1.0**, **QuadSpinner Mountain SOP 1.1**, **QuadSpinner Outcrops SOP 1.1**, **QuadSpinner Plates SOP 1.1**, **QuadSpinner Ridge SOP 1.1**, **QuadSpinner Rugged SOP 1.1**, **QuadSpinner Sandstone SOP 1.1**, **QuadSpinner Shatter SOP 1.1**, **QuadSpinner Slump SOP 1.1**, **QuadSpinner Snow SOP 1.1**, **QuadSpinner Stratify SOP 1.1**, **QuadSpinner TextureBase SOP 1.1**, **QuadSpinner Thermal2 SOP 1.1** - These tools are now hidden. They are replaced by *Gaea Terrain Processor SOP*.


**MINOR UPDATES** 
- [21.0.630](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.630) **Labs ML CV ROP Synthetic Data TOP 1.1** - Set license name and license url.
- [21.0.629](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.629) **VAT Help File** - Updated the link to the example file.
- [21.0.625](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.625) **README.md**, **contributors.md** - Added a list of contributors and a reference of that doc to the README.md. This is part of restructuring our docs and we will be making more changes and adding more docs in the near future.
- [21.0.624](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.624) **QuadSpinner Gaea 2.0 Plugin - processing_utils.py** - Add UTF-8 Encoding to the remaining missing file IO operations.
- [21.0.623](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.623) **index.txt** - Removed the Labs docs index file.
- [21.0.623](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.623) **README.md**, **installation.md** - Rewrote the documents, and changed the file structure.
- [21.0.621](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.621) **SideFX Labs Banner** - Added a SideFX Labs banner image with transparent background.
- [21.0.621](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.621) **CommitChecklist**, **HDABestPractices**, **StyleGuide** - Deleted the empty .md files.
- [21.0.621](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.621) **labsdocs.py** - Removed the banner image and video from the help file template.
- [21.0.614](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.614) **ZibraVDB for Houdini Plugin** - Updated the installation steps on the help pages.
- [21.0.610](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.610) **Labs Biome Configure SOP**, **Labs Biome Configure Multibiomes SOP** - Minor documentation edit.
- [21.0.609](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.609) **Labs Biome Attributes Evolve SOP 1.1**, **Labs Biome Attributes to Terrain SOP 1.1**, **Labs Biome Curve Label SOP 1.1**, **Labs Biome Define SOP 1.1**, **Labs Biome Definitions File SOP**, **Labs Biome Plant Define SOP 1.2**, **Labs Biome Plant Definitions File SOP 1.2**, **Labs Biome Plant Scatter SOP 1.2**, **Labs Biome Region Assign SOP 1.2** - Updated Biome help files to include example demo file and latest versions of tools in the related section.
- [21.0.609](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.609) **Labs Biome Configure SOP**, **Labs Biome Configure Multibiomes SOP** - Added help files with images for both Biome tool recipes.
- [21.0.608](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.608) **Documentation** - Updated the links to example files on the documentation.
- [21.0.608](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.608) **SideFXLabs** - Moved the example hip files and ArtStation example files to the SideFXLabsExamples repository. Removed the Biome Plant Scatter and Simple Shapes examples.
- [21.0.603](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.603) **Labs Thicken SOP 1.1 ** - Removed 'Reduce Back Side' operation from the tool to simplify the tool and UI. Users can instead use a *PolyReduce SOP* on the new 'thickenBack' output group if they want to achieve the same result.
- [21.0.603](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.603) **Labs Thicken SOP 1.1** minor UI changes.
- [21.0.603](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.603) **ZibraVDB File Cache SOP** - Updated to v1.2.3.
- [21.0.601](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.601) **Labs PolyWire UV SOP 1.1** - Renamed a few parameters in the UI.
- [21.0.601](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.601) **Labs Karma LOP 2.0**, **Labs Render Geometry OBJ**, **Labs Cook With Timeout SOP**, **Labs Extract Silhouette SOP**, **Labs File Cache SOP 2.0**, **Labs PolyWire UV SOP 1.1**, **Labs Tree Branch Placer SOP**, **Labs File Cache TOP 2.0**, **Labs Karma Render TOP 2.0** - Added help files. 
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs RBD Edge Strip SOP** - Removed unused *Labs UV Visualize SOP* from inside the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Building from Patterns SOP 1.1** - Replaced *Labs Split Primitives by Normals SOP* inside the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Automatic Trim Texture SOP** - Replaced *Labs Split Primitives by Normals SOP* inside the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Trim Texture Subutil SOP** - Replaced *Labs Split Primitives by Normals SOP* inside the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Houdini Icon SOP** - Replaced *Labs Auto UV SOP* and *Labs Delete Small Parts SOP* from the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Edge Damage SOP 2.1** - Replaced the deprecated *Labs Color Adjustment SOP* with *Attribute Adjust Color SOP* inside the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Cable Generator SOP 2.0** - Replaced the deprecated *Labs Calculate Occlusion SOP* inside the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Delight SOP** - Replaced the deprecated *Labs Color Adjustment SOP* with *Attribute Adjust Color SOP*, and *Labs Calculate Occlusion SOP* inside the network.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Biome Curve Label SOP 1.1**,  **Labs Biome Define SOP**, **Labs Biome Plant Define SOP 1.2**, **Labs Biome Definitions File SOP**, **Labs Biome Plant Definitions File SOP 1.2**, **Labs Biome Plant Scatter SOP 1.2** - Color coded the input/output names and wires to help users know how the suite of nodes are wired together.
- [21.0.597](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.597) **Labs Auto UV SOP** - Replaced the deprecated *Labs Calculate Occlusion SOP* from the network with *Mask by Feature SOP*.


**BUG FIXES**
- [21.0.609](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.609) **SideFX Labs Unreal Plugin 5.7** - Removed the debug files from Labs Plugin 5.7 Binaries
- [21.0.602](https://github.com/sideeffects/SideFXLabs/releases/tag/21.0.602) **Labs Thicken SOP 1.1** - Fixed a fuse distance too large bug. Added better interactive handle for smoother extrusion. Added output groups for front, back, side, and seams.