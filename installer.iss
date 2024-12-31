#define MyAppName "JVMan"
#define MyAppVersion "1.0.4"
#define MyAppPublisher "Your Company"
#define MyAppURL "https://gitee.com/jvman"
#define MyAppExeName "jvman.exe"

[Setup]
AppId={{8BE6E44F-3F36-4F3A-A3F9-C171A21B5F1A}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}/{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=d:/CodeRepository/Gitee/jvman/LICENSE
OutputDir=d:\CodeRepository\Gitee\jvman\release\jvman_1.0.4_windows_20241231_231537
OutputBaseFilename=JVMan_Setup
SetupIconFile=d:/CodeRepository/Gitee/jvman/resources/icons/app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"


[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "d:/CodeRepository/Gitee/jvman/dist/jvman/*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
