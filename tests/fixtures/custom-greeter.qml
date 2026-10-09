// VM-only example: native deployment can supply a completely different greeter.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.Greetd

ShellRoot {
    id: root
    property bool responding: false
    property string prompt: "Username"
    FloatingWindow {
        visible: true
        width: 700
        height: 480
        color: "#101c2c"
        ColumnLayout {
            anchors.centerIn: parent
            width: 380
            spacing: 18
            Text { text: "CUSTOM DEPLOYMENT"; color: "#72d4d4"; font.pixelSize: 25 }
            Text { text: "Independent Quickshell login"; color: "white"; font.pixelSize: 19 }
            Text { text: root.prompt; color: "white"; wrapMode: Text.Wrap; Layout.fillWidth: true }
            TextField {
                id: field
                Layout.fillWidth: true
                focus: true
                echoMode: root.responding ? TextInput.Password : TextInput.Normal
                onAccepted: {
                    const value = text;
                    text = "";
                    if (root.responding) Greetd.respond(value);
                    else Greetd.createSession(value);
                }
            }
            Button {
                text: "Start over"
                onClicked: { Greetd.cancelSession(); root.responding = false; root.prompt = "Username"; field.text = ""; field.forceActiveFocus(); }
            }
        }
    }
    Connections {
        target: Greetd
        function onAuthMessage(message, error, responseRequired, echoResponse) {
            root.prompt = message;
            root.responding = responseRequired;
            field.echoMode = echoResponse ? TextInput.Normal : TextInput.Password;
            field.forceActiveFocus();
        }
        function onAuthFailure(message) {
            root.prompt = "Sign-in failed. Username";
            root.responding = false;
            field.echoMode = TextInput.Normal;
            field.forceActiveFocus();
        }
        function onReadyToLaunch() { Greetd.launch(["uwsm", "start", "controlstack-hyprland.desktop"]); }
        function onError(error) {
            root.prompt = "Sign-in failed. Username";
            root.responding = false;
            field.text = "";
            field.echoMode = TextInput.Normal;
            field.forceActiveFocus();
        }
    }
}
