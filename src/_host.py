from __future__ import annotations

import os
import platform
import socket
import sys
from typing import Any, Dict


def get_host_context() -> Dict[str, Any]:
    """Host/device context for troubleshooting across multiple servers."""
    host_name = socket.gethostname()
    fqdn = socket.getfqdn()

    host_ip = None
    try:
        host_ip = socket.gethostbyname(host_name)
    except Exception:
        host_ip = None

    return {
        "host_name": host_name,
        "computername": os.getenv("COMPUTERNAME"),
        "fqdn": fqdn,
        "host_ip": host_ip,
        "platform": platform.platform(),
        "python": sys.version,
    }
