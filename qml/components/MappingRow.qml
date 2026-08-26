
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

    implicitHeight: 68
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
                border.color: destinationBox.activeFocus ? Theme.accent : Theme.border
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
                width: destinationBox.width - 8
                height: 40
                highlighted: destinationBox.highlightedIndex === index

                contentItem: Text {
                    text: destinationBox.textAt(index)
                    color: Theme.text
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                background: Rectangle {
                    radius: 8
                    color: parent.highlighted ? Theme.surfaceHover : "transparent"
                }
            }

            onActivated: function(index) {
                if (index >= 0)
                    root.mappingChanged(destinationBox.currentValue)
            }
        }
    }
}
