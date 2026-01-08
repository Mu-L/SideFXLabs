# Use the 'kwargs' dictionary to access information after the recipe data is applied.

target_node = kwargs['items']['TEMPERATE_SHRUB']
target_node.hm().setViewFlag(target_node)
target_node = kwargs['items']['PINE']
target_node.hm().setViewFlag(target_node)
target_node = kwargs['items']['ASPEN']
target_node.hm().setViewFlag(target_node)
target_node = kwargs['items']['biome_attributes_to_terrain']
target_node.hm().setViewFlag(target_node)
target_node = kwargs['items']['biome_attributes_evolve']
target_node.hm().setViewFlag(target_node)
