; ============================================================
; YouTube Downloader — Inno Setup Script
; ============================================================

[Setup]
AppName=YouTube Downloader
AppVersion=0.7.0
AppVerName=YouTube Downloader v0.7.0
AppPublisher=Styrbik
AppPublisherURL=https://github.com/Styrbik/youtube_downloader
AppSupportURL=https://github.com/Styrbik/youtube_downloader/issues
AppUpdatesURL=https://github.com/Styrbik/youtube_downloader/releases

DefaultDirName={autopf}\YouTube Downloader
DefaultGroupName=YouTube Downloader
DisableProgramGroupPage=yes

; Куда сохранять установщик
OutputDir=installer
OutputBaseFilename=YouTubeDownloader_Setup_v0.7.0

; Иконка установщика
SetupIconFile=icon.ico

; Сжатие
Compression=lzma2/ultra64
SolidCompression=yes

; Архитектура
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; Права
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Стиль
WizardStyle=modern

; ID для реестра (уникальный GUID)
AppId={{E62117A0-1234-5678-9ABC-DEF012345678}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Копируем ВСЁ из dist/YouTubeDownloader/
Source: "dist\YouTubeDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Ярлык в Пуск
Name: "{autoprograms}\YouTube Downloader"; Filename: "{app}\YouTubeDownloader.exe"; IconFilename: "{app}\icon.ico"
; Ярлык на рабочем столе (если выбрано)
Name: "{autodesktop}\YouTube Downloader"; Filename: "{app}\YouTubeDownloader.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; Опция "Запустить после установки"
Filename: "{app}\YouTubeDownloader.exe"; Description: "{cm:LaunchProgram,YouTube Downloader}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Удаляем папку с кэшем при удалении
Type: filesandordirs; Name: "{app}"

[Code]
// Проверка, что установлена 64-битная Windows
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsWin64 then begin
    MsgBox('YouTube Downloader требует 64-битную Windows.', mbError, MB_OK);
    Result := False;
  end;
end;