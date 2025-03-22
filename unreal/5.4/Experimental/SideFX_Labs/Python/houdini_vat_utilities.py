import unreal
import time

def create_directory_if_not_exists(path):
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)
        unreal.log("Created folder: {}".format(path))

def duplicate_material_instance(material_instance, vat_materials_folder, vat_name):
    new_material_instance_name = f"{material_instance.get_name()}_VAT_{vat_name}"
    new_material_instance_path = f"{vat_materials_folder}/{new_material_instance_name}"

    unreal.EditorAssetLibrary.duplicate_asset(material_instance.get_path_name(), new_material_instance_path)
    unreal.log("Duplicated Material Instance to: {}".format(new_material_instance_path))
    unreal.EditorAssetLibrary.save_asset(new_material_instance_path)

    return new_material_instance_path

def process_material(material, vat_materials_folder, master_folder, duplicated_parent_materials, vat_name):
    material_slot_name = str(material.material_slot_name)
    unreal.log("Processing Material Slot: {}".format(material_slot_name))

    all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)
    material_instance_path = next((path for path in all_assets if path.endswith(material_slot_name)), None)

    if material_instance_path:
        material_instance = unreal.EditorAssetLibrary.load_asset(material_instance_path)

        if isinstance(material_instance, unreal.MaterialInstance):
            new_material_instance_path = duplicate_material_instance(material_instance, vat_materials_folder, vat_name)
            parent_material = material_instance.get_editor_property('parent')

            while parent_material:
                if isinstance(parent_material, unreal.Material):
                    parent_material_path = parent_material.get_path_name()
                    if parent_material_path not in duplicated_parent_materials:
                        new_parent_material_name = f"{parent_material.get_name()}_VAT_{vat_name}"
                        new_parent_material_path = f"{master_folder}/{new_parent_material_name}"
                        unreal.EditorAssetLibrary.duplicate_asset(parent_material_path, new_parent_material_path)
                        unreal.log("Duplicated Parent Material to: {}".format(new_parent_material_path))
                        unreal.EditorAssetLibrary.save_asset(new_parent_material_path)
                        duplicated_parent_materials[parent_material_path] = new_parent_material_path
                    break
                else:
                    non_material_name = f"{parent_material.get_name()}_VAT_{vat_name}"
                    non_material_path = f"{master_folder}/{non_material_name}"
                    unreal.EditorAssetLibrary.duplicate_asset(parent_material.get_path_name(), non_material_path)
                    unreal.log("Duplicated Non-Material Parent to: {}".format(non_material_path))
                    unreal.EditorAssetLibrary.save_asset(non_material_path)

                parent_material = parent_material.get_editor_property('parent')
        else:
            unreal.log_warning("Loaded asset is not a valid Material Instance for slot: {}".format(material_slot_name))
    else:
        unreal.log_warning("Material Instance not found for slot: {}".format(material_slot_name))

def update_material_instances(vat_materials_folder, master_folder, vat_name):
    vat_materials_assets = unreal.EditorAssetLibrary.list_assets(vat_materials_folder, recursive=True)

    for asset_path in vat_materials_assets:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        
        if isinstance(asset, unreal.MaterialInstance):
            parent_material = asset.get_editor_property('parent')
            
            if parent_material:
                new_parent_material_name = f"{parent_material.get_name()}_VAT_{vat_name}"
                unreal.log("Looking for parent material: {}".format(new_parent_material_name))
                
                new_parent_material_path = f"{master_folder}/{new_parent_material_name}"
                new_parent_material = unreal.EditorAssetLibrary.load_asset(new_parent_material_path)
                
                if new_parent_material:
                    if asset.get_name() == new_parent_material.get_name():
                        unreal.log_warning("Skipping {}: parent material is the same as the material instance.".format(asset.get_name()))
                        continue
                    
                    try:
                        asset.set_editor_property('parent', new_parent_material)
                        old_parent_material_name = parent_material.get_name() if parent_material else "None"
                        unreal.log("Updated parent material for {}: {} -> {}".format(asset.get_name(), old_parent_material_name, new_parent_material_name))
                    except Exception as e:
                        unreal.log_warning("Failed to set parent material for {}: {}".format(asset.get_name(), str(e)))
                else:
                    unreal.log_warning("New parent material {} not found at path {}".format(new_parent_material_name, new_parent_material_path))
            else:
                unreal.log_warning("Material Instance {} has no parent material.".format(asset.get_name()))
        else:
            unreal.log_warning("Asset {} is not a Material Instance.".format(asset_path))
    
    for asset_path in vat_materials_assets:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        
        if isinstance(asset, unreal.MaterialInstance):
            unreal.EditorAssetLibrary.save_asset(asset_path)
            unreal.log("Saved Material Instance: {}".format(asset_path))

def assign_material_instances_to_blueprint(blueprint, vat_materials_folder, original_material_instances):
    vat_materials_assets = unreal.EditorAssetLibrary.list_assets(vat_materials_folder, recursive=True)
    material_instances = [None] * len(original_material_instances)
    
    original_material_names = [mat.get_name() for mat in original_material_instances]
    
    for asset_path in vat_materials_assets:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        
        if isinstance(asset, unreal.MaterialInstance):
            asset_name = asset.get_name()
            for index, original_name in enumerate(original_material_names):
                if original_name in asset_name:
                    material_instances[index] = asset
                    break
    
    material_instances = [mat for mat in material_instances if mat is not None]
    
    unreal.log("Assigning VAT Material Instances to the Blueprint: {}".format(blueprint.get_name()))
    blueprint.set_editor_property('Vat_MaterialInstances', material_instances)

    unreal.log("Assigning Original Material Instances to the Blueprint: {}".format(blueprint.get_name()))
    blueprint.set_editor_property('Original_MaterialInstances', original_material_instances)

def assign_material_instances_to_static_mesh(static_mesh_component, vat_materials_folder):
    if not isinstance(vat_materials_folder, str):
        unreal.log_warning("Invalid vat_materials_folder path provided.")
        return

    vat_materials_assets = unreal.EditorAssetLibrary.list_assets(vat_materials_folder, recursive=True)
    vat_material_instances = []

    for asset_path in vat_materials_assets:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if isinstance(asset, unreal.MaterialInstance):
            vat_material_instances.append(asset)

    if static_mesh_component:
        static_mesh = static_mesh_component.static_mesh

        if static_mesh:
            num_material_slots = len(static_mesh.static_materials)

            for idx, material_instance in enumerate(vat_material_instances):
                if idx < num_material_slots:
                    static_mesh_component.set_material(idx, material_instance)
                    unreal.log(f"Assigned VAT material {material_instance.get_name()} to material slot {idx}.")
                else:
                    unreal.log_warning(f"VAT material instance {material_instance.get_name()} does not fit in slot {idx}, skipping.")

            unreal.log("Successfully assigned VAT material instances to the Static Mesh Component.")
        else:
            unreal.log_warning("No Static Mesh found on the Static Mesh Component.")
    else:
        unreal.log_warning("No Static Mesh Component provided.")

def main():
    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()

    if selected_assets:
        selected_asset = selected_assets[0]

        if isinstance(selected_asset, unreal.Blueprint):
            blueprint_path = selected_asset.get_path_name()
            blueprint_name = selected_asset.get_name()
            vat_name = blueprint_name.replace("BP_", "").replace("VAT", "").strip()
            vat_name = vat_name.strip('_')

            unreal.log("VAT Name: {}".format(vat_name))

            blueprint_generated_class = unreal.EditorAssetLibrary.load_blueprint_class(blueprint_path)

            if blueprint_generated_class:
                default_object = unreal.get_default_object(blueprint_generated_class)
                static_mesh_component = default_object.get_component_by_class(unreal.StaticMeshComponent)

                if static_mesh_component:
                    static_mesh = static_mesh_component.static_mesh

                    if static_mesh:
                        unreal.log("Static Mesh Name: {}".format(static_mesh.get_name()))
                        static_materials = static_mesh.static_materials
                        blueprint_directory = unreal.EditorAssetLibrary.get_path_name(selected_asset.get_outer())
                        parent_directory = '/'.join(blueprint_directory.split('/')[:-1])
                        vat_materials_folder = f"{parent_directory}/VAT_Materials"
                        master_folder = f"{vat_materials_folder}/Master"

                        create_directory_if_not_exists(vat_materials_folder)
                        create_directory_if_not_exists(master_folder)

                        duplicated_parent_materials = {}
                        original_material_instances = []  

                        for material in static_materials:
                            material_slot_name = str(material.material_slot_name)
                            all_assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True)
                            material_instance_path = next((path for path in all_assets if path.endswith(material_slot_name)), None)
                            
                            if material_instance_path:
                                original_material_instance = unreal.EditorAssetLibrary.load_asset(material_instance_path)
                                if isinstance(original_material_instance, unreal.MaterialInstance):
                                    original_material_instances.append(original_material_instance)

                            process_material(material, vat_materials_folder, master_folder, duplicated_parent_materials, vat_name)
                            time.sleep(0.1)  

                        unreal.EditorAssetLibrary.save_asset(static_mesh.get_outer().get_path_name())
                        unreal.log("Saved Static Mesh Package: {}".format(static_mesh.get_outer().get_path_name()))
                        update_material_instances(vat_materials_folder, master_folder, vat_name)

                        
                        assign_material_instances_to_blueprint(default_object, vat_materials_folder, original_material_instances)
                        assign_material_instances_to_static_mesh(static_mesh_component, vat_materials_folder)

                    else:
                        unreal.log_warning("No Static Mesh found in the Static Mesh Component.")
                else:
                    unreal.log_warning("No Static Mesh Component found in the Blueprint.")
            else:
                unreal.log_warning("No Generated Class found in the Blueprint.")
        else:
            unreal.log_warning("Selected asset is not a Blueprint.")
    else:
        unreal.log_warning("No asset selected in the Content Browser.")

main()
