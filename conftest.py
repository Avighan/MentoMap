"""Root conftest: ensure both `import schemas` (bare) and `from backend.X import Y`
work regardless of where pytest is invoked from."""
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
