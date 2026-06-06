from __future__ import annotations

import argparse

from ai2thor.controller import Controller
from ai2thor import platform


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["cloudrendering", "linux64"], default="cloudrendering")
    args = parser.parse_args()

    selected_platform = {
        "cloudrendering": platform.CloudRendering,
        "linux64": platform.Linux64,
    }[args.platform]

    print(f"before controller platform={args.platform}", flush=True)
    controller = Controller(
        platform=selected_platform,
        scene="FloorPlan1",
        width=300,
        height=300,
    )
    print("after controller", flush=True)
    controller.stop()
    print("stopped", flush=True)


if __name__ == "__main__":
    main()
