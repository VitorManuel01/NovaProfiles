
import QtQuick
import QtQuick.Layouts
import "../Theme.js" as Theme

Rectangle {
    id: root
    property bool connected: false
    implicitWidth: label.implicitWidth + 34
    implicitHeight: 30
    radius: 15
    color: connected ? "#102B24" : "#29171B"
    border.color: connected ? "#1D5947" : "#5A2931"

    RowLayout {
        anchors.centerIn: parent
        spacing: 7

        Rectangle {
            width: 8
            height: 8
            radius: 4
            color: root.connected ? Theme.success : Theme.danger
        }

        Text {
            id: label
            text: root.connected ? "SUPER NOVA CONNECTED" : "SUPER NOVA DISCONNECTED"
            color: root.connected ? Theme.success : Theme.danger
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
    }
}
