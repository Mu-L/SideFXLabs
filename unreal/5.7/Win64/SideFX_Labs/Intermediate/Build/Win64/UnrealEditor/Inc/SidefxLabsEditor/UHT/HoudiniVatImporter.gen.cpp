// Copyright Epic Games, Inc. All Rights Reserved.
/*===========================================================================
	Generated code exported from UnrealHeaderTool.
	DO NOT modify this manually! Edit the corresponding .h files instead!
===========================================================================*/

#include "UObject/GeneratedCppIncludes.h"
#include "VatImporter/HoudiniVatImporter.h"

PRAGMA_DISABLE_DEPRECATION_WARNINGS
static_assert(!UE_WITH_CONSTINIT_UOBJECT, "This generated code can only be compiled with !UE_WITH_CONSTINIT_OBJECT");
void EmptyLinkFunctionForGeneratedCodeHoudiniVatImporter() {}

// ********** Begin Cross Module References ********************************************************
COREUOBJECT_API UClass* Z_Construct_UClass_UObject();
ENGINE_API UClass* Z_Construct_UClass_UMaterialFunction_NoRegister();
SIDEFXLABSEDITOR_API UClass* Z_Construct_UClass_UCreateNewVatProperties_NoRegister();
SIDEFXLABSEDITOR_API UClass* Z_Construct_UClass_UHoudiniVatImporter();
SIDEFXLABSEDITOR_API UClass* Z_Construct_UClass_UHoudiniVatImporter_NoRegister();
UPackage* Z_Construct_UPackage__Script_SidefxLabsEditor();
// ********** End Cross Module References **********************************************************

// ********** Begin Class UHoudiniVatImporter Function CreateVatBlueprint **************************
struct Z_Construct_UFunction_UHoudiniVatImporter_CreateVatBlueprint_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Function_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Creates a blueprint actor for the VAT. */" },
#endif
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Creates a blueprint actor for the VAT." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Function CreateVatBlueprint constinit property declarations ********************
// ********** End Function CreateVatBlueprint constinit property declarations **********************
	static const UECodeGen_Private::FFunctionParams FuncParams;
};
const UECodeGen_Private::FFunctionParams Z_Construct_UFunction_UHoudiniVatImporter_CreateVatBlueprint_Statics::FuncParams = { { (UObject*(*)())Z_Construct_UClass_UHoudiniVatImporter, nullptr, "CreateVatBlueprint", 	nullptr, 
	0, 
0,
RF_Public|RF_Transient|RF_MarkAsNative, (EFunctionFlags)0x00020401, 0, 0, METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UFunction_UHoudiniVatImporter_CreateVatBlueprint_Statics::Function_MetaDataParams), Z_Construct_UFunction_UHoudiniVatImporter_CreateVatBlueprint_Statics::Function_MetaDataParams)},  };
UFunction* Z_Construct_UFunction_UHoudiniVatImporter_CreateVatBlueprint()
{
	static UFunction* ReturnFunction = nullptr;
	if (!ReturnFunction)
	{
		UECodeGen_Private::ConstructUFunction(&ReturnFunction, Z_Construct_UFunction_UHoudiniVatImporter_CreateVatBlueprint_Statics::FuncParams);
	}
	return ReturnFunction;
}
DEFINE_FUNCTION(UHoudiniVatImporter::execCreateVatBlueprint)
{
	P_FINISH;
	P_NATIVE_BEGIN;
	P_THIS->CreateVatBlueprint();
	P_NATIVE_END;
}
// ********** End Class UHoudiniVatImporter Function CreateVatBlueprint ****************************

// ********** Begin Class UHoudiniVatImporter Function CreateVatMaterial ***************************
struct Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterial_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Function_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Creates the VAT material. */" },
#endif
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Creates the VAT material." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Function CreateVatMaterial constinit property declarations *********************
// ********** End Function CreateVatMaterial constinit property declarations ***********************
	static const UECodeGen_Private::FFunctionParams FuncParams;
};
const UECodeGen_Private::FFunctionParams Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterial_Statics::FuncParams = { { (UObject*(*)())Z_Construct_UClass_UHoudiniVatImporter, nullptr, "CreateVatMaterial", 	nullptr, 
	0, 
0,
RF_Public|RF_Transient|RF_MarkAsNative, (EFunctionFlags)0x00020401, 0, 0, METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterial_Statics::Function_MetaDataParams), Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterial_Statics::Function_MetaDataParams)},  };
UFunction* Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterial()
{
	static UFunction* ReturnFunction = nullptr;
	if (!ReturnFunction)
	{
		UECodeGen_Private::ConstructUFunction(&ReturnFunction, Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterial_Statics::FuncParams);
	}
	return ReturnFunction;
}
DEFINE_FUNCTION(UHoudiniVatImporter::execCreateVatMaterial)
{
	P_FINISH;
	P_NATIVE_BEGIN;
	P_THIS->CreateVatMaterial();
	P_NATIVE_END;
}
// ********** End Class UHoudiniVatImporter Function CreateVatMaterial *****************************

// ********** Begin Class UHoudiniVatImporter Function CreateVatMaterialInstance *******************
struct Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterialInstance_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Function_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Creates a material instance from the VAT material. */" },
#endif
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Creates a material instance from the VAT material." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Function CreateVatMaterialInstance constinit property declarations *************
// ********** End Function CreateVatMaterialInstance constinit property declarations ***************
	static const UECodeGen_Private::FFunctionParams FuncParams;
};
const UECodeGen_Private::FFunctionParams Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterialInstance_Statics::FuncParams = { { (UObject*(*)())Z_Construct_UClass_UHoudiniVatImporter, nullptr, "CreateVatMaterialInstance", 	nullptr, 
	0, 
0,
RF_Public|RF_Transient|RF_MarkAsNative, (EFunctionFlags)0x00020401, 0, 0, METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterialInstance_Statics::Function_MetaDataParams), Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterialInstance_Statics::Function_MetaDataParams)},  };
UFunction* Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterialInstance()
{
	static UFunction* ReturnFunction = nullptr;
	if (!ReturnFunction)
	{
		UECodeGen_Private::ConstructUFunction(&ReturnFunction, Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterialInstance_Statics::FuncParams);
	}
	return ReturnFunction;
}
DEFINE_FUNCTION(UHoudiniVatImporter::execCreateVatMaterialInstance)
{
	P_FINISH;
	P_NATIVE_BEGIN;
	P_THIS->CreateVatMaterialInstance();
	P_NATIVE_END;
}
// ********** End Class UHoudiniVatImporter Function CreateVatMaterialInstance *********************

// ********** Begin Class UHoudiniVatImporter Function ImportFiles *********************************
struct Z_Construct_UFunction_UHoudiniVatImporter_ImportFiles_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Function_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Imports all files. */" },
#endif
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Imports all files." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Function ImportFiles constinit property declarations ***************************
// ********** End Function ImportFiles constinit property declarations *****************************
	static const UECodeGen_Private::FFunctionParams FuncParams;
};
const UECodeGen_Private::FFunctionParams Z_Construct_UFunction_UHoudiniVatImporter_ImportFiles_Statics::FuncParams = { { (UObject*(*)())Z_Construct_UClass_UHoudiniVatImporter, nullptr, "ImportFiles", 	nullptr, 
	0, 
0,
RF_Public|RF_Transient|RF_MarkAsNative, (EFunctionFlags)0x00020401, 0, 0, METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UFunction_UHoudiniVatImporter_ImportFiles_Statics::Function_MetaDataParams), Z_Construct_UFunction_UHoudiniVatImporter_ImportFiles_Statics::Function_MetaDataParams)},  };
UFunction* Z_Construct_UFunction_UHoudiniVatImporter_ImportFiles()
{
	static UFunction* ReturnFunction = nullptr;
	if (!ReturnFunction)
	{
		UECodeGen_Private::ConstructUFunction(&ReturnFunction, Z_Construct_UFunction_UHoudiniVatImporter_ImportFiles_Statics::FuncParams);
	}
	return ReturnFunction;
}
DEFINE_FUNCTION(UHoudiniVatImporter::execImportFiles)
{
	P_FINISH;
	P_NATIVE_BEGIN;
	P_THIS->ImportFiles();
	P_NATIVE_END;
}
// ********** End Class UHoudiniVatImporter Function ImportFiles ***********************************

// ********** Begin Class UHoudiniVatImporter Function SetProperties *******************************
struct Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics
{
	struct HoudiniVatImporter_eventSetProperties_Parms
	{
		UCreateNewVatProperties* InProperties;
	};
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Function_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Sets the properties to use for VAT import. */" },
#endif
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Sets the properties to use for VAT import." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Function SetProperties constinit property declarations *************************
	static const UECodeGen_Private::FObjectPropertyParams NewProp_InProperties;
	static const UECodeGen_Private::FPropertyParamsBase* const PropPointers[];
// ********** End Function SetProperties constinit property declarations ***************************
	static const UECodeGen_Private::FFunctionParams FuncParams;
};

// ********** Begin Function SetProperties Property Definitions ************************************
const UECodeGen_Private::FObjectPropertyParams Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::NewProp_InProperties = { "InProperties", nullptr, (EPropertyFlags)0x0010000000000080, UECodeGen_Private::EPropertyGenFlags::Object, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(HoudiniVatImporter_eventSetProperties_Parms, InProperties), Z_Construct_UClass_UCreateNewVatProperties_NoRegister, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FPropertyParamsBase* const Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::PropPointers[] = {
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::NewProp_InProperties,
};
static_assert(UE_ARRAY_COUNT(Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::PropPointers) < 2048);
// ********** End Function SetProperties Property Definitions **************************************
const UECodeGen_Private::FFunctionParams Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::FuncParams = { { (UObject*(*)())Z_Construct_UClass_UHoudiniVatImporter, nullptr, "SetProperties", 	Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::PropPointers, 
	UE_ARRAY_COUNT(Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::PropPointers), 
sizeof(Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::HoudiniVatImporter_eventSetProperties_Parms),
RF_Public|RF_Transient|RF_MarkAsNative, (EFunctionFlags)0x00020401, 0, 0, METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::Function_MetaDataParams), Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::Function_MetaDataParams)},  };
static_assert(sizeof(Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::HoudiniVatImporter_eventSetProperties_Parms) < MAX_uint16);
UFunction* Z_Construct_UFunction_UHoudiniVatImporter_SetProperties()
{
	static UFunction* ReturnFunction = nullptr;
	if (!ReturnFunction)
	{
		UECodeGen_Private::ConstructUFunction(&ReturnFunction, Z_Construct_UFunction_UHoudiniVatImporter_SetProperties_Statics::FuncParams);
	}
	return ReturnFunction;
}
DEFINE_FUNCTION(UHoudiniVatImporter::execSetProperties)
{
	P_GET_OBJECT(UCreateNewVatProperties,Z_Param_InProperties);
	P_FINISH;
	P_NATIVE_BEGIN;
	P_THIS->SetProperties(Z_Param_InProperties);
	P_NATIVE_END;
}
// ********** End Class UHoudiniVatImporter Function SetProperties *********************************

// ********** Begin Class UHoudiniVatImporter ******************************************************
FClassRegistrationInfo Z_Registration_Info_UClass_UHoudiniVatImporter;
UClass* UHoudiniVatImporter::GetPrivateStaticClass()
{
	using TClass = UHoudiniVatImporter;
	if (!Z_Registration_Info_UClass_UHoudiniVatImporter.InnerSingleton)
	{
		GetPrivateStaticClassBody(
			TClass::StaticPackage(),
			TEXT("HoudiniVatImporter"),
			Z_Registration_Info_UClass_UHoudiniVatImporter.InnerSingleton,
			StaticRegisterNativesUHoudiniVatImporter,
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
	return Z_Registration_Info_UClass_UHoudiniVatImporter.InnerSingleton;
}
UClass* Z_Construct_UClass_UHoudiniVatImporter_NoRegister()
{
	return UHoudiniVatImporter::GetPrivateStaticClass();
}
struct Z_Construct_UClass_UHoudiniVatImporter_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Class_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/**\n * Handles the import and setup of Vertex Animation Texture (VAT) assets.\n * Manages FBX import, texture import, material creation, and blueprint generation.\n */" },
#endif
		{ "IncludePath", "VatImporter/HoudiniVatImporter.h" },
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Handles the import and setup of Vertex Animation Texture (VAT) assets.\nManages FBX import, texture import, material creation, and blueprint generation." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_VatProperties_MetaData[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Properties for the VAT import. */" },
#endif
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Properties for the VAT import." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_HoudiniVatMaterialFunction_MetaData[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** The material function to use for the VAT. */" },
#endif
		{ "ModuleRelativePath", "Private/VatImporter/HoudiniVatImporter.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The material function to use for the VAT." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Class UHoudiniVatImporter constinit property declarations **********************
	static const UECodeGen_Private::FObjectPropertyParams NewProp_VatProperties;
	static const UECodeGen_Private::FObjectPropertyParams NewProp_HoudiniVatMaterialFunction;
	static const UECodeGen_Private::FPropertyParamsBase* const PropPointers[];
// ********** End Class UHoudiniVatImporter constinit property declarations ************************
	static constexpr UE::CodeGen::FClassNativeFunction Funcs[] = {
		{ .NameUTF8 = UTF8TEXT("CreateVatBlueprint"), .Pointer = &UHoudiniVatImporter::execCreateVatBlueprint },
		{ .NameUTF8 = UTF8TEXT("CreateVatMaterial"), .Pointer = &UHoudiniVatImporter::execCreateVatMaterial },
		{ .NameUTF8 = UTF8TEXT("CreateVatMaterialInstance"), .Pointer = &UHoudiniVatImporter::execCreateVatMaterialInstance },
		{ .NameUTF8 = UTF8TEXT("ImportFiles"), .Pointer = &UHoudiniVatImporter::execImportFiles },
		{ .NameUTF8 = UTF8TEXT("SetProperties"), .Pointer = &UHoudiniVatImporter::execSetProperties },
	};
	static UObject* (*const DependentSingletons[])();
	static constexpr FClassFunctionLinkInfo FuncInfo[] = {
		{ &Z_Construct_UFunction_UHoudiniVatImporter_CreateVatBlueprint, "CreateVatBlueprint" }, // 1877378175
		{ &Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterial, "CreateVatMaterial" }, // 3061932975
		{ &Z_Construct_UFunction_UHoudiniVatImporter_CreateVatMaterialInstance, "CreateVatMaterialInstance" }, // 4196107780
		{ &Z_Construct_UFunction_UHoudiniVatImporter_ImportFiles, "ImportFiles" }, // 3501150509
		{ &Z_Construct_UFunction_UHoudiniVatImporter_SetProperties, "SetProperties" }, // 294637698
	};
	static_assert(UE_ARRAY_COUNT(FuncInfo) < 2048);
	static constexpr FCppClassTypeInfoStatic StaticCppClassTypeInfo = {
		TCppClassTypeTraits<UHoudiniVatImporter>::IsAbstract,
	};
	static const UECodeGen_Private::FClassParams ClassParams;
}; // struct Z_Construct_UClass_UHoudiniVatImporter_Statics

// ********** Begin Class UHoudiniVatImporter Property Definitions *********************************
const UECodeGen_Private::FObjectPropertyParams Z_Construct_UClass_UHoudiniVatImporter_Statics::NewProp_VatProperties = { "VatProperties", nullptr, (EPropertyFlags)0x0144000000000000, UECodeGen_Private::EPropertyGenFlags::Object | UECodeGen_Private::EPropertyGenFlags::ObjectPtr, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UHoudiniVatImporter, VatProperties), Z_Construct_UClass_UCreateNewVatProperties_NoRegister, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_VatProperties_MetaData), NewProp_VatProperties_MetaData) };
const UECodeGen_Private::FObjectPropertyParams Z_Construct_UClass_UHoudiniVatImporter_Statics::NewProp_HoudiniVatMaterialFunction = { "HoudiniVatMaterialFunction", nullptr, (EPropertyFlags)0x0144000000000000, UECodeGen_Private::EPropertyGenFlags::Object | UECodeGen_Private::EPropertyGenFlags::ObjectPtr, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(UHoudiniVatImporter, HoudiniVatMaterialFunction), Z_Construct_UClass_UMaterialFunction_NoRegister, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_HoudiniVatMaterialFunction_MetaData), NewProp_HoudiniVatMaterialFunction_MetaData) };
const UECodeGen_Private::FPropertyParamsBase* const Z_Construct_UClass_UHoudiniVatImporter_Statics::PropPointers[] = {
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UHoudiniVatImporter_Statics::NewProp_VatProperties,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_UHoudiniVatImporter_Statics::NewProp_HoudiniVatMaterialFunction,
};
static_assert(UE_ARRAY_COUNT(Z_Construct_UClass_UHoudiniVatImporter_Statics::PropPointers) < 2048);
// ********** End Class UHoudiniVatImporter Property Definitions ***********************************
UObject* (*const Z_Construct_UClass_UHoudiniVatImporter_Statics::DependentSingletons[])() = {
	(UObject* (*)())Z_Construct_UClass_UObject,
	(UObject* (*)())Z_Construct_UPackage__Script_SidefxLabsEditor,
};
static_assert(UE_ARRAY_COUNT(Z_Construct_UClass_UHoudiniVatImporter_Statics::DependentSingletons) < 16);
const UECodeGen_Private::FClassParams Z_Construct_UClass_UHoudiniVatImporter_Statics::ClassParams = {
	&UHoudiniVatImporter::StaticClass,
	nullptr,
	&StaticCppClassTypeInfo,
	DependentSingletons,
	FuncInfo,
	Z_Construct_UClass_UHoudiniVatImporter_Statics::PropPointers,
	nullptr,
	UE_ARRAY_COUNT(DependentSingletons),
	UE_ARRAY_COUNT(FuncInfo),
	UE_ARRAY_COUNT(Z_Construct_UClass_UHoudiniVatImporter_Statics::PropPointers),
	0,
	0x001000A0u,
	METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UClass_UHoudiniVatImporter_Statics::Class_MetaDataParams), Z_Construct_UClass_UHoudiniVatImporter_Statics::Class_MetaDataParams)
};
void UHoudiniVatImporter::StaticRegisterNativesUHoudiniVatImporter()
{
	UClass* Class = UHoudiniVatImporter::StaticClass();
	FNativeFunctionRegistrar::RegisterFunctions(Class, MakeConstArrayView(Z_Construct_UClass_UHoudiniVatImporter_Statics::Funcs));
}
UClass* Z_Construct_UClass_UHoudiniVatImporter()
{
	if (!Z_Registration_Info_UClass_UHoudiniVatImporter.OuterSingleton)
	{
		UECodeGen_Private::ConstructUClass(Z_Registration_Info_UClass_UHoudiniVatImporter.OuterSingleton, Z_Construct_UClass_UHoudiniVatImporter_Statics::ClassParams);
	}
	return Z_Registration_Info_UClass_UHoudiniVatImporter.OuterSingleton;
}
DEFINE_VTABLE_PTR_HELPER_CTOR_NS(, UHoudiniVatImporter);
UHoudiniVatImporter::~UHoudiniVatImporter() {}
// ********** End Class UHoudiniVatImporter ********************************************************

// ********** Begin Registration *******************************************************************
struct Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Private_VatImporter_HoudiniVatImporter_h__Script_SidefxLabsEditor_Statics
{
	static constexpr FClassRegisterCompiledInInfo ClassInfo[] = {
		{ Z_Construct_UClass_UHoudiniVatImporter, UHoudiniVatImporter::StaticClass, TEXT("UHoudiniVatImporter"), &Z_Registration_Info_UClass_UHoudiniVatImporter, CONSTRUCT_RELOAD_VERSION_INFO(FClassReloadVersionInfo, sizeof(UHoudiniVatImporter), 4009904005U) },
	};
}; // Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Private_VatImporter_HoudiniVatImporter_h__Script_SidefxLabsEditor_Statics 
static FRegisterCompiledInInfo Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Private_VatImporter_HoudiniVatImporter_h__Script_SidefxLabsEditor_1343150801{
	TEXT("/Script/SidefxLabsEditor"),
	Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Private_VatImporter_HoudiniVatImporter_h__Script_SidefxLabsEditor_Statics::ClassInfo, UE_ARRAY_COUNT(Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Private_VatImporter_HoudiniVatImporter_h__Script_SidefxLabsEditor_Statics::ClassInfo),
	nullptr, 0,
	nullptr, 0,
};
// ********** End Registration *********************************************************************

PRAGMA_ENABLE_DEPRECATION_WARNINGS
