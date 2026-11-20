import os
from pathlib import Path

from ..utils.helpers import read_config_file


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "examples" / "sfo_sjc" / "config.json"
CONFIG_PATH = Path(os.environ.get("VERTISIM_CONFIG", DEFAULT_CONFIG_PATH)).expanduser().resolve()
CONFIG = read_config_file(str(CONFIG_PATH))
