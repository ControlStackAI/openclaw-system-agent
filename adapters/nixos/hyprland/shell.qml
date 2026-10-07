//@ pragma IconTheme Papirus-Dark
//@ pragma UseQApplication
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower
import Quickshell.Services.SystemTray
import Quickshell.Networking
import "Theme.js" as Theme

Scope {
    id: shell
    property string panel: ""
    onPanelChanged: if (panel === "launcher") {
        search.text = "";
        apps.currentIndex = 0;
        Qt.callLater(() => search.forceActiveFocus());
    }
    property string settingsTab: "audio"
    property bool keepAwake: false
    property var popupScreen: Quickshell.screens[0]
    property var stats: ({agent: {state: "unknown"}})
    property real cpu: 0
    property real agentCpu: -1
    property double lastSample: 0
    readonly property bool fresh: clock.date.getTime() / 1000 - lastSample < 15
    readonly property var sink: Pipewire.defaultAudioSink
    readonly property var source: Pipewire.defaultAudioSource
    readonly property var connected: Networking.devices.values.filter(d => d.connected)
    readonly property string agentLabel: lastSample === 0 ? "Checking…" : !fresh ? "Unavailable" : stats.agent.state === "active" ? "Running" : stats.agent.state === "failed" ? "Needs attention" : stats.agent.state === "inactive" ? "Stopped" : stats.agent.state
    function open(name, screen) {
        popupScreen = screen || Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) || Quickshell.screens[0];
        panel = panel === name ? "" : name;
    }
    function settings(tab, screen) {
        const same = panel === "controls" && settingsTab === tab;
        settingsTab = tab;
        popupScreen = screen || Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) || Quickshell.screens[0];
        panel = same ? "" : "controls";
    }
    function assistant() { const entry = DesktopEntries.byId("controlstack-agent"); if (entry) entry.execute(); panel = ""; }
    function lockScreen() { panel = ""; Quickshell.execDetached(["hyprlock"]); }
    function launch(entry) {
        if (entry.runInTerminal) Quickshell.execDetached({command: ["kitty", "-e"].concat(entry.command), workingDirectory: entry.workingDirectory});
        else entry.execute();
        panel = "";
    }
    function memory(bytes) { return bytes === null || bytes === undefined ? "Unavailable" : Math.round(bytes / 1048576) + " MB"; }
    SystemClock { id: clock; precision: SystemClock.Seconds }
    PwObjectTracker { objects: [shell.sink, shell.source].filter(n => n !== null) }
    Process {
        id: telemetry
        command: ["controlstack-desktop-status"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const next = JSON.parse(text);
                    if (shell.lastSample > 0) {
                        const delta = next.cpu_total - (shell.stats.cpu_total || 0);
                        shell.cpu = delta > 0 ? Math.max(0, Math.min(100, 100 * (1 - (next.cpu_idle - shell.stats.cpu_idle) / delta))) : 0;
                        shell.agentCpu = next.agent.cpu_ns !== null && shell.stats.agent.cpu_ns !== null ? Math.max(0, (next.agent.cpu_ns - shell.stats.agent.cpu_ns) / ((next.sampled - shell.lastSample) * 1e7)) : -1;
                    }
                    shell.stats = next; shell.lastSample = next.sampled;
                } catch (e) { shell.lastSample = 0; }
            }
        }
    }
    Timer { interval: 4000; running: true; repeat: true; onTriggered: if (!telemetry.running) telemetry.running = true }
    IpcHandler {
        target: "shell"
        function launcher(): void { shell.open("launcher"); }
        function controls(): void { shell.open("controls"); }
        function network(): void { shell.settings("network"); }
        function monitor(): void { shell.open("monitor"); }
        function assistant(): void { shell.assistant(); }
        function lock(): void { shell.lockScreen(); }
    }
    Variants {
        model: Quickshell.screens
        delegate: Scope {
            required property var modelData
            PanelWindow {
                screen: modelData
                anchors { top: true; bottom: true; left: true; right: true }
                exclusionMode: ExclusionMode.Ignore
                WlrLayershell.layer: WlrLayer.Background
                WlrLayershell.namespace: "controlstack-wallpaper"
                mask: Region {}
                color: "#081321"
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient { GradientStop { position: 0; color: "#081321" } GradientStop { position: 1; color: "#18344b" } }
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            const c = getContext("2d"); c.reset();
                            for (let i = 0; i < 16; i++) {
                                c.beginPath(); c.moveTo(width * 0.25 + i * 24, height + 20);
                                c.bezierCurveTo(width * 0.5, height * 0.4 + i * 13, width * 0.9, height * 0.98 - i * 8, width + 40, height * 0.2 + i * 21);
                                c.strokeStyle = i === 5 ? "#335d7c" : "#203e54"; c.lineWidth = 1; c.stroke();
                            }
                        }
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                    }
                    Column {
                        anchors { left: parent.left; bottom: parent.bottom; margins: 42 } spacing: 10
                        Text { text: "C O N T R O L S T A C K"; color: "#7796b0"; font { family: Theme.font; pixelSize: 12; weight: Font.Medium } }
                        Text { text: "Your system. Your workspace."; color: "#4c6c85"; font { family: Theme.font; pixelSize: 12 } }
                    }
                }
            }
            PanelWindow {
                id: bar
                screen: modelData
                anchors { top: true; left: true; right: true }
                implicitHeight: width < 800 ? 96 : 56
                color: "transparent"
                WlrLayershell.namespace: "controlstack-islands"
                readonly property bool compact: width < 1200
                IdleInhibitor { window: bar; enabled: shell.keepAwake }
                mask: Region { Region { item: leftIsland } Region { item: centerIsland } Region { item: rightIsland } }
                Rectangle {
                    id: leftIsland
                    x: 12; y: 10; height: 36; width: leftRow.implicitWidth + 10
                    radius: 12; color: Theme.bg; border.color: Theme.border
                    RowLayout {
                        id: leftRow; anchors.centerIn: parent; spacing: 2
                        ShellButton { text: bar.compact ? "" : "Applications"; iconName: "view-grid-symbolic"; hint: "Applications · Super + Space"; onClicked: shell.open("launcher", bar.screen) }
                        Rectangle { width: 1; height: 14; color: Theme.border; Layout.leftMargin: 3; Layout.rightMargin: 3 }
                        Repeater {
                            model: 5
                            ShellButton {
                                required property int index
                                text: String(index + 1); implicitWidth: 27
                                selected: Hyprland.monitorFor(bar.screen)?.activeWorkspace?.id === index + 1
                                hint: "Workspace " + (index + 1)
                                onClicked: Quickshell.execDetached(["hyprctl", "dispatch", "hl.dsp.focus({ workspace = " + (index + 1) + " })"])
                            }
                        }
                    }
                }
                Rectangle {
                    id: centerIsland
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: bar.width < 800 ? 52 : 10; height: 36; width: centerRow.implicitWidth + 14
                    radius: 12; color: Theme.bg; border.color: Theme.border
                    RowLayout {
                        id: centerRow; anchors.centerIn: parent; spacing: 6
                        Rectangle { width: 6; height: 6; radius: 3; color: shell.fresh && shell.stats.agent.state === "active" ? Theme.green : Theme.warning }
                        ShellButton { text: "OpenClaw"; hint: "Resident agent monitor"; onClicked: shell.open("monitor", bar.screen) }
                        Text { visible: !bar.compact; text: shell.agentLabel; color: Theme.muted; font { family: Theme.font; pixelSize: 11 } }
                        ShellButton { iconName: "chat-message-new-symbolic"; hint: "Talk to OpenClaw · Super + A"; onClicked: shell.assistant() }
                    }
                }
                Rectangle {
                    id: rightIsland
                    anchors.right: parent.right; anchors.rightMargin: 12
                    y: 10; height: 36; width: rightRow.implicitWidth + 12
                    radius: 12; color: Theme.bg; border.color: Theme.border
                    RowLayout {
                        id: rightRow; anchors.centerIn: parent; spacing: 1
                        Repeater {
                            model: SystemTray.items
                            ShellButton {
                                required property var modelData
                                visible: !bar.compact
                                implicitWidth: 28; hint: modelData.title
                                contentItem: Image { source: modelData.icon; sourceSize.width: 18; sourceSize.height: 18; fillMode: Image.PreserveAspectFit }
                                onClicked: if (modelData.hasMenu) modelData.display(bar, rightIsland.x, bar.height); else modelData.activate()
                            }
                        }
                        ShellButton { iconName: shell.connected.some(d => d.type === DeviceType.Wifi) ? "network-wireless" : shell.connected.length ? "network-wired" : "network-offline"; hint: "Wi-Fi and Ethernet connections"; onClicked: shell.settings("network", bar.screen) }
                        ShellButton { iconName: shell.sink?.audio?.muted ? "audio-volume-muted" : "audio-volume-high"; hint: "Speakers and volume"; onClicked: shell.settings("audio", bar.screen) }
                        ShellButton { iconName: shell.source?.audio?.muted ? "microphone-sensitivity-muted-symbolic" : "audio-input-microphone"; hint: "Microphone and input device"; onClicked: shell.settings("audio", bar.screen) }
                        Text { visible: UPower.displayDevice?.isLaptopBattery ?? false; text: Math.round((UPower.displayDevice?.percentage ?? 0) * 100) + "%"; color: Theme.muted; font.pixelSize: 11; Layout.rightMargin: 6 }
                        ShellButton { text: Qt.formatDateTime(clock.date, bar.compact ? "hh:mm" : "ddd  hh:mm"); hint: Qt.formatDateTime(clock.date, "dddd, d MMMM yyyy"); onClicked: shell.open("controls", bar.screen) }
                        ShellButton { iconName: "preferences-system-symbolic"; hint: "Quick settings"; onClicked: shell.open("controls", bar.screen) }
                    }
                }
            }
        }
    }
    PanelWindow {
        id: overlay
        screen: shell.popupScreen
        visible: shell.panel !== ""
        anchors { top: true; bottom: true; left: true; right: true }
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.namespace: "controlstack-overlay"
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
        color: "#99050d18"
        onVisibleChanged: if (visible && shell.panel === "launcher") { search.text = ""; apps.currentIndex = 0; search.forceActiveFocus(); }
        MouseArea { anchors.fill: parent; onClicked: shell.panel = "" }
        Rectangle {
            id: launcher
            visible: shell.panel === "launcher"
            anchors.centerIn: parent
            width: Math.min(620, parent.width - 40); height: Math.min(610, parent.height - 80)
            radius: 22; color: Theme.bg; border.color: Theme.border
            MouseArea { anchors.fill: parent }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 26; spacing: 16
                RowLayout {
                    Text { text: "Applications"; color: Theme.text; font { family: Theme.font; pixelSize: 22; weight: Font.DemiBold } Layout.fillWidth: true }
                    Text { text: "YOUR WORKSPACE"; color: Theme.muted; font { family: Theme.font; pixelSize: 10; letterSpacing: 2 } }
                }
                Rectangle {
                    Layout.fillWidth: true; height: 52; radius: 12; color: Theme.surface; border.color: search.activeFocus ? Theme.accent : Theme.border
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12
                        ShellIcon { name: "edit-find-symbolic" }
                        TextField {
                            id: search; Layout.fillWidth: true; font { family: Theme.font; pixelSize: 16 }
                            placeholderText: "Find an application"; color: Theme.text; placeholderTextColor: Theme.muted
                            background: Item {}
                            onTextChanged: apps.currentIndex = 0
                            onAccepted: if (apps.count > 0) shell.launch(apps.model[apps.currentIndex]);
                            Keys.onEscapePressed: shell.panel = ""
                            Keys.onDownPressed: apps.currentIndex = Math.min(apps.count - 1, apps.currentIndex + 1)
                            Keys.onUpPressed: apps.currentIndex = Math.max(0, apps.currentIndex - 1)
                        }
                        Text { text: "⌘"; color: Theme.muted; font.pixelSize: 18 }
                    }
                }
                ListView {
                    id: apps; Layout.fillHeight: true; Layout.fillWidth: true; clip: true; spacing: 4
                    model: DesktopEntries.applications.values.filter(e => (e.name + " " + e.genericName).toLowerCase().includes(search.text.toLowerCase())).sort((a,b) => a.name.localeCompare(b.name))
                    currentIndex: 0
                    onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        width: apps.width; height: 62; radius: 12
                        color: apps.currentIndex === index ? Theme.hover : "transparent"
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 10; spacing: 14
                            ShellIcon { name: modelData.icon || "application-x-executable"; implicitSize: 36 }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { text: modelData.name; color: Theme.text; font { family: Theme.font; pixelSize: 14; weight: Font.Medium } elide: Text.ElideRight; Layout.fillWidth: true }
                                Text { text: modelData.genericName || modelData.comment || "Application"; color: Theme.muted; font { family: Theme.font; pixelSize: 11 } elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            Text { text: "↵"; visible: apps.currentIndex === index; color: Theme.accent; font.pixelSize: 18 }
                        }
                        MouseArea { anchors.fill: parent; hoverEnabled: true; onEntered: apps.currentIndex = index; onClicked: shell.launch(modelData) }
                    }
                    Text { anchors.centerIn: parent; visible: apps.count === 0; text: "No applications found"; color: Theme.muted; font.family: Theme.font }
                }
                Rectangle { height: 1; Layout.fillWidth: true; color: Theme.border }
                RowLayout {
                    Text { text: "↑ ↓  Select     ↵  Open"; color: Theme.muted; font { family: Theme.font; pixelSize: 11 } Layout.fillWidth: true }
                    ShellButton { text: "Esc  Close"; onClicked: shell.panel = "" }
                }
            }
        }
        Rectangle {
            visible: shell.panel === "controls" || shell.panel === "monitor" || shell.panel === "logout"
            anchors { top: parent.top; right: parent.right; topMargin: 64; rightMargin: 14 }
            width: Math.min(430, parent.width - 28); height: Math.min(content.implicitHeight + 40, parent.height - 86)
            radius: 20; color: Theme.bg; border.color: Theme.border
            MouseArea { anchors.fill: parent }
            ScrollView {
                anchors.fill: parent; anchors.margins: 20; clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    id: content; width: parent.width; spacing: 16
                    RowLayout {
                        Text { text: shell.panel === "monitor" ? "OpenClaw" : shell.panel === "logout" ? "Sign out?" : "Quick settings"; color: Theme.text; font { family: Theme.font; pixelSize: 22; weight: Font.DemiBold } Layout.fillWidth: true }
                        ShellButton { text: "✕"; hint: "Close"; onClicked: shell.panel = "" }
                    }
                    ColumnLayout {
                        visible: shell.panel === "monitor"; Layout.fillWidth: true; spacing: 14
                        Text { text: "●  " + shell.agentLabel; color: shell.fresh && shell.stats.agent.state === "active" ? Theme.green : Theme.warning; font { family: Theme.font; pixelSize: 16 } }
                        Text { text: "Resident system agent"; color: Theme.muted; font.family: Theme.font }
                        Text { text: "Memory   " + shell.memory(shell.stats.agent.memory) + "\nCPU   " + (shell.agentCpu < 0 ? "Unavailable" : shell.agentCpu.toFixed(1) + "%") + "\nRestarts   " + (shell.stats.agent.restarts ?? "Unavailable"); color: Theme.text; lineHeight: 1.7; font { family: Theme.font; pixelSize: 14 } }
                        Text { text: "Live service status, refreshed every four seconds. Provider sign-in and model availability are checked inside the assistant."; color: Theme.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; font { family: Theme.font; pixelSize: 12 } }
                        ShellButton { text: "Open assistant"; iconName: "chat-message-new-symbolic"; selected: true; onClicked: shell.assistant() }
                    }
                    ColumnLayout {
                        visible: shell.panel === "controls"; Layout.fillWidth: true; spacing: 16
                        Text { text: Qt.formatDateTime(clock.date, "dddd, d MMMM yyyy"); color: Theme.muted; font { family: Theme.font; pixelSize: 12 } }
                        RowLayout {
                            Repeater {
                                model: ["audio", "network", "system"]
                                ShellButton { required property string modelData; text: modelData.charAt(0).toUpperCase() + modelData.slice(1); selected: shell.settingsTab === modelData; Layout.fillWidth: true; onClicked: shell.settingsTab = modelData }
                            }
                        }
                        ColumnLayout {
                        visible: shell.settingsTab === "audio"; Layout.fillWidth: true; spacing: 12
                        AudioDevices { Layout.fillWidth: true }
                        Rectangle { height: 1; Layout.fillWidth: true; color: Theme.border }
                        AudioDevices { input: true; Layout.fillWidth: true }
                        Rectangle { height: 1; Layout.fillWidth: true; color: Theme.border }
                        }
                        NetworkControls { visible: shell.settingsTab === "network"; expanded: shell.panel === "controls" && shell.settingsTab === "network"; Layout.fillWidth: true }
                        Rectangle { height: 1; Layout.fillWidth: true; color: Theme.border }
                        Text { visible: shell.settingsTab === "system"; text: "CPU  " + Math.round(shell.cpu) + "%     Memory  " + (shell.stats.memory_percent ?? "—") + "%"; color: Theme.muted; font { family: Theme.font; pixelSize: 12 } }
                        Flow {
                            Layout.fillWidth: true; spacing: 4
                            ShellButton { visible: shell.settingsTab === "system"; text: "Bluetooth"; iconName: "bluetooth"; onClicked: Quickshell.execDetached(["blueman-manager"]) }
                            ShellButton { visible: shell.settingsTab === "audio"; text: "Sound mixer"; iconName: "multimedia-volume-control"; onClicked: Quickshell.execDetached(["pavucontrol"]) }
                            ShellButton { visible: shell.settingsTab === "system"; text: "Dim"; iconName: "display-brightness-symbolic"; onClicked: Quickshell.execDetached(["brightnessctl", "set", "5%-"]) }
                            ShellButton { visible: shell.settingsTab === "system"; text: "Brighten"; iconName: "display-brightness-symbolic"; onClicked: Quickshell.execDetached(["brightnessctl", "set", "+5%"]) }
                            ShellButton { visible: shell.settingsTab === "system"; text: "Customize"; iconName: "preferences-desktop-theme"; onClicked: Quickshell.execDetached(["kitty", "-e", "nvim", (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/quickshell/controlstack/shell.qml"]) }
                            ShellButton { visible: shell.settingsTab === "system"; text: shell.keepAwake ? "Keeping awake" : "Keep awake"; selected: shell.keepAwake; iconName: "weather-clear-night"; onClicked: shell.keepAwake = !shell.keepAwake }
                            ShellButton { text: "Lock"; iconName: "system-lock-screen"; onClicked: shell.lockScreen() }
                            ShellButton { text: "Sign out"; iconName: "system-log-out"; onClicked: shell.panel = "logout" }
                        }
                    }
                    ColumnLayout {
                        visible: shell.panel === "logout"; Layout.fillWidth: true
                        Text { text: "Save your work before signing out."; color: Theme.muted; font.family: Theme.font }
                        RowLayout {
                            ShellButton { text: "Cancel"; onClicked: shell.panel = "controls" }
                            ShellButton { text: "Sign out"; selected: true; onClicked: Quickshell.execDetached(["uwsm", "stop"]) }
                        }
                    }
                }
            }
        }
        Shortcut { sequence: "Escape"; onActivated: shell.panel = "" }
    }
}
