NOVA PROFILES 1.0
=================

A small Qt Quick/QML desktop app for automatic GameSir Super Nova profiles.

IMPORTANT
---------
The older NSSM service "GameSirAutoProfile" must NOT run at the same time.
Both programs would try to write to the same HID interface.

If your old service is still enabled:
1. Right-click PARAR_SERVICO_NSSM_ANTIGO.cmd
2. Run as Administrator
3. For permanent migration, later disable/remove the old NSSM service.

INSTALL
-------
1. Run INSTALAR.cmd
2. Run EXECUTAR.cmd

The first launch creates these built-in profiles:
- Default
- Mass Effect Andromeda
- Fallout New Vegas
- Grand Chase

They use the mappings reverse-engineered from the working Super Nova setup.

FEATURES
--------
- PySide6 + Qt Quick/QML UI
- Dark modern interface
- Profile creation, rename, duplicate and delete
- Link a profile to a Windows .exe
- Automatic switching by running process
- RB / L4 / R4 remapping
- Full standard USB HID keyboard destination catalog
- Known safe GameSir destinations: RB / L4 / R4
- Direct HID writes to VID 3537 / PID 103E
- Dongle disconnect/reconnect detection
- Reapply expected profile after reconnection
- System tray
- Start with Windows
- Minimize to tray
- Restore Default on exit
- Import/export profiles as JSON
- Persistent profiles in Windows AppData
- Logs
- Single-instance protection
- Warning when the legacy NSSM service is running

KEYBOARD LAYOUT NOTE
--------------------
Letters, numbers and standard control keys use USB HID usage IDs.
Punctuation usages such as HID 0x2F/0x30 can be interpreted differently by
different OS/game keyboard layouts. The bundled Fallout profile preserves
the exact usages captured from the working GameSir Connect configuration.

DATA
----
Profiles and logs are stored under the Windows application data directory:
%LOCALAPPDATA% or the Qt AppDataLocation selected for NovaProfiles.

BUILD EXE
---------
After INSTALAR.cmd:
1. Run BUILD_EXE.cmd
2. Result:
   dist\NovaProfiles\NovaProfiles.exe

PyInstaller creates a portable folder build. Copy the entire
dist\NovaProfiles folder when moving it to another PC.

WINDOWS STARTUP
---------------
Use the "Start with Windows" toggle inside Settings.
The app registers itself under the current user's Windows Run key and starts
with --background, so only the tray icon appears after sign-in.

SUPER NOVA CONNECTION
---------------------
Expected:
- GameSir Super Nova
- 2.4 GHz dongle
- XInput mode
- VID 3537 / PID 103E
- Vendor-defined MI_01/COL04 HID interface (with safe fallback detection)

GAMESIR CONNECT
---------------
Close GameSir Connect while Nova Profiles is applying mappings. Two apps
writing configuration to the controller at the same time can conflict.

V1.1 FIX
--------
- Fixed invalid QML Text property: letterSpacing -> font.letterSpacing.
- Mapping ComboBox now uses valueRole/currentValue.
- Startup/QML failures are written to %TEMP%\NovaProfiles-startup-error.log.
- EXECUTAR.cmd now keeps the console open when startup fails.
- EXECUTAR_DEBUG.cmd enables verbose QML import diagnostics.
