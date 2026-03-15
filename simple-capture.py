import sys
import numpy as np
import cv2
import time

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QElapsedTimer
from PySide6.QtGui import QSurfaceFormat
from OpenGL.GL import *

try:
    GL_BGR
except NameError:
    GL_BGR = 0x80E0  # formato BGR (OpenGL 1.2)

TARGET_FPS = 60
FRAME_TIME = 1.0 / TARGET_FPS
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

def find_capture_device():
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.release()
            return i
    return None


class CaptureWorker(QThread):
    """Thread que lê frames da câmera sem bloquear a UI."""
    frame_ready = Signal(object)

    def __init__(self, device_index):
        super().__init__()
        self.device_index = device_index
        self._running = True

    def run(self):
        cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
        try:
            while self._running:
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.frame_ready.emit(frame)
        finally:
            cap.release()

    def stop(self):
        self._running = False


class GLVideoWidget(QOpenGLWidget):
    def __init__(self, device_index):
        super().__init__()
        self.device_index = device_index
        self.texture = None
        self.frame = None
        self.video_w = DEFAULT_WIDTH
        self.video_h = DEFAULT_HEIGHT
        self._tex_allocated = False
        self._tex_w = 0
        self._tex_h = 0
        self.show_fps = False
        self.last_render = time.time()
        self.last_fps = time.time()
        self.pending_frame = None
        self._elapsed = QElapsedTimer()
        self._elapsed.start()
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_pending_frame)
        self.timer.start(0)

        self._capture_thread = CaptureWorker(device_index)
        self._capture_thread.frame_ready.connect(self.on_frame_captured, Qt.BlockingQueuedConnection)
        self._capture_thread.start()

    def initializeGL(self):
        glEnable(GL_TEXTURE_2D)
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def on_frame_captured(self, frame):
        """Chamado pela thread de captura; só guarda o frame mais recente."""
        if frame is not None and frame.size > 0:
            self.pending_frame = frame

    def process_pending_frame(self):
        """Roda no timer da UI: pega o frame pendente e atualiza a textura (60 FPS)."""
        if self.pending_frame is None:
            return
        if self._elapsed.elapsed() < int(FRAME_TIME * 1000):
            return

        self._elapsed.restart()
        now = time.time()
        self.last_render = now
        frame = self.pending_frame
        self.pending_frame = None

        h, w = frame.shape[:2]
        if w <= 0 or h <= 0 or len(frame.shape) < 3:
            return

        if w != self.video_w or h != self.video_h:
            self.video_w, self.video_h = w, h
            self._tex_allocated = False

        if self.show_fps:
            fps = 1 / (now - self.last_fps)
            self.last_fps = now
            cv2.putText(
                frame,
                f"{int(fps)} FPS",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        self.frame = np.ascontiguousarray(frame) if not frame.flags["C_CONTIGUOUS"] else frame
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
        needs_allocate = not self._tex_allocated or self._tex_w != self.video_w or self._tex_h != self.video_h
        if needs_allocate:
            self._tex_w, self._tex_h = self.video_w, self.video_h
            self._tex_allocated = True
            glTexImage2D(
                GL_TEXTURE_2D, 0, GL_RGB,
                self.video_w, self.video_h, 0,
                GL_BGR,
                GL_UNSIGNED_BYTE,
                self.frame,
            )
        else:
            glTexSubImage2D(
                GL_TEXTURE_2D, 0, 0, 0,
                self.video_w, self.video_h,
                GL_BGR,
                GL_UNSIGNED_BYTE,
                self.frame,
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

    def stop_capture(self):
        self._capture_thread.stop()
        self._capture_thread.wait(3000)

class CaptureApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PS5 Viewer")
        self.resize(1280,720)

        device = find_capture_device()
        if device is None:
            QMessageBox.critical(
                None,
                "Erro",
                "Nenhum dispositivo de captura encontrado.",
            )
            sys.exit(1)

        cap = cv2.VideoCapture(device, cv2.CAP_DSHOW)
        if not cap.isOpened():
            QMessageBox.critical(
                None,
                "Erro",
                "Não foi possível abrir o dispositivo de captura.",
            )
            sys.exit(1)
        cap.release()
        self.video = GLVideoWidget(device)
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

    def mouseMoveEvent(self, event):
        self.overlay.show()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.overlay_timer.start()

    def hide_overlay(self):
        self.overlay.hide()
        self.setCursor(Qt.CursorShape.BlankCursor)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            if self.saved_geometry:
                self.setGeometry(self.saved_geometry)
        else:
            self.overlay.hide()
            self.overlay_timer.stop()
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.saved_geometry = self.geometry()
            self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            self.toggle_fullscreen()
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()

    def closeEvent(self, event):
        self.video.timer.stop()
        self.video.stop_capture()
        event.accept()


app = QApplication(sys.argv)
fmt = QSurfaceFormat()
fmt.setSwapInterval(0)
QSurfaceFormat.setDefaultFormat(fmt)
window = CaptureApp()
window.show()
sys.exit(app.exec())