"""Tests for the additive /api/auth/* routes (user + role management).

Run without keys/DB: db.users is replaced by an in-memory fake (the same module
object api.auth imports), so signup/login/lockout/role logic is exercised
end-to-end through the FastAPI router with real bcrypt hashing and real JWTs.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import security
from db import users as db_users


class FakeUsersDB:
    """In-memory stand-in for the app_users table (incl. the emp_id trigger)."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self._emp_seq = 0

    def create_user(
        self, *, role, name, secret_hash, phone=None, email=None, address=None
    ):
        if phone and self._find("phone", phone):
            raise RuntimeError("duplicate phone")
        row = {
            "id": str(uuid.uuid4()),
            "role": role,
            "name": name,
            "phone": phone,
            "email": email,
            "emp_id": None,
            "secret_hash": secret_hash,
            "address": address,
            "is_active": True,
            "failed_attempts": 0,
            "locked_until": None,
        }
        if role in db_users.EMPLOYEE_ROLES:
            self._emp_seq += 1
            row["emp_id"] = f"SMEMP{self._emp_seq:03d}"
        self.rows[row["id"]] = row
        public = dict(row)
        public.pop("secret_hash")
        return public

    def _find(self, field, value):
        return next((r for r in self.rows.values() if r.get(field) == value), None)

    def get_by_login(self, field, value):
        row = self._find(field, value)
        return dict(row) if row else None

    def get_by_id(self, user_id):
        row = self.rows.get(user_id)
        if not row:
            return None
        public = dict(row)
        public.pop("secret_hash")
        return public

    def update_user(self, user_id, fields):
        row = self.rows.get(user_id)
        if not row:
            return None
        row.update(fields)
        public = dict(row)
        public.pop("secret_hash")
        return public

    def record_login_failure(self, user_id, failed_attempts, locked_until):
        self.rows[user_id]["failed_attempts"] = failed_attempts
        self.rows[user_id]["locked_until"] = locked_until

    def record_login_success(self, user_id):
        self.rows[user_id]["failed_attempts"] = 0
        self.rows[user_id]["locked_until"] = None

    def list_employees(self):
        return [
            self.get_by_id(rid)
            for rid, r in self.rows.items()
            if r["role"] in db_users.EMPLOYEE_ROLES
        ]


@pytest.fixture
def client(monkeypatch):
    fake = FakeUsersDB()
    for fn in (
        "create_user",
        "get_by_login",
        "get_by_id",
        "update_user",
        "record_login_failure",
        "record_login_success",
        "list_employees",
    ):
        monkeypatch.setattr(db_users, fn, getattr(fake, fn))
    from api import routes

    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), fake


SIGNUP = {
    "name": "Aarav Sharma",
    "phone": "9876543210",
    "pin": "123456",
    "confirm_pin": "123456",
}


def _signup(c, **over):
    return c.post("/api/auth/signup", json={**SIGNUP, **over}).json()


def _login(c, role="user", identifier="9876543210", secret="123456"):
    return c.post(
        "/api/auth/login",
        json={"role": role, "identifier": identifier, "secret": secret},
    ).json()


# ------------------------------ signup ------------------------------------ #


def test_signup_creates_customer_and_returns_token(client):
    c, fake = client
    res = _signup(c)
    assert res["ok"] is True
    assert res["user"]["role"] == "user"
    assert "secret_hash" not in res["user"]
    claims = security.decode_token(res["token"])
    assert claims["role"] == "user"
    # PIN is stored hashed, never in plaintext
    row = fake.get_by_login("phone", "9876543210")
    assert row["secret_hash"] != "123456"


def test_signup_rejects_bad_pin_and_mismatch(client):
    c, _ = client
    assert "pin" in _signup(c, pin="12345", confirm_pin="12345")["errors"]
    assert "pin" in _signup(c, pin="12345a", confirm_pin="12345a")["errors"]
    assert "pin" in _signup(c, confirm_pin="654321")["errors"]


def test_signup_rejects_invalid_name_and_phone(client):
    c, _ = client
    assert "name" in _signup(c, name="   ")["errors"]
    assert "phone" in _signup(c, phone="1234567890")["errors"]  # starts with 1
    assert "phone" in _signup(c, phone="98765")["errors"]


def test_signup_duplicate_phone_rejected(client):
    c, _ = client
    assert _signup(c)["ok"] is True
    res = _signup(c, name="Someone Else")
    assert res["ok"] is False
    assert "already registered" in res["errors"]["phone"]


# ------------------------------ login -------------------------------------- #


def test_login_success_and_me_roundtrip(client):
    c, _ = client
    _signup(c)
    res = _login(c)
    assert res["ok"] is True
    me = c.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {res['token']}"}
    ).json()
    assert me["ok"] is True
    assert me["user"]["phone"] == "9876543210"


def test_login_wrong_pin_generic_error(client):
    c, _ = client
    _signup(c)
    res = _login(c, secret="000000")
    assert res["ok"] is False
    assert "credentials" in res["errors"]


def test_login_unknown_account_same_generic_error(client):
    c, _ = client
    _signup(c)
    wrong = _login(c, secret="000000")["errors"]["credentials"]
    unknown = _login(c, identifier="9999999999")["errors"]["credentials"]
    assert wrong == unknown  # don't reveal which part failed


def test_login_locks_after_five_failures(client):
    c, fake = client
    _signup(c)
    for _ in range(security.MAX_FAILED_ATTEMPTS):
        res = _login(c, secret="000000")
    assert "Too many wrong attempts" in res["errors"]["credentials"]
    # Even the CORRECT pin is refused while locked
    res = _login(c)
    assert res["ok"] is False
    assert "Try again in" in res["errors"]["credentials"]


def test_login_success_resets_failure_count(client):
    c, fake = client
    _signup(c)
    _login(c, secret="000000")
    assert _login(c)["ok"] is True
    row = fake.get_by_login("phone", "9876543210")
    assert row["failed_attempts"] == 0


def test_login_role_must_match_account(client):
    c, fake = client
    fake.create_user(
        role="staff",
        name="Kiosk One",
        phone="9812345678",
        secret_hash=security.hash_secret("111111"),
    )
    # staff creds on the delivery screen -> generic failure
    res = _login(c, role="delivery", identifier="SMEMP001", secret="111111")
    assert res["ok"] is False
    assert _login(c, role="staff", identifier="SMEMP001", secret="111111")["ok"]


def test_login_deactivated_account_refused(client):
    c, fake = client
    emp = fake.create_user(
        role="delivery",
        name="Rider One",
        phone="9800000001",
        secret_hash=security.hash_secret("222222"),
    )
    fake.update_user(emp["id"], {"is_active": False})
    res = _login(c, role="delivery", identifier=emp["emp_id"], secret="222222")
    assert "deactivated" in res["errors"]["credentials"]


def test_me_requires_token(client):
    c, _ = client
    assert c.get("/api/auth/me").status_code == 401
    assert (
        c.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code
        == 401
    )


# ------------------------------ address ------------------------------------ #


def test_address_update_roundtrip(client):
    c, _ = client
    token = _signup(c)["token"]
    res = c.put(
        "/api/auth/me/address",
        json={
            "address": [
                {"label": "Home", "line": "D-42, New Ashok Nagar", "isDefault": True}
            ]
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert res["ok"] is True
    assert res["user"]["address"][0]["line"] == "D-42, New Ashok Nagar"


def test_address_rejects_empty_line(client):
    c, _ = client
    token = _signup(c)["token"]
    res = c.put(
        "/api/auth/me/address",
        json={"address": [{"label": "Home", "line": "   "}]},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert res["ok"] is False


# ------------------------- employee management ----------------------------- #


def _admin_token(fake):
    admin = fake.create_user(
        role="admin",
        name="Boss",
        email="admin@slicematic.in",
        secret_hash=security.hash_secret("supersecret1"),
    )
    return security.issue_token(admin["id"], "admin")


EMP = {
    "name": "Kitchen Guy",
    "phone": "9811111111",
    "role": "kitchen_staff",
    "pin": "445566",
}


def test_employee_create_requires_admin(client):
    c, fake = client
    customer_token = _signup(c)["token"]
    assert c.post("/api/auth/employees", json=EMP).status_code == 401
    assert (
        c.post(
            "/api/auth/employees",
            json=EMP,
            headers={"Authorization": f"Bearer {customer_token}"},
        ).status_code
        == 403
    )


def test_admin_creates_employee_with_generated_emp_id(client):
    c, fake = client
    headers = {"Authorization": f"Bearer {_admin_token(fake)}"}
    res = c.post("/api/auth/employees", json=EMP, headers=headers).json()
    assert res["ok"] is True
    emp = res["employee"]
    assert emp["emp_id"] == "SMEMP001"
    assert emp["role"] == "kitchen_staff"
    # and that employee can now sign in on the matching surface
    assert (
        _login(c, role="kitchen_staff", identifier="SMEMP001", secret="445566")["ok"]
        is True
    )
    listed = c.get("/api/auth/employees", headers=headers).json()
    assert len(listed["employees"]) == 1


def test_employee_create_rejects_bad_role_and_pin(client):
    c, fake = client
    headers = {"Authorization": f"Bearer {_admin_token(fake)}"}
    assert (
        "role"
        in c.post(
            "/api/auth/employees", json={**EMP, "role": "admin"}, headers=headers
        ).json()["errors"]
    )
    assert (
        "pin"
        in c.post(
            "/api/auth/employees", json={**EMP, "pin": "12"}, headers=headers
        ).json()["errors"]
    )


def test_admin_resets_pin_and_deactivates(client):
    c, fake = client
    headers = {"Authorization": f"Bearer {_admin_token(fake)}"}
    emp = c.post("/api/auth/employees", json=EMP, headers=headers).json()["employee"]

    res = c.patch(
        f"/api/auth/employees/{emp['id']}", json={"pin": "999999"}, headers=headers
    ).json()
    assert res["ok"] is True
    assert (
        _login(c, role="kitchen_staff", identifier=emp["emp_id"], secret="999999")["ok"]
        is True
    )

    res = c.patch(
        f"/api/auth/employees/{emp['id']}", json={"is_active": False}, headers=headers
    ).json()
    assert res["employee"]["is_active"] is False
    refused = _login(c, role="kitchen_staff", identifier=emp["emp_id"], secret="999999")
    assert refused["ok"] is False


def test_admin_cannot_patch_non_employee(client):
    c, fake = client
    headers = {"Authorization": f"Bearer {_admin_token(fake)}"}
    customer = _signup(c)["user"]
    res = c.patch(
        f"/api/auth/employees/{customer['id']}", json={"pin": "999999"}, headers=headers
    ).json()
    assert res["ok"] is False
