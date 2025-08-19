# Use the 'kwargs' dictionary to access information after the recipe data is applied.
# Common keys:
# name - The internal name of the recipe.
# node/central_node/anchor_node - The target presetnode for Node/Parm Preset, Decoration and Tool recipes.
# parms/cental_parms/anchor_parms - The list of hou.parmTuple objects affected by the recipe data on the target presetnode.
# items - All other nodes besided the target presetnode that are created/effected by this recipe at the top level.
# You can also call other recipes from here, for example this will apply another presetnode preset recipe to the target presetnode:
# hou.data.applyNodePresetRecipe('other_recipe_name', kwargs['anchor_node'])

node = kwargs['anchor_node']
node1 = kwargs['items']['TEMPERATE_SHRUB']
node2 = kwargs['items']['PINE']
node3 = kwargs['items']['ASPEN']
node4 = kwargs['items']['biome_attributes_to_terrain']
node5 = kwargs['items']['biome_attributes_evolve']

node.hm().setViewFlag(node)
node1.hm().setViewFlag(node1)
node2.hm().setViewFlag(node2)
node3.hm().setViewFlag(node3)
node4.hm().setViewFlag(node4)
node5.hm().setViewFlag(node5)