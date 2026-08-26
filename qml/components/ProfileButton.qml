
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

    implicitHeight: 64
    leftPadding: 14
    rightPadding: 12

    background: Rectangle {
        radius: 12
        color: control.selectedProfile
               ? Theme.surfaceHover
               : (control.hovered ? "#121C27" : "transparent")
        border.width: control.selectedProfile ? 1 : 0
        border.color: control.selectedProfile ? Theme.border : "transparent"
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
                Layout.fillWidth: true
                text: control.profileName
                color: Theme.text
                font.pixelSize: 14
                font.weight: control.selectedProfile ? Font.DemiBold : Font.Medium
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: control.exeName.length > 0 ? control.exeName : "Base profile"
                color: Theme.muted
                font.pixelSize: 11
                elide: Text.ElideMiddle
            }
        }
    }
}
