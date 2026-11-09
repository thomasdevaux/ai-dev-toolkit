## Needs INFO_COMPANYNAME and INFO_PRODUCTNAME (Wails' wails_tools.nsh, or the Python installer.nsi) and $INSTDIR. Include it, then:
##   Section "Add to the PATH (current user)" SecPath ... Call AppPathAdd ... SectionEnd   (optional component, ticked)
##   Section "Uninstall" ... Call un.AppPathRemove ... SectionEnd
##
## Adds the install folder to the user's PATH, and removes it again, without touching anything else.
##
## The rule these functions live by: the existing PATH is never lost. NSIS strings are limited to
## 1023 characters and ReadRegStr truncates silently, so writing back a PATH that was read through it
## could cut entries off. Every function therefore refuses to touch a PATH that is, or would become,
## longer than 1000 characters, and says so; the user then adds the folder by hand. Besides that:
##   - the value is read with ReadRegStr, which does not expand %VARIABLES%, and written back with
##     WriteRegExpandStr, so a REG_EXPAND_SZ PATH keeps its %VARIABLES%;
##   - our folder is appended, never inserted (after a trailing ';' it keeps one, so removal restores the value exactly), and only when it is not already one of the entries
##     (compared as a whole entry, case-insensitively);
##   - the previous value is saved under APP_BACKUP_KEY before the first write, and the write
##     is read back: if the old text is not intact at the start of the new value, the old value is put back;
##   - removal drops only entries equal to our folder and keeps every other entry, empty ones included.
##
## APP_ENV_KEY is the registry key holding the Path value (HKCU\Environment). Define it as a scratch
## key (-DAPP_ENV_KEY=Software\<co>\Scratch) to try an installer without touching the real PATH.

!include "LogicLib.nsh"

!ifndef APP_ENV_KEY
    !define APP_ENV_KEY "Environment"
!endif
!ifndef APP_BACKUP_KEY
    !define APP_BACKUP_KEY "Software\${INFO_COMPANYNAME}\${INFO_PRODUCTNAME}"
!endif
# Longest PATH (old or new) these functions agree to rewrite; NSIS strings stop at 1023.
!define APP_PATH_LIMIT 1000

Var PathScanInput
Var PathScanEntry
Var PathScanResult
Var PathScanCount

# Splits PathScanInput on ';' and drops every entry equal to PathScanEntry (case-insensitive, a
# trailing '' ignored). PathScanResult is the input without them, otherwise identical: empty
# entries and the order are kept. PathScanCount is how many were dropped. Plain loops on purpose:
# the WordFunc macros treat an empty word as missing, which is exactly what a PATH can contain.
!macro AppPathScanFunction PREFIX
Function ${PREFIX}AppPathScan
    Push $R0 # position
    Push $R1 # length of the input
    Push $R2 # character
    Push $R3 # current entry
    Push $R4 # entries kept so far
    Push $R5 # the entry, compared
    Push $R6 # the current entry, compared

    StrLen $R1 "$PathScanInput"
    StrCpy $R0 0
    StrCpy $R3 ""
    StrCpy $R4 0
    StrCpy $PathScanResult ""
    StrCpy $PathScanCount 0
    StrCpy $R5 "$PathScanEntry"
    StrCpy $R2 $R5 1 -1
    ${If} $R2 == "\"
        StrLen $R2 "$R5"
        IntOp $R2 $R2 - 1
        StrCpy $R5 $R5 $R2
    ${EndIf}

    ${Do}
        ${If} $R0 < $R1
            StrCpy $R2 $PathScanInput 1 $R0
        ${Else}
            StrCpy $R2 ";"
        ${EndIf}
        ${If} $R2 == ";"
            StrCpy $R6 $R3 1 -1
            ${If} $R6 == "\"
                StrLen $R6 "$R3"
                IntOp $R6 $R6 - 1
                StrCpy $R6 $R3 $R6
            ${Else}
                StrCpy $R6 $R3
            ${EndIf}
            ${If} $R6 != ""
            ${AndIf} $R6 == $R5
                IntOp $PathScanCount $PathScanCount + 1
            ${Else}
                ${If} $R4 == 0
                    StrCpy $PathScanResult "$R3"
                ${Else}
                    StrCpy $PathScanResult "$PathScanResult;$R3"
                ${EndIf}
                IntOp $R4 $R4 + 1
            ${EndIf}
            StrCpy $R3 ""
        ${Else}
            StrCpy $R3 "$R3$R2"
        ${EndIf}
        ${If} $R0 >= $R1
            ${Break}
        ${EndIf}
        IntOp $R0 $R0 + 1
    ${Loop}

    Pop $R6
    Pop $R5
    Pop $R4
    Pop $R3
    Pop $R2
    Pop $R1
    Pop $R0
FunctionEnd
!macroend
!insertmacro AppPathScanFunction ""
!insertmacro AppPathScanFunction "un."

# Tells running programs (Explorer, new terminals) that the environment changed.
!macro AppBroadcastEnvironment
    Push $R9
    System::Call 'user32::SendMessageTimeout(i 0xffff, i 0x1A, i 0, t "Environment", i 2, i 5000, *i .R9)'
    Pop $R9
!macroend

# Appends $INSTDIR to the user's PATH. Leaves the value alone and prints why when it cannot do so safely.
Function AppPathAdd
    Push $R0 # the PATH as it is
    Push $R1
    Push $R2
    Push $R3

    ClearErrors
    ReadRegStr $R0 HKCU "${APP_ENV_KEY}" "Path"
    ${If} ${Errors}
        ClearErrors
        # Unreadable is not the same as absent: only create the value when it really is absent.
        StrCpy $R1 0
        ${Do}
            EnumRegValue $R2 HKCU "${APP_ENV_KEY}" $R1
            ${If} ${Errors}
                ${Break}
            ${EndIf}
            ${If} $R2 == "Path"
                DetailPrint "The user PATH could not be read: left untouched. Add $INSTDIR to it by hand."
                IfSilent +2 0
                MessageBox MB_OK|MB_ICONINFORMATION "${INFO_PRODUCTNAME} is installed, but your user PATH could not be read, so it was left as it is.$\n$\nTo use it from a terminal, add this folder to your PATH yourself:$\n$INSTDIR"
                ClearErrors
                Goto done
            ${EndIf}
            IntOp $R1 $R1 + 1
        ${Loop}
        ClearErrors
        WriteRegExpandStr HKCU "${APP_ENV_KEY}" "Path" "$INSTDIR"
        DetailPrint "Added $INSTDIR to the user PATH."
        !insertmacro AppBroadcastEnvironment
        Goto done
    ${EndIf}

    StrLen $R1 "$R0"
    StrLen $R2 "$INSTDIR"
    IntOp $R2 $R1 + $R2
    IntOp $R2 $R2 + 2
    ${If} $R2 >= ${APP_PATH_LIMIT}
        DetailPrint "The user PATH is too long to edit safely: left untouched. Add $INSTDIR to it by hand."
        IfSilent +2 0
        MessageBox MB_OK|MB_ICONINFORMATION "${INFO_PRODUCTNAME} is installed, but your user PATH is too long to be edited safely, so it was left as it is.$\n$\nTo use it from a terminal, add this folder to your PATH yourself:$\n$INSTDIR"
        Goto done
    ${EndIf}

    # Already one of the entries: nothing to do (an upgrade or a reinstall).
    StrCpy $PathScanInput "$R0"
    StrCpy $PathScanEntry "$INSTDIR"
    Call AppPathScan
    ${If} $PathScanCount > 0
        DetailPrint "$INSTDIR is already in the user PATH."
        Goto done
    ${EndIf}

    WriteRegStr HKCU "${APP_BACKUP_KEY}" "PathBackup" "$R0"

    StrCpy $R2 $R0 1 -1
    ${If} $R0 == ""
        StrCpy $R3 "$INSTDIR"
    ${ElseIf} $R2 == ";"
        StrCpy $R3 "$R0$INSTDIR;"
    ${Else}
        StrCpy $R3 "$R0;$INSTDIR"
    ${EndIf}
    WriteRegExpandStr HKCU "${APP_ENV_KEY}" "Path" "$R3"

    # Read it back: the old text must still be there, untouched, at the start.
    ClearErrors
    ReadRegStr $R2 HKCU "${APP_ENV_KEY}" "Path"
    StrCpy $R1 $R2 $R1
    ${If} ${Errors}
    ${OrIf} $R1 != $R0
        WriteRegExpandStr HKCU "${APP_ENV_KEY}" "Path" "$R0"
        DetailPrint "The user PATH did not read back as expected: the previous value was put back."
        ClearErrors
        Goto done
    ${EndIf}
    DetailPrint "Added $INSTDIR to the user PATH."
    !insertmacro AppBroadcastEnvironment

    done:
    Pop $R3
    Pop $R2
    Pop $R1
    Pop $R0
FunctionEnd

# Removes $INSTDIR from the user's PATH; every other entry stays exactly as it was.
Function un.AppPathRemove
    Push $R0
    Push $R1
    Push $R2

    ClearErrors
    ReadRegStr $R0 HKCU "${APP_ENV_KEY}" "Path"
    ${If} ${Errors}
        ClearErrors
        Goto done
    ${EndIf}

    StrLen $R1 "$R0"
    ${If} $R1 >= ${APP_PATH_LIMIT}
        DetailPrint "The user PATH is too long to edit safely: left untouched. Remove $INSTDIR from it by hand."
        IfSilent +2 0
        MessageBox MB_OK|MB_ICONINFORMATION "${INFO_PRODUCTNAME} is uninstalled, but your user PATH is too long to be edited safely, so it was left as it is.$\n$\nYou can remove this folder from your PATH yourself:$\n$INSTDIR"
        Goto done
    ${EndIf}

    StrCpy $PathScanInput "$R0"
    StrCpy $PathScanEntry "$INSTDIR"
    Call un.AppPathScan
    ${If} $PathScanCount == 0
        Goto done
    ${EndIf}
    StrCpy $R1 "$PathScanResult"

    WriteRegStr HKCU "${APP_BACKUP_KEY}" "PathBackup" "$R0"

    ${If} $R1 == ""
        DeleteRegValue HKCU "${APP_ENV_KEY}" "Path"
    ${Else}
        WriteRegExpandStr HKCU "${APP_ENV_KEY}" "Path" "$R1"
    ${EndIf}
    DetailPrint "Removed $INSTDIR from the user PATH."
    !insertmacro AppBroadcastEnvironment

    done:
    Pop $R2
    Pop $R1
    Pop $R0
FunctionEnd
