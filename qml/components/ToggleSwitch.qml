
import QtQuick
import QtQuick.Controls
import "../Theme.js" as Theme

Switch {
    id: control
    implicitWidth: 50
    implicitHeight: 28

    indicator: Rectangle {
        implicitWidth: 48
        implicitHeight: 26
        radius: 13
        color: control.checked ? Theme.accent : Theme.surfaceHover
        border.color: control.checked ? Theme.accent : Theme.border

        Rectangle {
            width: 20
            height: 20
            radius: 10
            y: 3
            x: control.checked ? parent.width - width - 3 : 3
            color: control.checked ? "#071017" : Theme.muted
            Behavior on x { NumberAnimation { duration: 130 } }
        }
    }

    contentItem: Item {}
}
