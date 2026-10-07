import QtQuick
import QtQuick.Controls

Button {
    id: control
    implicitHeight: 34
    implicitWidth: Math.max(34, label.implicitWidth + 22)
    contentItem: Text {
        id: label
        text: control.text
        color: "#f1f5f9"
        font.pixelSize: 14
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        color: control.down ? "#347c78" : (control.hovered || control.activeFocus ? "#334155" : "#1e293b")
        radius: 6
        border.color: control.activeFocus ? "#76c7c0" : "transparent"
    }
}
