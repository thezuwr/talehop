# Talehop — programa para Windows

Junta um audiobook e o respetivo ebook num ficheiro `.tale`, que a app Android
abre com o texto sincronizado com o narrador. (Os ficheiros `.sincro`, do nome antigo da
app, continuam a abrir.)

## Instalar (uma vez)

1. Copia esta pasta (`talehop`) para o PC. **Não copies a subpasta `.venv`** se ela existir:
   foi criada no Mac e não funciona no Windows.
2. Faz duplo clique em **`instalar.bat`**. Este ficheiro:
   - instala o `uv` (um gestor de Python), se ainda não o tiveres;
   - instala o Python 3.11 e as bibliotecas, incluindo as da NVIDIA para usar a placa
     gráfica (cerca de 3 GB);
   - cria um atalho **Talehop** no Ambiente de Trabalho.

   Se o Windows mostrar o aviso "O Windows protegeu o seu PC", carrega em
   *Mais informações → Executar mesmo assim*.

## Usar

1. Abre o **Talehop** pelo atalho.
2. **Ebook:** escolhe o ficheiro (`.epub`, `.mobi` ou `.azw3`, sem DRM) ou arrasta-o para a janela.
3. **Audiobook:** escolhe o ficheiro (ex.: `.m4b`) ou a pasta com os MP3. Os ficheiros
   são ordenados pelo número no nome (2 antes de 10); confirma a ordem na lista.
4. Carrega em **Sincronizar**.

Na primeira vez, o programa descarrega o modelo de reconhecimento de voz (cerca de 1,5 GB).
A janela mostra o progresso e o tempo que falta. Podes cancelar a qualquer momento: da
próxima vez, os ficheiros de áudio já transcritos não são repetidos.

No fim, carrega em **Abrir pasta**, copia o ficheiro `.tale` para o telemóvel e
importa-o na app.

Se o EPUB indicar as páginas da edição impressa (muitos EPUBs comerciais indicam), o registo
diz "N páginas da edição impressa" e a app mostra essas páginas, as mesmas do Kindle. Se não
indicar, a app usa a percentagem.

A linha "Placa gráfica NVIDIA" na janela diz se a placa vai ser usada. Se disser
"não encontrada", volta a correr o `instalar.bat` ou atualiza o driver da NVIDIA.

### Opções

- **Qualidade:** "Rápida" chega para quase todos os livros. Usa "Máxima" se a
  sincronização ficar fraca.
- **Língua:** por omissão, usa a língua indicada no EPUB.

### Se a sincronização ficar fraca

O programa avisa quando menos de 80% das frases ficam sincronizadas. As causas mais
comuns são:

- o ebook e o audiobook são de edições ou traduções diferentes;
- o audiobook é uma versão resumida;
- a língua está errada.

## Linha de comandos

```
.venv\Scripts\python -m talehop livro.epub pasta_do_audio -o livro.tale
```

## Criar o instalador (para distribuir)

Faz duplo clique em **`criar-instalador.bat`**. Em poucos minutos aparece
`dist\TalehopSetup-<versão>.exe`: um só ficheiro, que instala o Talehop para o utilizador
(sem pedir administrador), com atalhos e desinstalador.

- Antes de distribuir uma versão nova, sobe o número em `talehop/__init__.py` (`__version__`).
- Precisa do Inno Setup 6 (`winget install JRSoftware.InnoSetup --scope user`) e do PyInstaller
  no `.venv` (`uv pip install -p .venv\Scripts\python.exe pyinstaller`).
- O instalador não traz as bibliotecas da NVIDIA (~2 GB). Quem tiver placa NVIDIA vê no
  cabeçalho o botão **Ativar a placa · 1,3 GB**, que as descarrega uma vez (`talehop/gpu_pack.py`).
- A receita está em `build/` (`talehop.spec` para o PyInstaller, `installer.iss` para o Inno Setup).

Para programar e experimentar, continua a usar o `Talehop.bat`: corre o código diretamente.

## Ficheiros

- `talehop/epub.py`: lê o texto do EPUB e divide-o em parágrafos e frases.
- `talehop/transcribe.py`: transcreve o áudio com marcas de tempo (faster-whisper).
- `talehop/align.py`: alinha a transcrição com o texto do livro.
- `talehop/package.py`: cria o `.tale` (o formato está descrito no topo do ficheiro).
- `talehop/gui_web.py` e `talehop/ui/`: a janela (HTML mostrado pelo WebView2 do Windows, com o
  `pywebview`). Escura por omissão; o botão da lua muda para clara. Precisa do Microsoft Edge
  WebView2, que já vem com o Windows 10 e 11 atualizados.
- `talehop/gui.py`: a janela antiga, em Tkinter. Só é usada se o `pywebview` não estiver instalado.
- `leitor-teste.html`: um leitor simples no browser para verificar um `.tale`.

## Licença

GPL-3.0. O texto completo está no ficheiro `LICENSE`, na raiz do repositório.
