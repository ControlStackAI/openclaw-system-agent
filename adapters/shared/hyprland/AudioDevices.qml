import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Services.Pipewire
import "Theme.js" as Theme
ColumnLayout {
    id: audio
    property bool input: false
    readonly property var node: input ? Pipewire.defaultAudioSource : Pipewire.defaultAudioSink
    readonly property var devices: Pipewire.nodes.values.filter(n => n.audio && !n.isStream && n.isSink !== input)
    spacing: 8
    PwObjectTracker { objects: audio.devices }
    RowLayout {
        ShellIcon { name: audio.input ? "audio-input-microphone" : "audio-speakers" }
        Text { text: audio.input ? "Microphone" : "Speakers"; color: Theme.text; font { family: Theme.font; pixelSize: 14; weight: Font.DemiBold } Layout.fillWidth: true }
        ShellButton {
            text: audio.node?.audio?.muted ? "Muted" : "Mute"
            selected: audio.node?.audio?.muted ?? false
            enabled: audio.node?.ready ?? false
            onClicked: audio.node.audio.muted = !audio.node.audio.muted
        }
    }
    RowLayout {
        ShellSlider {
            Layout.fillWidth: true; from: 0; to: 1
            value: audio.node?.audio?.volume ?? 0
            enabled: audio.node?.ready ?? false
            onMoved: if (audio.node?.audio) audio.node.audio.volume = value
            Accessible.name: audio.input ? "Microphone level" : "Speaker volume"
        }
        Text { text: Math.round((audio.node?.audio?.volume ?? 0) * 100) + "%"; color: Theme.muted; font { family: Theme.font; pixelSize: 12 } Layout.preferredWidth: 36 }
    }
    Repeater {
        model: audio.devices
        ShellButton {
            required property var modelData
            Layout.fillWidth: true
            text: modelData.description || modelData.name
            iconName: modelData === audio.node ? "emblem-ok-symbolic" : (audio.input ? "audio-input-microphone" : "audio-speakers")
            selected: modelData === audio.node
            onClicked: {
                if (audio.input) Pipewire.preferredDefaultAudioSource = modelData;
                else Pipewire.preferredDefaultAudioSink = modelData;
            }
        }
    }
    Text { visible: audio.devices.length === 0; text: audio.input ? "No microphone connected" : "No speaker connected"; color: Theme.muted; font { family: Theme.font; pixelSize: 12 } }
}
