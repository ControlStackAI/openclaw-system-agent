import QtQuick
import Quickshell
import Quickshell.Widgets
IconImage {
    property string name: "application-x-executable"
    implicitSize: 20
    source: Quickshell.iconPath(name, "application-x-executable")
}
