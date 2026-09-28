from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))


def pytest_addoption(parser):
    parser.addoption("--agent-traces-dir", default=None,
                     help="Directorio de trazas reales ya capturadas; sin llamadas de red")
