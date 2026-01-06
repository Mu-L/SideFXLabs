// Copyright Epic Games, Inc. All Rights Reserved.
/*===========================================================================
	Generated code exported from UnrealHeaderTool.
	DO NOT modify this manually! Edit the corresponding .h files instead!
===========================================================================*/

#include "UObject/GeneratedCppIncludes.h"
#include "HoudiniVatActor.h"

PRAGMA_DISABLE_DEPRECATION_WARNINGS
static_assert(!UE_WITH_CONSTINIT_UOBJECT, "This generated code can only be compiled with !UE_WITH_CONSTINIT_OBJECT");
void EmptyLinkFunctionForGeneratedCodeHoudiniVatActor() {}

// ********** Begin Cross Module References ********************************************************
COREUOBJECT_API UClass* Z_Construct_UClass_UClass_NoRegister();
ENGINE_API UClass* Z_Construct_UClass_AActor();
ENGINE_API UClass* Z_Construct_UClass_AActor_NoRegister();
ENGINE_API UClass* Z_Construct_UClass_UBoxComponent_NoRegister();
ENGINE_API UClass* Z_Construct_UClass_UMaterialInterface_NoRegister();
ENGINE_API UClass* Z_Construct_UClass_UStaticMeshComponent_NoRegister();
SIDEFXLABSRUNTIME_API UClass* Z_Construct_UClass_AHoudiniVatActor();
SIDEFXLABSRUNTIME_API UClass* Z_Construct_UClass_AHoudiniVatActor_NoRegister();
SIDEFXLABSRUNTIME_API UEnum* Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode();
UPackage* Z_Construct_UPackage__Script_SidefxLabsRuntime();
// ********** End Cross Module References **********************************************************

// ********** Begin Enum EVatObjectMatchMode *******************************************************
static FEnumRegistrationInfo Z_Registration_Info_UEnum_EVatObjectMatchMode;
static UEnum* EVatObjectMatchMode_StaticEnum()
{
	if (!Z_Registration_Info_UEnum_EVatObjectMatchMode.OuterSingleton)
	{
		Z_Registration_Info_UEnum_EVatObjectMatchMode.OuterSingleton = GetStaticEnum(Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode, (UObject*)Z_Construct_UPackage__Script_SidefxLabsRuntime(), TEXT("EVatObjectMatchMode"));
	}
	return Z_Registration_Info_UEnum_EVatObjectMatchMode.OuterSingleton;
}
template<> SIDEFXLABSRUNTIME_NON_ATTRIBUTED_API UEnum* StaticEnum<EVatObjectMatchMode>()
{
	return EVatObjectMatchMode_StaticEnum();
}
struct Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Enum_MetaDataParams[] = {
		{ "ActorClass.DisplayName", "Actor Class" },
		{ "ActorClass.Name", "EVatObjectMatchMode::ActorClass" },
		{ "ActorClass.ToolTip", "Match by actor class type." },
		{ "ActorTag.DisplayName", "Actor Tag" },
		{ "ActorTag.Name", "EVatObjectMatchMode::ActorTag" },
		{ "ActorTag.ToolTip", "Match by actor tags." },
		{ "BlueprintType", "true" },
#if !UE_BUILD_SHIPPING
		{ "Comment", "/**\n * Defines how objects are matched against filter criteria for VAT triggering.\n */" },
#endif
		{ "Contains.DisplayName", "Contains" },
		{ "Contains.Name", "EVatObjectMatchMode::Contains" },
		{ "Contains.ToolTip", "Object name must contain the filter text (use carefully as it can match many objects)." },
		{ "EndsWith.DisplayName", "Ends With" },
		{ "EndsWith.Name", "EVatObjectMatchMode::EndsWith" },
		{ "EndsWith.ToolTip", "Object name must end with the filter text." },
		{ "ExactMatch.DisplayName", "Exact Match" },
		{ "ExactMatch.Name", "EVatObjectMatchMode::ExactMatch" },
		{ "ExactMatch.ToolTip", "Object names must match exactly." },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
		{ "StartsWith.DisplayName", "Starts With" },
		{ "StartsWith.Name", "EVatObjectMatchMode::StartsWith" },
		{ "StartsWith.ToolTip", "Object name must start with the filter text." },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Defines how objects are matched against filter criteria for VAT triggering." },
#endif
	};
#endif // WITH_METADATA
	static constexpr UECodeGen_Private::FEnumeratorParam Enumerators[] = {
		{ "EVatObjectMatchMode::ExactMatch", (int64)EVatObjectMatchMode::ExactMatch },
		{ "EVatObjectMatchMode::StartsWith", (int64)EVatObjectMatchMode::StartsWith },
		{ "EVatObjectMatchMode::EndsWith", (int64)EVatObjectMatchMode::EndsWith },
		{ "EVatObjectMatchMode::Contains", (int64)EVatObjectMatchMode::Contains },
		{ "EVatObjectMatchMode::ActorClass", (int64)EVatObjectMatchMode::ActorClass },
		{ "EVatObjectMatchMode::ActorTag", (int64)EVatObjectMatchMode::ActorTag },
	};
	static const UECodeGen_Private::FEnumParams EnumParams;
}; // struct Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics 
const UECodeGen_Private::FEnumParams Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics::EnumParams = {
	(UObject*(*)())Z_Construct_UPackage__Script_SidefxLabsRuntime,
	nullptr,
	"EVatObjectMatchMode",
	"EVatObjectMatchMode",
	Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics::Enumerators,
	RF_Public|RF_Transient|RF_MarkAsNative,
	UE_ARRAY_COUNT(Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics::Enumerators),
	EEnumFlags::None,
	(uint8)UEnum::ECppForm::EnumClass,
	METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics::Enum_MetaDataParams), Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics::Enum_MetaDataParams)
};
UEnum* Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode()
{
	if (!Z_Registration_Info_UEnum_EVatObjectMatchMode.InnerSingleton)
	{
		UECodeGen_Private::ConstructUEnum(Z_Registration_Info_UEnum_EVatObjectMatchMode.InnerSingleton, Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode_Statics::EnumParams);
	}
	return Z_Registration_Info_UEnum_EVatObjectMatchMode.InnerSingleton;
}
// ********** End Enum EVatObjectMatchMode *********************************************************

// ********** Begin Class AHoudiniVatActor Function ResetVatPlayback *******************************
struct Z_Construct_UFunction_AHoudiniVatActor_ResetVatPlayback_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Function_MetaDataParams[] = {
		{ "Category", "Houdini VAT" },
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Resets VAT animation to its initial state. */" },
#endif
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Resets VAT animation to its initial state." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Function ResetVatPlayback constinit property declarations **********************
// ********** End Function ResetVatPlayback constinit property declarations ************************
	static const UECodeGen_Private::FFunctionParams FuncParams;
};
const UECodeGen_Private::FFunctionParams Z_Construct_UFunction_AHoudiniVatActor_ResetVatPlayback_Statics::FuncParams = { { (UObject*(*)())Z_Construct_UClass_AHoudiniVatActor, nullptr, "ResetVatPlayback", 	nullptr, 
	0, 
0,
RF_Public|RF_Transient|RF_MarkAsNative, (EFunctionFlags)0x04020401, 0, 0, METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UFunction_AHoudiniVatActor_ResetVatPlayback_Statics::Function_MetaDataParams), Z_Construct_UFunction_AHoudiniVatActor_ResetVatPlayback_Statics::Function_MetaDataParams)},  };
UFunction* Z_Construct_UFunction_AHoudiniVatActor_ResetVatPlayback()
{
	static UFunction* ReturnFunction = nullptr;
	if (!ReturnFunction)
	{
		UECodeGen_Private::ConstructUFunction(&ReturnFunction, Z_Construct_UFunction_AHoudiniVatActor_ResetVatPlayback_Statics::FuncParams);
	}
	return ReturnFunction;
}
DEFINE_FUNCTION(AHoudiniVatActor::execResetVatPlayback)
{
	P_FINISH;
	P_NATIVE_BEGIN;
	P_THIS->ResetVatPlayback();
	P_NATIVE_END;
}
// ********** End Class AHoudiniVatActor Function ResetVatPlayback *********************************

// ********** Begin Class AHoudiniVatActor Function TriggerVatPlayback *****************************
struct Z_Construct_UFunction_AHoudiniVatActor_TriggerVatPlayback_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Function_MetaDataParams[] = {
		{ "Category", "Houdini VAT" },
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Triggers VAT animation playback. */" },
#endif
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Triggers VAT animation playback." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Function TriggerVatPlayback constinit property declarations ********************
// ********** End Function TriggerVatPlayback constinit property declarations **********************
	static const UECodeGen_Private::FFunctionParams FuncParams;
};
const UECodeGen_Private::FFunctionParams Z_Construct_UFunction_AHoudiniVatActor_TriggerVatPlayback_Statics::FuncParams = { { (UObject*(*)())Z_Construct_UClass_AHoudiniVatActor, nullptr, "TriggerVatPlayback", 	nullptr, 
	0, 
0,
RF_Public|RF_Transient|RF_MarkAsNative, (EFunctionFlags)0x04020401, 0, 0, METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UFunction_AHoudiniVatActor_TriggerVatPlayback_Statics::Function_MetaDataParams), Z_Construct_UFunction_AHoudiniVatActor_TriggerVatPlayback_Statics::Function_MetaDataParams)},  };
UFunction* Z_Construct_UFunction_AHoudiniVatActor_TriggerVatPlayback()
{
	static UFunction* ReturnFunction = nullptr;
	if (!ReturnFunction)
	{
		UECodeGen_Private::ConstructUFunction(&ReturnFunction, Z_Construct_UFunction_AHoudiniVatActor_TriggerVatPlayback_Statics::FuncParams);
	}
	return ReturnFunction;
}
DEFINE_FUNCTION(AHoudiniVatActor::execTriggerVatPlayback)
{
	P_FINISH;
	P_NATIVE_BEGIN;
	P_THIS->TriggerVatPlayback();
	P_NATIVE_END;
}
// ********** End Class AHoudiniVatActor Function TriggerVatPlayback *******************************

// ********** Begin Class AHoudiniVatActor *********************************************************
FClassRegistrationInfo Z_Registration_Info_UClass_AHoudiniVatActor;
UClass* AHoudiniVatActor::GetPrivateStaticClass()
{
	using TClass = AHoudiniVatActor;
	if (!Z_Registration_Info_UClass_AHoudiniVatActor.InnerSingleton)
	{
		GetPrivateStaticClassBody(
			TClass::StaticPackage(),
			TEXT("HoudiniVatActor"),
			Z_Registration_Info_UClass_AHoudiniVatActor.InnerSingleton,
			StaticRegisterNativesAHoudiniVatActor,
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
	return Z_Registration_Info_UClass_AHoudiniVatActor.InnerSingleton;
}
UClass* Z_Construct_UClass_AHoudiniVatActor_NoRegister()
{
	return AHoudiniVatActor::GetPrivateStaticClass();
}
struct Z_Construct_UClass_AHoudiniVatActor_Statics
{
#if WITH_METADATA
	static constexpr UECodeGen_Private::FMetaDataPairParam Class_MetaDataParams[] = {
#if !UE_BUILD_SHIPPING
		{ "Comment", "/**\n * Actor that manages VAT playback.\n * Supports triggering animations based on begin play, hit events, and overlap events.\n */" },
#endif
		{ "IncludePath", "HoudiniVatActor.h" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Actor that manages VAT playback.\nSupports triggering animations based on begin play, hit events, and overlap events." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_Vat_StaticMesh_MetaData[] = {
		{ "Category", "Houdini VAT|Asset" },
		{ "DisplayName", "VAT Static Mesh" },
		{ "EditInline", "true" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The static mesh component for the VAT static mesh." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_Vat_MaterialInstances_MetaData[] = {
		{ "Category", "Houdini VAT|Asset" },
		{ "DisplayName", "VAT Material Instances" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The material instances that are parented to materials containing VAT material functions. Each array index corresponds with each material slot on the VAT static mesh." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_Original_MaterialInstances_MetaData[] = {
		{ "Category", "Houdini VAT|Asset" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "These are the material instances that will be assigned to the VAT static mesh before the VAT is triggered. Each array index corresponds with each material slot on the VAT static mesh." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bTriggerOnBeginPlay_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "VAT will play when begin play starts." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bTriggerOnHit_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "VAT will play when hit." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_HitMatchMode_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnHit" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "How to match objects for hit detection." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_HitObjectNames_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnHit && (HitMatchMode == EVatObjectMatchMode::ExactMatch || HitMatchMode == EVatObjectMatchMode::StartsWith || HitMatchMode == EVatObjectMatchMode::EndsWith || HitMatchMode == EVatObjectMatchMode::Contains)" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Object names or patterns to match against." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_HitActorClasses_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnHit && HitMatchMode == EVatObjectMatchMode::ActorClass" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Actor classes that will trigger VAT to play." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_HitActorTags_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnHit && HitMatchMode == EVatObjectMatchMode::ActorTag" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Actor tags that will trigger VAT to play." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bExcludeHitObjects_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnHit" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Inverts the filter logic. When true: listed objects will NOT trigger. When false: ONLY listed objects will trigger." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bTriggerOnOverlap_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "VAT will play when objects overlap with specified shape in the Overlap Shape parameter." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_OverlapShape_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnOverlap" },
		{ "EditConditionHides", "" },
		{ "EditInline", "true" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "The bounding region used to trigger the VAT to play." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_OverlapMatchMode_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnOverlap" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "How to match objects for overlap detection." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_OverlapObjectNames_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnOverlap && (OverlapMatchMode == EVatObjectMatchMode::ExactMatch || OverlapMatchMode == EVatObjectMatchMode::StartsWith || OverlapMatchMode == EVatObjectMatchMode::EndsWith || OverlapMatchMode == EVatObjectMatchMode::Contains)" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Object names or patterns to match against for overlaps." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_OverlapActorClasses_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnOverlap && OverlapMatchMode == EVatObjectMatchMode::ActorClass" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Actor classes that will trigger VAT to play on overlap." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_OverlapActorTags_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnOverlap && OverlapMatchMode == EVatObjectMatchMode::ActorTag" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Actor tags that will trigger VAT to play on overlap." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bExcludeOverlapObjects_MetaData[] = {
		{ "Category", "Houdini VAT|Conditions" },
		{ "EditCondition", "bTriggerOnOverlap" },
		{ "EditConditionHides", "" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Inverts the filter logic. When true: listed objects will NOT trigger. When false: ONLY listed objects will trigger." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_bTriggerOnce_MetaData[] = {
		{ "Category", "Houdini VAT|Properties" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "When enabled the VAT will only trigger once and not repeat." },
#endif
	};
	static constexpr UECodeGen_Private::FMetaDataPairParam NewProp_ResetFallbackMaterialRef_MetaData[] = {
		{ "Category", "Houdini VAT|Materials" },
#if !UE_BUILD_SHIPPING
		{ "Comment", "/** Fallback material for ResetVatPlayback function. */" },
#endif
		{ "DisplayName", "Reset VAT Fallback Material" },
		{ "ModuleRelativePath", "Public/HoudiniVatActor.h" },
#if !UE_BUILD_SHIPPING
		{ "ToolTip", "Fallback material for ResetVatPlayback function." },
#endif
	};
#endif // WITH_METADATA

// ********** Begin Class AHoudiniVatActor constinit property declarations *************************
	static const UECodeGen_Private::FObjectPropertyParams NewProp_Vat_StaticMesh;
	static const UECodeGen_Private::FObjectPropertyParams NewProp_Vat_MaterialInstances_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_Vat_MaterialInstances;
	static const UECodeGen_Private::FObjectPropertyParams NewProp_Original_MaterialInstances_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_Original_MaterialInstances;
	static void NewProp_bTriggerOnBeginPlay_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bTriggerOnBeginPlay;
	static void NewProp_bTriggerOnHit_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bTriggerOnHit;
	static const UECodeGen_Private::FBytePropertyParams NewProp_HitMatchMode_Underlying;
	static const UECodeGen_Private::FEnumPropertyParams NewProp_HitMatchMode;
	static const UECodeGen_Private::FStrPropertyParams NewProp_HitObjectNames_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_HitObjectNames;
	static const UECodeGen_Private::FClassPropertyParams NewProp_HitActorClasses_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_HitActorClasses;
	static const UECodeGen_Private::FNamePropertyParams NewProp_HitActorTags_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_HitActorTags;
	static void NewProp_bExcludeHitObjects_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bExcludeHitObjects;
	static void NewProp_bTriggerOnOverlap_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bTriggerOnOverlap;
	static const UECodeGen_Private::FObjectPropertyParams NewProp_OverlapShape;
	static const UECodeGen_Private::FBytePropertyParams NewProp_OverlapMatchMode_Underlying;
	static const UECodeGen_Private::FEnumPropertyParams NewProp_OverlapMatchMode;
	static const UECodeGen_Private::FStrPropertyParams NewProp_OverlapObjectNames_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_OverlapObjectNames;
	static const UECodeGen_Private::FClassPropertyParams NewProp_OverlapActorClasses_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_OverlapActorClasses;
	static const UECodeGen_Private::FNamePropertyParams NewProp_OverlapActorTags_Inner;
	static const UECodeGen_Private::FArrayPropertyParams NewProp_OverlapActorTags;
	static void NewProp_bExcludeOverlapObjects_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bExcludeOverlapObjects;
	static void NewProp_bTriggerOnce_SetBit(void* Obj);
	static const UECodeGen_Private::FBoolPropertyParams NewProp_bTriggerOnce;
	static const UECodeGen_Private::FSoftObjectPropertyParams NewProp_ResetFallbackMaterialRef;
	static const UECodeGen_Private::FPropertyParamsBase* const PropPointers[];
// ********** End Class AHoudiniVatActor constinit property declarations ***************************
	static constexpr UE::CodeGen::FClassNativeFunction Funcs[] = {
		{ .NameUTF8 = UTF8TEXT("ResetVatPlayback"), .Pointer = &AHoudiniVatActor::execResetVatPlayback },
		{ .NameUTF8 = UTF8TEXT("TriggerVatPlayback"), .Pointer = &AHoudiniVatActor::execTriggerVatPlayback },
	};
	static UObject* (*const DependentSingletons[])();
	static constexpr FClassFunctionLinkInfo FuncInfo[] = {
		{ &Z_Construct_UFunction_AHoudiniVatActor_ResetVatPlayback, "ResetVatPlayback" }, // 816966967
		{ &Z_Construct_UFunction_AHoudiniVatActor_TriggerVatPlayback, "TriggerVatPlayback" }, // 294039989
	};
	static_assert(UE_ARRAY_COUNT(FuncInfo) < 2048);
	static constexpr FCppClassTypeInfoStatic StaticCppClassTypeInfo = {
		TCppClassTypeTraits<AHoudiniVatActor>::IsAbstract,
	};
	static const UECodeGen_Private::FClassParams ClassParams;
}; // struct Z_Construct_UClass_AHoudiniVatActor_Statics

// ********** Begin Class AHoudiniVatActor Property Definitions ************************************
const UECodeGen_Private::FObjectPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Vat_StaticMesh = { "Vat_StaticMesh", nullptr, (EPropertyFlags)0x011400000008000d, UECodeGen_Private::EPropertyGenFlags::Object | UECodeGen_Private::EPropertyGenFlags::ObjectPtr, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, Vat_StaticMesh), Z_Construct_UClass_UStaticMeshComponent_NoRegister, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_Vat_StaticMesh_MetaData), NewProp_Vat_StaticMesh_MetaData) };
const UECodeGen_Private::FObjectPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Vat_MaterialInstances_Inner = { "Vat_MaterialInstances", nullptr, (EPropertyFlags)0x0104000000000000, UECodeGen_Private::EPropertyGenFlags::Object | UECodeGen_Private::EPropertyGenFlags::ObjectPtr, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, Z_Construct_UClass_UMaterialInterface_NoRegister, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Vat_MaterialInstances = { "Vat_MaterialInstances", nullptr, (EPropertyFlags)0x0114000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, Vat_MaterialInstances), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_Vat_MaterialInstances_MetaData), NewProp_Vat_MaterialInstances_MetaData) };
const UECodeGen_Private::FObjectPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Original_MaterialInstances_Inner = { "Original_MaterialInstances", nullptr, (EPropertyFlags)0x0104000000000000, UECodeGen_Private::EPropertyGenFlags::Object | UECodeGen_Private::EPropertyGenFlags::ObjectPtr, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, Z_Construct_UClass_UMaterialInterface_NoRegister, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Original_MaterialInstances = { "Original_MaterialInstances", nullptr, (EPropertyFlags)0x0114000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, Original_MaterialInstances), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_Original_MaterialInstances_MetaData), NewProp_Original_MaterialInstances_MetaData) };
void Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnBeginPlay_SetBit(void* Obj)
{
	((AHoudiniVatActor*)Obj)->bTriggerOnBeginPlay = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnBeginPlay = { "bTriggerOnBeginPlay", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(AHoudiniVatActor), &Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnBeginPlay_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bTriggerOnBeginPlay_MetaData), NewProp_bTriggerOnBeginPlay_MetaData) };
void Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnHit_SetBit(void* Obj)
{
	((AHoudiniVatActor*)Obj)->bTriggerOnHit = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnHit = { "bTriggerOnHit", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(AHoudiniVatActor), &Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnHit_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bTriggerOnHit_MetaData), NewProp_bTriggerOnHit_MetaData) };
const UECodeGen_Private::FBytePropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitMatchMode_Underlying = { "UnderlyingType", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Byte, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, nullptr, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FEnumPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitMatchMode = { "HitMatchMode", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Enum, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, HitMatchMode), Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_HitMatchMode_MetaData), NewProp_HitMatchMode_MetaData) }; // 4067450990
const UECodeGen_Private::FStrPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitObjectNames_Inner = { "HitObjectNames", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Str, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitObjectNames = { "HitObjectNames", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, HitObjectNames), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_HitObjectNames_MetaData), NewProp_HitObjectNames_MetaData) };
const UECodeGen_Private::FClassPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorClasses_Inner = { "HitActorClasses", nullptr, (EPropertyFlags)0x0004000000000000, UECodeGen_Private::EPropertyGenFlags::Class, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, Z_Construct_UClass_UClass_NoRegister, Z_Construct_UClass_AActor_NoRegister, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorClasses = { "HitActorClasses", nullptr, (EPropertyFlags)0x0014000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, HitActorClasses), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_HitActorClasses_MetaData), NewProp_HitActorClasses_MetaData) };
const UECodeGen_Private::FNamePropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorTags_Inner = { "HitActorTags", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Name, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorTags = { "HitActorTags", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, HitActorTags), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_HitActorTags_MetaData), NewProp_HitActorTags_MetaData) };
void Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeHitObjects_SetBit(void* Obj)
{
	((AHoudiniVatActor*)Obj)->bExcludeHitObjects = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeHitObjects = { "bExcludeHitObjects", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(AHoudiniVatActor), &Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeHitObjects_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bExcludeHitObjects_MetaData), NewProp_bExcludeHitObjects_MetaData) };
void Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnOverlap_SetBit(void* Obj)
{
	((AHoudiniVatActor*)Obj)->bTriggerOnOverlap = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnOverlap = { "bTriggerOnOverlap", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(AHoudiniVatActor), &Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnOverlap_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bTriggerOnOverlap_MetaData), NewProp_bTriggerOnOverlap_MetaData) };
const UECodeGen_Private::FObjectPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapShape = { "OverlapShape", nullptr, (EPropertyFlags)0x011400000008000d, UECodeGen_Private::EPropertyGenFlags::Object | UECodeGen_Private::EPropertyGenFlags::ObjectPtr, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, OverlapShape), Z_Construct_UClass_UBoxComponent_NoRegister, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_OverlapShape_MetaData), NewProp_OverlapShape_MetaData) };
const UECodeGen_Private::FBytePropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapMatchMode_Underlying = { "UnderlyingType", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Byte, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, nullptr, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FEnumPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapMatchMode = { "OverlapMatchMode", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Enum, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, OverlapMatchMode), Z_Construct_UEnum_SidefxLabsRuntime_EVatObjectMatchMode, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_OverlapMatchMode_MetaData), NewProp_OverlapMatchMode_MetaData) }; // 4067450990
const UECodeGen_Private::FStrPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapObjectNames_Inner = { "OverlapObjectNames", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Str, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapObjectNames = { "OverlapObjectNames", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, OverlapObjectNames), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_OverlapObjectNames_MetaData), NewProp_OverlapObjectNames_MetaData) };
const UECodeGen_Private::FClassPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorClasses_Inner = { "OverlapActorClasses", nullptr, (EPropertyFlags)0x0004000000000000, UECodeGen_Private::EPropertyGenFlags::Class, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, Z_Construct_UClass_UClass_NoRegister, Z_Construct_UClass_AActor_NoRegister, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorClasses = { "OverlapActorClasses", nullptr, (EPropertyFlags)0x0014000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, OverlapActorClasses), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_OverlapActorClasses_MetaData), NewProp_OverlapActorClasses_MetaData) };
const UECodeGen_Private::FNamePropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorTags_Inner = { "OverlapActorTags", nullptr, (EPropertyFlags)0x0000000000000000, UECodeGen_Private::EPropertyGenFlags::Name, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, 0, METADATA_PARAMS(0, nullptr) };
const UECodeGen_Private::FArrayPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorTags = { "OverlapActorTags", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Array, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, OverlapActorTags), EArrayPropertyFlags::None, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_OverlapActorTags_MetaData), NewProp_OverlapActorTags_MetaData) };
void Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeOverlapObjects_SetBit(void* Obj)
{
	((AHoudiniVatActor*)Obj)->bExcludeOverlapObjects = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeOverlapObjects = { "bExcludeOverlapObjects", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(AHoudiniVatActor), &Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeOverlapObjects_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bExcludeOverlapObjects_MetaData), NewProp_bExcludeOverlapObjects_MetaData) };
void Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnce_SetBit(void* Obj)
{
	((AHoudiniVatActor*)Obj)->bTriggerOnce = 1;
}
const UECodeGen_Private::FBoolPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnce = { "bTriggerOnce", nullptr, (EPropertyFlags)0x0010000000000005, UECodeGen_Private::EPropertyGenFlags::Bool | UECodeGen_Private::EPropertyGenFlags::NativeBool, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, sizeof(bool), sizeof(AHoudiniVatActor), &Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnce_SetBit, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_bTriggerOnce_MetaData), NewProp_bTriggerOnce_MetaData) };
const UECodeGen_Private::FSoftObjectPropertyParams Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_ResetFallbackMaterialRef = { "ResetFallbackMaterialRef", nullptr, (EPropertyFlags)0x0014000000010001, UECodeGen_Private::EPropertyGenFlags::SoftObject, RF_Public|RF_Transient|RF_MarkAsNative, nullptr, nullptr, 1, STRUCT_OFFSET(AHoudiniVatActor, ResetFallbackMaterialRef), Z_Construct_UClass_UMaterialInterface_NoRegister, METADATA_PARAMS(UE_ARRAY_COUNT(NewProp_ResetFallbackMaterialRef_MetaData), NewProp_ResetFallbackMaterialRef_MetaData) };
const UECodeGen_Private::FPropertyParamsBase* const Z_Construct_UClass_AHoudiniVatActor_Statics::PropPointers[] = {
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Vat_StaticMesh,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Vat_MaterialInstances_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Vat_MaterialInstances,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Original_MaterialInstances_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_Original_MaterialInstances,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnBeginPlay,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnHit,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitMatchMode_Underlying,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitMatchMode,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitObjectNames_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitObjectNames,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorClasses_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorClasses,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorTags_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_HitActorTags,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeHitObjects,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnOverlap,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapShape,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapMatchMode_Underlying,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapMatchMode,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapObjectNames_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapObjectNames,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorClasses_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorClasses,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorTags_Inner,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_OverlapActorTags,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bExcludeOverlapObjects,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_bTriggerOnce,
	(const UECodeGen_Private::FPropertyParamsBase*)&Z_Construct_UClass_AHoudiniVatActor_Statics::NewProp_ResetFallbackMaterialRef,
};
static_assert(UE_ARRAY_COUNT(Z_Construct_UClass_AHoudiniVatActor_Statics::PropPointers) < 2048);
// ********** End Class AHoudiniVatActor Property Definitions **************************************
UObject* (*const Z_Construct_UClass_AHoudiniVatActor_Statics::DependentSingletons[])() = {
	(UObject* (*)())Z_Construct_UClass_AActor,
	(UObject* (*)())Z_Construct_UPackage__Script_SidefxLabsRuntime,
};
static_assert(UE_ARRAY_COUNT(Z_Construct_UClass_AHoudiniVatActor_Statics::DependentSingletons) < 16);
const UECodeGen_Private::FClassParams Z_Construct_UClass_AHoudiniVatActor_Statics::ClassParams = {
	&AHoudiniVatActor::StaticClass,
	"Engine",
	&StaticCppClassTypeInfo,
	DependentSingletons,
	FuncInfo,
	Z_Construct_UClass_AHoudiniVatActor_Statics::PropPointers,
	nullptr,
	UE_ARRAY_COUNT(DependentSingletons),
	UE_ARRAY_COUNT(FuncInfo),
	UE_ARRAY_COUNT(Z_Construct_UClass_AHoudiniVatActor_Statics::PropPointers),
	0,
	0x009000A4u,
	METADATA_PARAMS(UE_ARRAY_COUNT(Z_Construct_UClass_AHoudiniVatActor_Statics::Class_MetaDataParams), Z_Construct_UClass_AHoudiniVatActor_Statics::Class_MetaDataParams)
};
void AHoudiniVatActor::StaticRegisterNativesAHoudiniVatActor()
{
	UClass* Class = AHoudiniVatActor::StaticClass();
	FNativeFunctionRegistrar::RegisterFunctions(Class, MakeConstArrayView(Z_Construct_UClass_AHoudiniVatActor_Statics::Funcs));
}
UClass* Z_Construct_UClass_AHoudiniVatActor()
{
	if (!Z_Registration_Info_UClass_AHoudiniVatActor.OuterSingleton)
	{
		UECodeGen_Private::ConstructUClass(Z_Registration_Info_UClass_AHoudiniVatActor.OuterSingleton, Z_Construct_UClass_AHoudiniVatActor_Statics::ClassParams);
	}
	return Z_Registration_Info_UClass_AHoudiniVatActor.OuterSingleton;
}
DEFINE_VTABLE_PTR_HELPER_CTOR_NS(, AHoudiniVatActor);
AHoudiniVatActor::~AHoudiniVatActor() {}
// ********** End Class AHoudiniVatActor ***********************************************************

// ********** Begin Registration *******************************************************************
struct Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h__Script_SidefxLabsRuntime_Statics
{
	static constexpr FEnumRegisterCompiledInInfo EnumInfo[] = {
		{ EVatObjectMatchMode_StaticEnum, TEXT("EVatObjectMatchMode"), &Z_Registration_Info_UEnum_EVatObjectMatchMode, CONSTRUCT_RELOAD_VERSION_INFO(FEnumReloadVersionInfo, 4067450990U) },
	};
	static constexpr FClassRegisterCompiledInInfo ClassInfo[] = {
		{ Z_Construct_UClass_AHoudiniVatActor, AHoudiniVatActor::StaticClass, TEXT("AHoudiniVatActor"), &Z_Registration_Info_UClass_AHoudiniVatActor, CONSTRUCT_RELOAD_VERSION_INFO(FClassReloadVersionInfo, sizeof(AHoudiniVatActor), 3245015107U) },
	};
}; // Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h__Script_SidefxLabsRuntime_Statics 
static FRegisterCompiledInInfo Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h__Script_SidefxLabsRuntime_1400820587{
	TEXT("/Script/SidefxLabsRuntime"),
	Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h__Script_SidefxLabsRuntime_Statics::ClassInfo, UE_ARRAY_COUNT(Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h__Script_SidefxLabsRuntime_Statics::ClassInfo),
	nullptr, 0,
	Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h__Script_SidefxLabsRuntime_Statics::EnumInfo, UE_ARRAY_COUNT(Z_CompiledInDeferFile_FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h__Script_SidefxLabsRuntime_Statics::EnumInfo),
};
// ********** End Registration *********************************************************************

PRAGMA_ENABLE_DEPRECATION_WARNINGS
