import sys
import cv2
import time

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QHBoxLayout
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QTimer
from OpenGL.GL import *

TARGET_FPS = 60
FRAME_TIME = 1.0 / TARGET_FPS

def find_capture_device():
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.release()
            return i
    return 0


class GLVideoWidget(QOpenGLWidget):
    def __init__(self, cap):
        super().__init__()
        self.cap = cap
        self.texture = None
        self.frame = None
        self.video_w = 1920
        self.video_h = 1080
        self.show_fps = False
        self.last_render = time.time()
        self.last_fps = time.time()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(0)

    def initializeGL(self):
        self.context().swapInterval = lambda x: None
        glEnable(GL_TEXTURE_2D)
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def update_frame(self):
        now = time.time()
        if now - self.last_render < FRAME_TIME:
            return

        self.last_render = now
        ret, frame = self.cap.read()

        if not ret:
            return

        self.video_h, self.video_w, _ = frame.shape
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self.show_fps:
            fps = 1 / (now - self.last_fps)
            self.last_fps = now
            cv2.putText(
                frame,
                f"{int(fps)} FPS",
                (20,40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,255,0),
                2
            )

        self.frame = frame
        self.update()

    def paintGL(self):
        if self.frame is None:
            return

        window_w = self.width()
        window_h = self.height()
        video_ratio = self.video_w / self.video_h
        window_ratio = window_w / window_h
        
        if window_ratio > video_ratio:
            viewport_h = window_h
            viewport_w = int(viewport_h * video_ratio)
        else:
            viewport_w = window_w
            viewport_h = int(viewport_w / video_ratio)

        x = (window_w - viewport_w) // 2
        y = (window_h - viewport_h) // 2

        glViewport(x, y, viewport_w, viewport_h)

        glBindTexture(GL_TEXTURE_2D, self.texture)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            self.video_w,
            self.video_h,
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            self.frame
        )

        glClear(GL_COLOR_BUFFER_BIT)
        glBegin(GL_QUADS)
        glTexCoord2f(0,1)
        glVertex2f(-1,-1)
        glTexCoord2f(1,1)
        glVertex2f(1,-1)
        glTexCoord2f(1,0)
        glVertex2f(1,1)
        glTexCoord2f(0,0)
        glVertex2f(-1,1)
        glEnd()

    def toggle_fps(self):
        self.show_fps = not self.show_fps

class CaptureApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PS5 Viewer")
        self.resize(1280,720)

        device = find_capture_device()

        self.cap = cv2.VideoCapture(device, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        self.cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
        self.cap.set(cv2.CAP_PROP_FPS,60)
        self.video = GLVideoWidget(self.cap)
        self.fullscreen_btn = QPushButton("⛶")
        self.fps_btn = QPushButton("FPS")
        self.fullscreen_btn.setFixedSize(36,26)
        self.fps_btn.setFixedSize(40,26)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.fps_btn.clicked.connect(self.video.toggle_fps)

        layout = QHBoxLayout()
        layout.addWidget(self.fullscreen_btn)
        layout.addWidget(self.fps_btn)
        layout.addStretch()

        self.overlay = QWidget(self.video)
        self.overlay.setLayout(layout)
        self.overlay.move(10,10)
        self.overlay.setStyleSheet(
            "background-color: rgba(0,0,0,120); border-radius:6px;"
        )

        self.overlay_timer = QTimer()
        self.overlay_timer.setInterval(2000)
        self.overlay_timer.timeout.connect(self.hide_overlay)
        self.setCentralWidget(self.video)
        self.saved_geometry = None

    def mouseMoveEvent(self,event):
        self.overlay.show()
        QApplication.setOverrideCursor(Qt.ArrowCursor)
        self.overlay_timer.start()

    def hide_overlay(self):
        self.overlay.hide()
        QApplication.setOverrideCursor(Qt.BlankCursor)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()

            if self.saved_geometry:
                self.setGeometry(self.saved_geometry)
        else:
            self.saved_geometry = self.geometry()
            self.showFullScreen()

    def keyPressEvent(self,event):
        if event.key()==Qt.Key_F:
            self.toggle_fullscreen()
        if event.key()==Qt.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()

app = QApplication(sys.argv)
window = CaptureApp()
window.show()
sys.exit(app.exec())