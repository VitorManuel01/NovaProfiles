
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Theme.js" as Theme

Button {
    id: control
    property string profileName: ""
    property string exeName: ""
    property bool selectedProfile: false
    property bool activeProfile: false
    property bool defaultProfile: false

    focusPolicy: Qt.StrongFocus
    Accessible.name: profileName
    Accessible.description: defaultProfile
                            ? qsTr("Fallback profile")
                            : (exeName.length > 0
                               ? qsTr("Linked to %1").arg(exeName)
                               : qsTr("No executable linked"))
    Accessible.role: Accessible.Button

    ToolTip.visible: hovered && (profileNameText.truncated || executableText.truncated)
    ToolTip.text: profileName + "\n" + executableText.text
    ToolTip.delay: 650

    Keys.onReturnPressed: function(event) {
        control.clicked()
        event.accepted = true
    }
    Keys.onEnterPressed: function(event) {
        control.clicked()
        event.accepted = true
    }

    implicitHeight: 64
    leftPadding: 14
    rightPadding: 12

    background: Rectangle {
        radius: 12
        color: control.selectedProfile
               ? Theme.surfaceHover
               : (control.hovered ? "#121C27" : "transparent")
        border.width: control.activeFocus ? 2 : (control.selectedProfile ? 1 : 0)
        border.color: control.activeFocus
                      ? Theme.focus
                      : (control.selectedProfile ? Theme.border : "transparent")
    }

    contentItem: RowLayout {
        spacing: 10

        Rectangle {
            Layout.preferredWidth: 8
            Layout.preferredHeight: 8
            radius: 4
            color: control.activeProfile ? Theme.success : Theme.muted2
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            Text {
                id: profileNameText
                Layout.fillWidth: true
                text: control.profileName
                color: Theme.text
                font.pixelSize: 14
                font.weight: control.selectedProfile ? Font.DemiBold : Font.Medium
                elide: Text.ElideRight
            }

            Text {
                id: executableText
                Layout.fillWidth: true
                text: control.defaultProfile
                      ? qsTr("Fallback profile")
                      : (control.exeName.length > 0
                         ? control.exeName
                         : qsTr("No executable linked"))
                color: Theme.muted
                font.pixelSize: 11
                elide: Text.ElideMiddle
            }
        }
    }
}
