/*
* Copyright (c) 2025 Side Effects Software Inc.  All rights reserved.
*
* Redistribution and use of in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*
* 1. Redistributions of source code must retain the above copyright notice,
* this list of conditions and the following disclaimer.
*
* 2. The name of Side Effects Software may not be used to endorse or
* promote products derived from this software without specific prior
* written permission.
*
* THIS SOFTWARE IS PROVIDED BY SIDE EFFECTS SOFTWARE `AS IS' AND ANY EXPRESS
* OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
* OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN
* NO EVENT SHALL SIDE EFFECTS SOFTWARE BE LIABLE FOR ANY DIRECT, INDIRECT,
* INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
* LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
* OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
* LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
* NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

#include "HoudiniVatImporter.h"
#include "HoudiniCreateNewVatWindowParameters.h"
#include "HoudiniVatActor.h"
#include "UnrealEd.h"
#include "MaterialEditingLibrary.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"

UHoudiniVatImporter::UHoudiniVatImporter()
{
    VatProperties = nullptr;
    HoudiniVatMaterialFunction = nullptr;
    bCanceled = false;

    static ConstructorHelpers::FObjectFinder<UMaterialFunction> MaterialFunctionFinder(TEXT("/SideFX_Labs/Materials/MaterialFunctions/Houdini_VAT_RigidBodyDynamics"));
    
    if (MaterialFunctionFinder.Succeeded())
    {
        HoudiniVatMaterialFunction = MaterialFunctionFinder.Object;
    }
    else
    {
        HoudiniVatMaterialFunction = nullptr;
        UE_LOG(LogTemp, Error, TEXT("Failed to find Houdini_VAT_RigidBodyDynamics material function"));
    }
}

void UHoudiniVatImporter::SetProperties(UCreateNewVatProperties* InProperties)
{
    VatProperties = InProperties;

    if (VatProperties)
    {
        UMaterialFunction* MaterialFunction = nullptr;
        switch (VatProperties->VatType)
        {
        case EVatType::VatType1:
            MaterialFunction = LoadObject<UMaterialFunction>(nullptr, TEXT("/SideFX_Labs/Materials/MaterialFunctions/Houdini_VAT_SoftBodyDeformation"));
            if (!MaterialFunction)
            {
                UE_LOG(LogTemp, Error, TEXT("Failed to create Houdini_VAT_SoftBodyDeformation material function"));
            }
            break;

        case EVatType::VatType2:
            MaterialFunction = LoadObject<UMaterialFunction>(nullptr, TEXT("/SideFX_Labs/Materials/MaterialFunctions/Houdini_VAT_RigidBodyDynamics"));
            if (!MaterialFunction)
            {
                UE_LOG(LogTemp, Error, TEXT("Failed to create Houdini_VAT_RigidBodyDynamics material function"));
            }
            break;
            
        case EVatType::VatType3:
            MaterialFunction = LoadObject<UMaterialFunction>(nullptr, TEXT("/SideFX_Labs/Materials/MaterialFunctions/Houdini_VAT_DynamicRemeshing"));
            if (!MaterialFunction)
            {
                UE_LOG(LogTemp, Error, TEXT("Failed to create Houdini_VAT_DynamicRemeshing material function"));
            }
            break;

        case EVatType::VatType4:
            MaterialFunction = LoadObject<UMaterialFunction>(nullptr, TEXT("/SideFX_Labs/Materials/MaterialFunctions/Houdini_VAT_ParticleSprites"));
            if (!MaterialFunction)
            {
                UE_LOG(LogTemp, Error, TEXT("Failed to create Houdini_VAT_ParticleSprites material function"));
            }
            break;

        default:
            UE_LOG(LogTemp, Error, TEXT("Invalid VAT type"));
            break;
        }

        HoudiniVatMaterialFunction = MaterialFunction;
    }
}

void UHoudiniVatImporter::ImportFiles()
{
    if (VatProperties)
    {
        // Import FBX
        FullFbxPath = FPaths::ConvertRelativePathToFull(VatProperties->VatFbxFilePath.FilePath);
        TArray<FString> TexturePaths;
        
        for (const auto& [FilePath] : VatProperties->VatTextureFilePath)
        {
            FString FullTexturePath = FPaths::ConvertRelativePathToFull(FilePath);
            TexturePaths.Add(FullTexturePath);
        }
        
        ImportFbx(FullFbxPath, VatProperties->VatAssetPath.Path);

        if (bCanceled)
        {
            UE_LOG(LogTemp, Warning, TEXT("FBX Import was canceled. Skipping further processing."));
            return;
        }

        const FString StaticMeshPath = VatProperties->VatAssetPath.Path / FPaths::GetBaseFilename(FullFbxPath);
        UStaticMesh* ImportedStaticMesh = LoadObject<UStaticMesh>(nullptr, *StaticMeshPath);

        if (!ImportedStaticMesh)
        {
            UE_LOG(LogTemp, Error, TEXT("Failed to load imported static mesh: %s"), *StaticMeshPath);
            return;
        }

        StaticMesh = ImportedStaticMesh;

        if (VatProperties->VatType == EVatType::VatType3)
        {
            FStaticMeshSourceModel& SourceModel = StaticMesh->GetSourceModel(0);
            FMeshBuildSettings& BuildSettings = SourceModel.BuildSettings;
            BuildSettings.bUseFullPrecisionUVs = true;
            BuildSettings.bUseBackwardsCompatibleF16TruncUVs = true;
        }
        
        // Import Textures
        TArray<UTexture2D*> ImportedTextures;
        for (const FString& TextureFilePath : TexturePaths)
        {
            ImportTexture(TextureFilePath, VatProperties->VatAssetPath.Path);

            if (UTexture2D* ImportedTexture = LoadObject<UTexture2D>(nullptr, *FPaths::Combine(VatProperties->VatAssetPath.Path, FPaths::GetBaseFilename(TextureFilePath))))
            {
                ImportedTextures.Add(ImportedTexture);
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("Failed to load texture: %s"), *TextureFilePath);
            }
        }

        SetTextureParameters(ImportedTextures);

        // Get static mesh package
        if (StaticMesh.IsValid())
        {
            // Get the package of the static mesh
            if (const UPackage* StaticMeshPackage = StaticMesh->GetPackage())
            {
                // Mark the package as modified
                StaticMeshPackage->MarkPackageDirty();
            }
        }

        // Get texture packages
        TArray<UPackage*> TexturePackages;
        for (const UTexture2D* Texture : ImportedTextures)
        {
            if (Texture)
            {
                // Get the package of the texture
                if (UPackage* TexturePackage = Texture->GetPackage())
                {
                    // Mark the package as modified
                    TexturePackage->MarkPackageDirty();
                    TexturePackages.Add(TexturePackage);
                }
            }
        }

        // Save all packages
        TArray<UPackage*> PackagesToSave;
        if (StaticMesh.IsValid())
        {
            PackagesToSave.Add(StaticMesh->GetPackage());
        }
        PackagesToSave.Append(TexturePackages);

        if (PackagesToSave.Num() > 0)
        {
            UEditorLoadingAndSavingUtils::SavePackages(PackagesToSave, true);
        }
    }
}

void UHoudiniVatImporter::ImportFbx(const FString& FBXPath, const FString& AssetPath)
{
    UFbxFactory* FbxFactory = NewObject<UFbxFactory>();
    FbxFactory->AddToRoot();
    
    if (!FbxFactory->ConfigureProperties())
    {
        UE_LOG(LogTemp, Warning, TEXT("FBX Import canceled by user."));
        bCanceled = true;
        return;
    }

    const FString PackageName = AssetPath / FPaths::GetBaseFilename(FBXPath);
    UPackage* Package = CreatePackage(*PackageName);
    const FString Name = FPaths::GetBaseFilename(FBXPath);
    
    const UObject* ImportedObject = FbxFactory->ImportObject(UStaticMesh::StaticClass(), Package, FName(*Name), RF_Public | RF_Standalone, FBXPath, nullptr, bCanceled);

    if (bCanceled)
    {
        return;
    }

    if (ImportedObject)
    {
        UE_LOG(LogTemp, Log, TEXT("FBX File Imported: %s"), *FBXPath);
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("FBX Import failed: %s"), *FBXPath);
    }
}

void UHoudiniVatImporter::ImportTexture(const FString& TexturePath, const FString& AssetPath)
{
    UTextureFactory* TextureFactory = NewObject<UTextureFactory>();
    TextureFactory->AddToRoot();
    const FString PackageName = AssetPath / FPaths::GetBaseFilename(TexturePath);
    UPackage* Package = CreatePackage(*PackageName);
    bool bCanceled = false;
    const FString Name = FPaths::GetBaseFilename(TexturePath);
    
    const UObject* ImportedObject = TextureFactory->ImportObject(UTexture2D::StaticClass(), Package, FName(*Name), RF_Public | RF_Standalone, TexturePath, nullptr, bCanceled);

    if (bCanceled)
    {
        UE_LOG(LogTemp, Warning, TEXT("Texture Import canceled."));
    }
    else if (ImportedObject)
    {
        UE_LOG(LogTemp, Log, TEXT("Texture File Imported: %s"), *TexturePath);
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("Texture Import failed: %s"), *TexturePath);
    }
}

void UHoudiniVatImporter::SetTextureParameters(TArray<UTexture2D*> Textures)
{
    for (UTexture2D* Texture2D : Textures)
    {
        if (Texture2D && Texture2D->AssetImportData)
        {
            if (const FAssetImportInfo& AssetImportInfo = Texture2D->AssetImportData->SourceData; AssetImportInfo.SourceFiles.Num() >= 1)
            {
                FString SourceFilePath = AssetImportInfo.SourceFiles[0].RelativeFilename;

                if (FString Extension = FPaths::GetExtension(SourceFilePath).ToLower(); Extension == TEXT("exr"))
                {
                    // Set parameters for .exr textures
                    Texture2D->Filter = TF_Nearest;
                    Texture2D->LODGroup = TEXTUREGROUP_16BitData;
                    Texture2D->MipGenSettings = TMGS_NoMipmaps;
                    Texture2D->CompressionSettings = TC_HDR;
                    Texture2D->SRGB = false;
                }
                else if (Extension == TEXT("png"))
                {
                    // Set parameters for .png textures
                    Texture2D->Filter = TF_Nearest;
                    Texture2D->LODGroup = TEXTUREGROUP_8BitData;
                    Texture2D->MipGenSettings = TMGS_NoMipmaps;
                    Texture2D->CompressionSettings = TC_VectorDisplacementmap;
                    Texture2D->SRGB = false;
                }

                (void)Texture2D->MarkPackageDirty();
                Texture2D->PostEditChange();

                UE_LOG(LogTemp, Log, TEXT("Set parameters for texture: %s"), *Texture2D->GetName());
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("No source files found for texture: %s"), *Texture2D->GetName());
            }
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("Texture is null or has no AssetImportData"));
        }
    }
}

void UHoudiniVatImporter::CreateVatMaterial()
{
    if (!VatProperties)
    {
        UE_LOG(LogTemp, Warning, TEXT("VatProperties is not set."));
        return;
    }

    SetProperties(VatProperties);
    FString MaterialName = VatProperties->VatMaterialName;
    
    if (MaterialName.IsEmpty())
    {
        MaterialName = TEXT("M_HoudiniVAT");
    }
    else if (!MaterialName.StartsWith(TEXT("M_")))
    {
        MaterialName = TEXT("M_") + MaterialName;
    }

    CreatedMaterialName = MaterialName;

    UMaterialFactoryNew* MaterialFactory = NewObject<UMaterialFactoryNew>();
    MaterialFactory->AddToRoot();
    const FString PackageName = VatProperties->VatAssetPath.Path / MaterialName;
    UPackage* Package = CreatePackage(*PackageName);

    Material = Cast<UMaterial>(MaterialFactory->FactoryCreateNew(UMaterial::StaticClass(), Package, FName(*MaterialName), RF_Public | RF_Standalone, nullptr, GWarn));

    if (!Material.Get())
    {
        UE_LOG(LogTemp, Error, TEXT("VatMaterial is null"));
        return;
    }

    switch (VatProperties->VatType)
    {
    case EVatType::VatType1:
        Material->NumCustomizedUVs = 5.0f;
        Material->bTangentSpaceNormal = false;
        break;

    case EVatType::VatType2:
        Material->NumCustomizedUVs = 5.0f;
        Material->bTangentSpaceNormal = false;
        break;

    case EVatType::VatType3:
        Material->NumCustomizedUVs = 4.0f;
        Material->bTangentSpaceNormal = false;
        break;

    case EVatType::VatType4:
        Material->NumCustomizedUVs = 2.0f;
        Material->bTangentSpaceNormal = false;
        break;

    default:
        UE_LOG(LogTemp, Error, TEXT("Invalid VAT type"));
        return;
    }

    VatMaterialExp = UMaterialEditingLibrary::CreateMaterialExpression(Material.Get(), UMaterialExpressionMaterialFunctionCall::StaticClass());
    
    if (UMaterialExpressionMaterialFunctionCall* CastedVatMaterialExp = Cast<UMaterialExpressionMaterialFunctionCall>(VatMaterialExp))
    {
        if (HoudiniVatMaterialFunction)
        {
            CastedVatMaterialExp->MaterialFunction = HoudiniVatMaterialFunction;
            VatMaterialExp->MaterialExpressionEditorX -= 700;
            Material->PostEditChange();
            Material->GetEditorOnlyData()->ExpressionCollection.Expressions.Add(VatMaterialExp.Get());

            switch (VatProperties->VatType)
            {
            case EVatType::VatType1:
                if (VatMaterialExp->Outputs.Num() > 0)
                {
                    // Connect BaseColor
                    Material->GetEditorOnlyData()->BaseColor.Connect(0, VatMaterialExp.Get());
                    UE_LOG(LogTemp, Warning, TEXT("Connected BaseColor to output index 0 (1st output)."));

                    // Connect Normal
                    if (VatMaterialExp->Outputs.Num() >= 4)
                    {
                        Material->GetEditorOnlyData()->Normal.Connect(3, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Normal to output index 3 (4th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Normal input."));
                    }

                    // Connect World Position Offset
                    if (VatMaterialExp->Outputs.Num() >= 5)
                    {
                        Material->GetEditorOnlyData()->WorldPositionOffset.Connect(4, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected World Position Offset to output index 4 (5th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to World Position Offset input."));
                    }

                    // Connect UV2
                    if (VatMaterialExp->Outputs.Num() >= 19)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[2].Connect(19, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV2 to output index 20 (21st output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV2 input."));
                    }

                    // Connect UV3
                    if (VatMaterialExp->Outputs.Num() >= 20)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[3].Connect(20, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV3 to output index 21 (22nd output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV3 input."));
                    }

                    // Connect UV4
                    if (VatMaterialExp->Outputs.Num() >= 21 )
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[4].Connect(21, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV4 to output index 22 (22nd output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV4 input."));
                    }
                }
                else
                {
                    UE_LOG(LogTemp, Error, TEXT("VatMaterialExp does not have any outputs to connect."));
                }
                break;

            case EVatType::VatType2:
                if (VatMaterialExp->Outputs.Num() > 0)
                {
                    // Connect BaseColor
                    Material->GetEditorOnlyData()->BaseColor.Connect(0, VatMaterialExp.Get());
                    UE_LOG(LogTemp, Warning, TEXT("Connected BaseColor to output index 0 (1st output)."));

                    // Connect Normal
                    if (VatMaterialExp->Outputs.Num() >= 4)
                    {
                        Material->GetEditorOnlyData()->Normal.Connect(3, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Normal to output index 3 (4th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Normal input."));
                    }

                    // Connect World Position Offset
                    if (VatMaterialExp->Outputs.Num() >= 5)
                    {
                        Material->GetEditorOnlyData()->WorldPositionOffset.Connect(4, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected World Position Offset to output index 4 (5th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to World Position Offset input."));
                    }

                    // Connect UV2
                    if (VatMaterialExp->Outputs.Num() >= 22)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[2].Connect(21, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV2 to output index 21 (22nd output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV2 input."));
                    }

                    // Connect UV3
                    if (VatMaterialExp->Outputs.Num() >= 23)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[3].Connect(22, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV3 to output index 22 (23rd output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV3 input."));
                    }

                    // Connect UV4
                    if (VatMaterialExp->Outputs.Num() >= 24)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[4].Connect(23, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV4 to output index 23 (24th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV4 input."));
                    }
                }
                else
                {
                    UE_LOG(LogTemp, Error, TEXT("VatMaterialExp does not have any outputs to connect."));
                }
                break;

            case EVatType::VatType3:
                if (VatMaterialExp->Outputs.Num() > 0)
                {
                    // Connect BaseColor
                    Material->GetEditorOnlyData()->BaseColor.Connect(0, VatMaterialExp.Get());
                    UE_LOG(LogTemp, Warning, TEXT("Connected BaseColor to output index 0 (1st output)."));

                    // Connect Normal
                    if (VatMaterialExp->Outputs.Num() >= 4)
                    {
                        Material->GetEditorOnlyData()->Normal.Connect(3, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Normal to output index 3 (4th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Normal input."));
                    }

                    // Connect World Position Offset
                    if (VatMaterialExp->Outputs.Num() >= 5)
                    {
                        Material->GetEditorOnlyData()->WorldPositionOffset.Connect(4, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected World Position Offset to output index 4 (5th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to World Position Offset input."));
                    }

                    // Connect UV2
                    if (VatMaterialExp->Outputs.Num() >= 20)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[2].Connect(20, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV2 to output index 20 (21st output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV2 input."));
                    }

                    // Connect UV3
                    if (VatMaterialExp->Outputs.Num() >= 21)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[3].Connect(21, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV3 to output index 21 (22nd output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV3 input."));
                    }
                }
                else
                {
                    UE_LOG(LogTemp, Error, TEXT("VatMaterialExp does not have any outputs to connect."));
                }
                break;

            case EVatType::VatType4:
                if (VatMaterialExp->Outputs.Num() > 0)
                {
                    // Connect BaseColor
                    Material->GetEditorOnlyData()->BaseColor.Connect(0, VatMaterialExp.Get());
                    UE_LOG(LogTemp, Warning, TEXT("Connected BaseColor to output index 0 (1st output)."));

                    // Connect Normal
                    if (VatMaterialExp->Outputs.Num() >= 4)
                    {
                        Material->GetEditorOnlyData()->Normal.Connect(3, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Normal to output index 3 (4th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Normal input."));
                    }

                    // Connect World Position Offset
                    if (VatMaterialExp->Outputs.Num() >= 5)
                    {
                        Material->GetEditorOnlyData()->WorldPositionOffset.Connect(4, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected World Position Offset to output index 4 (5th output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to World Position Offset input."));
                    }

                    // Connect UV0
                    if (VatMaterialExp->Outputs.Num() >= 19)
                    {
                        Material->GetEditorOnlyData()->CustomizedUVs[2].Connect(19, VatMaterialExp.Get());
                        UE_LOG(LogTemp, Warning, TEXT("Connected Customized UV2 to output index 20 (21st output)."));
                    }
                    else
                    {
                        UE_LOG(LogTemp, Error, TEXT("Not enough outputs to connect to Customized UV2 input."));
                    }
                }
                else
                {
                    UE_LOG(LogTemp, Error, TEXT("VatMaterialExp does not have any outputs to connect."));
                }
                break;

            default:
                UE_LOG(LogTemp, Error, TEXT("Invalid VAT type"));
                break;
            }
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("HoudiniVatMaterialFunction is null"));
        }
        
        // Save the material
        if (Material.Get())
        {
            if (const UPackage* VatMaterialPackage = Material->GetPackage())
            {
                VatMaterialPackage->MarkPackageDirty();
            }
        }

        // Save asset packages
        TArray<UPackage*> PackagesToSave;
        if (Material.Get())
        {
            PackagesToSave.Add(Material->GetPackage());
        }

        if (PackagesToSave.Num() > 0)
        {
            UEditorLoadingAndSavingUtils::SavePackages(PackagesToSave, true);
        }
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to create UMaterialExpressionMaterialFunctionCall"));
    }
}

void UHoudiniVatImporter::CreateVatMaterialInstance()
{
    if (CreatedMaterialName.IsEmpty())
    {
        UE_LOG(LogTemp, Error, TEXT("CreatedMaterialName is empty."));
        return;
    }

    const FString PackagePath = VatProperties->VatAssetPath.Path / CreatedMaterialName;
    
    UMaterial* CreatedMaterial = LoadObject<UMaterial>(nullptr, *PackagePath);
    
    if (!CreatedMaterial)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to load created material: %s"), *PackagePath);
        return;
    }

    UMaterialInstanceConstantFactoryNew* MaterialInstanceFactory = NewObject<UMaterialInstanceConstantFactoryNew>();
    MaterialInstanceFactory->AddToRoot();
    const FString MaterialInstanceName = CreatedMaterialName.Replace(TEXT("M_"), TEXT("MI_"));
    const FString MaterialInstancePackageName = VatProperties->VatAssetPath.Path / MaterialInstanceName;
    UPackage* MaterialInstancePackage = CreatePackage(*MaterialInstancePackageName);

    MaterialInstance = Cast<UMaterialInstanceConstant>(MaterialInstanceFactory->FactoryCreateNew(UMaterialInstanceConstant::StaticClass(), MaterialInstancePackage, FName(*MaterialInstanceName), RF_Public | RF_Standalone, nullptr, GWarn));
    MaterialInstance->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(MaterialInstance.Get());
    
    if (!MaterialInstance.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to create material instance: %s"), *MaterialInstanceName);
        return;
    }

    MaterialInstance->SetParentEditorOnly(CreatedMaterial);
    MaterialInstance->SetScalarParameterValueEditorOnly(FName("Houdini FPS"), VatProperties->VatFps);
    MaterialInstance->SetStaticSwitchParameterValueEditorOnly(FName("Loop Animation"), VatProperties->bVatLoopAnimation);
    MaterialInstance->SetScalarParameterValueEditorOnly(FName("Animation Length"), VatProperties->VatAnimationLength);
    MaterialInstance->SetStaticSwitchParameterValueEditorOnly(FName("Interframe Interpolation"), VatProperties->bVatInterpolate);
    MaterialInstance->SetStaticSwitchParameterValueEditorOnly(FName("Support Legacy Parameters and Instancing"), VatProperties->bVatSupportLegacyParametersAndInstancing);

    if (VatProperties->bVatSupportLegacyParametersAndInstancing)
    {
        FullLegacyDataPath = FPaths::ConvertRelativePathToFull(VatProperties->VatLegacyDataFilePath.FilePath);

        if (FString JsonString; FFileHelper::LoadFileToString(JsonString, *FullLegacyDataPath))
        {
            float BoundMaxX = 0.0f;
            float BoundMaxY = 0.0f;
            float BoundMaxZ = 0.0f;
            float BoundMinX = 0.0f;
            float BoundMinY = 0.0f;
            float BoundMinZ = 0.0f;

            for (const TArray<TPair<FString, float*>> Keys = {
                     { TEXT("\"Bound Max X\": "), &BoundMaxX },
                     { TEXT("\"Bound Max Y\": "), &BoundMaxY },
                     { TEXT("\"Bound Max Z\": "), &BoundMaxZ },
                     { TEXT("\"Bound Min X\": "), &BoundMinX },
                     { TEXT("\"Bound Min Y\": "), &BoundMinY },
                     { TEXT("\"Bound Min Z\": "), &BoundMinZ }
                 }; const TPair<FString, float*>& KeyPair : Keys)
            {
                const FString& Key = KeyPair.Key;
                float* const& ValuePtr = KeyPair.Value;

                if (const int32 KeyIndex = JsonString.Find(Key); KeyIndex != INDEX_NONE)
                {
                    const int32 ValueStartIndex = KeyIndex + Key.Len();
                    int32 ValueEndIndex = JsonString.Find(TEXT(","), ESearchCase::IgnoreCase, ESearchDir::FromStart, ValueStartIndex);
                    
                    if (ValueEndIndex == INDEX_NONE)
                    {
                        ValueEndIndex = JsonString.Find(TEXT("}"), ESearchCase::IgnoreCase, ESearchDir::FromStart, ValueStartIndex);
                    }

                    if (ValueEndIndex != INDEX_NONE)
                    {
                        FString ValueString = JsonString.Mid(ValueStartIndex, ValueEndIndex - ValueStartIndex).TrimStartAndEnd();
                        *ValuePtr = FCString::Atof(*ValueString);
                    }
                    else
                    {
                        UE_LOG(LogTemp, Warning, TEXT("Could not find the end of the value for '%s'."), *Key);
                    }
                }
                else
                {
                    UE_LOG(LogTemp, Warning, TEXT("Field '%s' not found in the JSON file."), *Key);
                }
            }

            MaterialInstance->SetScalarParameterValueEditorOnly(FName("Bound Max X"), BoundMaxX);
            MaterialInstance->SetScalarParameterValueEditorOnly(FName("Bound Max Y"), BoundMaxY);
            MaterialInstance->SetScalarParameterValueEditorOnly(FName("Bound Max Z"), BoundMaxZ);
            MaterialInstance->SetScalarParameterValueEditorOnly(FName("Bound Min X"), BoundMinX);
            MaterialInstance->SetScalarParameterValueEditorOnly(FName("Bound Min Y"), BoundMinY);
            MaterialInstance->SetScalarParameterValueEditorOnly(FName("Bound Min Z"), BoundMinZ);
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("Failed to load JSON file: %s"), *FullLegacyDataPath);
        }
    }
    
    for (const auto& [FilePath] : VatProperties->VatTextureFilePath)
    {
        FString TextureName = FPaths::GetBaseFilename(FilePath);
        UE_LOG(LogTemp, Log, TEXT("Imported 2D Texture: %s"), *TextureName);

        // Load the imported textures
        if (UTexture2D* ImportedTexture = LoadObject<UTexture2D>(nullptr, *FPaths::Combine(VatProperties->VatAssetPath.Path, TextureName)))
        {
            if (TextureName.Contains(TEXT("pos")))
            {
                MaterialInstance->SetTextureParameterValueEditorOnly(FName("Position Texture"), ImportedTexture);
                UE_LOG(LogTemp, Log, TEXT("Set Position Texture: %s"), *TextureName);
            }
            else if (TextureName.Contains(TEXT("rot")))
            {
                MaterialInstance->SetTextureParameterValueEditorOnly(FName("Rotation Texture"), ImportedTexture);
                UE_LOG(LogTemp, Log, TEXT("Set Rotation Texture: %s"), *TextureName);
            }
            else if (TextureName.Contains(TEXT("col")))
            {
                MaterialInstance->SetTextureParameterValueEditorOnly(FName("Color Texture"), ImportedTexture);
                UE_LOG(LogTemp, Log, TEXT("Set Color Texture: %s"), *TextureName);
            }
            else if (TextureName.Contains(TEXT("lookup")))
            {
                MaterialInstance->SetTextureParameterValueEditorOnly(FName("Lookup Table"), ImportedTexture);
                UE_LOG(LogTemp, Log, TEXT("Set Lookup Texture: %s"), *TextureName);
            }
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("Failed to load texture: %s"), *TextureName);
        }
    }
    
    // Save the material instance
    if (MaterialInstance.Get())
    {
        if (const UPackage* VatMaterialInstancePackage = MaterialInstance->GetPackage())
        {
            VatMaterialInstancePackage->MarkPackageDirty();
        }
    }

    // Save asset packages
    TArray<UPackage*> PackagesToSave;
    if (MaterialInstance.Get())
    {
        PackagesToSave.Add(MaterialInstance->GetPackage());
    }

    if (PackagesToSave.Num() > 0)
    {
        UEditorLoadingAndSavingUtils::SavePackages(PackagesToSave, true);
    }
}

void UHoudiniVatImporter::CreateVatBlueprint()
{
    if (CreatedMaterialName.IsEmpty())
    {
        UE_LOG(LogTemp, Error, TEXT("CreatedMaterialName is empty."));
        return;
    }

    const FString PackagePath = VatProperties->VatAssetPath.Path / CreatedMaterialName;

    if (const UMaterial* CreatedMaterial = LoadObject<UMaterial>(nullptr, *PackagePath); !CreatedMaterial)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to load created material: %s"), *PackagePath);
        return;
    }

    const FString BlueprintName = CreatedMaterialName.Replace(TEXT("M_"), TEXT("BP_"));
    const FString BlueprintPackageName = VatProperties->VatAssetPath.Path / BlueprintName;
    UPackage* BlueprintPackage = CreatePackage(*BlueprintPackageName);
    
    UBlueprintFactory* BlueprintFactory = NewObject<UBlueprintFactory>();
    BlueprintFactory->AddToRoot();
    BlueprintFactory->ParentClass = AHoudiniVatActor::StaticClass();

    Blueprint = Cast<UBlueprint>(BlueprintFactory->FactoryCreateNew(UBlueprint::StaticClass(), BlueprintPackage, FName(*BlueprintName), RF_Public | RF_Standalone, nullptr, GWarn));
    Blueprint->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Blueprint.Get());
    
	if (!Blueprint.Get())
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to create blueprint: %s"), *BlueprintName);
        return;
    }

    if (Blueprint->GeneratedClass)
    {
        if (AHoudiniVatActor* DefaultActor = Cast<AHoudiniVatActor>(Blueprint->GeneratedClass->GetDefaultObject()))
        {
            if (DefaultActor->Vat_StaticMesh)
            {
                DefaultActor->Vat_StaticMesh->SetStaticMesh(StaticMesh.Get());
                DefaultActor->Vat_MaterialInstances.Empty();

                for (int32 SlotIndex = 0; SlotIndex < DefaultActor->Vat_StaticMesh->GetNumMaterials(); ++SlotIndex)
                {
                    DefaultActor->Vat_StaticMesh->SetMaterial(SlotIndex, MaterialInstance.Get());
                    DefaultActor->Vat_MaterialInstances.Add(MaterialInstance.Get());
                }
            }
        }

        // Save the material instance
        if (Blueprint.Get())
        {
            if (const UPackage* VatBlueprintPackage = Blueprint->GetPackage())
            {
                VatBlueprintPackage->MarkPackageDirty();
            }
        }

        // Save asset packages
        TArray<UPackage*> PackagesToSave;
        if (Blueprint.Get())
        {
            PackagesToSave.Add(Blueprint->GetPackage());
        }

        if (PackagesToSave.Num() > 0)
        {
            UEditorLoadingAndSavingUtils::SavePackages(PackagesToSave, true);
        }
    }
    
    FKismetEditorUtilities::CompileBlueprint(Blueprint.Get());
}
