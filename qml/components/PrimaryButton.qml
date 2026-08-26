
import QtQuick
import QtQuick.Controls
import "../Theme.js" as Theme

Button {
    id: control
    property bool danger: false
    property bool secondary: false

    implicitHeight: 42
    leftPadding: 18
    rightPadding: 18

    contentItem: Text {
        text: control.text
        color: control.enabled
               ? (control.secondary ? Theme.text : "#071017")
               : Theme.muted2
        font.pixelSize: 14
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 10
        border.width: control.secondary ? 1 : 0
        border.color: control.danger ? Theme.danger : Theme.border
        color: {
            if (!control.enabled) return Theme.surface2
            if (control.secondary) return control.hovered ? Theme.surfaceHover : Theme.surface2
            if (control.danger) return control.hovered ? "#FF7D88" : Theme.danger
            return control.hovered ? "#68D1FF" : Theme.accent
        }
    }
}
