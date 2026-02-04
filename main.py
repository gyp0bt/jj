from __future__ import annotations

from services.service.entry import main as service_main


def main() -> int:
    return service_main()


if __name__ == "__main__":
    raise SystemExit(main())
