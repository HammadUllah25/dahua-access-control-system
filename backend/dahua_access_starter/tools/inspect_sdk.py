"""Inspect symbols exposed by the installed Dahua NetSDK Python wheel.

Run this with the same Windows virtual environment in which NetSDK-2.0.0.1
is installed. Save the output and share it before we implement card CRUD,
access schedules, door parameters and access-record queries.
"""

from __future__ import annotations

import importlib
import inspect
from ctypes import sizeof


def show_module(module_name: str) -> None:
    print(f"\n{'=' * 90}\nMODULE: {module_name}\n{'=' * 90}")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        print(f"IMPORT ERROR: {exc}")
        return

    for name in sorted(dir(module)):
        if any(token in name.lower() for token in (
            "record", "access", "card", "login", "ctrl", "config", "door", "time"
        )):
            value = getattr(module, name)
            if inspect.isclass(value):
                print(f"\nCLASS {name}")
                try:
                    print(f"  sizeof: {sizeof(value)}")
                except Exception:
                    pass
                fields = getattr(value, "_fields_", None)
                if fields:
                    for field in fields:
                        print(f"  field: {field}")
                members = getattr(value, "__members__", None)
                if members:
                    print(f"  enum: {members}")
            elif hasattr(value, "__members__"):
                print(f"ENUM {name}: {value.__members__}")
            else:
                print(f"SYMBOL {name}: {value!r}")


def main() -> None:
    try:
        from NetSDK.NetSDK import NetClient
        client = NetClient()
        print("NetClient imported successfully")
        print("NetClient methods:")
        for name in sorted(dir(client)):
            if not name.startswith("_") and any(token in name.lower() for token in (
                "init", "login", "logout", "control", "find", "record", "config", "last", "error"
            )):
                member = getattr(client, name)
                try:
                    signature = inspect.signature(member)
                except Exception:
                    signature = "<signature unavailable>"
                print(f"  {name}{signature}")
    except Exception as exc:
        print(f"Could not inspect NetClient: {exc}")

    show_module("NetSDK.SDK_Enum")
    show_module("NetSDK.SDK_Struct")
    print("\nInspection complete. Do not post device passwords or secret keys with this output.")


if __name__ == "__main__":
    main()
