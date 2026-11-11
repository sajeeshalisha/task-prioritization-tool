"""Draws TaskBoard's icon: a turquoise rounded square with a checklist, two items ticked off.

    .venv/bin/python tools/make_icon.py

Writes taskboard/resources/icon.png (used for the running app's Dock icon) and
TaskBoard.app/Contents/Resources/AppIcon.icns (used by Finder and a pinned Dock icon).
"""
import os
import subprocess
import sys
import tempfile

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 1024
GREEN_TOP, GREEN_BOTTOM = QColor("#34d6c0"), QColor("#0e8f88")
WHITE = QColor("white")


def draw(size=SIZE):
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    p.scale(size / SIZE, size / SIZE)

    # macOS-style tile: a rounded square inset from the canvas edge.
    tile = QRectF(100, 100, 824, 824)
    gradient = QLinearGradient(tile.topLeft(), tile.bottomLeft())
    gradient.setColorAt(0, GREEN_TOP)
    gradient.setColorAt(1, GREEN_BOTTOM)
    p.setPen(Qt.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(tile, 185, 185)

    # Three tasks: the first two done (filled circle with a tick), the last still to do.
    for index, done in enumerate((True, True, False)):
        cy = 336 + index * 176
        centre = QPointF(330, cy)
        if done:
            p.setPen(Qt.NoPen)
            p.setBrush(WHITE)
            p.drawEllipse(centre, 58, 58)
            tick = QPainterPath(QPointF(330 - 26, cy + 2))
            tick.lineTo(330 - 6, cy + 24)
            tick.lineTo(330 + 30, cy - 22)
            pen = QPen(GREEN_BOTTOM, 24, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(tick)
        else:
            p.setPen(QPen(WHITE, 22))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(centre, 52, 52)
        line = QColor(WHITE)
        line.setAlphaF(1.0 if done else 0.6)
        p.setPen(Qt.NoPen)
        p.setBrush(line)
        p.drawRoundedRect(QRectF(440, cy - 22, 300 if index != 1 else 250, 44), 22, 22)

    p.end()
    return image


def main():
    QGuiApplication(sys.argv)
    master = draw()

    resources = os.path.join(ROOT, "taskboard", "resources")
    os.makedirs(resources, exist_ok=True)
    master.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(os.path.join(resources, "icon.png"))

    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "AppIcon.iconset")
        os.makedirs(iconset)
        for base in (16, 32, 128, 256, 512):
            for scale, suffix in ((1, ""), (2, "@2x")):
                px = base * scale
                master.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(
                    os.path.join(iconset, f"icon_{base}x{base}{suffix}.png"))
        target = os.path.join(ROOT, "TaskBoard.app", "Contents", "Resources")
        os.makedirs(target, exist_ok=True)
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(target, "AppIcon.icns")], check=True)
    print("wrote", resources, "and", target)


if __name__ == "__main__":
    main()
