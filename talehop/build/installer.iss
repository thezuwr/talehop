; Instalador do Talehop (Inno Setup 6). Corre-se pelo criar-instalador.bat, que passa a versão.
; Instala só para o utilizador (sem pedir administrador), em %LOCALAPPDATA%\Programs\Talehop.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{BCEE9888-935A-4AB5-975E-B67F5D76BAF3}
AppName=Talehop
AppVersion={#AppVersion}
AppVerName=Talehop {#AppVersion}
AppPublisher=Talehop
DefaultDirName={autopf}\Talehop
DefaultGroupName=Talehop
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=TalehopSetup-{#AppVersion}
SetupIconFile=..\talehop\talehop.ico
UninstallDisplayIcon={app}\Talehop.exe
UninstallDisplayName=Talehop
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
; os ficheiros .tale passam a ter o ícone do Talehop no Explorador
ChangesAssociations=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; ao atualizar, tira os ficheiros da versão anterior (os livros e as definições ficam noutro sítio)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\Talehop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Registry]
; .tale (e .sincro, o nome antigo): "Livro Talehop" com o ícone do programa. Só o ícone e o nome:
; o livro lê-se na app do telemóvel, por isso não há ação de abrir. Sai com o desinstalador.
Root: HKCU; Subkey: "Software\Classes\.tale"; ValueType: string; ValueName: ""; ValueData: "Talehop.Book"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.sincro"; ValueType: string; ValueName: ""; ValueData: "Talehop.Book"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Talehop.Book"; ValueType: string; ValueName: ""; ValueData: "Livro Talehop"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Talehop.Book\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Talehop.exe,0"

[Icons]
Name: "{autoprograms}\Talehop"; Filename: "{app}\Talehop.exe"; AppUserModelID: "Talehop.Talehop"
Name: "{autodesktop}\Talehop"; Filename: "{app}\Talehop.exe"; AppUserModelID: "Talehop.Talehop"; Tasks: desktopicon

[Run]
Filename: "{app}\Talehop.exe"; Description: "{cm:LaunchProgram,Talehop}"; Flags: nowait postinstall skipifsilent
