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
#include "Components/ShapeComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "HoudiniVatActor.generated.h"

UCLASS()
class SIDEFXLABSRUNTIME_API AHoudiniVatActor : public AActor
{
	GENERATED_BODY()

public:	
	AHoudiniVatActor();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Asset", DisplayName = "VAT Static Mesh", meta = (ToolTip = "The static mesh component for the VAT static mesh."))
	TObjectPtr<UStaticMeshComponent> Vat_StaticMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Asset", DisplayName = "VAT Material Instances", meta = (ToolTip = "The material instances that are parented to materials containing VAT material functions. Each array index corresponds with each material slot on the VAT static mesh."))
	TArray<TObjectPtr<UMaterialInterface>> Vat_MaterialInstances;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Asset", meta = (ToolTip = "These are the material instances that will be assigned to the VAT static mesh before the VAT is triggered. Each array index corresponds with each material slot on the VAT static mesh."))
	TArray<TObjectPtr<UMaterialInterface>> Original_MaterialInstances;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (ToolTip = "VAT will play when begin play starts."))
	bool bTriggerOnBeginPlay;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (ToolTip = "VAT will play when hit."))
	bool bTriggerOnHit;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (EditCondition="bTriggerOnHit", EditConditionHides, ToolTip = "Objects that will trigger VAT to play."))
	TArray<TObjectPtr<UObject>> HitObjects;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (EditCondition="bTriggerOnHit && HasHitObjects", EditConditionHides, ToolTip = "When enabled, objects in the Hit Objects parameter will be excluded and not trigger the VAT to play."))
	bool bExcludeHitObjects;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (ToolTip = "VAT will play when objects overlap with specified shape in the Overlap Shape parameter."))
	bool bTriggerOnOverlap;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (EditCondition="bTriggerOnOverlap", EditConditionHides, ToolTip = "The bounding region used to trigger the VAT to play."))
	TObjectPtr<UShapeComponent> OverlapShape;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (EditCondition="bTriggerOnOverlap", EditConditionHides, ToolTip = "Objects that will trigger VAT to play when overlapping with the specified Overlap Shape."))
	TArray<TObjectPtr<UObject>> OverlapObjects;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Conditions", meta = (EditCondition="bTriggerOnOverlap && HasOverlapObjects", EditConditionHides, ToolTip = "When enabled, objects in the Overlap Objects parameter will be excluded and not trigger the VAT to play."))
	bool bExcludeOverlapObjects;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Houdini VAT|Properties", meta = (ToolTip = "When enabled the VAT will only trigger once and not repeat."))
	bool bTriggerOnce;
	
	virtual void Tick(float DeltaTime) override;
	
	virtual void NotifyHit(UPrimitiveComponent* MyComp, AActor* Other, UPrimitiveComponent* OtherComp, bool bSelfMoved, FVector HitLocation, FVector HitNormal, FVector NormalImpulse, const FHitResult& Hit) override;

	virtual void NotifyActorBeginOverlap(AActor* OtherActor) override;

protected:
	virtual void BeginPlay() override;
	
	UFUNCTION(BlueprintCallable, Category="Houdini VAT")
	void TriggerVatPlayback();
	
	UFUNCTION(BlueprintCallable, Category="Houdini VAT")
	void ResetVatPlayback();

	UFUNCTION(Category="Houdini VAT|Conditions")
	bool HasHitObjects() const;

	UFUNCTION(Category="Houdini VAT|Conditions")
	bool HasOverlapObjects() const;

	void ApplyMaterials(const TArray<TObjectPtr<UMaterialInterface>>& Materials) const;
	
	float StartSeconds;
	bool bPlay;
};
