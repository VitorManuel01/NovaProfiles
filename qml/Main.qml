
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "components"
import "Theme.js" as Theme

ApplicationWindow {
    id: window
    width: 1120
    height: 740
    minimumWidth: 900
    minimumHeight: 620
    visible: false
    title: "Nova Profiles"
    color: Theme.bg

    property string toastMessage: ""

    function showToast(message) {
        toastMessage = message
        toastBox.visible = true
        toastTimer.restart()
    }

    onClosing: function(close) {
        close.accepted = false
        if (app.minimizeToTray && app.trayAvailable) {
            window.hide()
        } else {
            app.quitApplication()
        }
    }

    Connections {
        target: app
        function onToast(message) { window.showToast(message) }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.bg

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // Sidebar
            Rectangle {
                Layout.preferredWidth: 284
                Layout.fillHeight: true
                color: Theme.sidebar
                border.color: Theme.borderSoft

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Rectangle {
                            width: 38
                            height: 38
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
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Text {
                                text: "NOVA PROFILES"
                                color: Theme.text
                                font.pixelSize: 15
                                font.bold: true
                                font.letterSpacing: 0.6
                            }
                            Text {
                                text: "Super Nova Auto Mapper"
                                color: Theme.muted
                                font.pixelSize: 10
                            }
                        }

                        Button {
                            id: settingsButton
                            width: 36
                            height: 36
                            text: "⚙"
                            background: Rectangle {
                                radius: 10
                                color: settingsButton.hovered ? Theme.surfaceHover : "transparent"
                            }
                            contentItem: Text {
                                text: settingsButton.text
                                color: Theme.muted
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.pixelSize: 17
                            }
                            onClicked: settingsDrawer.open()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSoft
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "PROFILES"
                            color: Theme.muted
                            font.pixelSize: 10
                            font.bold: true
                                font.letterSpacing: 1.2
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: app.profiles.length
                            color: Theme.muted2
                            font.pixelSize: 11
                        }
                    }

                    ListView {
                        id: profileList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 6
                        clip: true
                        model: app.profiles

                        delegate: ProfileButton {
                            width: profileList.width
                            profileName: modelData.name
                            exeName: modelData.exeName
                            selectedProfile: modelData.selected
                            activeProfile: modelData.active
                            onClicked: app.selectProfile(modelData.id)
                        }

                        ScrollIndicator.vertical: ScrollIndicator {}
                    }

                    PrimaryButton {
                        Layout.fillWidth: true
                        text: "+  New profile"
                        secondary: true
                        onClicked: newProfileDialog.open()
                    }
                }
            }

            // Main content
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text {
                                text: app.selectedProfile.name || "Profile"
                                color: Theme.text
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: app.selectedProfile.isDefault
                                      ? "Base mapping used when no game profile is active"
                                      : "Per-game mapping"
                                color: Theme.muted
                                font.pixelSize: 12
                            }
                        }

                        StatusPill {
                            connected: app.deviceConnected
                        }
                    }

                    Rectangle {
                        visible: app.legacyServiceRunning
                        Layout.fillWidth: true
                        implicitHeight: legacyText.implicitHeight + 26
                        radius: 12
                        color: "#2C2112"
                        border.color: "#5D4621"

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
                                text: "The old NSSM service “GameSirAutoProfile” is running. Stop it before using this app so both programs do not compete for the HID interface."
                                color: "#F2D39A"
                                font.pixelSize: 12
                            }
                        }
                    }

                    // Profile details card
                    Rectangle {
                        Layout.fillWidth: true
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
                                text: "PROFILE"
                                color: Theme.muted
                                font.pixelSize: 10
                                font.bold: true
                                font.letterSpacing: 1.2
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                TextField {
                                    id: profileNameField
                                    Layout.preferredWidth: 280
                                    enabled: !app.selectedProfile.isDefault
                                    text: app.selectedProfile.name || ""
                                    placeholderText: "Profile name"
                                    color: Theme.text
                                    selectByMouse: true
                                    leftPadding: 12
                                    rightPadding: 12

                                    background: Rectangle {
                                        radius: 10
                                        color: Theme.bg
                                        border.color: profileNameField.activeFocus
                                                      ? Theme.accent : Theme.border
                                    }

                                    onEditingFinished: {
                                        if (enabled)
                                            app.renameProfile(app.selectedProfile.id, text)
                                    }
                                }

                                TextField {
                                    id: exeField
                                    Layout.fillWidth: true
                                    readOnly: true
                                    text: app.selectedProfile.isDefault
                                          ? "No executable — fallback profile"
                                          : (app.selectedProfile.exePath.length > 0
                                             ? app.selectedProfile.exePath
                                             : (app.selectedProfile.exeName.length > 0
                                                ? app.selectedProfile.exeName
                                                : "No game executable selected"))
                                    color: app.selectedProfile.exeName.length > 0
                                           ? Theme.text : Theme.muted
                                    selectByMouse: true
                                    leftPadding: 12
                                    rightPadding: 12

                                    background: Rectangle {
                                        radius: 10
                                        color: Theme.bg
                                        border.color: Theme.border
                                    }
                                }

                                PrimaryButton {
                                    visible: !app.selectedProfile.isDefault
                                    text: "Browse"
                                    secondary: true
                                    onClicked: app.chooseExecutable(app.selectedProfile.id)
                                }
                            }
                        }
                    }

                    // Mappings card
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radius
                        color: Theme.surface
                        border.color: Theme.borderSoft

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text {
                                        text: "BUTTON MAPPING"
                                        color: Theme.text
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                    }
                                    Text {
                                        text: "Mappings are written directly to the Super Nova HID interface."
                                        color: Theme.muted
                                        font.pixelSize: 11
                                    }
                                }

                                Rectangle {
                                    implicitWidth: activeLabel.implicitWidth + 24
                                    implicitHeight: 30
                                    radius: 15
                                    color: app.activeProfileId === app.selectedProfile.id
                                           ? "#102B24" : Theme.surface2
                                    Text {
                                        id: activeLabel
                                        anchors.centerIn: parent
                                        text: app.activeProfileId === app.selectedProfile.id
                                              ? "ACTIVE" : "INACTIVE"
                                        color: app.activeProfileId === app.selectedProfile.id
                                               ? Theme.success : Theme.muted
                                        font.pixelSize: 10
                                        font.bold: true
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: Theme.borderSoft
                            }

                            MappingRow {
                                Layout.fillWidth: true
                                sourceName: "RB"
                                destinationKey: app.selectedProfile.rb || "gp:04"
                                destinationModel: app.destinationCatalog
                                onMappingChanged: function(key) {
                                    app.setMapping(app.selectedProfile.id, "RB", key)
                                }
                            }

                            MappingRow {
                                Layout.fillWidth: true
                                sourceName: "L4"
                                destinationKey: app.selectedProfile.l4 || "gp:24"
                                destinationModel: app.destinationCatalog
                                onMappingChanged: function(key) {
                                    app.setMapping(app.selectedProfile.id, "L4", key)
                                }
                            }

                            MappingRow {
                                Layout.fillWidth: true
                                sourceName: "R4"
                                destinationKey: app.selectedProfile.r4 || "gp:25"
                                destinationModel: app.destinationCatalog
                                onMappingChanged: function(key) {
                                    app.setMapping(app.selectedProfile.id, "R4", key)
                                }
                            }

                            Item { Layout.fillHeight: true }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                PrimaryButton {
                                    visible: !app.selectedProfile.isDefault
                                    text: "Duplicate"
                                    secondary: true
                                    onClicked: app.duplicateProfile(app.selectedProfile.id)
                                }

                                PrimaryButton {
                                    visible: !app.selectedProfile.isDefault
                                    text: "Delete"
                                    secondary: true
                                    danger: true
                                    onClicked: deleteDialog.open()
                                }

                                Item { Layout.fillWidth: true }

                                PrimaryButton {
                                    text: "Apply profile"
                                    enabled: app.deviceConnected && !app.legacyServiceRunning
                                    onClicked: {
                                        if (!app.applyProfile(app.selectedProfile.id))
                                            window.showToast("Could not apply profile")
                                    }
                                }
                            }
                        }
                    }

                    // Footer
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 58
                        radius: 14
                        color: Theme.surface
                        border.color: Theme.borderSoft

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 12

                            ToggleSwitch {
                                checked: app.autoSwitchEnabled
                                onToggled: app.setAutoSwitchEnabled(checked)
                            }

                            ColumnLayout {
                                spacing: 0
                                Text {
                                    text: "AUTO SWITCH"
                                    color: Theme.text
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                Text {
                                    text: app.autoSwitchEnabled
                                          ? "Watching game processes"
                                          : "Paused"
                                    color: Theme.muted
                                    font.pixelSize: 10
                                }
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: "Active:"
                                color: Theme.muted
                                font.pixelSize: 11
                            }
                            Text {
                                text: app.activeProfileName
                                color: Theme.accent
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                        }
                    }
                }
            }
        }
    }

    // Settings drawer
    Drawer {
        id: settingsDrawer
        edge: Qt.RightEdge
        width: Math.min(390, window.width * 0.42)
        height: window.height
        modal: true
        dim: true

        background: Rectangle {
            color: Theme.sidebar
            border.color: Theme.border
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Settings"
                    color: Theme.text
                    font.pixelSize: 22
                    font.weight: Font.DemiBold
                }
                Button {
                    text: "×"
                    width: 38
                    height: 38
                    background: Rectangle {
                        radius: 10
                        color: parent.hovered ? Theme.surfaceHover : "transparent"
                    }
                    contentItem: Text {
                        text: "×"
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
                height: 1
                color: Theme.borderSoft
            }

            Repeater {
                model: [
                    {
                        title: "Automatic profile switching",
                        subtitle: "Detect linked game executables",
                        value: app.autoSwitchEnabled,
                        kind: "auto"
                    },
                    {
                        title: "Start with Windows",
                        subtitle: "Launch hidden after sign-in",
                        value: app.startupEnabled,
                        kind: "startup"
                    },
                    {
                        title: "Minimize to tray",
                        subtitle: "Closing the window keeps Nova Profiles running",
                        value: app.minimizeToTray,
                        kind: "tray"
                    },
                    {
                        title: "Restore Default on exit",
                        subtitle: "Return RB/L4/R4 to their base mappings",
                        value: app.restoreDefaultOnExit,
                        kind: "restore"
                    }
                ]

                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: modelData.title
                            color: Theme.text
                            font.pixelSize: 13
                            font.weight: Font.Medium
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.subtitle
                            color: Theme.muted
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                    }

                    ToggleSwitch {
                        checked: modelData.value
                        onToggled: {
                            if (modelData.kind === "auto")
                                app.setAutoSwitchEnabled(checked)
                            else if (modelData.kind === "startup")
                                app.setStartupEnabled(checked)
                            else if (modelData.kind === "tray")
                                app.setMinimizeToTray(checked)
                            else if (modelData.kind === "restore")
                                app.setRestoreDefaultOnExit(checked)
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderSoft
            }

            Text {
                text: "DATA"
                color: Theme.muted
                font.pixelSize: 10
                font.bold: true
                                font.letterSpacing: 1.2
            }

            RowLayout {
                Layout.fillWidth: true
                PrimaryButton {
                    Layout.fillWidth: true
                    text: "Import"
                    secondary: true
                    onClicked: app.importProfiles()
                }
                PrimaryButton {
                    Layout.fillWidth: true
                    text: "Export"
                    secondary: true
                    onClicked: app.exportProfiles()
                }
            }

            PrimaryButton {
                Layout.fillWidth: true
                text: "Open data folder"
                secondary: true
                onClicked: app.openDataFolder()
            }

            PrimaryButton {
                Layout.fillWidth: true
                text: "Open log"
                secondary: true
                onClicked: app.openLogFile()
            }

            Item { Layout.fillHeight: true }

            Text {
                Layout.fillWidth: true
                text: "Nova Profiles v" + app.appVersion + "\nSuper Nova · VID 3537 / PID 103E · XInput dongle"
                color: Theme.muted2
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
        }
    }

    // New profile dialog
    Dialog {
        id: newProfileDialog
        anchors.centerIn: Overlay.overlay
        width: 430
        modal: true
        title: ""

        background: Rectangle {
            radius: 16
            color: Theme.surface
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 14

            Text {
                text: "New profile"
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }

            Text {
                text: "Create a game profile, then link its executable."
                color: Theme.muted
                font.pixelSize: 11
            }

            TextField {
                id: newProfileName
                Layout.fillWidth: true
                placeholderText: "Profile name"
                color: Theme.text
                leftPadding: 12
                background: Rectangle {
                    radius: 10
                    color: Theme.bg
                    border.color: newProfileName.activeFocus
                                  ? Theme.accent : Theme.border
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                PrimaryButton {
                    text: "Cancel"
                    secondary: true
                    onClicked: newProfileDialog.close()
                }
                PrimaryButton {
                    text: "Create"
                    enabled: newProfileName.text.trim().length > 0
                    onClicked: {
                        app.createProfile(newProfileName.text)
                        newProfileName.text = ""
                        newProfileDialog.close()
                    }
                }
            }
        }
    }

    // Delete confirmation
    Dialog {
        id: deleteDialog
        anchors.centerIn: Overlay.overlay
        width: 420
        modal: true

        background: Rectangle {
            radius: 16
            color: Theme.surface
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 14
            Text {
                text: "Delete profile?"
                color: Theme.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }
            Text {
                Layout.fillWidth: true
                text: "This removes “" + (app.selectedProfile.name || "") + "”."
                color: Theme.muted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                PrimaryButton {
                    text: "Cancel"
                    secondary: true
                    onClicked: deleteDialog.close()
                }
                PrimaryButton {
                    text: "Delete"
                    danger: true
                    onClicked: {
                        app.deleteProfile(app.selectedProfile.id)
                        deleteDialog.close()
                    }
                }
            }
        }
    }

    // Toast
    Rectangle {
        id: toastBox
        visible: false
        z: 1000
        width: Math.min(460, toastText.implicitWidth + 34)
        height: toastText.implicitHeight + 24
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 22
        anchors.bottomMargin: 22
        radius: 12
        color: "#16212C"
        border.color: Theme.border

        Text {
            id: toastText
            anchors.centerIn: parent
            width: parent.width - 28
            text: window.toastMessage
            color: Theme.text
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Timer {
            id: toastTimer
            interval: 3600
            onTriggered: toastBox.visible = false
        }
    }
}
