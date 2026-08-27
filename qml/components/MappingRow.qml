
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Theme.js" as Theme

Rectangle {
    id: root
    property string sourceName: ""
    property string destinationKey: ""
    property var destinationModel: []
    signal mappingChanged(string destinationKey)

    implicitHeight: 72
    radius: 12
    color: Theme.surface2
    border.color: Theme.borderSoft

    function syncIndex() {
        var idx = destinationBox.indexOfValue(destinationKey)
        destinationBox.currentIndex = idx
    }

    onDestinationKeyChanged: syncIndex()
    onDestinationModelChanged: syncIndex()
    Component.onCompleted: syncIndex()

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 14

        Rectangle {
            Layout.preferredWidth: 54
            Layout.preferredHeight: 42
            radius: 10
            color: Theme.bg
            border.color: Theme.border

            Text {
                anchors.centerIn: parent
                text: root.sourceName
                color: Theme.accent
                font.pixelSize: 15
                font.bold: true
            }

            Accessible.name: qsTr("Source button %1").arg(root.sourceName)
            Accessible.role: Accessible.StaticText
        }

        Text {
            text: "→"
            color: Theme.muted2
            font.pixelSize: 22
        }

        ComboBox {
            id: destinationBox
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            model: root.destinationModel
            textRole: "label"
            valueRole: "key"
            focusPolicy: Qt.StrongFocus

            Accessible.name: qsTr("Destination for %1").arg(root.sourceName)
            Accessible.description: qsTr("Select a gamepad button or keyboard HID usage")
            Accessible.role: Accessible.ComboBox

            ToolTip.visible: hovered
            ToolTip.text: qsTr("Choose the output sent when %1 is pressed").arg(root.sourceName)
            ToolTip.delay: 650

            contentItem: Text {
                leftPadding: 12
                rightPadding: 34
                text: destinationBox.displayText
                color: Theme.text
                font.pixelSize: 14
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            background: Rectangle {
                radius: 10
                color: destinationBox.hovered ? Theme.surfaceHover : Theme.bg
                border.width: destinationBox.activeFocus ? 2 : 1
                border.color: destinationBox.activeFocus ? Theme.focus : Theme.border
            }

            indicator: Text {
                x: destinationBox.width - width - 14
                anchors.verticalCenter: parent.verticalCenter
                text: "⌄"
                color: Theme.muted
                font.pixelSize: 16
            }

            popup: Popup {
                y: destinationBox.height + 4
                width: destinationBox.width
                implicitHeight: Math.min(contentItem.implicitHeight + 8, 360)
                padding: 4

                background: Rectangle {
                    radius: 12
                    color: Theme.surface
                    border.color: Theme.border
                }

                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: destinationBox.popup.visible ? destinationBox.delegateModel : null
                    currentIndex: destinationBox.highlightedIndex
                    ScrollIndicator.vertical: ScrollIndicator {}
                }
            }

            delegate: ItemDelegate {
                id: optionDelegate
                required property int index
                width: destinationBox.width - 8
                height: 40
                highlighted: destinationBox.highlightedIndex === optionDelegate.index

                Accessible.name: destinationBox.textAt(optionDelegate.index)
                Accessible.role: Accessible.ListItem

                contentItem: Text {
                    text: destinationBox.textAt(optionDelegate.index)
                    color: Theme.text
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                background: Rectangle {
                    radius: 8
                    color: optionDelegate.highlighted ? Theme.surfaceHover : "transparent"
                }
            }

            onActivated: function(index) {
                if (index >= 0)
                    root.mappingChanged(destinationBox.currentValue)
            }
        }
    }
}
