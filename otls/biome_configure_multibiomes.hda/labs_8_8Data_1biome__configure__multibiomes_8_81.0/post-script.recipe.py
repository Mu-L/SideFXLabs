node_names = ['ASPEN', 'PINE', 'BOREAL_SHRUB', 'GRASSLAND_SHRUB', 'TEMPERATE_SHRUB', 'BOREAL_SNOW_PINE', 'biome_attributes_evolve', 'biome_attributes_to_terrain', 'biome_region_assign']

anchor_node = kwargs['anchor_node']
anchor_node.hm().setViewFlag(anchor_node)

for node_name in node_names:
    node = kwargs['items'][node_name]
    node.hm().setViewFlag(node)