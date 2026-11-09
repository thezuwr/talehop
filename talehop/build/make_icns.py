"""talehop.ico -> talehop.icns (o ícone da app de Mac). Corre no GitHub, antes do PyInstaller."""
from pathlib import Path

from PIL import Image

here = Path(__file__).parent
ico = Image.open(here.parent / "talehop" / "talehop.ico")
# a maior imagem dentro do .ico
best = max(ico.info.get("sizes") or {ico.size}, key=lambda s: s[0])
ico.size = best
img = ico.convert("RGBA").resize((1024, 1024), Image.LANCZOS)
img.save(here / "talehop.icns", sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
print("talehop.icns a partir de", best)
