"""Stage 2 judge-friendly smoke test.

Starts the app with swapped menu files, places one API order, verifies pricing,
and confirms the order log was written. Smoke-test logs are written under
database/smoke_test_data so they can be shown to judges without changing the
real local order history.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("SMOKE_PORT", "7870"))
BASE_URL = f"http://127.0.0.1:{PORT}"
SMOKE_DATA_DIR = ROOT / "database" / "smoke_test_data"
SMOKE_LOG_PATH = SMOKE_DATA_DIR / "smoke_orders_log.txt"

# Set to True when you want the script to delete database/smoke_test_data after
# verification. Keep False when you want to show the smoke log to a judge.
DELETE_SMOKE_DATA_AFTER_TEST = False


def write_swapped_menu(menu_dir: Path) -> None:
    menu_dir.mkdir(parents=True, exist_ok=True)
    (menu_dir / "Types_of_Base.txt").write_text(
        "B9;Judge Base;100\nB10;Backup Base;120\n",
        encoding="utf-8",
    )
    (menu_dir / "Types_of_Pizza.txt").write_text(
        "P9;Judge Pizza;200\nP10;Backup Pizza;220\n",
        encoding="utf-8",
    )
    (menu_dir / "Types_of_Toppings.txt").write_text(
        "T9;Judge Topping;50\nT10;Backup Topping;70\n",
        encoding="utf-8",
    )


def request_json(path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode("utf-8"))


def wait_for_app(proc: subprocess.Popen, output_path: Path) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            output = output_path.read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(f"App exited early.\n\n{output}")
        try:
            health = request_json("/api/health")
            if health.get("status") == "ok":
                return
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(1)
    output = output_path.read_text(encoding="utf-8", errors="replace")
    raise RuntimeError(f"App did not become healthy on port {PORT}.\n\n{output}")


def assert_money(actual: float, expected: float, label: str) -> None:
    if round(float(actual), 2) != expected:
        raise AssertionError(f"{label}: expected {expected:.2f}, got {float(actual):.2f}")


def main() -> int:
    print("Starting Stage 2 smoke test...")
    if SMOKE_DATA_DIR.exists():
        shutil.rmtree(SMOKE_DATA_DIR)
    SMOKE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="slicematic_stage2_") as tmp:
        tmp_path = Path(tmp)
        menu_dir = tmp_path / "swapped_menu"
        output_path = tmp_path / "app_output.log"
        write_swapped_menu(menu_dir)

        env = os.environ.copy()
        env["PORT"] = str(PORT)
        env["MENU_DIR"] = str(menu_dir)
        env["DATABASE_DIR"] = str(SMOKE_DATA_DIR)
        env["PYTHONIOENCODING"] = "utf-8"

        with output_path.open("w", encoding="utf-8") as output:
            proc = subprocess.Popen(
                [sys.executable, "app.py"],
                cwd=ROOT,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
            )

        try:
            wait_for_app(proc, output_path)
            print("App started.")

            menu = request_json("/api/menu")
            if menu["bases"][0]["name"] != "Judge Base":
                raise AssertionError("Swapped menu was not loaded.")
            print("Swapped menu loaded successfully.")

            order = request_json(
                "/api/order",
                {
                    "name": "Judge Tester",
                    "phone": "9876543210",
                    "base_id": "B9",
                    "pizza_id": "P9",
                    "topping_id": "T9",
                    "quantity": "5",
                    "payment_mode": "3",
                },
            )
            if not order.get("ok"):
                raise AssertionError(f"Order failed: {order}")
            print("Order placed successfully.")

            bill = order["bill"]
            assert_money(bill["unit_price"], 350.00, "unit_price")
            assert_money(bill["subtotal"], 1750.00, "subtotal")
            assert_money(bill["discount"], 175.00, "discount")
            assert_money(bill["gst"], 283.50, "gst")
            assert_money(bill["total"], 1858.50, "total")
            print("Bill verified.")

            log_path = SMOKE_DATA_DIR / "orders_log.txt"
            if not log_path.exists():
                raise AssertionError("orders_log.txt was not created.")
            log_text = log_path.read_text(encoding="utf-8")
            required = [
                "Judge Tester",
                "9876543210",
                "Judge Base",
                "Judge Pizza",
                "Judge Topping",
                "350.00",
                "5",
                "1858.50",
                "UPI",
            ]
            missing = [item for item in required if item not in log_text]
            if missing:
                raise AssertionError(f"Order log missing values: {missing}")
            log_path.replace(SMOKE_LOG_PATH)
            print("Order log verified.")
            print(f"Smoke log saved: {SMOKE_LOG_PATH}")
            print("PASS")
            return 0
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            if DELETE_SMOKE_DATA_AFTER_TEST and SMOKE_DATA_DIR.exists():
                shutil.rmtree(SMOKE_DATA_DIR)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
