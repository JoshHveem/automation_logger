from __future__ import annotations

import os
import sys
from typing import Optional


def resolve_entry_script_path(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        p = os.path.abspath(explicit)
        return p if os.path.isfile(p) else None

    # 1) __main__.__file__ (best signal for normal execution)
    try:
        import __main__  # type: ignore
        main_file = getattr(__main__, "__file__", None)
        if main_file:
            p = os.path.abspath(main_file)
            if os.path.isfile(p):
                return p
    except Exception:
        pass

    # 2) sys.argv[0]
    if sys.argv and sys.argv[0]:
        p = os.path.abspath(sys.argv[0])
        if os.path.isfile(p):
            return p

    # 3) stack inspection fallback (optional, but convenient)
    try:
        for frame_info in inspect.stack():
            filename = frame_info.filename
            # ignore stdlib + this package frames
            if not filename:
                continue
            if "automation_logger" in filename.replace("\\", "/"):
                continue
            p = os.path.abspath(filename)
            if os.path.isfile(p):
                return p
    except Exception:
        pass

    return None


def resolve_path(path_mode: str, script_path: Optional[str]) -> str:
    """
    path_mode:
      - 'cwd': current working directory (default)
      - 'script': directory of the calling script (requires script_path)
    """
    path_mode = (path_mode or "cwd").strip().lower()
    if path_mode == "script" and script_path:
        return os.path.dirname(os.path.abspath(script_path))
    return os.getcwd()
