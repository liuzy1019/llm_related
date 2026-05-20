"""pytest 配置

强制开启 MOCK_LLM，让测试在没有任何 API Key 的环境下也能跑通。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MOCK_LLM", "1")
os.environ.setdefault("CHECKPOINTER", "memory")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
