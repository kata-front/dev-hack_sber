import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


def main() -> None:
    output_path = PROJECT_ROOT / "openapi.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(app.openapi(), file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"OpenAPI schema exported to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
