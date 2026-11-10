## Updates: running a newer installer over an installed version, the way the MSI's upgrade code did.
##
##   - the folder of the installed version is the default folder (unless /D or the user says otherwise),
##     so an update never leaves a second copy next to the first;
##   - an older installer refuses to replace a newer version;
##   - files are only overwritten once the application and the command line are closed: the assistant
##     may keep a second executable (APP_EXTRA_EXE, e.g. a CLI) running, and an open executable cannot be overwritten.
##
## Per-user installs only: it reads HKCU and the default folder $LOCALAPPDATA\Programs\<product>. For Wails that
## means !define WAILS_INSTALL_SCOPE "user" (its default is machine-wide, HKLM, and none of this would match).
##
## Define APP_EXTRA_EXE ("tool.exe") before the include to guard a second executable. Needs UNINST_KEY,
## PRODUCT_EXECUTABLE, INFO_PRODUCTNAME and INFO_PRODUCTVERSION (Wails' wails_tools.nsh, or the Python installer.nsi). Call AppCheckInstalled
## from .onInit and AppWaitForExit first thing in the install section.
##
## The installed version and folder are read from the uninstall key that wails.writeUninstaller
## writes (DisplayVersion) plus an InstallLocation value we add next to it.
##
## The uninstaller needs the same guard (an open executable cannot be deleted either): call
## un.AppWaitForExit first thing in the uninstall section.
##
## Messages are English by default. To translate them, define the APP_MSG_* below before the include,
## typically as "$(LangStringName)" with the LangString declared after !insertmacro MUI_LANGUAGE:
##   APP_MSG_NEWER          a newer version is installed; may use $AppInstalledVersion
##   APP_MSG_RUNNING_RETRY  the app is running, Retry/Cancel box
##   APP_MSG_CANCELLED      aborted by the user (details pane)
##   APP_MSG_RUNNING_SILENT aborted in silent mode (details pane)

!include "LogicLib.nsh"
!include "WordFunc.nsh"
!insertmacro VersionCompare

!ifndef APP_MSG_NEWER
    !define APP_MSG_NEWER "A newer version of ${INFO_PRODUCTNAME} ($AppInstalledVersion) is already installed. This installer is version ${INFO_PRODUCTVERSION} and will not replace it.$\n$\nUninstall the installed version first if you really want to go back."
!endif
!ifndef APP_MSG_RUNNING_RETRY
    !define APP_MSG_RUNNING_RETRY "${INFO_PRODUCTNAME} is running. Close it (and anything started from it), then click Retry."
!endif
!ifndef APP_MSG_CANCELLED
    !define APP_MSG_CANCELLED "Cancelled: ${INFO_PRODUCTNAME} is running."
!endif
!ifndef APP_MSG_RUNNING_SILENT
    !define APP_MSG_RUNNING_SILENT "${INFO_PRODUCTNAME} is running: close it and run the installer again."
!endif

Var AppInstalledVersion

# "0.1.0-beta.2" -> "0.1.0": the part VersionCompare can order. Pre-releases of one number are
# treated as the same version (an update between them is always allowed).
!macro AppNumericVersion IN OUT
    Push $R8
    Push $R9
    StrCpy ${OUT} ""
    StrCpy $R8 0
    ${Do}
        StrCpy $R9 ${IN} 1 $R8
        ${If} $R9 == ""
        ${OrIf} $R9 == "-"
            ${Break}
        ${EndIf}
        StrCpy ${OUT} "${OUT}$R9"
        IntOp $R8 $R8 + 1
    ${Loop}
    Pop $R9
    Pop $R8
!macroend

# Called from .onInit: reuses the installed folder, refuses a downgrade.
Function AppCheckInstalled
    Push $R0 # installed folder
    Push $R1 # installed version
    Push $R2
    Push $R3

    SetRegView 64
    ReadRegStr $R0 HKCU "${UNINST_KEY}" "InstallLocation"
    ReadRegStr $R1 HKCU "${UNINST_KEY}" "DisplayVersion"

    # The default folder is replaced by the installed one; a folder given with /D is kept.
    ${If} $R0 != ""
    ${AndIf} $INSTDIR == "$LOCALAPPDATA\Programs\${INFO_PRODUCTNAME}"
    ${AndIf} ${FileExists} "$R0\${PRODUCT_EXECUTABLE}"
        StrCpy $INSTDIR $R0
    ${EndIf}

    ${If} $R1 != ""
        !insertmacro AppNumericVersion $R1 $R2
        !insertmacro AppNumericVersion "${INFO_PRODUCTVERSION}" $R3
        ${VersionCompare} $R2 $R3 $R2
        # 1: the installed version is newer than this installer.
        ${If} $R2 == 1
            StrCpy $AppInstalledVersion $R1
            IfSilent +2 0
            MessageBox MB_OK|MB_ICONEXCLAMATION "${APP_MSG_NEWER}"
            SetErrorLevel 2
            Quit
        ${EndIf}
    ${EndIf}

    Pop $R3
    Pop $R2
    Pop $R1
    Pop $R0
FunctionEnd

# True (in $0) when the file exists and cannot be opened for writing: the program is running.
!macro AppIsRunning FILE
    StrCpy $0 0
    ${If} ${FileExists} "${FILE}"
        ClearErrors
        FileOpen $1 "${FILE}" a
        ${If} ${Errors}
            StrCpy $0 1
            ClearErrors
        ${Else}
            FileClose $1
        ${EndIf}
    ${EndIf}
!macroend

# Called at the start of the install section (AppWaitForExit) or of the uninstall section
# (un.AppWaitForExit): waits until nothing in $INSTDIR is running.
!macro AppWaitForExitFunction PREFIX
Function ${PREFIX}AppWaitForExit
    Push $0
    Push $1
    ${Do}
        !insertmacro AppIsRunning "$INSTDIR\${PRODUCT_EXECUTABLE}"
        ${If} $0 == 0
            !ifdef APP_EXTRA_EXE
            !insertmacro AppIsRunning "$INSTDIR\${APP_EXTRA_EXE}"
            !endif
        ${EndIf}
        ${If} $0 == 0
            ${Break}
        ${EndIf}
        IfSilent quit_silently 0
        MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "${APP_MSG_RUNNING_RETRY}" IDRETRY retry
        Abort "${APP_MSG_CANCELLED}"
        quit_silently:
        SetErrorLevel 5
        Abort "${APP_MSG_RUNNING_SILENT}"
        retry:
    ${Loop}
    Pop $1
    Pop $0
FunctionEnd
!macroend

!insertmacro AppWaitForExitFunction ""
!insertmacro AppWaitForExitFunction "un."
