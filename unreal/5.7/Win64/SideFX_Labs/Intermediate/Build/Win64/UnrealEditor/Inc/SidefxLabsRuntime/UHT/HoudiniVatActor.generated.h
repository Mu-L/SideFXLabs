// Copyright Epic Games, Inc. All Rights Reserved.
/*===========================================================================
	Generated code exported from UnrealHeaderTool.
	DO NOT modify this manually! Edit the corresponding .h files instead!
===========================================================================*/

// IWYU pragma: private, include "HoudiniVatActor.h"

#ifdef SIDEFXLABSRUNTIME_HoudiniVatActor_generated_h
#error "HoudiniVatActor.generated.h already included, missing '#pragma once' in HoudiniVatActor.h"
#endif
#define SIDEFXLABSRUNTIME_HoudiniVatActor_generated_h

#include "UObject/ObjectMacros.h"
#include "UObject/ScriptMacros.h"

PRAGMA_DISABLE_DEPRECATION_WARNINGS

// ********** Begin Class AHoudiniVatActor *********************************************************
#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_58_RPC_WRAPPERS_NO_PURE_DECLS \
	DECLARE_FUNCTION(execResetVatPlayback); \
	DECLARE_FUNCTION(execTriggerVatPlayback);


struct Z_Construct_UClass_AHoudiniVatActor_Statics;
SIDEFXLABSRUNTIME_API UClass* Z_Construct_UClass_AHoudiniVatActor_NoRegister();

#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_58_INCLASS_NO_PURE_DECLS \
private: \
	static void StaticRegisterNativesAHoudiniVatActor(); \
	friend struct ::Z_Construct_UClass_AHoudiniVatActor_Statics; \
	static UClass* GetPrivateStaticClass(); \
	friend SIDEFXLABSRUNTIME_API UClass* ::Z_Construct_UClass_AHoudiniVatActor_NoRegister(); \
public: \
	DECLARE_CLASS2(AHoudiniVatActor, AActor, COMPILED_IN_FLAGS(0 | CLASS_Config), CASTCLASS_None, TEXT("/Script/SidefxLabsRuntime"), Z_Construct_UClass_AHoudiniVatActor_NoRegister) \
	DECLARE_SERIALIZER(AHoudiniVatActor)


#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_58_ENHANCED_CONSTRUCTORS \
	/** Deleted move- and copy-constructors, should never be used */ \
	AHoudiniVatActor(AHoudiniVatActor&&) = delete; \
	AHoudiniVatActor(const AHoudiniVatActor&) = delete; \
	DECLARE_VTABLE_PTR_HELPER_CTOR(NO_API, AHoudiniVatActor); \
	DEFINE_VTABLE_PTR_HELPER_CTOR_CALLER(AHoudiniVatActor); \
	DEFINE_DEFAULT_CONSTRUCTOR_CALL(AHoudiniVatActor) \
	NO_API virtual ~AHoudiniVatActor();


#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_55_PROLOG
#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_58_GENERATED_BODY \
PRAGMA_DISABLE_DEPRECATION_WARNINGS \
public: \
	FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_58_RPC_WRAPPERS_NO_PURE_DECLS \
	FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_58_INCLASS_NO_PURE_DECLS \
	FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h_58_ENHANCED_CONSTRUCTORS \
private: \
PRAGMA_ENABLE_DEPRECATION_WARNINGS


class AHoudiniVatActor;

// ********** End Class AHoudiniVatActor ***********************************************************

#undef CURRENT_FILE_ID
#define CURRENT_FILE_ID FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsRuntime_Public_HoudiniVatActor_h

// ********** Begin Enum EVatObjectMatchMode *******************************************************
#define FOREACH_ENUM_EVATOBJECTMATCHMODE(op) \
	op(EVatObjectMatchMode::ExactMatch) \
	op(EVatObjectMatchMode::StartsWith) \
	op(EVatObjectMatchMode::EndsWith) \
	op(EVatObjectMatchMode::Contains) \
	op(EVatObjectMatchMode::ActorClass) \
	op(EVatObjectMatchMode::ActorTag) 

enum class EVatObjectMatchMode : uint8;
template<> struct TIsUEnumClass<EVatObjectMatchMode> { enum { Value = true }; };
template<> SIDEFXLABSRUNTIME_NON_ATTRIBUTED_API UEnum* StaticEnum<EVatObjectMatchMode>();
// ********** End Enum EVatObjectMatchMode *********************************************************

PRAGMA_ENABLE_DEPRECATION_WARNINGS
