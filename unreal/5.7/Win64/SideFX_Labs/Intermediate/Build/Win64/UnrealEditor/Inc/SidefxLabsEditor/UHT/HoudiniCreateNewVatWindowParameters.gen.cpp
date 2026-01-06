// Copyright Epic Games, Inc. All Rights Reserved.
/*===========================================================================
	Generated code exported from UnrealHeaderTool.
	DO NOT modify this manually! Edit the corresponding .h files instead!
===========================================================================*/

#include "UObject/GeneratedCppIncludes.h"
#include "HoudiniCreateNewVatWindowParameters.h"
#include "UObject/SoftObjectPath.h"

PRAGMA_DISABLE_DEPRECATION_WARNINGS
static_assert(!UE_WITH_CONSTINIT_UOBJECT, "This generated code can only be compiled with !UE_WITH_CONSTINIT_OBJECT");
void EmptyLinkFunctionForGeneratedCodeHoudiniCreateNewVatWindowParameters() {}

// ********** Begin Cross Module References ********************************************************
COREUOBJECT_API UClass* Z_Construct_UClass_UObject();
COREUOBJECT_API UScriptStruct* Z_Construct_UScriptStruct_FDirectoryPath();
COREUOBJECT_API UScriptStruct* Z_Construct_UScriptStruct_FFilePath();
SIDEFXLABSEDITOR_API UClass* Z_Construct_UClass_UCreateNewVatProperties();
SIDEFXLABSEDITOR_API UClass* Z_Construct_UClass_UCreateNewVatProperties_NoRegister();
SIDEFXLABSEDITOR_API UEnum* Z_Construct_UEnum_SidefxLabsEditor_EVatType();
UPackage* Z_Construct_UPackage__Script_SidefxLabsEditor();
// ********** End Cross Module References **********************************************************

// ********** Begin Enum EVatType ******************************************************************
static FEnumRegistrationInfo Z_Registration_Info_UEnum_EVatType;
static UEnum* EVatType_StaticEnum()
{
	if (!Z_Registration_Info_UEnum_EVatType.OuterSingleton)
	{
		Z_Registration_Info_UEnum_EVatType.OuterSingleton = GetStaticEnum(Z_Construct_UEnum_SidefxLabsEditor_EVatType, (UObject*)Z_Construct_UPackage__Script_SidefxLabsEditor(), TEXT("EVatType"));
	}
	return Z_Registration_Info_UEnum_EVatType.OuterSingleton;
}
template<> SIDEFXLABSEDITOR_NON_ATTRIBUTED_API UEnum* StaticEnum<EVatType>()
{
	return EVatType_StaticEnum();
}
struct Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Enum_MetaDataParams[] = {
		{ "BlueprintType", "true" },
#if !UE_BUILD_SHIPPING
		{ "Comment", "/**\n * Defines the type of Vertex Animation Texture (VAT) to create.\n * Each type corresponds to a different animation type exported from Houdini.\n */" },
#endif
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Defines the type of Vertex Animation Texture (VAT) to create.\nEach type corresponds to a different animation type exported from Houdini." },
#endif
		{ "VatType1.DisplayName", "Soft-Body Deformation (Soft)" },
		{ "VatType1.Name", "EVatType::VatType1" },
		{ "VatType2.DisplayName", "Rigid-Body Dynamics (Rigid)" },
		{ "VatType2.Name", "EVatType::VatType2" },
		{ "VatType3.DisplayName", "Dynamic Remeshing (Fluid)" },
		{ "VatType3.Name", "EVatType::VatType3" },
		{ "VatType4.DisplayName", "Particle Sprites (Sprite)" },
		{ "VatType4.Name", "EVatType::VatType4" },
	};
#endif // WITH_METADATA
	static constexpr UECodeGen_Private::FEnumeratorParam Enumerators[] = {
		{ "EVatType::VatType1", (int64)EVatType::VatType1 },
		{ "EVatType::VatType2", (int64)EVatType::VatType2 },
		{ "EVatType::VatType3", (int64)EVatType::VatType3 },
		{ "EVatType::VatType4", (int64)EVatType::VatType4 },
	};
	static const UECodeGen_Private::FEnumParams EnumParams;
}; // struct Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics 
const UECodeGen_Private::FEnumParams Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics::EnumParams = {
	(UObject*(*)())Z_Construct_UPackage__Script_SidefxLabsEditor,
	nullptr,
	"EVatType",
	"EVatType",
	Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics::Enumerators,
	RF_Public|RF_Transient|RF_MarkAsNative,
	UE_ARRAY_COUNT(Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics::Enumerators),
	EEnumFlags::None,
	(uint8)UEnum::ECppForm::EnumClass,
	METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics::Enum_MetaDataParams), Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics::Enum_MetaDataParams)
};
UEnum* Z_Construct_UEnum_SidefxLabsEditor_EVatType()
{
	if (!Z_Registration_Info_UEnum_EVatType.InnerSingleton)
	{
		UECodeGen_Private::ConstructUEnum(Z_Registration_Info_UEnum_EVatType.InnerSingleton, Z_Construct_UEnum_SidefxLabsEditor_EVatType_Statics::EnumParams);
	}
	return Z_Registration_Info_UEnum_EVatType.InnerSingleton;
}
// ********** End Enum EVatType ********************************************************************

// ********** Begin Class UCreateNewVatProperties **************************************************
FClassRegistrationInfo Z_Registration_Info_UClass_UCreateNewVatProperties;
UClass* UCreateNewVatProperties::GetPrivateStaticClass()
{
	using TClass = UCreateNewVatProperties;
	if (!Z_Registration_Info_UClass_UCreateNewVatProperties.InnerSingleton)
	{
		GetPrivateStaticClassBody(
			TClass::StaticPackage(),
			TEXT("CreateNewVatProperties"),
			Z_Registration_Info_UClass_UCreateNewVatProperties.InnerSingleton,
			StaticRegisterNativesUCreateNewVatProperties,
			sizeof(TClass),
			alignof(TClass),
			TClass::StaticClassFlags,
			TClass::StaticClassCastFlags(),
			TClass::StaticConfigName(),
			(UClass::ClassConstructorType)InternalConstructor<TClass>,
			(UClass::ClassVTableHelperCtorCallerType)InternalVTableHelperCtorCaller<TClass>,
			UOBJECT_CPPCLASS_STATICFUNCTIONS_FORCLASS(TClass),
			&TClass::Super::StaticClass,
			&TClass::WithinClass::StaticClass
		);
	}
	return Z_Registration_Info_UClass_UCreateNewVatProperties.InnerSingleton;
}
UClass* Z_Construct_UClass_UCreateNewVatProperties_NoRegister()
{
	return UCreateNewVatProperties::GetPrivateStaticClass();
}
struct Z_Construct_UClass_UCreateNewVatProperties_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Class_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/**\n * Properties for creating a new VAT asset.\n * Contains all parameters needed for importing and configuring VAT materials.\n */" },
#endif
		{ "IncludePath", "HoudiniCreateNewVatWindowParameters.h" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Properties for creating a new VAT asset.\nContains all parameters needed for importing and configuring VAT materials." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatFbxFilePath_MetaData[] = {
		{ "Category", "Import" },
		{ "DisplayName", "FBX File Path" },
		{ "FilePathFilter", "FBX (*.fbx)|*.fbx" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The file path to the exported FBX file from the Labs Vertex Animation Textures ROP." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatTextureFilePath_MetaData[] = {
		{ "Category", "Import" },
		{ "DisplayName", "Texture File Path" },
		{ "FilePathFilter", "Textures (*.exr;*.png)|*.exr;*.png" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The file path to the exported texture files from the Labs Vertex Animation Textures ROP." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatAssetPath_MetaData[] = {
		{ "Category", "Import" },
		{ "ContentDir", "" },
		{ "DisplayName", "Asset Path" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The Unreal asset path where files will be created and imported." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bCreateVatBlueprint_MetaData[] = {
		{ "Category", "Import" },
		{ "DisplayName", "Create VAT Blueprint" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Turn this on to create a blueprint that allows for control of VAT functionality." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatMaterialName_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "Material Name" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The name of the created VAT material." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatType_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "VAT Type" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The VAT type depends on what kind of animation you have exported from Houdini. This should match the selected mode in the Labs Vertex Animation Textures ROP." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatFps_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "Houdini FPS" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The FPS of the Houdini HIP file when exporting the animation." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bVatInterpolate_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "Interframe Interpolation" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Interpolates interframe data when the animation frame is a fractional number. This results in smooth visuals even when you slow down the animation or when the frame rate is unstable." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bVatLoopAnimation_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "Loop Animation" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Determines if VAT animation will loop continuously or stop after a specified number of seconds. If disabled, make sure to set the Animation Length parameter accordingly." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatAnimationLength_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "Animation Length" },
		{ "EditCondition", "!bVatLoopAnimation" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The amount of time, in seconds, the VAT animation will play before stopping." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bVatSupportLegacyParametersAndInstancing_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "Support Legacy Parameters and Instancing" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "If you want to use this Material Instance with ISM/HISM or mesh particles, turn this on and turn on Support Real-Time Instancing in Houdini. If you simply want to use the legacy parameters or modify the object's bounds, turn this on and only turn on Allow Exporting Real-Time Data JSON File (Legacy) in Houdini without turning on Support Real-Time Instancing. Legacy parameters are a list of numerical values exported through a JSON file. They contain the embedded data just like the actual mesh, but when Support Legacy Parameters and Instancing is turned on, the shader will read the bounds and the embedded data from the legacy parameters instead of the actual mesh. Using legacy parameters is less convenient, but it does produce more accurate results if the animation spans a huge area; it also leads to lower instruction counts." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatLegacyDataFilePath_MetaData[] = {
		{ "Category", "Parameters" },
		{ "DisplayName", "Data File Path" },
		{ "EditCondition", "bVatSupportLegacyParametersAndInstancing" },
		{ "EditConditionHides", "" },
		{ "FilePathFilter", "JSON (*.json)|*.json" },
		{ "ModuleRelativePath", "Public/HoudiniCreateNewVatWindowParameters.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The file path to the exported JSON file from the Labs Vertex Animation Textures ROP." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Class UCreateNewVatProperties constinit property declarations ******************
	static const UECodeGen_Private::FStructPropertyParams NewProp_VatFbxFilePath;
	static const UECodeGen_Private::FStructPropertyParams NewProp_VatTextureFilePath_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_VatTextureFilePath;
	static const UECodeGen_Private::FStructPropertyParams NewProp_VatAssetPath;
	static void NewProp_bCreateVatBlueprint_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bCreateVatBlueprint;
	static const UECodeGen_Private::FStrPropertyParams NewProp_VatMaterialName;
	static const UECodeGen_Private::FBytePropertyParams NewProp_VatType_Underlying;
	static const UECodeGen_Private::FEnumPropertyParams NewProp_VatType;
	static const UECodeGen_Private::FIntPropertyParams NewProp_VatFps;
	static void NewProp_bVatInterpolate_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bVatInterpolate;
	static void NewProp_bVatLoopAnimation_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bVatLoopAnimation;
	static const UECodeGen_Private::FFloatPropertyParams NewProp_VatAnimationLength;
	static void NewProp_bVatSupportLegacyParametersAndInstancing_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bVatSupportLegacyParametersAndInstancing;
	static const UECodeGen_Private::FStructPropertyParams NewProp_VatLegacyDataFilePath;
	static const UECodeGen_Private::FPropertyParamsBase* const PropPointers[];
// ********** End Class UCreateNewVatProperties constinit property declarations ********************
	static UObject* (*const DependentSingletons[])();
	static constexpr FCppClassTypeInfoStatic StaticCppClassTypeInfo = {
		TCppClassTypeTraits<UCreateNewVatProperties>::IsAbstract,
	};
	static const UECodeGen_Private::FClassParams ClassParams;
}; // struct Z_Construct_UClass_UCreateNewVatProperties_Statics

// ********** Begin Class UCreateNewVatProperties Property Definitions *****************************
const UECodeGen_Private::FStructPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatFbxFilePath = { "VatFbxFilePath", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Struct, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatFbxFilePath), Z_Construct_UScriptStruct_FFilePath, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatFbxFilePath_MetaData), NewProp_VatFbxFilePath_MetaData) }; // 1592925316
const UECodeGen_Private::FStructPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatTextureFilePath_Inner = { "VatTextureFilePath", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Struct, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, Z_Construct_UScriptStruct_FFilePath, METADATA_PARAMS(0, nullptr) }; // 1592925316
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatTextureFilePath = { "VatTextureFilePath", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatTextureFilePath), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatTextureFilePath_MetaData), NewProp_VatTextureFilePath_MetaData) }; // 1592925316
const UECodeGen_Private::FStructPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatAssetPath = { "VatAssetPath", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Struct, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatAssetPath), Z_Construct_UScriptStruct_FDirectoryPath, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatAssetPath_MetaData), NewProp_VatAssetPath_MetaData) }; // 1225349189
void Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bCreateVatBlueprint_SetBit(void* Obj)
{
	((UCreateNewVatProperties*)Obj)->bCreateVatBlueprint = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bCreateVatBlueprint = { "bCreateVatBlueprint", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(UCreateNewVatProperties), &Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bCreateVatBlueprint_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bCreateVatBlueprint_MetaData), NewProp_bCreateVatBlueprint_MetaData) };
const UECodeGen_Private::FStrPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatMaterialName = { "VatMaterialName", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Str, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatMaterialName), METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatMaterialName_MetaData), NewProp_VatMaterialName_MetaData) };
const UECodeGen_Private::FBytePropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatType_Underlying = { "UnderlyingType", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Byte, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, nullptr, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FEnumPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatType = { "VatType", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Enum, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatType), Z_Construct_UEnum_SidefxLabsEditor_EVatType, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatType_MetaData), NewProp_VatType_MetaData) }; // 1780643717
const UECodeGen_Private::FIntPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatFps = { "VatFps", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Int, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatFps), METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatFps_MetaData), NewProp_VatFps_MetaData) };
void Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatInterpolate_SetBit(void* Obj)
{
	((UCreateNewVatProperties*)Obj)->bVatInterpolate = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatInterpolate = { "bVatInterpolate", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(UCreateNewVatProperties), &Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatInterpolate_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bVatInterpolate_MetaData), NewProp_bVatInterpolate_MetaData) };
void Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatLoopAnimation_SetBit(void* Obj)
{
	((UCreateNewVatProperties*)Obj)->bVatLoopAnimation = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatLoopAnimation = { "bVatLoopAnimation", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(UCreateNewVatProperties), &Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatLoopAnimation_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bVatLoopAnimation_MetaData), NewProp_bVatLoopAnimation_MetaData) };
const UECodeGen_Private::FFloatPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatAnimationLength = { "VatAnimationLength", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Float, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatAnimationLength), METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatAnimationLength_MetaData), NewProp_VatAnimationLength_MetaData) };
void Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatSupportLegacyParametersAndInstancing_SetBit(void* Obj)
{
	((UCreateNewVatProperties*)Obj)->bVatSupportLegacyParametersAndInstancing = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatSupportLegacyParametersAndInstancing = { "bVatSupportLegacyParametersAndInstancing", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(UCreateNewVatProperties), &Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatSupportLegacyParametersAndInstancing_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bVatSupportLegacyParametersAndInstancing_MetaData), NewProp_bVatSupportLegacyParametersAndInstancing_MetaData) };
const UECodeGen_Private::FStructPropertyParams Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatLegacyDataFilePath = { "VatLegacyDataFilePath", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Struct, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UCreateNewVatProperties, VatLegacyDataFilePath), Z_Construct_UScriptStruct_FFilePath, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatLegacyDataFilePath_MetaData), NewProp_VatLegacyDataFilePath_MetaData) }; // 1592925316
const UECodeGen_Private::FPropertyParamsBase* const Z_Construct_UClass_UCreateNewVatProperties_Statics::PropPointers[] = {
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatFbxFilePath,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatTextureFilePath_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatTextureFilePath,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatAssetPath,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bCreateVatBlueprint,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatMaterialName,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatType_Underlying,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatType,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatFps,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatInterpolate,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatLoopAnimation,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatAnimationLength,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_bVatSupportLegacyParametersAndInstancing,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UCreateNewVatProperties_Statics::NewProp_VatLegacyDataFilePath,
};
static_assert(UE_ARRAY_COUNT(Z_Construct_UClass_UCreateNewVatProperties_Statics::PropPointers) < 2048);
// ********** End Class UCreateNewVatProperties Property Definitions *******************************
UObject* (*const Z_Construct_UClass_UCreateNewVatProperties_Statics::DependentSingletons[])() = {
	(UObject* (*)())Z_Construct_UClass_UObject,
	(UObject* (*)())Z_Construct_UPackage__Script_SidefxLabsEditor,
};
static_assert(UE_ARRAY_COUNT(Z_Construct_UClass_UCreateNewVatProperties_Statics::DependentSingletons) < 16);
const UECodeGen_Private::FClassParams Z_Construct_UClass_UCreateNewVatProperties_Statics::ClassParams = {
	&UCreateNewVatProperties::StaticClass,
	nullptr,
	&StaticCppClassTypeInfo,
	DependentSingletons,
	nullptr,
	Z_Construct_UClass_UCreateNewVatProperties_Statics::PropPointers,
	nullptr,
	UE_ARRAY_COUNT(DependentSingletons),
	0,
	UE_ARRAY_COUNT(Z_Construct_UClass_UCreateNewVatProperties_Statics::PropPointers),
	0,
	0x001000A0u,
	METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UClass_UCreateNewVatProperties_Statics::Class_MetaDataParams), Z_Construct_UClass_UCreateNewVatProperties_Statics::Class_MetaDataParams)
};
void UCreateNewVatProperties::StaticRegisterNativesUCreateNewVatProperties()
{
}
UClass* Z_Construct_UClass_UCreateNewVatProperties()
{
	if (!Z_Registration_Info_UClass_UCreateNewVatProperties.OuterSingleton)
	{
		UECodeGen_Private::ConstructUClass(Z_Registration_Info_UClass_UCreateNewVatProperties.OuterSingleton, Z_Construct_UClass_UCreateNewVatProperties_Statics::ClassParams);
	}
	return Z_Registration_Info_UClass_UCreateNewVatProperties.OuterSingleton;
}
DEFINE_VTABLE_PTR_HELPER_CTOR_NS(, UCreateNewVatProperties);
UCreateNewVatProperties::~UCreateNewVatProperties() {}
// ********** End Class UCreateNewVatProperties ****************************************************

// ********** Begin Registration *******************************************************************
struct Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h__Script_SidefxLabsEditor_Statics
{
	static constexpr FEnumRegisterCompiledInInfo EnumInfo[] = {
		{ EVatType_StaticEnum, TEXT("EVatType"), &Z_Registration_Info_UEnum_EVatType, CONSTRUCT_RELOAD_VERSION_INFO(FEnumReloadVersionInfo, 1780643717U) },
	};
	static constexpr FClassRegisterCompiledInInfo ClassInfo[] = {
		{ Z_Construct_UClass_UCreateNewVatProperties, UCreateNewVatProperties::StaticClass, TEXT("UCreateNewVatProperties"), &Z_Registration_Info_UClass_UCreateNewVatProperties, CONSTRUCT_RELOAD_VERSION_INFO(FClassReloadVersionInfo, sizeof(UCreateNewVatProperties), 4123115343U) },
	};
}; // Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h__Script_SidefxLabsEditor_Statics 
static FRegisterCompiledInInfo Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h__Script_SidefxLabsEditor_2758522807{
	TEXT("/Script/SidefxLabsEditor"),
	Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h__Script_SidefxLabsEditor_Statics::ClassInfo, UE_ARRAY_COUNT(Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h__Script_SidefxLabsEditor_Statics::ClassInfo),
	nullptr, 0,
	Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h__Script_SidefxLabsEditor_Statics::EnumInfo, UE_ARRAY_COUNT(Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h__Script_SidefxLabsEditor_Statics::EnumInfo),
};
// ********** End Registration *********************************************************************

PRAGMA_ENABLE_DEPRECATION_WARNINGS
