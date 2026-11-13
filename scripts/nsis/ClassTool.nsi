Unicode true
SetCompressor /SOLID lzma
SetCompressorDictSize 64

!ifndef VERSION
  !error "VERSION is required"
!endif
!ifndef FILEVERSION
  !define FILEVERSION "${VERSION}.0"
!endif
!ifndef PAYLOAD
  !error "PAYLOAD is required"
!endif
!ifndef OUTFILE
  !error "OUTFILE is required"
!endif
!ifndef ICON
  !error "ICON is required"
!endif

!define PRODUCT_NAME "ClassTool"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\ClassTool"
!define CONTEXT_MENU_KEY "Software\Classes\DesktopBackground\shell\ClassTool"
!define INSTANCE_MUTEX "Local\ClassTool_Yexiaxingkong233_SingleInstance"

Name "${PRODUCT_NAME} ${VERSION}"
Caption "${PRODUCT_NAME} ${VERSION} 安装程序"
BrandingText "${PRODUCT_NAME}"
InstallDir "D:\ClassTool"
InstallDirRegKey HKLM "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel admin
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${FILEVERSION}"
VIAddVersionKey /LANG=2052 "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=2052 "FileDescription" "${PRODUCT_NAME} 安装程序"
VIAddVersionKey /LANG=2052 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=2052 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=2052 "CompanyName" "Mario-Benny"
VIAddVersionKey /LANG=2052 "LegalCopyright" "MIT License"

OutFile "${OUTFILE}"
Icon "${ICON}"
UninstallIcon "${ICON}"

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"
!include "x64.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_WELCOMEPAGE_TITLE "欢迎安装 ${PRODUCT_NAME} ${VERSION}"
!define MUI_WELCOMEPAGE_TEXT "${PRODUCT_NAME} 是一套面向课堂的桌面工具集。安装程序将安装主程序，并允许你选择需要的课堂插件。默认优先安装到 D:\ClassTool；如果 D 盘不可用，则安装到 C 盘的 Program Files。"
!define MUI_DIRECTORYPAGE_TEXT_TOP "请选择 ${PRODUCT_NAME} 的安装目录。学校一体机建议保留默认的 D:\ClassTool，以避免 C 盘被影子系统还原后丢失程序文件。"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
Page custom FinishPageCreate FinishPageLeave

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

Var RecycleButton
Var RunAfterInstallCheck

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP|MB_OK "${PRODUCT_NAME} 仅支持 64 位 Windows。" /SD IDOK
    Abort
  ${EndIf}
  SetRegView 64
  Call CheckRunningInstance
  ReadRegStr $0 HKLM "${UNINSTALL_KEY}" "InstallLocation"
  StrCmp $0 "" chooseDefault
  StrCpy $INSTDIR $0
  Return

  chooseDefault:
  System::Call 'kernel32::GetDriveTypeW(w "D:\") i .r0'
  StrCmp $0 "0" useProgramFiles
  StrCmp $0 "1" useProgramFiles
  StrCmp $0 "5" useProgramFiles
  StrCpy $INSTDIR "D:\ClassTool"
  Return

  useProgramFiles:
  StrCpy $INSTDIR "$PROGRAMFILES64\ClassTool"
FunctionEnd

Function CheckRunningInstance
  System::Call 'kernel32::OpenMutexW(i 0x00100000, i 0, w "${INSTANCE_MUTEX}") i .r0'
  IntCmp $0 0 mutexFree
  System::Call 'kernel32::CloseHandle(i $0)'
  MessageBox MB_ICONSTOP|MB_OK "${PRODUCT_NAME} 正在运行，请先从托盘完全退出程序。" /SD IDOK
  Abort
  mutexFree:
FunctionEnd

Function un.onInit
  SetRegView 64
  System::Call 'kernel32::OpenMutexW(i 0x00100000, i 0, w "${INSTANCE_MUTEX}") i .r0'
  IntCmp $0 0 unMutexFree
  System::Call 'kernel32::CloseHandle(i $0)'
  MessageBox MB_ICONSTOP|MB_OK "${PRODUCT_NAME} 正在运行，请先从托盘完全退出程序，再重新卸载。" /SD IDOK
  Abort
  unMutexFree:
FunctionEnd

Function FinishPageCreate
  !insertmacro MUI_HEADER_TEXT "安装完成" "${PRODUCT_NAME} 已成功安装。"
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0 0 100% 18u "${PRODUCT_NAME} ${VERSION} 已安装到："
  Pop $0
  ${NSD_CreateLabel} 0 18u 100% 18u "$INSTDIR"
  Pop $0
  ${NSD_CreateLabel} 0 42u 100% 18u "桌面、开始菜单和右键菜单已经配置完成。"
  Pop $0
  ${NSD_CreateCheckbox} 0 68u 100% 18u "关闭安装器后启动 ${PRODUCT_NAME}"
  Pop $RunAfterInstallCheck
  ${NSD_Check} $RunAfterInstallCheck
  ${NSD_CreateButton} 0 98u 190u 26u "关闭并移动到回收站"
  Pop $RecycleButton
  ${NSD_OnClick} $RecycleButton OnRecycleInstaller
  GetDlgItem $0 $HWNDPARENT 1
  SendMessage $0 ${WM_SETTEXT} 0 "STR:关闭"
  GetDlgItem $0 $HWNDPARENT 3
  EnableWindow $0 0
  GetDlgItem $0 $HWNDPARENT 2
  ShowWindow $0 0
  nsDialogs::Show
FunctionEnd

Function MaybeRunClassTool
  ${NSD_GetState} $RunAfterInstallCheck $0
  ${If} $0 == ${BST_CHECKED}
    System::Call 'kernel32::GetCurrentProcessId() i .r0'
    System::Call 'kernel32::SetEnvironmentVariableW(w "CLASSTOOL_APP_PATH", w "$INSTDIR\ClassTool.exe")'
    Exec '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -WindowStyle Hidden -Command "Wait-Process -Id $0 -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 1200; Start-Process -FilePath $$env:CLASSTOOL_APP_PATH -WorkingDirectory ([IO.Path]::GetDirectoryName($$env:CLASSTOOL_APP_PATH))"'
  ${EndIf}
FunctionEnd

Function FinishPageLeave
  Call MaybeRunClassTool
FunctionEnd

Function OnRecycleInstaller
  Call MaybeRunClassTool
  System::Call 'kernel32::GetCurrentProcessId() i .r0'
  System::Call 'kernel32::SetEnvironmentVariableW(w "CLASSTOOL_SETUP_PATH", w "$EXEPATH")'
  Exec '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -WindowStyle Hidden -Command "Wait-Process -Id $0 -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 800; try { Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($$env:CLASSTOOL_SETUP_PATH, [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs, [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin) } catch {}"'
  Quit
FunctionEnd

Section "${PRODUCT_NAME} 主程序（必选）" SecMain
  SectionIn RO
  SetShellVarContext current
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\ClassTool.exe"
  SetOutPath "$INSTDIR"
  File "${PAYLOAD}\ClassTool.exe"
  File "${PAYLOAD}\重建ClassTool快捷方式.cmd"
  File "${PAYLOAD}\注册桌面右键菜单.cmd"
  File "${PAYLOAD}\清除桌面右键菜单.cmd"
  SetOutPath "$INSTDIR\_internal"
  File /r "${PAYLOAD}\_internal\*.*"
  CreateDirectory "$INSTDIR\data"
  CreateDirectory "$INSTDIR\tools"
  Delete "$INSTDIR\tools\calculator_tool.py"
  Delete "$INSTDIR\tools\countdown_timer.py"
  Delete "$INSTDIR\tools\document_camera_tool.py"
  Delete "$INSTDIR\tools\random_picker.py"
  Delete "$INSTDIR\tools\screen_doodle_tool.py"
  Delete "$INSTDIR\tools\voting_tool.py"
SectionEnd

SectionGroup /e "课堂插件（可选）" SecPluginGroup
  Section "简易计算器" SecCalculator
    SetOutPath "$INSTDIR\tools"
    File "${PAYLOAD}\tools\calculator_tool.py"
  SectionEnd
  Section "倒计时装置" SecCountdown
    SetOutPath "$INSTDIR\tools"
    File "${PAYLOAD}\tools\countdown_timer.py"
  SectionEnd
  Section "展台" SecCamera
    SetOutPath "$INSTDIR\tools"
    File "${PAYLOAD}\tools\document_camera_tool.py"
  SectionEnd
  Section "随机点名器" SecRandomPicker
    SetOutPath "$INSTDIR\tools"
    File "${PAYLOAD}\tools\random_picker.py"
  SectionEnd
  Section "涂鸦模块" SecDoodle
    SetOutPath "$INSTDIR\tools"
    File "${PAYLOAD}\tools\screen_doodle_tool.py"
  SectionEnd
  Section "投票模块" SecVoting
    SetOutPath "$INSTDIR\tools"
    File "${PAYLOAD}\tools\voting_tool.py"
  SectionEnd
SectionGroupEnd

Section -PostInstall SecPost
  SetShellVarContext current
  SetRegView 64
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\uninstall.exe"
  CreateShortCut "$DESKTOP\ClassTool.lnk" "$INSTDIR\ClassTool.exe" "" "$INSTDIR\ClassTool.exe" 0
  CreateShortCut "$SMPROGRAMS\ClassTool.lnk" "$INSTDIR\ClassTool.exe" "" "$INSTDIR\ClassTool.exe" 0
  CreateDirectory "$SMPROGRAMS\ClassTool"
  CreateShortCut "$SMPROGRAMS\ClassTool\ClassTool.lnk" "$INSTDIR\ClassTool.exe" "" "$INSTDIR\ClassTool.exe" 0
  CreateShortCut "$SMPROGRAMS\ClassTool\卸载 ClassTool.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME} ${VERSION}"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "Publisher" "Mario-Benny"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "URLInfoAbout" "https://github.com/Mario-Benny/ClassTool"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\ClassTool.exe"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTALL_KEY}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
  WriteRegStr HKLM "${UNINSTALL_KEY}" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair" 1
  IfFileExists "$INSTDIR\tools\calculator_tool.py" registerContextMenu
  IfFileExists "$INSTDIR\tools\countdown_timer.py" registerContextMenu
  IfFileExists "$INSTDIR\tools\document_camera_tool.py" registerContextMenu
  IfFileExists "$INSTDIR\tools\random_picker.py" registerContextMenu
  IfFileExists "$INSTDIR\tools\screen_doodle_tool.py" registerContextMenu
  IfFileExists "$INSTDIR\tools\voting_tool.py" registerContextMenu
  nsExec::ExecToLog '"$SYSDIR\cmd.exe" /d /c ""$INSTDIR\清除桌面右键菜单.cmd" /silent"'
  Pop $0
  Goto contextMenuDone
  registerContextMenu:
  nsExec::ExecToLog '"$SYSDIR\cmd.exe" /d /c ""$INSTDIR\注册桌面右键菜单.cmd" /silent"'
  Pop $0
  contextMenuDone:
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  SetRegView 64
  IfFileExists "$INSTDIR\清除桌面右键菜单.cmd" 0 contextFallback
  nsExec::ExecToLog '"$SYSDIR\cmd.exe" /d /c ""$INSTDIR\清除桌面右键菜单.cmd" /silent"'
  Pop $0
  contextFallback:
  DeleteRegKey HKCU "${CONTEXT_MENU_KEY}"
  Delete "$DESKTOP\ClassTool.lnk"
  Delete "$SMPROGRAMS\ClassTool.lnk"
  Delete "$SMPROGRAMS\ClassTool\ClassTool.lnk"
  Delete "$SMPROGRAMS\ClassTool\卸载 ClassTool.lnk"
  RMDir "$SMPROGRAMS\ClassTool"
  Delete "$INSTDIR\tools\calculator_tool.py"
  Delete "$INSTDIR\tools\countdown_timer.py"
  Delete "$INSTDIR\tools\document_camera_tool.py"
  Delete "$INSTDIR\tools\random_picker.py"
  Delete "$INSTDIR\tools\screen_doodle_tool.py"
  Delete "$INSTDIR\tools\voting_tool.py"
  RMDir "$INSTDIR\tools"
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\ClassTool.exe"
  Delete "$INSTDIR\重建ClassTool快捷方式.cmd"
  Delete "$INSTDIR\注册桌面右键菜单.cmd"
  Delete "$INSTDIR\清除桌面右键菜单.cmd"
  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  Delete /REBOOTOK "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
