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

#pragma once

#include "CoreMinimal.h"
#include "Materials/MaterialInstanceConstant.h"
#include "HoudiniVatImporter.generated.h"

class UCreateNewVatProperties;

UCLASS()
class SIDEFXLABSEDITOR_API UHoudiniVatImporter : public UObject
{
	GENERATED_BODY()

public:
	UHoudiniVatImporter();

	UFUNCTION()
	void SetProperties(UCreateNewVatProperties* InProperties);

	UFUNCTION()
	void ImportFiles();

	UFUNCTION()
	static void SetTextureParameters(TArray<UTexture2D*> Textures);

	UFUNCTION()
	void CreateVatMaterial();

	UFUNCTION()
	void CreateVatMaterialInstance();

	UFUNCTION()
	void CreateVatBlueprint();
	
	TWeakObjectPtr<UMaterialExpression> VatMaterialExp;
	TWeakObjectPtr<UMaterial> Material;
	TWeakObjectPtr<UMaterialInstanceConstant> MaterialInstance;
	TWeakObjectPtr<UStaticMesh> StaticMesh;
	TWeakObjectPtr<UBlueprint> Blueprint;
	
	bool bCanceled;
	
private:
	UPROPERTY()
	UCreateNewVatProperties* VatProperties;

	UPROPERTY()
	UMaterialFunction* HoudiniVatMaterialFunction;

	void ImportFbx(const FString& FBXPath, const FString& AssetPath);
	static void ImportTexture(const FString& TexturePath, const FString& AssetPath);
	
	FString CreatedMaterialName;
	FString FullFbxPath;
	FString FullLegacyDataPath;
};
