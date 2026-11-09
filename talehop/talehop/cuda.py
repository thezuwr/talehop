"""Escolha entre placa gráfica NVIDIA (CUDA) e processador.

No Windows, as bibliotecas da NVIDIA (cuBLAS, cuDNN) vêm em pacotes pip
(nvidia-cublas-cu12, nvidia-cudnn-cu12) ou, no programa instalado, do suporte
descarregado à parte (gpu_pack), e têm de ser adicionadas ao caminho de DLLs
antes de o ctranslate2 as procurar.
"""
import ctypes
import importlib.util
import os
import sys

from . import gpu_pack
from .i18n import t

_dll_dirs = set()


def _add_nvidia_dlls():
    """Junta as pastas das DLLs da NVIDIA (pode chamar-se outra vez depois de descarregar o suporte)."""
    if sys.platform != "win32":
        return
    dirs = list(gpu_pack.dll_dirs())
    spec = importlib.util.find_spec("nvidia")
    if spec is not None and spec.submodule_search_locations:
        for base in spec.submodule_search_locations:
            for sub in ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc"):
                dirs.append(os.path.join(base, sub, "bin"))
    for d in dirs:
        if d not in _dll_dirs and os.path.isdir(d):
            _dll_dirs.add(d)
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


_LIBS = ("cublas64_12.dll", "cudnn_ops64_9.dll")
last_error = None  # porque é que as bibliotecas da placa não carregaram (para o registo)


def _cuda_libs_ok():
    """Sem cuBLAS/cuDNN o ctranslate2 pode fechar o programa sem erro; confirma antes."""
    global last_error
    if sys.platform != "win32":
        return True  # Linux: confia no ctranslate2
    for name in _LIBS:
        try:
            _load(name)
        except OSError as e:
            last_error = f"{name}: {e}"
            return False
    last_error = None
    return True


# procurar as dependências na pasta da própria DLL e nas pastas normais (incluindo as do add_dll_directory)
_SEARCH = 0x00000100 | 0x00001000  # LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS


def _load(name):
    """Carrega uma DLL da NVIDIA pelo caminho completo, se estiver no suporte descarregado: pelo nome
    só, o Windows procura-a de maneiras diferentes conforme o programa foi aberto (atalho ou não)."""
    for d in gpu_pack.dll_dirs():
        path = os.path.join(d, name)
        if os.path.isfile(path):
            return ctypes.WinDLL(path, winmode=_SEARCH)
    return ctypes.WinDLL(name)


def diagnose():
    """Tudo o que conta para usar a placa, para perceber um problema (TALEHOP_GPU_CHECK)."""
    _add_nvidia_dlls()
    out = {"frozen": bool(getattr(sys, "frozen", False)), "dll_dirs": sorted(_dll_dirs),
           "pack_installed": gpu_pack.installed()}
    try:
        import ctranslate2
        out["ctranslate2"] = ctranslate2.__version__
        out["cuda_devices"] = ctranslate2.get_cuda_device_count()
    except Exception as e:
        out["ctranslate2_error"] = repr(e)
    for name in _LIBS + ("cublasLt64_12.dll", "cudnn_graph64_9.dll", "cudnn64_9.dll") if sys.platform == "win32" else ():
        try:
            _load(name)
            out[name] = "ok"
        except OSError as e:
            out[name] = repr(e)
    out["path_head"] = os.environ.get("PATH", "").split(os.pathsep)[:6]
    out["cwd"] = os.getcwd()
    return out


def pick_device(log=print):
    _add_nvidia_dlls()
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            if _cuda_libs_ok():
                log(t("gpu"))
                return "cuda", "float16"
            log(t("gpu_no_libs"))
    except Exception as e:
        log(t("gpu_failed", error=e))
    log(t("cpu"))
    return "cpu", "int8"


def summary():
    """Para a janela: {"gpu": se vai usar a placa NVIDIA, "name": o nome da placa, se se souber,
    "needs_pack": há placa NVIDIA mas faltam as bibliotecas (o programa pode descarregá-las)}."""
    _add_nvidia_dlls()
    try:
        import ctranslate2
        card = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        card = False
    libs = card and _cuda_libs_ok()
    gpu = card and libs
    # suporte já descarregado mas não carrega: descarregar outra vez não resolve, o motivo vai para o registo
    broken = card and not libs and gpu_pack.installed()
    name = None
    if card:
        try:
            import subprocess
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True,
                timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            name = out.stdout.strip().splitlines()[0].replace("NVIDIA GeForce ", "NVIDIA ") or None
        except Exception:
            pass
    return {"gpu": gpu, "name": name, "needs_pack": card and not libs and not broken,
            "libs_error": last_error if broken else None, "mac": sys.platform == "darwin"}


def describe():
    """Texto curto para a janela: onde vai correr."""
    _add_nvidia_dlls()
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0 and _cuda_libs_ok():
            return "Placa gráfica NVIDIA: sim (rápido)"
    except Exception:
        pass
    return "Placa gráfica NVIDIA: não encontrada (vai usar o processador, mais lento)"
