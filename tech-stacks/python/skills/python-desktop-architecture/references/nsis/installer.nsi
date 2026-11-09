## Per-user installer for a PyInstaller --onedir build. Copy to installer/installer.nsi next to
## path.nsh and upgrade.nsh (same folder). Build, from scripts/package.ps1:
##
##   makensis /DINFO_COMPANYNAME="Acme" /DINFO_PRODUCTNAME="My App" /DINFO_PRODUCTVERSION="1.2.0" `
##            /DPRODUCT_EXECUTABLE="myapp.exe" /DSOURCE_DIR="..\dist\release\myapp" `
##            /DOUT_FILE="..\dist\release\myapp-1.2.0-setup.exe" installer\installer.nsi
##
## Optional: /DAPP_EXTRA_EXE="myapp-cli.exe" when a CLI sits in the same folder (one .spec, two EXE,
## one COLLECT), so an update waits for it too; /DINFO_FILEVERSION="1.2.0" (digits only) when
## INFO_PRODUCTVERSION carries a pre-release suffix such as 1.2.0-beta.2.
## Installs under %LOCALAPPDATA%\Programs: no UAC prompt. path.nsh / upgrade.nsh assume exactly that.

Unicode true
RequestExecutionLevel user
ManifestDPIAware true

!macro RequireDefine NAME
    !ifndef ${NAME}
        !error "installer.nsi: pass /D${NAME}=... (see the header)"
    !endif
!macroend
!insertmacro RequireDefine INFO_COMPANYNAME
!insertmacro RequireDefine INFO_PRODUCTNAME
!insertmacro RequireDefine INFO_PRODUCTVERSION
!insertmacro RequireDefine PRODUCT_EXECUTABLE
!insertmacro RequireDefine SOURCE_DIR
!insertmacro RequireDefine OUT_FILE
!ifndef INFO_FILEVERSION
    !define INFO_FILEVERSION "${INFO_PRODUCTVERSION}"
!endif
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${INFO_COMPANYNAME}${INFO_PRODUCTNAME}"

VIProductVersion "${INFO_FILEVERSION}.0"
VIFileVersion    "${INFO_FILEVERSION}.0"
VIAddVersionKey "CompanyName"     "${INFO_COMPANYNAME}"
VIAddVersionKey "FileDescription" "${INFO_PRODUCTNAME} Installer"
VIAddVersionKey "ProductVersion"  "${INFO_PRODUCTVERSION}"
VIAddVersionKey "FileVersion"     "${INFO_FILEVERSION}"
VIAddVersionKey "ProductName"     "${INFO_PRODUCTNAME}"
VIAddVersionKey "LegalCopyright"  "${INFO_COMPANYNAME}"

!include "MUI2.nsh"
!include "path.nsh"
!include "upgrade.nsh"

Name "${INFO_PRODUCTNAME}"
OutFile "${OUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\${INFO_PRODUCTNAME}"
ShowInstDetails show

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
    Call AppCheckInstalled
FunctionEnd

Section "!${INFO_PRODUCTNAME}" SecApp
    SectionIn RO
    SetShellVarContext current
    Call AppWaitForExit

    # An update must not leave the previous build's libraries behind (PyInstaller 6+ keeps them in _internal).
    RMDir /r "$INSTDIR\_internal"
    SetOutPath "$INSTDIR"
    File /r "${SOURCE_DIR}\*.*"
    CreateShortcut "$SMPROGRAMS\${INFO_PRODUCTNAME}.lnk" "$INSTDIR\${PRODUCT_EXECUTABLE}"

    WriteUninstaller "$INSTDIR\uninstall.exe"
    SetRegView 64
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${INFO_PRODUCTNAME}"
    WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${INFO_COMPANYNAME}"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${INFO_PRODUCTVERSION}"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_EXECUTABLE}"
    WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKCU "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
SectionEnd

# Only worth ticking when the folder holds something to run from a terminal (a CLI, or the app itself).
Section "Add to the PATH (current user)" SecPath
    Call AppPathAdd
SectionEnd

Section "Uninstall"
    SetShellVarContext current
    Call un.AppPathRemove

    Delete "$SMPROGRAMS\${INFO_PRODUCTNAME}.lnk"
    # Everything under the folder the user chose goes: the installer's folder page must not accept a shared one.
    RMDir /r "$INSTDIR"
    SetRegView 64
    DeleteRegKey HKCU "${UNINST_KEY}"
    # Settings the uninstall itself wrote (the PATH backup); the app's own data lives elsewhere and stays.
    DeleteRegKey HKCU "${APP_BACKUP_KEY}"
    DeleteRegKey /ifempty HKCU "Software\${INFO_COMPANYNAME}"
SectionEnd
