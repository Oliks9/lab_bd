import json
import platform
import struct
import sys
import traceback
from pathlib import Path


def check_oracledb():
    import oracledb

    oracledb.ConnectParams(host="localhost", port=1521, service_name="self_check")
    if hasattr(oracledb, "enable_thin_mode"):
        oracledb.enable_thin_mode()
    if not oracledb.is_thin_mode():
        raise RuntimeError("The application requires Oracle Thin mode")
    return {"version": oracledb.__version__, "path": oracledb.__file__, "thin": True}


def check_cryptography():
    import cryptography
    from cryptography.fernet import Fernet

    cipher = Fernet(Fernet.generate_key())
    payload = b"Oracle Quiz dependency check"
    if cipher.decrypt(cipher.encrypt(payload)) != payload:
        raise RuntimeError("Cryptography round-trip failed")
    return {"version": cryptography.__version__, "path": cryptography.__file__}


def check_tkinter():
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    try:
        root.withdraw()
        ttk.Button(root, text="Dependency check").pack()
        root.update_idletasks()
        return {
            "tcl": str(root.tk.call("info", "patchlevel")),
            "tk": str(root.tk.call("package", "require", "Tk")),
        }
    finally:
        root.destroy()


def collect_runtime_report():
    report = {
        "ok": True,
        "python": sys.version,
        "executable": sys.executable,
        "architecture_bits": struct.calcsize("P") * 8,
        "platform": platform.platform(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "checks": {},
    }
    for name, check in (
        ("oracledb", check_oracledb),
        ("cryptography", check_cryptography),
        ("tkinter", check_tkinter),
        ("installation_sql", check_installation_sql),
    ):
        try:
            report["checks"][name] = {"ok": True, **check()}
        except Exception as exc:
            report["ok"] = False
            report["checks"][name] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
    return report


def check_installation_sql():
    from .installer import installation_steps, sql_directory

    steps = installation_steps()
    return {"path": str(sql_directory()), "statements": sum(bool(step.sql) for step in steps)}


def run_self_check(report_path):
    report = collect_runtime_report()
    serialized = json.dumps(report, ensure_ascii=True, indent=2)
    try:
        Path(report_path).write_text(serialized + "\n", encoding="utf-8")
    except OSError as exc:
        if sys.stderr is not None:
            print(f"Cannot write dependency report: {exc}", file=sys.stderr)
        return 2
    if sys.stdout is not None:
        print(serialized)
    return 0 if report["ok"] else 1
