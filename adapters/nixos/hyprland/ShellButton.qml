import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme
Button {
    id: control
    property string iconName: ""
    property string hint: text
    property bool selected: false
    implicitHeight: 34
    implicitWidth: row.implicitWidth + 20
    hoverEnabled: true
    ToolTip.visible: hovered && hint.length > 0
    ToolTip.delay: 650
    ToolTip.text: hint
    Accessible.name: hint
    contentItem: RowLayout {
        id: row
        spacing: 8
        ShellIcon { visible: control.iconName !== ""; name: control.iconName; implicitSize: 18 }
        Text {
            visible: control.text !== ""
            text: control.text; color: control.selected ? Theme.accent : Theme.text
            font { family: Theme.font; pixelSize: 12; weight: Font.Medium }
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }
    background: Rectangle {
        color: control.down ? Theme.hover : (control.selected || control.hovered || control.activeFocus ? Theme.surface : "transparent")
        radius: 9
        border.color: control.activeFocus ? Theme.accent : "transparent"
        Behavior on color { ColorAnimation { duration: 100 } }
    }
}
