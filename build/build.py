"""
Gera o .exe com ícone a partir de logo.png (dentro da pasta build).
Requer: pip install pyinstaller pillow
Rode da raiz do projeto: python build/build.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BUILD_DIR.parent
LOGO_PNG = BUILD_DIR / "logo.png"
LOGO_ICO = BUILD_DIR / "logo.ico"
MAIN = PROJECT_ROOT / "simple-capture.py"


def png_to_ico():
    """Converte logo.png em logo.ico (necessário para o ícone do .exe no Windows)."""
    if not LOGO_PNG.exists():
        print(f"Erro: {LOGO_PNG} não encontrado. Coloque logo.png na pasta build/.")
        sys.exit(1)
    try:
        from PIL import Image
    except ImportError:
        print("Instale o Pillow: pip install pillow")
        sys.exit(1)
    img = Image.open(LOGO_PNG).convert("RGBA")
    img.save(LOGO_ICO, format="ICO", sizes=[(s, s) for s in (256, 128, 64, 48, 32, 16)])
    print(f"Ícone gerado: {LOGO_ICO}")


def cleanup():
    """Remove pastas e arquivos temporários do build, mantendo só o exe."""
    work_dir = BUILD_DIR / "work"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    for spec in BUILD_DIR.glob("*.spec"):
        spec.unlink()
    if LOGO_ICO.exists():
        LOGO_ICO.unlink()
    print("Limpeza concluída.")


def build():
    png_to_ico()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--noconsole",
            f"--icon={LOGO_ICO}",
            "--name=Simple Capture",
            "--distpath=build/dist",
            "--workpath=build/work",
            "--specpath=build",
            str(MAIN),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    cleanup()
    print("\nExecutável gerado em: build/dist/Simple Capture.exe")


if __name__ == "__main__":
    build()
