; Inno Setup script for lmath — built by build.bat (do not run by hand).
#ifndef AppVersion
  #define AppVersion "4.0.0"
#endif

[Setup]
AppId={{B68437DF-F6AE-4614-9BD5-93CF4003EDE6}
AppName=lmath
AppVersion={#AppVersion}
AppVerName=lmath {#AppVersion}
AppPublisher=lmath
DefaultDirName={autopf}\lmath
DefaultGroupName=lmath
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=lmath-{#AppVersion}-setup
SetupIconFile=..\icons\lmath.ico
UninstallDisplayIcon={app}\lmath.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\lmath\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\lmath"; Filename: "{app}\lmath.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\lmath"; Filename: "{app}\lmath.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\lmath.exe"; Description: "Start lmath now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
