import json
from pathlib import Path
import sys
from pipeline import build

if __name__ == "__main__":
    build(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), strict=True)
