// Copyright Epic Games, Inc. All Rights Reserved.
/*===========================================================================
	Generated code exported from UnrealHeaderTool.
	DO NOT modify this manually! Edit the corresponding .h files instead!
===========================================================================*/

// IWYU pragma: private, include "HoudiniCreateNewVatWindowParameters.h"

#ifdef SIDEFXLABSEDITOR_HoudiniCreateNewVatWindowParameters_generated_h
#error "HoudiniCreateNewVatWindowParameters.generated.h already included, missing '#pragma once' in HoudiniCreateNewVatWindowParameters.h"
#endif
#define SIDEFXLABSEDITOR_HoudiniCreateNewVatWindowParameters_generated_h

#include "UObject/ObjectMacros.h"
#include "UObject/ScriptMacros.h"

PRAGMA_DISABLE_DEPRECATION_WARNINGS

// ********** Begin Class UCreateNewVatProperties **************************************************
struct Z_Construct_UClass_UCreateNewVatProperties_Statics;
SIDEFXLABSEDITOR_API UClass* Z_Construct_UClass_UCreateNewVatProperties_NoRegister();

#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h_51_INCLASS_NO_PURE_DECLS \
private: \
	static void StaticRegisterNativesUCreateNewVatProperties(); \
	friend struct ::Z_Construct_UClass_UCreateNewVatProperties_Statics; \
	static UClass* GetPrivateStaticClass(); \
	friend SIDEFXLABSEDITOR_API UClass* ::Z_Construct_UClass_UCreateNewVatProperties_NoRegister(); \
public: \
	DECLARE_CLASS2(UCreateNewVatProperties, UObject, COMPILED_IN_FLAGS(0), CASTCLASS_None, TEXT("/Script/SidefxLabsEditor"), Z_Construct_UClass_UCreateNewVatProperties_NoRegister) \
	DECLARE_SERIALIZER(UCreateNewVatProperties)


#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h_51_ENHANCED_CONSTRUCTORS \
	/** Deleted move- and copy-constructors, should never be used */ \
	UCreateNewVatProperties(UCreateNewVatProperties&&) = delete; \
	UCreateNewVatProperties(const UCreateNewVatProperties&) = delete; \
	DECLARE_VTABLE_PTR_HELPER_CTOR(NO_API, UCreateNewVatProperties); \
	DEFINE_VTABLE_PTR_HELPER_CTOR_CALLER(UCreateNewVatProperties); \
	DEFINE_DEFAULT_CONSTRUCTOR_CALL(UCreateNewVatProperties) \
	NO_API virtual ~UCreateNewVatProperties();


#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h_48_PROLOG
#define FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h_51_GENERATED_BODY \
PRAGMA_DISABLE_DEPRECATION_WARNINGS \
public: \
	FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h_51_INCLASS_NO_PURE_DECLS \
	FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h_51_ENHANCED_CONSTRUCTORS \
private: \
PRAGMA_ENABLE_DEPRECATION_WARNINGS


class UCreateNewVatProperties;

// ********** End Class UCreateNewVatProperties ****************************************************

#undef CURRENT_FILE_ID
#define CURRENT_FILE_ID FID_Users_Mo_Documents_Unreal_Projects_UE57Cpp_Plugins_SideFX_Labs_Source_SidefxLabsEditor_Public_HoudiniCreateNewVatWindowParameters_h

// ********** Begin Enum EVatType ******************************************************************
#define FOREACH_ENUM_EVATTYPE(op) \
	op(EVatType::VatType1) \
	op(EVatType::VatType2) \
	op(EVatType::VatType3) \
	op(EVatType::VatType4) 

enum class EVatType : uint8;
template<> struct TIsUEnumClass<EVatType> { enum { Value = true }; };
template<> SIDEFXLABSEDITOR_NON_ATTRIBUTED_API UEnum* StaticEnum<EVatType>();
// ********** End Enum EVatType ********************************************************************

PRAGMA_ENABLE_DEPRECATION_WARNINGS
