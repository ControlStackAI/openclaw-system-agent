import QtQuick
import Quickshell
import Quickshell.Widgets
IconImage {
    property string name: "application-x-executable"
    implicitSize: 20
    source: name === "" ? "" : Quickshell.iconPath(Quickshell.hasThemeIcon(name) || name.startsWith("/") ? name : "application-x-executable")
}
