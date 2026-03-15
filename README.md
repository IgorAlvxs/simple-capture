# Simple Capture

Visualizador de placa de captura HDMI em Python + OpenGL, focado em **baixa latência** e 1080p60 para jogar no PC (PS5, Xbox, Switch, etc.).

## Requisitos

- Python 3.9+
- Windows 10+
- Placa de captura com driver instalado

## Instalação e execução

```bash
pip install PySide6 opencv-python PyOpenGL
python simple-capture.py
```

O programa detecta automaticamente a primeira placa de captura disponível.

## Controles

| Ação | Tecla / Botão |
|------|----------------|
| Fullscreen | **F** ou botão ⛶ |
| Sair do fullscreen | **ESC** |
| Contador de FPS | Botão **FPS** |

Os controles aparecem ao mover o mouse e somem sozinhos após alguns segundos; em fullscreen só o vídeo é exibido.

## Tecnologias

- **OpenCV** (captura via DirectShow)
- **PySide6** (interface)
- **OpenGL** (textura na GPU, sem conversão BGR→RGB na CPU)

Pipeline: câmera → thread de captura → textura OpenGL → tela.

## Gerar .exe

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole simple-capture.py
```

Executável em `dist/simple-capture.exe`.
