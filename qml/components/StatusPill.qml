
import QtQuick
import QtQuick.Layouts
import "../Theme.js" as Theme

Rectangle {
    id: root
    property bool connected: false
    implicitWidth: label.implicitWidth + 34
    implicitHeight: 30
    radius: 15
    color: connected ? Theme.successSurface : Theme.dangerSurface
    border.color: connected ? "#1D5947" : "#5A2931"

    Accessible.name: connected
                     ? qsTr("Super Nova connected")
                     : qsTr("Super Nova disconnected")
    Accessible.role: Accessible.StaticText

    RowLayout {
        anchors.centerIn: parent
        spacing: 7

        Rectangle {
            Layout.preferredWidth: 8
            Layout.preferredHeight: 8
            radius: 4
            color: root.connected ? Theme.success : Theme.danger
        }

        Text {
            id: label
            text: root.connected
                  ? qsTr("SUPER NOVA CONNECTED")
                  : qsTr("SUPER NOVA DISCONNECTED")
            color: root.connected ? Theme.success : Theme.danger
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
    }
}
