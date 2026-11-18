Unicode true

####
## Per-user installer (no administrator rights, installs under %LOCALAPPDATA%\Programs).
##
## Built by `wails3 package INSTALL_SCOPE=user` (from scripts/package.ps1). Reference copy kept in the
## toolkit: copy it over build/windows/nsis/project.nsi, next to upgrade.nsh, and adjust the product wording.
## Template replacements do not work in this file: values come from the defines below or from
## "wails_tools.nsh" (generated, do not edit). To iterate on the installer without a full build,
## populate wails_tools.nsh with one `wails3 package`, then:
## > makensis -DARG_WAILS_AMD64_BINARY=..\..\..\bin\MarkdownDesigner.exe project.nsi
##
## What this file adds to the Wails template:
##   - update in place (upgrade.nsh): reuses the installed folder, refuses a downgrade, waits for the
##     app to be closed -- the same guard protects the uninstaller;
##   - uninstall deletes only the files this installer wrote (never `RMDir /r` on a folder the user
##     may have chosen), and asks before deleting the user's settings and WebView2 cache;
##   - French and English (the system language decides), optional desktop shortcut whose choice
##     is remembered across updates, "Launch" box on the last page, no Modify/Repair buttons.
##
## Keep the file saved as UTF-8 *with* a BOM: this is a Unicode installer and NSIS reads a script
## without one as ANSI, which garbles the accents below.
####
!ifndef WAILS_INSTALL_SCOPE # `wails3 package INSTALL_SCOPE=user` already passes it
    !define WAILS_INSTALL_SCOPE "user"
!endif

## Include the wails tools
!include "wails_tools.nsh"

## Translatable messages of upgrade.nsh (the LangStrings are declared further down)
!define APP_MSG_NEWER "$(MsgNewerInstalled)"
!define APP_MSG_RUNNING_RETRY "$(MsgRunningRetry)"
!define APP_MSG_CANCELLED "$(MsgCancelled)"
!define APP_MSG_RUNNING_SILENT "$(MsgRunningSilent)"
!include "upgrade.nsh"

# The version information for this two must consist of 4 parts
VIProductVersion "${INFO_PRODUCTVERSION}.0"
VIFileVersion    "${INFO_PRODUCTVERSION}.0"

VIAddVersionKey "CompanyName"     "${INFO_COMPANYNAME}"
VIAddVersionKey "FileDescription" "${INFO_PRODUCTNAME} Installer"
VIAddVersionKey "ProductVersion"  "${INFO_PRODUCTVERSION}"
VIAddVersionKey "FileVersion"     "${INFO_PRODUCTVERSION}"
VIAddVersionKey "LegalCopyright"  "${INFO_COPYRIGHT}"
VIAddVersionKey "ProductName"     "${INFO_PRODUCTNAME}"

# Enable HiDPI support. https://nsis.sourceforge.io/Reference/ManifestDPIAware
ManifestDPIAware true

!include "MUI2.nsh"
!include "Sections.nsh"

!define MUI_ICON "..\icon.ico"
!define MUI_UNICON "..\icon.ico"
!define MUI_ABORTWARNING # Warn the user if they exit before the end.
!define MUI_FINISHPAGE_NOAUTOCLOSE # Stay on the progress page so the log can be read.
!define MUI_COMPONENTSPAGE_NODESC # One optional item: no description pane.
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT_EXECUTABLE}"
!define MUI_FINISHPAGE_RUN_TEXT "$(RunApp)"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

# The first language is the fallback; NSIS picks the one matching the system language.
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"

LangString SecDesktopName ${LANG_ENGLISH} "Desktop shortcut"
LangString SecDesktopName ${LANG_FRENCH}  "Raccourci sur le Bureau"
LangString RunApp ${LANG_ENGLISH} "Launch ${INFO_PRODUCTNAME}"
LangString RunApp ${LANG_FRENCH}  "Lancer ${INFO_PRODUCTNAME}"
LangString MsgRemoveData ${LANG_ENGLISH} "Also delete your ${INFO_PRODUCTNAME} settings and cache?$\n$\nChoose No to keep them for a later reinstall."
LangString MsgRemoveData ${LANG_FRENCH}  "Supprimer aussi les paramètres et le cache de ${INFO_PRODUCTNAME} ?$\n$\nChoisissez Non pour les conserver en vue d'une réinstallation."

LangString MsgNewerInstalled ${LANG_ENGLISH} "A newer version of ${INFO_PRODUCTNAME} ($AppInstalledVersion) is already installed. This installer is version ${INFO_PRODUCTVERSION} and will not replace it.$\n$\nUninstall the installed version first if you really want to go back."
LangString MsgNewerInstalled ${LANG_FRENCH}  "Une version plus récente de ${INFO_PRODUCTNAME} ($AppInstalledVersion) est déjà installée. Cet installeur est en version ${INFO_PRODUCTVERSION} et ne la remplacera pas.$\n$\nDésinstallez d'abord la version installée si vous voulez vraiment revenir en arrière."
LangString MsgRunningRetry ${LANG_ENGLISH} "${INFO_PRODUCTNAME} is running. Close it (and anything started from it), then click Retry."
LangString MsgRunningRetry ${LANG_FRENCH}  "${INFO_PRODUCTNAME} est en cours d'exécution. Fermez-le (ainsi que tout ce qu'il a lancé), puis cliquez sur Réessayer."
LangString MsgCancelled ${LANG_ENGLISH} "Cancelled: ${INFO_PRODUCTNAME} is running."
LangString MsgCancelled ${LANG_FRENCH}  "Annulé : ${INFO_PRODUCTNAME} est en cours d'exécution."
LangString MsgRunningSilent ${LANG_ENGLISH} "${INFO_PRODUCTNAME} is running: close it and run the installer again."
LangString MsgRunningSilent ${LANG_FRENCH}  "${INFO_PRODUCTNAME} est en cours d'exécution : fermez-le et relancez l'installeur."

## The following two statements can be used to sign the installer and the uninstaller. The path to the binaries are provided in %1
#!uninstfinalize 'signtool --file "%1"'
#!finalize 'signtool --file "%1"'

Name "${INFO_PRODUCTNAME}"
OutFile "..\..\..\bin\${INFO_PROJECTNAME}-${ARCH}-installer.exe" # Name of the installer's file.
InstallDir "$LOCALAPPDATA\Programs\${INFO_PRODUCTNAME}"
ShowInstDetails hide # A "Show details" button stays available on the progress page.
ShowUninstDetails hide

# Files an earlier version shipped that the current one does not: one `Delete` line each. An update
# only overwrites what the new version contains, so a file that was dropped would otherwise stay.
!macro AppObsoleteFiles
!macroend

Section "-Main" SecMain
    !insertmacro wails.setShellContext

    Call AppWaitForExit # an open executable cannot be overwritten

    !insertmacro wails.webview2runtime

    SetOutPath $INSTDIR
    !insertmacro AppObsoleteFiles
    !insertmacro wails.files

    CreateShortcut "$SMPROGRAMS\${INFO_PRODUCTNAME}.lnk" "$INSTDIR\${PRODUCT_EXECUTABLE}"

    !insertmacro wails.associateFiles
    !insertmacro wails.associateCustomProtocols

SectionEnd

Section "$(SecDesktopName)" SecDesktop
    CreateShortcut "$DESKTOP\${INFO_PRODUCTNAME}.lnk" "$INSTDIR\${PRODUCT_EXECUTABLE}"
SectionEnd

Section "-Finish"
    !insertmacro wails.writeUninstaller
    # Read back by upgrade.nsh on the next update; Modify/Repair have nothing to offer here.
    WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1

    ${If} ${SectionIsSelected} ${SecDesktop}
        WriteRegStr HKCU "${UNINST_KEY}" "DesktopShortcut" "1"
    ${Else}
        WriteRegStr HKCU "${UNINST_KEY}" "DesktopShortcut" "0"
        Delete "$DESKTOP\${INFO_PRODUCTNAME}.lnk" # unticked on an update
    ${EndIf}
SectionEnd

Function .onInit
    !insertmacro wails.checkArchitecture
    Call AppCheckInstalled # reuses the installed folder, refuses a downgrade

    # An update keeps the earlier answer about the desktop shortcut.
    SetRegView 64
    ReadRegStr $0 HKCU "${UNINST_KEY}" "DesktopShortcut"
    ${If} $0 == "0"
        !insertmacro UnselectSection ${SecDesktop}
    ${EndIf}
FunctionEnd

Section "Uninstall"
    !insertmacro wails.setShellContext

    Call un.AppWaitForExit

    # Only what the installer wrote: the folder may be one the user picked (Documents, a project...).
    Delete "$INSTDIR\${PRODUCT_EXECUTABLE}"
    !insertmacro AppObsoleteFiles

    Delete "$SMPROGRAMS\${INFO_PRODUCTNAME}.lnk"
    Delete "$DESKTOP\${INFO_PRODUCTNAME}.lnk"

    !insertmacro wails.unassociateFiles
    !insertmacro wails.unassociateCustomProtocols

    # Settings and the WebView2 profile live in %AppData%\<exe name> (go-webview2's default).
    # Silent uninstalls (/S, e.g. an update by script) always keep them.
    IfSilent keep_data
    MessageBox MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2 "$(MsgRemoveData)" IDNO keep_data
    RMDir /r "$AppData\${PRODUCT_EXECUTABLE}"
    keep_data:

    !insertmacro wails.deleteUninstaller
    RMDir "$INSTDIR" # removes the folder only when nothing else is left in it
SectionEnd
