; Inno Setup 스크립트 — Glossa (Windows x64, 머신 단위 설치)
;
; 값(이름/버전/소스경로/출력)은 빌드 시 ISCC 의 /D 정의로 주입된다.
;   → plugin/.github/scripts/Package-Windows.ps1 참고
; OBS Studio 는 Windows 에서 플러그인을 C:\ProgramData\obs-studio\plugins (권장) 또는
; C:\Program Files\obs-studio\obs-plugins\64bit (레거시)에서만 스캔한다. %APPDATA%(Roaming)는
; 스캔하지 않으므로 ProgramData(= CMake defaults.cmake 의 ALLUSERSPROFILE)에 설치한다.
; 머신 단위 위치라 관리자 권한이 필요하다. (출처: https://obsproject.com/kb/plugins-guide)

#ifndef MyAppName
  #define MyAppName "glossa"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "Glossa"
#endif
#ifndef MySourceDir
  #define MySourceDir "."
#endif
#ifndef MyOutputDir
  #define MyOutputDir "."
#endif
#ifndef MyOutputBase
  #define MyOutputBase "glossa-installer"
#endif

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 머신 단위(ProgramData) 설치 — OBS 가 스캔하는 위치라 관리자 권한 필요
PrivilegesRequired=admin
DefaultDirName={commonappdata}\obs-studio\plugins\{#MyAppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
UninstallDisplayName={#MyAppName}
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBase}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
WizardStyle=modern

[Files]
; obs-studio 플러그인 로드 레이아웃: <name>\bin\64bit\<name>.dll + <name>\data\
Source: "{#MySourceDir}\bin\64bit\*"; DestDir: "{app}\bin\64bit"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MySourceDir}\data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
