import QtQuick

Item {
    id: root

    property int pillHeight: 44
    property int hiddenOffset: 24
    property int marginPx: 0
    property int contentPadding: 12
    property int minWidth: 280
    property bool slideVisible: false
    property string phase: "listening"
    property real level: 0.0
    property color accent: "#7b2ff7"
    property color accentSecondary: "#f97316"

    property real smoothedLevel: 0.0
    property int elapsedSeconds: 0
    property real slideY: slideVisible ? marginPx : -(pillHeight + hiddenOffset)

    width: Math.max(minWidth, contentPadding * 2 + leftCluster.implicitWidth + timerText.implicitWidth + contentPadding)
    height: pillHeight + hiddenOffset + marginPx

    function formatElapsed(total) {
        var mins = Math.floor(total / 60)
        var secs = total % 60
        return mins + ":" + (secs < 10 ? "0" : "") + secs
    }

    Behavior on smoothedLevel {
        NumberAnimation { duration: 80; easing.type: Easing.OutQuad }
    }

    Behavior on slideY {
        NumberAnimation { duration: 350; easing.type: Easing.OutCubic }
    }

    onLevelChanged: smoothedLevel = level

    onSlideVisibleChanged: {
        if (slideVisible) {
            elapsedSeconds = 0
        }
    }

    Timer {
        interval: 1000
        running: slideVisible
        repeat: true
        onTriggered: elapsedSeconds += 1
    }

    Item {
        id: pillContainer
        x: 0
        y: slideY
        width: root.width
        height: pillHeight
        clip: true

        Rectangle {
            id: shadow
            anchors.left: pill.left
            anchors.right: pill.right
            anchors.top: pill.top
            anchors.topMargin: 4
            anchors.bottom: pill.bottom
            topLeftRadius: 0
            topRightRadius: 0
            bottomLeftRadius: pillHeight / 2
            bottomRightRadius: pillHeight / 2
            color: "#000000"
            opacity: 0.22
            z: -1
        }

        Rectangle {
            id: pill
            x: 0
            y: -1
            width: parent.width
            height: parent.height + 1
            topLeftRadius: 0
            topRightRadius: 0
            bottomLeftRadius: pillHeight / 2
            bottomRightRadius: pillHeight / 2
            color: "#000000"
            opacity: 0.72
        }

        Row {
            id: leftCluster
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: contentPadding
            spacing: 8

            Row {
                id: barsRow
                spacing: 3
                height: 28
                visible: phase === "listening"
                width: visible ? implicitWidth : 0

                Repeater {
                    model: 7

                    Rectangle {
                        width: 4
                        radius: 2
                        color: index % 2 === 0 ? accent : accentSecondary
                        property real barFactor: 0.35 + 0.65 * ((index + 1) / 7)
                        height: 6 + smoothedLevel * 18 * barFactor
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            Canvas {
                id: spinnerCanvas
                visible: phase === "processing"
                width: visible ? 24 : 0
                height: 24
                anchors.verticalCenter: parent.verticalCenter
                property real spinAngle: 0

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.strokeStyle = accent
                    ctx.lineWidth = 2.5
                    ctx.lineCap = "round"
                    ctx.beginPath()
                    ctx.arc(
                        width / 2,
                        height / 2,
                        9,
                        spinAngle * Math.PI / 180,
                        (spinAngle + 270) * Math.PI / 180,
                        false
                    )
                    ctx.stroke()
                }

                Timer {
                    interval: 16
                    running: phase === "processing" && slideVisible
                    repeat: true
                    onTriggered: {
                        spinnerCanvas.spinAngle = (spinnerCanvas.spinAngle + 8) % 360
                        spinnerCanvas.requestPaint()
                    }
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: phase === "processing" ? "Transcribing…" : "Listening…"
                color: "#ffffff"
                font.pixelSize: 13
                font.weight: Font.DemiBold
            }
        }

        Text {
            id: timerText
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: contentPadding
            text: formatElapsed(elapsedSeconds)
            visible: slideVisible
            color: "#a3ffffff"
            font.pixelSize: 12
            font.weight: Font.Medium
            font.family: "Consolas, Cascadia Mono, SF Mono, Menlo, monospace"
        }
    }
}
