import json
from pathlib import Path

from app.main import app


def main() -> None:
    output_path = Path("openapi.json")
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(app.openapi(), file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"OpenAPI schema exported to: {output_path.resolve()}")


if __name__ == "__main__":
    main()

