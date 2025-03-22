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

#include "HoudiniCreateNewVatWindow.h"
#include "HoudiniCreateNewVatWindowParameters.h"
#include "SidefxLabsEditor/Private/VatImporter/HoudiniVatImporter.h"

#define LOCTEXT_NAMESPACE "FHoudiniCreateNewVatWindow"

void FHoudiniCreateNewVatWindow::OpenPropertyEditorWindow()
{
    FGlobalTabmanager::Get()->TryInvokeTab(FName("CreateNewVATTab"));
}

TSharedRef<IDetailCustomization> FHoudiniCreateNewVatWindow::MakeInstance()
{
    return MakeShareable(new FHoudiniCreateNewVatWindow());
}

TSharedRef<SDockTab> FHoudiniCreateNewVatWindow::CreatePropertyEditorTab(const FSpawnTabArgs& Args)
{
    FPropertyEditorModule& PropertyEditorModule = FModuleManager::LoadModuleChecked<FPropertyEditorModule>("PropertyEditor");

    UCreateNewVatProperties* VatProperties = NewObject<UCreateNewVatProperties>();

    FDetailsViewArgs DetailsViewArgs;
    DetailsViewArgs.bShowOptions = false;
    DetailsViewArgs.bAllowSearch = false;
    DetailsViewArgs.bHideSelectionTip = true;

    TSharedRef<IDetailsView> const DetailsView = PropertyEditorModule.CreateDetailView(DetailsViewArgs);
    DetailsView->SetObject(VatProperties);

    UHoudiniVatImporter* VatImporter = NewObject<UHoudiniVatImporter>();
    VatImporter->SetProperties(VatProperties);

    TSharedRef<SDockTab> NewTab = SNew(SDockTab)
        .Label(LOCTEXT("CreateNewVATEditorTitle", "Create New VAT"));

    TSharedRef<SVerticalBox> const TabContent = SNew(SVerticalBox)
        + SVerticalBox::Slot()
        .FillHeight(1.0f)
        .Padding(5)
        [
            DetailsView
        ]
        + SVerticalBox::Slot()
        .AutoHeight()
        .Padding(5)
        [
            CreateVatButton(VatImporter, VatProperties)
        ];

    NewTab->SetContent(TabContent);

    return NewTab;
}

TSharedRef<SWidget> FHoudiniCreateNewVatWindow::CreateVatButton(UHoudiniVatImporter* VatImporter, UCreateNewVatProperties* VatProperties)
{
    TSharedPtr<SWindow> WindowPtr = FSlateApplication::Get().GetActiveTopLevelWindow();

    return SNew(SBox)
        .HeightOverride(35)
        [
            SNew(SButton)
            .Text(FText::FromString(TEXT("Create New VAT")))
            .HAlign(HAlign_Center)
            .VAlign(VAlign_Center)
            .OnClicked_Lambda([VatImporter, VatProperties, WindowPtr]()
            {
                UE_LOG(LogTemp, Log, TEXT("Creating VAT"));
                VatImporter->ImportFiles();
                if (VatImporter->bCanceled)
                {
                    if (WindowPtr.IsValid())
                    {
                        WindowPtr->RequestDestroyWindow();
                    }
                    return FReply::Handled();
                }
                VatImporter->CreateVatMaterial();
                VatImporter->CreateVatMaterialInstance();
                if (VatProperties->bCreateVatBlueprint)
                {
                    VatImporter->CreateVatBlueprint();
                }
                if (WindowPtr.IsValid())
                {
                    WindowPtr->RequestDestroyWindow();
                }
                return FReply::Handled();
            })
        ];
}

void FHoudiniCreateNewVatWindow::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
}

#undef LOCTEXT_NAMESPACE
