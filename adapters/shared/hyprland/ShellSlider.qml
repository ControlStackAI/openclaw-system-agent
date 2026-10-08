import QtQuick
import QtQuick.Controls
import "Theme.js" as Theme
Slider {
    id: slider
    implicitHeight: 28
    background: Rectangle {
        x: slider.leftPadding; y: slider.topPadding + slider.availableHeight / 2 - height / 2
        width: slider.availableWidth; height: 5; radius: 3; color: Theme.hover
        Rectangle { width: slider.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.accent }
    }
    handle: Rectangle {
        x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
        y: slider.topPadding + slider.availableHeight / 2 - height / 2
        width: 14; height: 14; radius: 7; color: slider.pressed ? "white" : Theme.accent
    }
}
