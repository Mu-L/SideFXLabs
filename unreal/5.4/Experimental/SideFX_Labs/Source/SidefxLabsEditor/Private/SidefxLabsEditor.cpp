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

#include "SidefxLabsEditor.h"
#include "HoudiniCreateNewVatWindow.h"

#define LOCTEXT_NAMESPACE "FSidefxLabsEditorModule"

class FMenuManager
{
public:
    static void RegisterSidefxLabsMenu(FSidefxLabsEditorModule* EditorModule);
    static void RegisterSidefxLabsSubMenu(FSidefxLabsEditorModule* EditorModule);

private:
    static void RegisterHelpAndSupportSection(UToolMenu* SidefxLabsEditorSubMenu, FSidefxLabsEditorModule* EditorModule);
};

class FPropertyCustomizationManager
{
public:
    static void Initialize(FSidefxLabsEditorModule* EditorModule);
    static void RegisterCustomizations(FSidefxLabsEditorModule* EditorModule);
    static void UnregisterCustomizations();

private:
    static void RegisterHoudiniDetailsCategory();
};

void FSidefxLabsEditorModule::StartupModule()
{
    MenuManager = MakeUnique<FMenuManager>();
    PropertyCustomizationManager = MakeUnique<FPropertyCustomizationManager>();

    InitializeMenu();
    InitializePropertyCustomization();
    RegisterTabSpawners();
}

void FSidefxLabsEditorModule::ShutdownModule()
{
    Cleanup();
}

void FSidefxLabsEditorModule::InitializeMenu()
{
    MenuManager->RegisterSidefxLabsMenu(this);
}

void FSidefxLabsEditorModule::InitializePropertyCustomization()
{
    PropertyCustomizationManager->Initialize(this);
}

void FSidefxLabsEditorModule::RegisterTabSpawners()
{
    FGlobalTabmanager::Get()->RegisterNomadTabSpawner("CreateNewVATTab", FOnSpawnTab::CreateStatic(&FHoudiniCreateNewVatWindow::CreatePropertyEditorTab))
        .SetDisplayName(LOCTEXT("CreateNewVATTabTitle", "Create New VAT"))
        .SetMenuType(ETabSpawnerMenuType::Hidden);
}

void FSidefxLabsEditorModule::Cleanup()
{
    MenuManager.Reset();
    PropertyCustomizationManager.Reset();
}

void FMenuManager::RegisterSidefxLabsMenu(FSidefxLabsEditorModule* EditorModule)
{
    FToolMenuOwnerScoped OwnerScoped(EditorModule);
    if (UToolMenus* ToolMenus = UToolMenus::Get())
    {
        if (UToolMenu* MainMenu = ToolMenus->ExtendMenu("LevelEditor.MainMenu"))
        {
            FToolMenuSection& PluginsSection = MainMenu->AddSection("SideFX Labs", LOCTEXT("SideFX Labs", "SideFX Labs"));
            PluginsSection.AddSubMenu(
                "SidefxLabsEditor_SubMenu",
                LOCTEXT("SidefxLabsEditor_SubMenu", "SideFX Labs"),
                LOCTEXT("SidefxLabsEditor_SubMenu_ToolTip", "Open the SideFX Labs menu"),
                FNewToolMenuChoice(),
                false,
                FSlateIcon("EditorStyle", "LevelEditor.Tabs.Tools")
            );

            RegisterSidefxLabsSubMenu(EditorModule);
        }
    }
}

void FMenuManager::RegisterSidefxLabsSubMenu(FSidefxLabsEditorModule* EditorModule)
{
    UToolMenus* ToolMenus = UToolMenus::Get();
    if (UToolMenu* SidefxLabsEditorSubMenu = ToolMenus->ExtendMenu("LevelEditor.MainMenu.SidefxLabsEditor_SubMenu"))
    {
        FToolMenuSection& VertexAnimationSection = SidefxLabsEditorSubMenu->AddSection("Vertex Animation", LOCTEXT("VertexAnimation_Heading", "Vertex Animation"));

        VertexAnimationSection.AddMenuEntry(
            "CreateNewVat",
            LOCTEXT("CreateNewVat", "Create New VAT"),
            LOCTEXT("CreateNewVat_ToolTip", "Create a new VAT"),
            FSlateIcon(),
            FUIAction(FExecuteAction::CreateStatic(&FSidefxLabsEditorModule::CreateNewVat))
        );

        RegisterHelpAndSupportSection(SidefxLabsEditorSubMenu, EditorModule);
    }
}

void FMenuManager::RegisterHelpAndSupportSection(UToolMenu* SidefxLabsEditorSubMenu, FSidefxLabsEditorModule* EditorModule)
{
    FToolMenuSection& HelpAndSupportSection = SidefxLabsEditorSubMenu->AddSection("HelpAndSupport", LOCTEXT("HelpAndSupport_Heading", "Help and Support"));
    HelpAndSupportSection.AddMenuEntry(
        "Website",
        LOCTEXT("Website", "Website"),
        LOCTEXT("Website_ToolTip", "SideFX Labs website"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateLambda([]() { FPlatformProcess::LaunchURL(TEXT("https://www.sidefx.com/products/sidefx-labs/"), nullptr, nullptr); }))
    );
    HelpAndSupportSection.AddMenuEntry(
        "Documentation",
        LOCTEXT("Documentation", "Documentation"),
        LOCTEXT("Documentation_ToolTip", "SideFX Labs documentation"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateLambda([]() { FPlatformProcess::LaunchURL(TEXT("https://www.sidefx.com/docs/houdini/labs/"), nullptr, nullptr); }))
    );
    HelpAndSupportSection.AddMenuEntry(
        "GitHub",
        LOCTEXT("GitHub", "GitHub"),
        LOCTEXT("GitHub_ToolTip", "SideFX Labs GitHub"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateLambda([]() { FPlatformProcess::LaunchURL(TEXT("https://github.com/sideeffects/SidefxLabs"), nullptr, nullptr); }))
    );
    HelpAndSupportSection.AddMenuEntry(
        "ArtStation",
        LOCTEXT("ArtStation", "ArtStation"),
        LOCTEXT("ArtStation_ToolTip", "SideFX Labs ArtStation"),
        FSlateIcon(),
        FUIAction(FExecuteAction::CreateLambda([]() { FPlatformProcess::LaunchURL(TEXT("https://www.artstation.com/SidefxLabs"), nullptr, nullptr); }))
    );
}

void FPropertyCustomizationManager::Initialize(FSidefxLabsEditorModule* EditorModule)
{
    RegisterHoudiniDetailsCategory();
    RegisterCustomizations(EditorModule);
}

void FPropertyCustomizationManager::RegisterHoudiniDetailsCategory()
{
    static const FName PropertyEditor("PropertyEditor");
    FPropertyEditorModule& PropertyEditorModule = FModuleManager::GetModuleChecked<FPropertyEditorModule>(PropertyEditor);

    const TSharedRef<FPropertySection> HoudiniSection = PropertyEditorModule.FindOrCreateSection("Object", "Houdini", LOCTEXT("Houdini", "Houdini"));
    HoudiniSection->AddCategory("Houdini VAT");
}

void FPropertyCustomizationManager::RegisterCustomizations(FSidefxLabsEditorModule* EditorModule)
{
    FPropertyEditorModule& PropertyEditorModule = FModuleManager::LoadModuleChecked<FPropertyEditorModule>("PropertyEditor");
    PropertyEditorModule.RegisterCustomClassLayout("SidefxLabs", FOnGetDetailCustomizationInstance::CreateStatic(&FHoudiniCreateNewVatWindow::MakeInstance));
}

void FPropertyCustomizationManager::UnregisterCustomizations()
{
    if (FModuleManager::Get().IsModuleLoaded("PropertyEditor"))
    {
        FPropertyEditorModule& PropertyEditorModule = FModuleManager::GetModuleChecked<FPropertyEditorModule>("PropertyEditor");
        PropertyEditorModule.UnregisterCustomClassLayout("SidefxLabs");
    }
}

void FSidefxLabsEditorModule::CreateNewVat()
{
    FHoudiniCreateNewVatWindow::OpenPropertyEditorWindow();
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FSidefxLabsEditorModule, SidefxLabsEditor);
