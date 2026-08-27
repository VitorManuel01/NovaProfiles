
import QtQuick
import QtQuick.Controls
import "../Theme.js" as Theme

Switch {
    id: control
    property string accessibleName: ""
    property string accessibleDescription: ""
    implicitWidth: 50
    implicitHeight: 42
    focusPolicy: Qt.StrongFocus

    Accessible.name: accessibleName
    Accessible.description: accessibleDescription
    Accessible.role: Accessible.CheckBox
    Accessible.checked: checked

    ToolTip.visible: hovered && accessibleDescription.length > 0
    ToolTip.text: accessibleDescription
    ToolTip.delay: 650

    Keys.onReturnPressed: function(event) {
        control.toggle()
        event.accepted = true
    }
    Keys.onEnterPressed: function(event) {
        control.toggle()
        event.accepted = true
    }

    indicator: Rectangle {
        implicitWidth: 48
        implicitHeight: 26
        radius: 13
        anchors.verticalCenter: parent.verticalCenter
        color: control.checked ? Theme.accent : Theme.surfaceHover
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus
                      ? Theme.focus
                      : (control.checked ? Theme.accent : Theme.border)

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
