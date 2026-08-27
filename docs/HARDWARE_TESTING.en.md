# Physical validation checklist

<p align="center"><a href="HARDWARE_TESTING.md">Português</a> | <strong>English</strong></p>

Record Windows, NovaProfiles version, firmware, controller revision, connection mode, and each step's result. Close GameSir Connect and use a disposable profile.

## Connection and discovery

- [ ] the 2.4 GHz dongle in XInput mode is detected;
- [ ] cable, Bluetooth, and same-name devices are not selected accidentally;
- [ ] two controllers/collections result in an unambiguous selection or safe error;
- [ ] disconnecting while idle updates the UI;
- [ ] reconnecting invalidates and reapplies the expected profile exactly once;
- [ ] Windows suspend/resume recovers state;
- [ ] a disconnect/reconnect shorter than the polling interval does not leave a false-positive UI state; if reproducible, record the timing and reapply manually.

## Application

- [ ] default RB, L4, and R4 mappings are restored correctly;
- [ ] every known safe target works in-game;
- [ ] a partial/simulated write is handled as failure;
- [ ] disconnecting at every sequence stage does not mark the profile active;
- [ ] editing the active profile shows pending status until application;
- [ ] a failure does not erase the specific message or change the applied state;
- [ ] a mid-sequence failure warns that the mapping may be partial and instructs the user to reconnect/reapply;
- [ ] an open GameSir Connect causes blocking/warning without competing writes.

## Automatic switching

- [ ] the correct full path activates the profile;
- [ ] a same-name executable in another directory does not activate it;
- [ ] closing the game restores the Default profile;
- [ ] two simultaneous games produce an explicit conflict and no arbitrary switch;
- [ ] an inaccessible process does not block the interface.

## Legacy service

- [ ] `running` blocks application;
- [ ] `stopped` permits application;
- [ ] access denied, timeout, missing service, and unexpected error display the correct states;
- [ ] `unknown` blocks writes;
- [ ] `PARAR_SERVICO_NSSM_ANTIGO.cmd` propagates success and failure.

## Layout and long-duration testing

- [ ] test US and ABNT2, especially punctuation and ISO keys;
- [ ] test 100%, 125%, 150%, and 200% scaling;
- [ ] test minimum resolution and keyboard-only navigation;
- [ ] run switching/reconnection cycles for at least 30 minutes;
- [ ] confirm there is no continuous growth in threads, handles, or memory.

Do not publish a raw USB capture before checking it for serial numbers, instance paths, and other identifiers.
