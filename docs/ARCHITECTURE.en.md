# Architecture and invariants

<p align="center"><a href="ARCHITECTURE.md">Português</a> | <strong>English</strong></p>

## Components

- `main.py`: Qt lifecycle, single instance, translations, and fatal error handling;
- `qml/`: presentation and accessibility;
- `backend/app_controller.py`: public state, process matching, and asynchronous coordination;
- `backend/profile_store.py`: schema, validation, migration, and atomic persistence;
- `backend/hid_controller.py`: collection discovery and GameSir protocol;
- `backend/startup.py`: per-user startup entry;
- `version.py`: single version source;
- `packaging/`: installation, VersionInfo, build, smoke test, SBOM, and release package.

## Application flow

1. The UI or detector requests a profile by ID and persisted state.
2. The controller records the intent and serializes the operation outside the UI thread.
3. The worker confirms that a connection exists and the legacy service is stopped.
4. The HID adapter selects exactly one compatible collection and sends complete reports.
5. Only successful completion of the entire sequence updates the applied state.
6. The UI compares the profile, effective mapping hash, device identity, and connection generation to display **Active** or **Pending**. Name/executable-only changes do not pretend that hardware state changed.

## Safety invariants

- `unknown` does not mean the service is stopped;
- a partial write is never success;
- reconnection invalidates the previously applied state;
- in-memory changes become visible only after successful persistence;
- imports are validated and confirmed before replacing data;
- a configured full path takes precedence over an executable name;
- only one worker writes to HID;
- detailed errors remain available to the UI and log without exposing unnecessary data.

## Current limitations

The protocol is specific to Super Nova and the known reports. Future support for other devices must be introduced through a `ControllerAdapter` with explicit capabilities, without silently broadening the targets considered safe.

The known protocol does not provide an ACK/readback used by the application. Success therefore means that the driver accepted all complete reports, not that the firmware confirmed them. A very brief disconnect that occurs entirely between two polls and reuses the same HID path may also go unnoticed. After unexpected physical behavior, reconnect and reapply the profile.

The `hidapi` write calls do not expose portable cancellation/timeouts on Windows. The single worker prevents concurrency, but a stalled driver can still delay shutdown. Isolating writes in a cancellable process would require new physical protocol validation and remains a known limitation.
