import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Widgets
import "Theme.js" as Theme
IconImage {
    property string name: "application-x-executable"
    implicitSize: 20
    layer.enabled: name.endsWith("-symbolic")
    layer.effect: MultiEffect { colorization: 1; colorizationColor: Theme.text; brightness: 0.5 }
    source: name === "" ? "" : Quickshell.iconPath(Quickshell.hasThemeIcon(name) || name.startsWith("/") ? name : "application-x-executable")
}
