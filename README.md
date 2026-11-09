# Talehop

Talehop syncs an audiobook with its ebook into one `.tale` file, so you can switch between listening and reading without losing your place.

This repository holds the source code of the Windows app, in [`talehop/`](talehop/). It reads EPUB, MOBI and AZW3 files without DRM, transcribes the audio with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and matches it to the text. The Android app that opens `.tale` files is not in this repository.

Downloads and more information: <https://talehop.hugobranquinho.com>

## Run it from the source

On Windows, in the `talehop` folder:

1. Run `instalar.bat` once. It installs Python 3.11 and the libraries (about 3 GB).
2. Run `Talehop.bat` to open the window.

Or from the command line:

```
.venv\Scripts\python -m talehop book.epub audio_folder -o book.tale
```

[`talehop/LEIA-ME.md`](talehop/LEIA-ME.md) has the full notes in Portuguese, including how to build the installer.

## License

Copyright (C) 2026 Hugo Branquinho

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 3. It comes with no warranty. See [`LICENSE`](LICENSE) for the full terms.

The installer includes third-party libraries under their own licenses, among them [mobi](https://github.com/iscc/mobi) (GPL-3.0), which adds MOBI and AZW3 support.

---

# Talehop (português)

O Talehop sincroniza um audiobook com o respetivo ebook num só ficheiro `.tale`, para poderes trocar entre ouvir e ler sem perder o sítio onde ias.

Este repositório tem o código da app para Windows, na pasta [`talehop/`](talehop/). As notas completas estão em [`talehop/LEIA-ME.md`](talehop/LEIA-ME.md). A app Android não está aqui.

Licença: GPL-3.0, no ficheiro [`LICENSE`](LICENSE).
