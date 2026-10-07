import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Networking
import "Theme.js" as Theme
ColumnLayout {
    id: network
    property bool expanded: false
    property var passwordNetwork: null
    property string message: ""
    spacing: 8
    onExpandedChanged: if (!expanded) { passwordNetwork = null; password.text = ""; message = ""; }
    function needsPassword(n) { return [WifiSecurityType.WpaPsk, WifiSecurityType.Wpa2Psk, WifiSecurityType.Sae].includes(n.security); }
    RowLayout {
        Text { text: "Connections"; color: Theme.text; font { family: Theme.font; pixelSize: 14; weight: Font.DemiBold } Layout.fillWidth: true }
        ShellButton { visible: Networking.devices.values.some(d => d.type === DeviceType.Wifi); text: Networking.wifiEnabled ? "Wi-Fi on" : "Wi-Fi off"; selected: Networking.wifiEnabled; enabled: Networking.wifiHardwareEnabled; onClicked: Networking.wifiEnabled = !Networking.wifiEnabled }
    }
    Text {
        text: Networking.connectivity === NetworkConnectivity.Portal ? "This network needs browser sign-in" : Networking.connectivity === NetworkConnectivity.Limited ? "Connected, with limited internet access" : Networking.connectivity === NetworkConnectivity.Full ? "Internet connected" : "Choose a connection below"
        color: Theme.muted; font { family: Theme.font; pixelSize: 12 }
    }
    Repeater {
        model: Networking.devices
        ColumnLayout {
            id: device
            required property var modelData
            Layout.fillWidth: true
            property bool wireless: modelData.type === DeviceType.Wifi
            Binding { target: device.wireless ? device.modelData : null; property: "scannerEnabled"; value: network.expanded; when: device.wireless }
            Text {
                text: (device.wireless ? "Wi-Fi" : "Ethernet") + " · " + device.modelData.name + (device.modelData.connected ? " · Connected" : " · Disconnected")
                color: Theme.muted; font { family: Theme.font; pixelSize: 12 }
            }
            Repeater {
                model: device.modelData.networks
                ShellButton {
                    required property var modelData
                    Layout.fillWidth: true
                    text: modelData.name + (modelData.stateChanging ? " · Connecting…" : modelData.connected ? " · Connected" : "")
                    iconName: modelData.connected ? "emblem-ok-symbolic" : (device.wireless ? "network-wireless" : "network-wired")
                    selected: modelData.connected
                    enabled: !modelData.stateChanging
                    onClicked: {
                        network.message = "";
                        if (modelData.connected) { modelData.disconnect(); return; }
                        if (!device.wireless || modelData.known || modelData.security === WifiSecurityType.Open || modelData.security === WifiSecurityType.Owe) modelData.connect();
                        else if (network.needsPassword(modelData)) { network.passwordNetwork = modelData; password.forceActiveFocus(); }
                        else { network.message = "Use advanced connections for this network’s sign-in settings."; Quickshell.execDetached(["nm-connection-editor"]); }
                    }
                    Connections {
                        target: modelData
                        function onConnectionFailed(reason) {
                            network.message = "Could not connect. Check the password or try again.";
                            if (device.wireless && network.needsPassword(modelData)) network.passwordNetwork = modelData;
                        }
                    }
                }
            }
            Text { visible: device.wireless && device.modelData.networks.values.length === 0; text: Networking.wifiEnabled ? "Looking for nearby networks…" : "Turn on Wi-Fi to find networks"; color: Theme.muted; font.pixelSize: 12 }
        }
    }
    Text { visible: Networking.devices.values.length === 0; text: "No network adapter available"; color: Theme.muted; font.pixelSize: 12 }
    ColumnLayout {
        visible: network.passwordNetwork !== null
        Text { text: "Password for " + (network.passwordNetwork?.name ?? "Wi-Fi"); color: Theme.text; font.pixelSize: 12 }
        TextField {
            id: password
            Layout.fillWidth: true
            echoMode: TextInput.Password
            placeholderText: "Wi-Fi password"
            color: Theme.text; placeholderTextColor: Theme.muted
            background: Rectangle { radius: 8; color: Theme.surface; border.color: Theme.border }
            onAccepted: join.clicked()
        }
        RowLayout {
            ShellButton { text: "Cancel"; onClicked: { network.passwordNetwork = null; password.text = ""; } }
            ShellButton { id: join; text: "Connect"; selected: true; enabled: password.text.length > 0; onClicked: { network.passwordNetwork.connectWithPsk(password.text); password.text = ""; network.passwordNetwork = null; } }
        }
    }
    Text { visible: text !== ""; text: network.message; color: Theme.warning; wrapMode: Text.Wrap; Layout.fillWidth: true; font.pixelSize: 12 }
    ShellButton { text: "Advanced connections"; iconName: "preferences-system-network"; onClicked: Quickshell.execDetached(["nm-connection-editor"]) }
}
