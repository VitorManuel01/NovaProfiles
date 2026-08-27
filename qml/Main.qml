pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "components"
import "Theme.js" as Theme

ApplicationWindow {
    id: window
    objectName: "mainWindow"

    width: 1120
    height: 740
    minimumWidth: 900
    minimumHeight: 620
    visible: false
    title: qsTr("Nova Profiles")
    color: Theme.bg

    // Optional capabilities pass through this compatibility boundary so older
    // development controllers can still render the interface.
    // qmllint disable unqualified
    property var controller: app
    // qmllint enable unqualified
    property string toastMessage: ""
    property bool toastPersistent: false
    property bool toastTracksLastError: false

    readonly property var selectedProfile: backendValue("selectedProfile", ({}))
    readonly property string selectedId: selectedProfile.id || ""
    readonly property string activeId: backendValue("activeProfileId", "")
    readonly property bool deviceConnected: Boolean(backendValue("deviceConnected", false))
    readonly property bool pendingChanges: Boolean(backendValue("pendingChanges", false))
    readonly property bool applyInProgress: Boolean(backendValue("applyInProgress", false))
    readonly property bool hardwareStateValid: Boolean(backendValue("hardwareStateValid", true))
    readonly property string lastError: String(backendValue("lastError", "") || "")
    readonly property string applyError: String(backendValue("applyError", "") || "")
    readonly property string profileConflict: String(backendValue("profileConflict", "") || "")
    readonly property var importPreview: backendValue("importPreview", ({}))
    readonly property bool hasImportPreview: importPreview
                                                   && Object.keys(importPreview).length > 0
    readonly property string legacyState: {
        var state = String(backendValue("legacyServiceState", "") || "").toLowerCase()
        if (state === "running" || state === "stopped" || state === "unknown")
            return state
        return Boolean(backendValue("legacyServiceRunning", false)) ? "running" : "stopped"
    }
    readonly property bool legacyBlocked: legacyState !== "stopped"
    readonly property string mappingState: {
        if (applyError.length > 0 && (!hardwareStateValid || pendingChanges))
            return "error"
        if (applyInProgress || !deviceConnected || pendingChanges
                || !hardwareStateValid || selectedId !== activeId)
            return "pending"
        return "active"
    }

    function backendValue(name, fallbackValue) {
        if (!controller)
            return fallbackValue
        try {
            var candidate = controller[name]
            return candidate === undefined || candidate === null ? fallbackValue : candidate
        } catch (error) {
            return fallbackValue
        }
    }

    function backendCall(name) {
        if (!controller)
            return undefined
        try {
            var fn = controller[name]
            if (typeof fn !== "function")
                return undefined
            var args = Array.prototype.slice.call(arguments, 1)
            return fn.apply(controller, args)
        } catch (error) {
            showToast(qsTr("The requested action is not available in this build."), true)
            return undefined
        }
    }

    function looksLikeError(message) {
        var value = String(message || "").toLowerCase()
        return value.indexOf("error") >= 0 || value.indexOf("failed") >= 0
                || value.indexOf("could not") >= 0 || value.indexOf("unsupported") >= 0
    }

    function showToast(message, persistent, tracksLastError) {
        if (!message)
            return
        toastTimer.stop()
        toastMessage = String(message)
        toastPersistent = Boolean(persistent)
        toastTracksLastError = Boolean(tracksLastError)
        toastBox.visible = true
        if (!toastPersistent)
            toastTimer.restart()
    }

    function hideToast() {
        toastTimer.stop()
        toastBox.visible = false
        toastPersistent = false
        toastTracksLastError = false
    }

    function importNamesText() {
        var names = importPreview.names || []
        if (!names.length)
            return ""
        var visibleNames = names.slice(0, 8).join(", ")
        if (names.length > 8)
            visibleNames += qsTr(" and %1 more").arg(names.length - 8)
        return visibleNames
    }

    function removedImportNamesText() {
        var names = importPreview.removedNames || []
        if (!names.length)
            return ""
        var visibleNames = names.slice(0, 6).join(", ")
        if (names.length > 6)
            visibleNames += qsTr(" and %1 more").arg(names.length - 6)
        return visibleNames
    }

    function cancelImportPreview() {
        backendCall("cancelImportProfiles")
    }

    onClosing: function(close) {
        close.accepted = false
        if (Boolean(backendValue("minimizeToTray", false))
                && Boolean(backendValue("trayAvailable", false))) {
            window.hide()
        } else {
            backendCall("quitApplication")
        }
    }

    Connections {
        target: window.controller
        ignoreUnknownSignals: true

        function onToast(message) {
            var isLastError = window.lastError.length > 0
                    && String(message) === window.lastError
            window.showToast(message,
                             isLastError || window.looksLikeError(message),
                             isLastError)
        }

        function onLastErrorChanged() {
            if (window.lastError.length > 0)
                window.showToast(window.lastError, true, true)
            else if (window.toastTracksLastError)
                window.hideToast()
        }

        function onImportPreviewChanged() {
            if (window.hasImportPreview)
                importDialog.open()
            else if (importDialog.visible)
                importDialog.close()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.bg

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                id: sidebar
                objectName: "sidebar"
                Layout.preferredWidth: window.width < 1040 ? 248 : 276
                Layout.minimumWidth: 236
                Layout.fillHeight: true
                color: Theme.sidebar
                border.color: Theme.borderSoft

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: window.height < 680 ? 14 : 18
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            Layout.preferredWidth: 36
                            Layout.preferredHeight: 36
                            radius: 11
                            color: Theme.accentSoft
                            border.color: "#24546A"

                            Text {
                                anchors.centerIn: parent
                                text: "N"
                                color: Theme.accent
                                font.pixelSize: 20
                                font.bold: true
                            }

                            Accessible.name: qsTr("Nova Profiles")
                            Accessible.role: Accessible.StaticText
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("NOVA PROFILES")
                                color: Theme.text
                                font.pixelSize: 14
                                font.bold: true
                                font.letterSpacing: 0.3
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Super Nova Auto Mapper")
                                color: Theme.muted
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                        }

                        Button {
                            id: settingsButton
                            Layout.preferredWidth: 38
                            Layout.preferredHeight: 38
                            text: "⚙"
                            focusPolicy: Qt.StrongFocus

                            Accessible.name: qsTr("Open settings")
                            Accessible.description: qsTr("Manage startup, switching and profile data")
                            Accessible.role: Accessible.Button

                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Settings")
                            ToolTip.delay: 650

                            background: Rectangle {
                                radius: 10
                                color: settingsButton.hovered ? Theme.surfaceHover : "transparent"
                                border.width: settingsButton.activeFocus ? 2 : 0
                                border.color: Theme.focus
                            }

                            contentItem: Text {
                                text: settingsButton.text
                                color: Theme.muted
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.pixelSize: 17
                            }

                            Keys.onReturnPressed: function(event) {
                                settingsButton.clicked()
                                event.accepted = true
                            }
                            Keys.onEnterPressed: function(event) {
                                settingsButton.clicked()
                                event.accepted = true
                            }
                            onClicked: settingsDrawer.open()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.borderSoft
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Text {
                            text: qsTr("PROFILES")
                            color: Theme.muted
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1.2
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: String(window.backendValue("profiles", []).length)
                            color: Theme.muted2
                            font.pixelSize: 11
                            Accessible.name: qsTr("%1 profiles").arg(text)
                        }
                    }

                    ListView {
                        id: profileList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 6
                        clip: true
                        model: window.backendValue("profiles", [])
                        activeFocusOnTab: true
                        keyNavigationEnabled: true

                        Accessible.name: qsTr("Profiles")
                        Accessible.role: Accessible.List

                        delegate: ProfileButton {
                            id: profileDelegate
                            required property var modelData
                            width: profileList.width
                            profileName: profileDelegate.modelData.name || qsTr("Unnamed profile")
                            exeName: profileDelegate.modelData.exeName || ""
                            selectedProfile: Boolean(profileDelegate.modelData.selected)
                            activeProfile: Boolean(profileDelegate.modelData.active)
                            defaultProfile: Boolean(profileDelegate.modelData.isDefault)
                            onClicked: window.backendCall("selectProfile", profileDelegate.modelData.id)
                        }

                        ScrollIndicator.vertical: ScrollIndicator {}
                    }

                    PrimaryButton {
                        Layout.fillWidth: true
                        text: qsTr("+  New profile")
                        secondary: true
                        accessibleDescription: qsTr("Create a new game-specific mapping")
                        onClicked: newProfileDialog.open()
                    }
                }
            }

            Item {
                id: mainPane
                Layout.fillWidth: true
                Layout.fillHeight: true

                ScrollView {
                    id: mainScroll
                    objectName: "mainScroll"
                    anchors.fill: parent
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    ColumnLayout {
                        id: mainColumn
                        objectName: "mainColumn"
                        width: mainScroll.availableWidth
                        spacing: 14

                        Item { Layout.preferredHeight: 4 }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    Layout.fillWidth: true
                                    text: window.selectedProfile.name || qsTr("Profile")
                                    color: Theme.text
                                    font.pixelSize: 24
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight

                                    ToolTip.visible: headerNameHover.hovered && truncated
                                    ToolTip.text: text
                                    ToolTip.delay: 650
                                    HoverHandler { id: headerNameHover }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: window.selectedProfile.isDefault
                                          ? qsTr("Fallback mapping used when no game profile is active")
                                          : ((window.selectedProfile.exeName || "").length > 0
                                             ? qsTr("Game-specific mapping")
                                             : qsTr("Game profile · no executable linked"))
                                    color: Theme.muted
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }

                            StatusPill { connected: window.deviceConnected }
                        }

                        Rectangle {
                            visible: window.legacyBlocked
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            implicitHeight: legacyText.implicitHeight + 26
                            radius: 12
                            color: Theme.warningSurface
                            border.color: "#765A2B"

                            Accessible.name: legacyText.text
                            Accessible.role: Accessible.AlertMessage

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 13
                                spacing: 10

                                Text {
                                    text: "!"
                                    color: Theme.warning
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                Text {
                                    id: legacyText
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    text: window.legacyState === "running"
                                          ? qsTr("The old GameSirAutoProfile service is running. Stop it before applying mappings so the two programs do not compete for the controller.")
                                          : qsTr("The state of the old GameSirAutoProfile service could not be verified. Applying mappings is blocked until it can be checked safely.")
                                    color: "#FFE0A6"
                                    font.pixelSize: 12
                                }
                            }
                        }

                        Rectangle {
                            visible: window.profileConflict.length > 0
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            implicitHeight: conflictText.implicitHeight + 26
                            radius: 12
                            color: Theme.warningSurface
                            border.color: "#765A2B"

                            Accessible.name: conflictText.text
                            Accessible.role: Accessible.AlertMessage

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 13
                                spacing: 10

                                Text {
                                    text: "!"
                                    color: Theme.warning
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                Text {
                                    id: conflictText
                                    Layout.fillWidth: true
                                    text: window.profileConflict
                                    color: "#FFE0A6"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        Rectangle {
                            visible: window.lastError.length > 0
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            implicitHeight: errorRow.implicitHeight + 24
                            radius: 12
                            color: Theme.dangerSurface
                            border.color: "#71323D"

                            Accessible.name: qsTr("Error: %1").arg(window.lastError)
                            Accessible.role: Accessible.AlertMessage

                            RowLayout {
                                id: errorRow
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.margins: 12
                                spacing: 10

                                Text {
                                    text: "×"
                                    color: Theme.danger
                                    font.pixelSize: 19
                                    font.bold: true
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: window.lastError
                                    color: "#FFD7DC"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }

                                PrimaryButton {
                                    visible: window.controller
                                             && typeof window.controller.clearLastError === "function"
                                    text: qsTr("Dismiss")
                                    secondary: true
                                    accessibleDescription: qsTr("Dismiss this error message")
                                    onClicked: window.backendCall("clearLastError")
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            implicitHeight: profileDetails.implicitHeight + 32
                            radius: Theme.radius
                            color: Theme.surface
                            border.color: Theme.borderSoft

                            ColumnLayout {
                                id: profileDetails
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 16
                                spacing: 12

                                Text {
                                    text: qsTr("PROFILE")
                                    color: Theme.muted
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.letterSpacing: 1.2
                                }

                                TextField {
                                    id: profileNameField
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 42
                                    enabled: !Boolean(window.selectedProfile.isDefault)
                                    text: window.selectedProfile.name || ""
                                    placeholderText: qsTr("Profile name")
                                    color: Theme.text
                                    selectByMouse: true
                                    leftPadding: 12
                                    rightPadding: 12
                                    focusPolicy: Qt.StrongFocus

                                    Accessible.name: qsTr("Profile name")
                                    Accessible.description: enabled
                                                            ? qsTr("Rename the selected profile")
                                                            : qsTr("The fallback profile cannot be renamed")

                                    background: Rectangle {
                                        radius: 10
                                        color: Theme.bg
                                        border.width: profileNameField.activeFocus ? 2 : 1
                                        border.color: profileNameField.activeFocus
                                                      ? Theme.focus : Theme.border
                                    }

                                    onEditingFinished: {
                                        if (enabled) {
                                            var renamed = window.backendCall(
                                                        "renameProfile",
                                                        window.selectedId,
                                                        text)
                                            if (renamed !== true)
                                                text = window.selectedProfile.name || ""
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    TextField {
                                        id: exeField
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 42
                                        readOnly: true
                                        text: window.selectedProfile.isDefault
                                              ? qsTr("No executable · fallback profile")
                                              : ((window.selectedProfile.exePath || "").length > 0
                                                 ? window.selectedProfile.exePath
                                                 : ((window.selectedProfile.exeName || "").length > 0
                                                    ? window.selectedProfile.exeName
                                                    : qsTr("No game executable linked")))
                                        color: (window.selectedProfile.exeName || "").length > 0
                                               ? Theme.text : Theme.muted
                                        selectByMouse: true
                                        leftPadding: 12
                                        rightPadding: 12
                                        focusPolicy: Qt.StrongFocus

                                        Accessible.name: qsTr("Linked game executable")
                                        Accessible.description: text

                                        ToolTip.visible: hovered && contentWidth > width - leftPadding - rightPadding
                                        ToolTip.text: text
                                        ToolTip.delay: 650

                                        background: Rectangle {
                                            radius: 10
                                            color: Theme.bg
                                            border.width: exeField.activeFocus ? 2 : 1
                                            border.color: exeField.activeFocus ? Theme.focus : Theme.border
                                        }
                                    }

                                    PrimaryButton {
                                        visible: !Boolean(window.selectedProfile.isDefault)
                                        text: qsTr("Browse")
                                        secondary: true
                                        accessibleDescription: qsTr("Choose the game executable for this profile")
                                        onClicked: window.backendCall("chooseExecutable", window.selectedId)
                                    }

                                    PrimaryButton {
                                        visible: !Boolean(window.selectedProfile.isDefault)
                                                 && ((window.selectedProfile.exeName || "").length > 0
                                                     || (window.selectedProfile.exePath || "").length > 0)
                                        text: qsTr("Unlink")
                                        secondary: true
                                        accessibleDescription: qsTr("Remove the executable link without deleting the profile")
                                        onClicked: unlinkDialog.open()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            implicitHeight: mappingsContent.implicitHeight + 36
                            radius: Theme.radius
                            color: Theme.surface
                            border.color: Theme.borderSoft

                            ColumnLayout {
                                id: mappingsContent
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 18
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Text {
                                            Layout.fillWidth: true
                                            text: qsTr("BUTTON MAPPING")
                                            color: Theme.text
                                            font.pixelSize: 15
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: qsTr("Mappings are written directly to the Super Nova HID interface.")
                                            color: Theme.muted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                        }
                                    }

                                    Rectangle {
                                        implicitWidth: stateLabel.implicitWidth + 26
                                        implicitHeight: 32
                                        radius: 16
                                        color: window.mappingState === "active"
                                               ? Theme.successSurface
                                               : (window.mappingState === "error"
                                                  ? Theme.dangerSurface : Theme.warningSurface)
                                        border.color: window.mappingState === "active"
                                                      ? "#1D5947"
                                                      : (window.mappingState === "error"
                                                         ? "#71323D" : "#765A2B")

                                        Accessible.name: stateLabel.text
                                        Accessible.description: stateDescription.text
                                        Accessible.role: Accessible.StaticText

                                        Text {
                                            id: stateLabel
                                            anchors.centerIn: parent
                                            text: window.mappingState === "active"
                                                  ? qsTr("ACTIVE")
                                                  : (window.mappingState === "error"
                                                     ? qsTr("ERROR") : qsTr("PENDING"))
                                            color: window.mappingState === "active"
                                                   ? Theme.success
                                                   : (window.mappingState === "error"
                                                      ? Theme.danger : Theme.warning)
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }
                                }

                                Text {
                                    id: stateDescription
                                    Layout.fillWidth: true
                                    text: window.mappingState === "active"
                                          ? qsTr("The driver accepted all mapping reports on this connection.")
                                          : (window.mappingState === "error"
                                             ? qsTr("The last write failed. Review the error above before trying again.")
                                             : (window.applyInProgress
                                                ? qsTr("Applying this profile to the controller…")
                                                : (!window.deviceConnected
                                                   ? qsTr("Connect the controller to apply this profile.")
                                                   : qsTr("These mapping changes have not been sent successfully on this connection."))))
                                    color: window.mappingState === "error" ? Theme.danger : Theme.muted
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 1
                                    color: Theme.borderSoft
                                }

                                MappingRow {
                                    id: rbMappingRow
                                    Layout.fillWidth: true
                                    sourceName: "RB"
                                    destinationKey: window.selectedProfile.rb || "gp:04"
                                    destinationModel: window.backendValue("destinationCatalog", [])
                                    onMappingChanged: function(key) {
                                        if (window.backendCall("setMapping", window.selectedId, "RB", key) !== true)
                                            rbMappingRow.syncIndex()
                                    }
                                }

                                MappingRow {
                                    id: l4MappingRow
                                    Layout.fillWidth: true
                                    sourceName: "L4"
                                    destinationKey: window.selectedProfile.l4 || "gp:24"
                                    destinationModel: window.backendValue("destinationCatalog", [])
                                    onMappingChanged: function(key) {
                                        if (window.backendCall("setMapping", window.selectedId, "L4", key) !== true)
                                            l4MappingRow.syncIndex()
                                    }
                                }

                                MappingRow {
                                    id: r4MappingRow
                                    Layout.fillWidth: true
                                    sourceName: "R4"
                                    destinationKey: window.selectedProfile.r4 || "gp:25"
                                    destinationModel: window.backendValue("destinationCatalog", [])
                                    onMappingChanged: function(key) {
                                        if (window.backendCall("setMapping", window.selectedId, "R4", key) !== true)
                                            r4MappingRow.syncIndex()
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: hidHelp.implicitHeight + 20
                                    radius: 10
                                    color: Theme.infoSurface
                                    border.color: "#24546A"

                                    Text {
                                        id: hidHelp
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.margins: 10
                                        text: qsTr("Keyboard choices are USB HID usage positions. Their labels follow the US layout, so the character produced by ABNT2 or another keyboard layout can differ.")
                                        color: "#BFEAFF"
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                    }

                                    Accessible.name: hidHelp.text
                                    Accessible.role: Accessible.Note
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    PrimaryButton {
                                        visible: !Boolean(window.selectedProfile.isDefault)
                                        text: qsTr("Duplicate")
                                        secondary: true
                                        accessibleDescription: qsTr("Create a copy of this profile")
                                        onClicked: window.backendCall("duplicateProfile", window.selectedId)
                                    }

                                    PrimaryButton {
                                        visible: !Boolean(window.selectedProfile.isDefault)
                                        text: qsTr("Delete")
                                        secondary: true
                                        danger: true
                                        accessibleDescription: qsTr("Permanently delete this profile")
                                        onClicked: deleteDialog.open()
                                    }

                                    Item { Layout.fillWidth: true }

                                    PrimaryButton {
                                        text: window.applyInProgress ? qsTr("Applying…") : qsTr("Apply profile")
                                        enabled: window.deviceConnected && !window.legacyBlocked
                                                 && !window.applyInProgress && window.selectedId.length > 0
                                        accessibleDescription: enabled
                                                               ? qsTr("Write this profile to the connected controller")
                                                               : qsTr("Connect the controller and resolve service warnings before applying")
                                        onClicked: window.backendCall("applyProfile", window.selectedId)
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            implicitHeight: 62
                            radius: 14
                            color: Theme.surface
                            border.color: Theme.borderSoft

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16
                                spacing: 12

                                ToggleSwitch {
                                    checked: Boolean(window.backendValue("autoSwitchEnabled", false))
                                    accessibleName: qsTr("Automatic profile switching")
                                    accessibleDescription: qsTr("Watch running games and apply their linked profiles")
                                    onToggled: window.backendCall("setAutoSwitchEnabled", checked)
                                }

                                ColumnLayout {
                                    spacing: 0

                                    Text {
                                        text: qsTr("AUTO SWITCH")
                                        color: Theme.text
                                        font.pixelSize: 11
                                        font.bold: true
                                    }

                                    Text {
                                        text: Boolean(window.backendValue("autoSwitchEnabled", false))
                                              ? qsTr("Watching game processes") : qsTr("Paused")
                                        color: Theme.muted
                                        font.pixelSize: 10
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: qsTr("Active:")
                                    color: Theme.muted
                                    font.pixelSize: 11
                                }

                                Text {
                                    Layout.maximumWidth: Math.max(120, mainPane.width * 0.28)
                                    text: window.backendValue("activeProfileName", qsTr("None"))
                                    color: Theme.accent
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight

                                    ToolTip.visible: footerNameHover.hovered && truncated
                                    ToolTip.text: text
                                    ToolTip.delay: 650
                                    HoverHandler { id: footerNameHover }
                                }
                            }
                        }

                        Item { Layout.preferredHeight: 6 }
                    }
                }
            }
        }
    }

    Drawer {
        id: settingsDrawer
        edge: Qt.RightEdge
        width: Math.min(420, Math.max(350, window.width * 0.45))
        height: window.height
        modal: true
        dim: true

        onOpened: settingsCloseButton.forceActiveFocus()

        background: Rectangle {
            color: Theme.sidebar
            border.color: Theme.border
        }

        ScrollView {
            anchors.fill: parent
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            Accessible.name: qsTr("Settings")
            Accessible.role: Accessible.Dialog

            ColumnLayout {
                width: parent.width
                spacing: 16

                Item { Layout.preferredHeight: 6 }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Settings")
                        color: Theme.text
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                    }

                    Button {
                        id: settingsCloseButton
                        Layout.preferredWidth: 42
                        Layout.preferredHeight: 42
                        text: "×"
                        focusPolicy: Qt.StrongFocus

                        Accessible.name: qsTr("Close settings")
                        Accessible.role: Accessible.Button

                        background: Rectangle {
                            radius: 10
                            color: settingsCloseButton.hovered ? Theme.surfaceHover : "transparent"
                            border.width: settingsCloseButton.activeFocus ? 2 : 0
                            border.color: Theme.focus
                        }

                        contentItem: Text {
                            text: settingsCloseButton.text
                            color: Theme.muted
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 22
                        }

                        onClicked: settingsDrawer.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22
                    Layout.preferredHeight: 1
                    color: Theme.borderSoft
                }

                Repeater {
                    model: [
                        {
                            title: qsTr("Automatic profile switching"),
                            subtitle: qsTr("Detect linked game executables"),
                            value: Boolean(window.backendValue("autoSwitchEnabled", false)),
                            kind: "auto"
                        },
                        {
                            title: qsTr("Start with Windows"),
                            subtitle: qsTr("Launch hidden after sign-in"),
                            value: Boolean(window.backendValue("startupEnabled", false)),
                            kind: "startup"
                        },
                        {
                            title: qsTr("Minimize to tray"),
                            subtitle: qsTr("Closing the window keeps Nova Profiles running"),
                            value: Boolean(window.backendValue("minimizeToTray", false)),
                            kind: "tray"
                        },
                        {
                            title: qsTr("Restore Default on exit"),
                            subtitle: qsTr("Return RB, L4 and R4 to their base mappings"),
                            value: Boolean(window.backendValue("restoreDefaultOnExit", false)),
                            kind: "restore"
                        }
                    ]

                    delegate: RowLayout {
                        id: settingRow
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.leftMargin: 22
                        Layout.rightMargin: 22
                        spacing: 12

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                Layout.fillWidth: true
                                text: settingRow.modelData.title
                                color: Theme.text
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                Layout.fillWidth: true
                                text: settingRow.modelData.subtitle
                                color: Theme.muted
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                        }

                        ToggleSwitch {
                            checked: Boolean(settingRow.modelData.value)
                            accessibleName: settingRow.modelData.title
                            accessibleDescription: settingRow.modelData.subtitle
                            onToggled: {
                                if (settingRow.modelData.kind === "auto")
                                    window.backendCall("setAutoSwitchEnabled", checked)
                                else if (settingRow.modelData.kind === "startup")
                                    window.backendCall("setStartupEnabled", checked)
                                else if (settingRow.modelData.kind === "tray")
                                    window.backendCall("setMinimizeToTray", checked)
                                else if (settingRow.modelData.kind === "restore")
                                    window.backendCall("setRestoreDefaultOnExit", checked)
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22
                    Layout.preferredHeight: 1
                    color: Theme.borderSoft
                }

                Text {
                    Layout.leftMargin: 22
                    text: qsTr("DATA")
                    color: Theme.muted
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 1.2
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22

                    PrimaryButton {
                        Layout.fillWidth: true
                        text: qsTr("Import")
                        secondary: true
                        accessibleDescription: qsTr("Choose a profile backup and review it before replacing data")
                        onClicked: window.backendCall("importProfiles")
                    }

                    PrimaryButton {
                        Layout.fillWidth: true
                        text: qsTr("Export")
                        secondary: true
                        accessibleDescription: qsTr("Save all profiles to a JSON backup")
                        onClicked: window.backendCall("exportProfiles")
                    }
                }

                PrimaryButton {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22
                    text: qsTr("Open data folder")
                    secondary: true
                    accessibleDescription: qsTr("Open the folder containing profiles and logs")
                    onClicked: window.backendCall("openDataFolder")
                }

                PrimaryButton {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22
                    text: qsTr("Open log")
                    secondary: true
                    accessibleDescription: qsTr("Open the Nova Profiles diagnostic log")
                    onClicked: window.backendCall("openLogFile")
                }

                Item { Layout.fillHeight: true; Layout.minimumHeight: 18 }

                Text {
                    Layout.fillWidth: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22
                    Layout.bottomMargin: 18
                    text: qsTr("Nova Profiles v%1\nSuper Nova · VID 3537 / PID 103E · XInput dongle")
                          .arg(window.backendValue("appVersion", ""))
                    color: Theme.muted2
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    Dialog {
        id: newProfileDialog
        anchors.centerIn: Overlay.overlay
        width: Math.min(430, window.width - 48)
        modal: true
        title: ""
        closePolicy: Popup.CloseOnEscape

        onOpened: newProfileName.forceActiveFocus()
        onRejected: newProfileName.text = ""

        background: Rectangle {
            radius: 16
            color: Theme.surface
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 14

            Accessible.name: qsTr("New profile")
            Accessible.role: Accessible.Dialog

            Text {
                text: qsTr("New profile")
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("Create a game profile, then link its executable.")
                color: Theme.muted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }

            TextField {
                id: newProfileName
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                placeholderText: qsTr("Profile name")
                color: Theme.text
                leftPadding: 12
                rightPadding: 12

                Accessible.name: qsTr("Profile name")
                Accessible.description: qsTr("Enter a name for the new profile")

                background: Rectangle {
                    radius: 10
                    color: Theme.bg
                    border.width: newProfileName.activeFocus ? 2 : 1
                    border.color: newProfileName.activeFocus ? Theme.focus : Theme.border
                }

                Keys.onReturnPressed: function(event) {
                    if (newProfileName.text.trim().length > 0) {
                        if (window.backendCall("createProfile", newProfileName.text) === true) {
                            newProfileName.text = ""
                            newProfileDialog.close()
                        }
                    }
                    event.accepted = true
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }

                PrimaryButton {
                    text: qsTr("Cancel")
                    secondary: true
                    onClicked: {
                        newProfileName.text = ""
                        newProfileDialog.reject()
                    }
                }

                PrimaryButton {
                    text: qsTr("Create")
                    enabled: newProfileName.text.trim().length > 0
                    accessibleDescription: qsTr("Create the profile")
                    onClicked: {
                        if (window.backendCall("createProfile", newProfileName.text) === true) {
                            newProfileName.text = ""
                            newProfileDialog.close()
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteDialog
        anchors.centerIn: Overlay.overlay
        width: Math.min(420, window.width - 48)
        modal: true
        closePolicy: Popup.CloseOnEscape

        onOpened: deleteCancelButton.forceActiveFocus()

        background: Rectangle {
            radius: 16
            color: Theme.surface
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 14

            Accessible.name: qsTr("Delete profile")
            Accessible.role: Accessible.Dialog

            Text {
                text: qsTr("Delete profile?")
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("This permanently removes “%1”.").arg(window.selectedProfile.name || "")
                color: Theme.muted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }

                PrimaryButton {
                    id: deleteCancelButton
                    text: qsTr("Cancel")
                    secondary: true
                    onClicked: deleteDialog.reject()
                }

                PrimaryButton {
                    text: qsTr("Delete")
                    danger: true
                    accessibleDescription: qsTr("Permanently delete the selected profile")
                    onClicked: {
                        if (window.backendCall("deleteProfile", window.selectedId) === true)
                            deleteDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: unlinkDialog
        anchors.centerIn: Overlay.overlay
        width: Math.min(440, window.width - 48)
        modal: true
        closePolicy: Popup.CloseOnEscape

        onOpened: unlinkCancelButton.forceActiveFocus()

        background: Rectangle {
            radius: 16
            color: Theme.surface
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 14

            Accessible.name: qsTr("Unlink executable")
            Accessible.role: Accessible.Dialog

            Text {
                text: qsTr("Unlink executable?")
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("The profile and its mappings will be kept, but it will no longer activate automatically for %1.")
                      .arg(window.selectedProfile.exeName || qsTr("this game"))
                color: Theme.muted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }

                PrimaryButton {
                    id: unlinkCancelButton
                    text: qsTr("Cancel")
                    secondary: true
                    onClicked: unlinkDialog.reject()
                }

                PrimaryButton {
                    text: qsTr("Unlink")
                    secondary: true
                    danger: true
                    accessibleDescription: qsTr("Remove the executable link")
                    onClicked: {
                        if (window.backendCall("clearExecutable", window.selectedId) === true)
                            unlinkDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: importDialog
        anchors.centerIn: Overlay.overlay
        width: Math.min(520, window.width - 48)
        modal: true
        closePolicy: Popup.CloseOnEscape

        onOpened: importCancelButton.forceActiveFocus()
        onRejected: window.cancelImportPreview()

        background: Rectangle {
            radius: 16
            color: Theme.surface
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 14

            Accessible.name: qsTr("Review profile import")
            Accessible.role: Accessible.Dialog

            Text {
                text: qsTr("Review profile import")
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("File: %1").arg(window.importPreview.fileName || "")
                color: Theme.text
                font.pixelSize: 12
                elide: Text.ElideMiddle
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: importSummary.implicitHeight + 24
                radius: 10
                color: Theme.infoSurface
                border.color: "#24546A"

                Text {
                    id: importSummary
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: 12
                    text: qsTr("%1 profiles · %2 new · %3 replaced · %4 removed")
                          .arg(window.importPreview.profileCount || 0)
                          .arg(window.importPreview.newCount || 0)
                          .arg(window.importPreview.replacedCount || 0)
                          .arg(window.importPreview.removedCount || 0)
                    color: "#BFEAFF"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }

            Text {
                visible: window.importNamesText().length > 0
                Layout.fillWidth: true
                text: window.importNamesText()
                color: Theme.muted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                maximumLineCount: 4
                elide: Text.ElideRight
            }

            Text {
                visible: Number(window.importPreview.removedCount || 0) > 0
                Layout.fillWidth: true
                text: qsTr("This import replaces the entire catalog and removes %1 existing profiles: %2")
                      .arg(window.importPreview.removedCount || 0)
                      .arg(window.removedImportNamesText())
                color: Theme.danger
                font.pixelSize: 12
                font.weight: Font.DemiBold
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                text: Boolean(window.importPreview.backupWillBeCreated)
                      ? qsTr("Your current profiles will be backed up before the import.")
                      : qsTr("Importing replaces the entire profile catalog. Export a backup first if needed.")
                color: Boolean(window.importPreview.backupWillBeCreated)
                       ? Theme.success : Theme.warning
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }

                PrimaryButton {
                    id: importCancelButton
                    text: qsTr("Cancel")
                    secondary: true
                    onClicked: importDialog.reject()
                }

                PrimaryButton {
                    text: qsTr("Import profiles")
                    accessibleDescription: qsTr("Confirm and apply the reviewed import")
                    onClicked: {
                        var imported = window.backendCall("confirmImportProfiles")
                        if (imported === true)
                            importDialog.close()
                    }
                }
            }
        }
    }

    Rectangle {
        id: toastBox
        objectName: "toastBox"
        visible: false
        z: 1000
        width: Math.min(500, Math.max(300, toastText.implicitWidth + 78))
        implicitHeight: Math.max(52, toastText.implicitHeight + 24)
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 22
        anchors.bottomMargin: 22
        radius: 12
        color: "#16212C"
        border.color: window.toastPersistent ? Theme.danger : Theme.border

        Accessible.name: window.toastMessage
        Accessible.description: window.toastPersistent
                                ? qsTr("This notification remains until dismissed")
                                : qsTr("Notification")
        Accessible.role: Accessible.AlertMessage

        HoverHandler { id: toastHover }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 6
            spacing: 8

            Text {
                id: toastText
                Layout.fillWidth: true
                text: window.toastMessage
                color: Theme.text
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignLeft
            }

            Button {
                id: toastCloseButton
                Layout.preferredWidth: 42
                Layout.preferredHeight: 42
                text: "×"
                focusPolicy: Qt.StrongFocus

                Accessible.name: qsTr("Dismiss notification")
                Accessible.role: Accessible.Button

                background: Rectangle {
                    radius: 9
                    color: toastCloseButton.hovered ? Theme.surfaceHover : "transparent"
                    border.width: toastCloseButton.activeFocus ? 2 : 0
                    border.color: Theme.focus
                }

                contentItem: Text {
                    text: toastCloseButton.text
                    color: Theme.muted
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 20
                }

                onClicked: window.hideToast()
            }
        }

        Timer {
            id: toastTimer
            objectName: "toastTimer"
            interval: 8000
            running: toastBox.visible && !window.toastPersistent && !toastHover.hovered
            onTriggered: window.hideToast()
        }
    }
}
