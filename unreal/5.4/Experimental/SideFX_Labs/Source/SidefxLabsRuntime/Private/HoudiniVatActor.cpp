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

#include "HoudiniVatActor.h"
#include "Components/ShapeComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AHoudiniVatActor::AHoudiniVatActor()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("DefaultSceneRoot"));
    Vat_StaticMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VAT Mesh"));
    Vat_StaticMesh->SetupAttachment(RootComponent);
    
    Vat_MaterialInstances.Reset();
    OverlapShape = CreateDefaultSubobject<UShapeComponent>(TEXT("VAT Overlap Area"));

    bTriggerOnBeginPlay = true;
    bPlay = true;
}

void AHoudiniVatActor::BeginPlay()
{
    Super::BeginPlay();
    
    StartSeconds = GetWorld()->GetTimeSeconds();
    ApplyMaterials(Original_MaterialInstances);

    if (!bTriggerOnBeginPlay && Original_MaterialInstances.IsEmpty())
    {
        const FString WorldGridMaterialPath = TEXT("/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial");
    
        if (UMaterialInterface* WorldGridMaterial = Cast<UMaterialInterface>(StaticLoadObject(UMaterialInterface::StaticClass(), nullptr, *WorldGridMaterialPath)))
        {
            const int32 NumMaterials = Vat_StaticMesh->GetNumMaterials();
            for (int32 MaterialIndex = 0; MaterialIndex < NumMaterials; ++MaterialIndex)
            {
                Vat_StaticMesh->SetMaterial(MaterialIndex, WorldGridMaterial);
            }
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("Failed to load material at path: %s"), *WorldGridMaterialPath);
        }
    }

    if (Vat_StaticMesh)
    {
        if (Vat_MaterialInstances.Num() > 0 && bTriggerOnBeginPlay)
        {
            TriggerVatPlayback();
        }
        else if (!bTriggerOnBeginPlay && Original_MaterialInstances.IsValidIndex(0))
        {
            UMaterialInterface* WorldGridMaterial = Original_MaterialInstances[0];
            Vat_StaticMesh->SetMaterial(0, WorldGridMaterial);
        }
    }
}

void AHoudiniVatActor::Tick(const float DeltaTime)
{
    Super::Tick(DeltaTime);
}

void AHoudiniVatActor::NotifyHit(UPrimitiveComponent* MyComp, AActor* Other, UPrimitiveComponent* OtherComp, bool bSelfMoved, FVector HitLocation, FVector HitNormal, FVector NormalImpulse, const FHitResult& Hit)
{
    if (Vat_StaticMesh && Vat_MaterialInstances.Num() > 0 && bTriggerOnHit)
    {
        bool bShouldTrigger = !bExcludeHitObjects;

        if (HitObjects.Num() > 0)
        {
            const FString OtherName = Other->GetName();
            bShouldTrigger = false;

            for (const TObjectPtr<UObject>& HitObject : HitObjects)
            {
                if (HitObject)
                {
                    if (FString HitObjectName = HitObject->GetName(); OtherName.Contains(HitObjectName))
                    {
                        bShouldTrigger = !bExcludeHitObjects;
                        break;
                    }
                    else
                    {
                        bShouldTrigger = bExcludeHitObjects;
                    }
                }
            }
        }

        if (bShouldTrigger)
        {
            TriggerVatPlayback();
        }
    }
}

void AHoudiniVatActor::NotifyActorBeginOverlap(AActor* OtherActor)
{
    if (Vat_StaticMesh && Vat_MaterialInstances.Num() > 0 && bTriggerOnOverlap)
    {
        bool bShouldTrigger = !bExcludeOverlapObjects;

        if (OverlapObjects.Num() > 0)
        {
            const FString OtherName = OtherActor->GetName();
            bShouldTrigger = false;

            for (const TObjectPtr<UObject>& OverlapObject : OverlapObjects)
            {
                if (OverlapObject)
                {
                    if (FString OverlapObjectName = OverlapObject->GetName(); OtherName.Contains(OverlapObjectName))
                    {
                        bShouldTrigger = !bExcludeOverlapObjects;
                        break;
                    }
                    else
                    {
                        bShouldTrigger = bExcludeOverlapObjects;
                    }
                }
            }
        }

        if (bShouldTrigger)
        {
            TriggerVatPlayback();
        }
    }
}

void AHoudiniVatActor::ApplyMaterials(const TArray<TObjectPtr<UMaterialInterface>>& Materials) const
{
    if (Vat_StaticMesh)
    {
        const int32 NumMaterials = Materials.Num();
        
        for (int32 Index = 0; Index < NumMaterials; ++Index)
        {
            if (Materials.IsValidIndex(Index))
            {
                Vat_StaticMesh->SetMaterial(Index, Materials[Index]);
            }
            else
            {
                Vat_StaticMesh->SetMaterial(Index, nullptr);
            }
        }
    }
}

void AHoudiniVatActor::TriggerVatPlayback()
{
    const float GameTimeInSeconds = GetWorld()->GetTimeSeconds() - StartSeconds;
    
    for (int32 Index = 0; Index < Vat_MaterialInstances.Num(); ++Index)
    {
        if (Vat_MaterialInstances.IsValidIndex(Index))
        {
            if (UMaterialInstanceDynamic* DynamicMaterialInstance = UMaterialInstanceDynamic::Create(Vat_MaterialInstances[Index], this); DynamicMaterialInstance && bPlay)
            {
                Vat_StaticMesh->SetMaterial(Index, DynamicMaterialInstance);
                DynamicMaterialInstance->SetScalarParameterValue(TEXT("Game Time at First Frame"), GameTimeInSeconds);
            }
        }
    }
    
    if (bTriggerOnce)
    {
        bPlay = false;
    }
}

void AHoudiniVatActor::ResetVatPlayback()
{
    if (Vat_StaticMesh)
    {
        ApplyMaterials(Original_MaterialInstances);
        const int32 NumMaterials = Vat_StaticMesh->GetNumMaterials();
        
        for (int32 Index = 0; Index < NumMaterials; ++Index)
        {
            if (UMaterialInstanceDynamic* DynamicMaterialInstance = Cast<UMaterialInstanceDynamic>(Vat_StaticMesh->GetMaterial(Index)))
            {
                DynamicMaterialInstance->SetScalarParameterValue(FName("Game Time at First Frame"), 0.0f);
                DynamicMaterialInstance->SetScalarParameterValue(FName("Animation Length"), 0.0f);
            }
        }
        
        bPlay = true;
    }
}

bool AHoudiniVatActor::HasHitObjects() const
{
    return HitObjects.Num() > 0;
}

bool AHoudiniVatActor::HasOverlapObjects() const
{
    return OverlapObjects.Num() > 0;
}
