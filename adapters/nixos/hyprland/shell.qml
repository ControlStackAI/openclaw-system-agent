import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

Scope {
    id: shell
    property string clock: Qt.formatDateTime(new Date(), "ddd  hh:mm")
    property bool showLauncher: false
    property bool showControls: false
    function assistant() {
        const entry = DesktopEntries.byId("controlstack-agent");
        if (entry) entry.execute();
    }
    function launch(entry) {
        // DesktopEntry.execute does not handle Terminal=true in this pinned release.
        if (entry.runInTerminal)
            Quickshell.execDetached({ command: ["xterm", "-e"].concat(entry.command), workingDirectory: entry.workingDirectory });
        else entry.execute();
        shell.showLauncher = false;
    }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: shell.clock = Qt.formatDateTime(new Date(), "ddd  hh:mm") }
    IpcHandler {
        target: "shell"
        function launcher(): void { shell.showLauncher = !shell.showLauncher; }
        function assistant(): void { shell.assistant(); }
    }
    Variants {
        model: Quickshell.screens
        delegate: PanelWindow {
            required property var modelData
            screen: modelData
            anchors { top: true; left: true; right: true }
            implicitHeight: 48
            color: "#101827"
            RowLayout {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 6
                ShellButton { text: "Applications"; onClicked: shell.showLauncher = !shell.showLauncher }
                Repeater {
                    model: 5
                    ShellButton {
                        required property int index
                        text: String(index + 1)
                        onClicked: Quickshell.execDetached(["hyprctl", "dispatch", "hl.dsp.focus({ workspace = " + (index + 1) + " })"])
                    }
                }
                Item { Layout.fillWidth: true }
                ShellButton { text: "Assistant"; onClicked: shell.assistant() }
                ShellButton { text: "Controls"; onClicked: shell.showControls = !shell.showControls }
                Text { text: shell.clock; color: "#f1f5f9"; font.pixelSize: 14; Layout.leftMargin: 8 }
            }
        }
    }
    FloatingWindow {
        id: launcherWindow
        title: "Applications"
        visible: shell.showLauncher
        implicitWidth: 520
        implicitHeight: 540
        color: "#101827"
        onVisibleChanged: { if (!visible) shell.showLauncher = false; else search.forceActiveFocus(); }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            Text { text: "Applications"; color: "white"; font.pixelSize: 24 }
            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: "Find an application"
                onAccepted: { if (apps.count > 0) shell.launch(apps.model[0]); }
                Keys.onEscapePressed: shell.showLauncher = false
            }
            ListView {
                id: apps
                Layout.fillHeight: true
                Layout.fillWidth: true
                clip: true
                spacing: 5
                model: DesktopEntries.applications.values.filter(e => e.name.toLowerCase().includes(search.text.toLowerCase())).sort((a,b) => a.name.localeCompare(b.name))
                delegate: ShellButton {
                    required property var modelData
                    width: ListView.view.width
                    text: modelData.name
                    onClicked: shell.launch(modelData)
                }
            }
            ShellButton { text: "Close"; onClicked: shell.showLauncher = false }
        }
    }
    FloatingWindow {
        title: "Desktop controls"
        visible: shell.showControls
        implicitWidth: 460
        implicitHeight: 460
        color: "#101827"
        onVisibleChanged: if (!visible) shell.showControls = false
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 10
            Text { text: "Desktop controls"; color: "white"; font.pixelSize: 24 }
            ShellButton { text: "Network connections"; Layout.fillWidth: true; onClicked: Quickshell.execDetached(["xterm", "-T", "Network connections", "-e", "nmtui"]) }
            ShellButton { text: "Sound"; Layout.fillWidth: true; onClicked: Quickshell.execDetached(["pavucontrol"]) }
            ShellButton { text: "Files"; Layout.fillWidth: true; onClicked: Quickshell.execDetached(["thunar"]) }
            ShellButton { text: "Customize this desktop"; Layout.fillWidth: true; onClicked: Quickshell.execDetached(["mousepad", (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/quickshell/controlstack/shell.qml"]) }
            ShellButton { text: "Lock screen"; Layout.fillWidth: true; onClicked: { shell.showControls = false; Quickshell.execDetached(["loginctl", "lock-session"]); } }
            ShellButton { text: "Sign out…"; Layout.fillWidth: true; onClicked: confirmLogout.visible = true }
            Text { text: "Super + Space: applications   •   Super + A: assistant"; color: "#94a3b8"; font.pixelSize: 12 }
            Item { Layout.fillHeight: true }
            ShellButton { text: "Close"; onClicked: shell.showControls = false }
        }
    }
    FloatingWindow {
        id: confirmLogout
        title: "Sign out?"
        visible: false
        implicitWidth: 400
        implicitHeight: 160
        color: "#101827"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            Text { text: "Save your work before signing out."; color: "white" }
            RowLayout {
                ShellButton { text: "Cancel"; onClicked: confirmLogout.visible = false }
                ShellButton { text: "Sign out"; onClicked: Quickshell.execDetached(["uwsm", "stop"]) }
            }
        }
    }
}
