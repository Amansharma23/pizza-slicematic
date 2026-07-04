"""Tests for protected Admin API foundation routes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import admin_routes

ORDER_FILTER_CALLS = []


def _user(permissions=None):
    return {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "email": "admin@slicematic.local",
        "full_name": "Aman Admin",
        "status": "active",
        "roles": ["Admin"],
        "permissions": permissions or ["admin.access", "admin.dashboard.read"],
    }


def _client(monkeypatch, user=None):
    monkeypatch.setenv("ADMIN_DEV_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_DEV_EMAIL", "admin@slicematic.local")
    monkeypatch.setattr(admin_routes.admin_db, "get_user_by_email", lambda _: user)
    monkeypatch.setattr(
        admin_routes.admin_db,
        "get_dashboard_metrics",
        lambda: {
            "today": {"total_orders": 0, "revenue": 0, "average_order_value": 0},
            "recent_orders": [],
            "top_pizzas": [],
            "peak_hour": {},
            "low_inventory_alerts": 0,
            "ai_summary": [],
            "ai_insights": [],
        },
    )
    ORDER_FILTER_CALLS.clear()
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_orders",
        lambda **kwargs: ORDER_FILTER_CALLS.append(kwargs) or [],
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "update_order_status",
        lambda order_id, **_: {
            "id": order_id,
            "order_no": "SM-20260702-0001",
            "status": "Confirmed",
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "get_order_detail",
        lambda order_id: {
            "order": {
                "id": order_id,
                "order_no": "SM-20260702-0001",
                "status": "Confirmed",
            },
            "status_history": [{"new_status": "Confirmed"}],
            "payments": [],
            "refunds": [],
            "inventory_deductions": [],
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_menu_items",
        lambda: {"items": []},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "create_menu_item",
        lambda **_: {"id": "menu-1", "name": "Test Pizza"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "update_menu_item",
        lambda item_id, **_: {"id": item_id, "name": "Test Pizza"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "soft_delete_menu_item",
        lambda item_id, **_: {"id": item_id, "is_deleted": True},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "get_pricing_settings",
        lambda: {
            "gst_rate_percent": 18,
            "discount_rate_percent": 10,
            "discount_quantity_threshold": 5,
            "discount_rules": [],
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_price_history",
        lambda **_: [
            {
                "id": "history-1",
                "item_code": "PZ1",
                "menu_item_name": "Margherita",
                "old_price": 199,
                "new_price": 219,
            }
        ],
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "update_pricing_settings",
        lambda **_: {
            "gst_rate_percent": 18,
            "discount_rate_percent": 10,
            "discount_quantity_threshold": 5,
            "discount_rules": [],
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_payments_and_refunds",
        lambda: {"payments": [], "refunds": []},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "request_refund",
        lambda *_, **__: {"id": "refund-1", "status": "Requested"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "decide_refund",
        lambda refund_id, **kwargs: {"id": refund_id, "status": kwargs["status"]},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_inventory",
        lambda: {
            "ingredients": [],
            "transactions": [],
            "requests": [],
            "recipes": [],
            "recipe_coverage": {"coverage_percent": 0},
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "create_ingredient",
        lambda **_: {"id": "ingredient-1", "name": "Cheese"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "update_ingredient",
        lambda ingredient_id, **_: {"id": ingredient_id, "is_active": True},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "adjust_stock",
        lambda ingredient_id, **_: {"id": ingredient_id, "stock_quantity": 10},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "create_inventory_request",
        lambda **_: {"id": "request-1", "status": "Requested"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "decide_inventory_request",
        lambda request_id, **kwargs: {"id": request_id, "status": kwargs["status"]},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "upsert_menu_item_ingredient",
        lambda **_: {"id": "recipe-1", "quantity_per_unit": 1},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "delete_menu_item_ingredient",
        lambda recipe_id, **_: {"id": recipe_id},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "get_analytics_report",
        lambda **_: {
            "totals": {"total_orders": 1},
            "refund_rate": 0,
            "cancellation_rate": 0,
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "generate_ai_insights",
        lambda **_: {
            "provider": "mock",
            "fallback_used": False,
            "provider_error": None,
            "insights": [{"type": "x", "text": "real metric", "metrics": {}}],
            "logs": [],
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "generate_forecast",
        lambda **_: {"method": "test", "baseline": {}, "forecast": []},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_ai_insight_logs",
        lambda **_: [{"id": "log-1", "provider": "mock", "insight_type": "peak"}],
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "get_ai_business_intelligence",
        lambda **_: {
            "provider": "deterministic_mock",
            "demand_forecast": {"forecast": []},
            "peak_rush": {"top_hours": []},
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "simulate_revenue_scenario",
        lambda **kwargs: {
            "method": "deterministic_margin_simulation",
            "inputs": kwargs,
            "projected": {"margin_delta": 100},
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "get_recommendation_impact",
        lambda **_: {"totals": {"accepted": 1}, "by_type": [], "recent": []},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "record_recommendation_event",
        lambda **kwargs: {"id": "event-1", "status": kwargs["status"]},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_customer_feedback",
        lambda **_: {
            "summary": {"status": "active", "totals": {"total": 1}},
            "feedback": [{"id": "feedback-1", "sentiment_label": "positive"}],
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "record_customer_feedback",
        lambda **kwargs: {
            "id": "feedback-1",
            "rating": kwargs["rating"],
            "sentiment_label": "positive",
        },
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "list_notifications",
        lambda: {"logs": []},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "create_mock_notification",
        lambda **_: {"id": "n-1", "status": "mocked"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "get_settings",
        lambda: {"settings": [{"key": "restaurant_name", "value": {"value": "SliceMatic"}}]},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "update_settings",
        lambda **_: {"settings": [{"key": "restaurant_name", "value": {"value": "SliceMatic"}}]},
    )
    monkeypatch.setattr(admin_routes.admin_db, "list_roles", lambda: [{"name": "Admin"}])
    monkeypatch.setattr(
        admin_routes.admin_db,
        "create_staff",
        lambda **_: {"id": "staff-1", "full_name": "Test Staff"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "update_staff",
        lambda staff_id, **_: {"id": staff_id, "full_name": "Test Staff"},
    )
    monkeypatch.setattr(
        admin_routes.admin_db,
        "upsert_discount_rule",
        lambda **_: {"id": "discount-1", "name": "Launch"},
    )
    app = FastAPI()
    app.include_router(admin_routes.router)
    return TestClient(app)


def test_admin_me_requires_bearer_token(monkeypatch):
    client = _client(monkeypatch, _user())
    res = client.get("/admin/me")
    assert res.status_code == 401


def test_admin_me_returns_seeded_user(monkeypatch):
    client = _client(monkeypatch, _user())
    res = client.get("/admin/me", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "admin@slicematic.local"


def test_dashboard_requires_dashboard_permission(monkeypatch):
    client = _client(monkeypatch, _user(["admin.access"]))
    res = client.get("/admin/dashboard", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 403


def test_dashboard_returns_metrics(monkeypatch):
    client = _client(monkeypatch, _user())
    res = client.get("/admin/dashboard", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200
    assert res.json()["dashboard"]["today"]["total_orders"] == 0


def test_admin_json_serializer_handles_uuid():
    from uuid import UUID

    assert (
        admin_routes.admin_db._json({"id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")})
        == '{"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}'
    )


def test_order_status_update_route(monkeypatch):
    user = _user(["admin.access", "orders.update_status"])
    client = _client(monkeypatch, user)
    res = client.put(
        "/admin/orders/order-1/status",
        headers={"Authorization": "Bearer test-token"},
        json={"status": "Confirmed", "reason": "test"},
    )
    assert res.status_code == 200
    assert res.json()["order"]["status"] == "Confirmed"


def test_orders_route_passes_filters(monkeypatch):
    user = _user(["admin.access", "orders.read"])
    client = _client(monkeypatch, user)
    res = client.get(
        "/admin/orders",
        headers={"Authorization": "Bearer test-token"},
        params={
            "status_filter": "Preparing",
            "payment_mode": "UPI",
            "payment_status": "Paid",
            "date_from": "2026-07-01",
            "date_to": "2026-07-04",
            "customer_search": "Aman",
            "source": "staff_pos",
            "total_min": 300,
            "total_max": 900,
            "limit": 25,
        },
    )
    assert res.status_code == 200
    assert ORDER_FILTER_CALLS[-1] == {
        "status_filter": "Preparing",
        "payment_mode": "UPI",
        "payment_status": "Paid",
        "date_from": "2026-07-01",
        "date_to": "2026-07-04",
        "customer_search": "Aman",
        "source": "staff_pos",
        "total_min": 300.0,
        "total_max": 900.0,
        "limit": 25,
    }


def test_order_detail_route(monkeypatch):
    user = _user(["admin.access", "orders.read"])
    client = _client(monkeypatch, user)
    res = client.get(
        "/admin/orders/order-1",
        headers={"Authorization": "Bearer test-token"},
    )
    assert res.status_code == 200
    assert res.json()["order"]["order_no"] == "SM-20260702-0001"
    assert res.json()["status_history"][0]["new_status"] == "Confirmed"


def test_analytics_route(monkeypatch):
    user = _user(["admin.access", "analytics.read"])
    client = _client(monkeypatch, user)
    res = client.get("/admin/analytics", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200
    assert res.json()["analytics"]["totals"]["total_orders"] == 1


def test_ai_insights_and_forecast_routes(monkeypatch):
    user = _user(["admin.access", "ai.insights.read"])
    client = _client(monkeypatch, user)
    insights = client.get(
        "/admin/ai/insights", headers={"Authorization": "Bearer test-token"}
    )
    provider = client.get(
        "/admin/ai/provider-status", headers={"Authorization": "Bearer test-token"}
    )
    logs = client.get(
        "/admin/ai/insight-logs",
        headers={"Authorization": "Bearer test-token"},
        params={"provider": "mock", "limit": 5},
    )
    forecast = client.post(
        "/admin/ai/forecast",
        headers={"Authorization": "Bearer test-token"},
        json={"days": 7},
    )
    intelligence = client.get(
        "/admin/ai/business-intelligence",
        headers={"Authorization": "Bearer test-token"},
        params={"days": 7},
    )
    scenario = client.post(
        "/admin/ai/revenue-scenario",
        headers={"Authorization": "Bearer test-token"},
        json={
            "menu_price_adjustment_percent": 5,
            "ingredient_price_increase_percent": 8,
        },
    )
    impact = client.get(
        "/admin/ai/recommendation-impact",
        headers={"Authorization": "Bearer test-token"},
    )
    event = client.post(
        "/admin/ai/recommendation-events",
        headers={"Authorization": "Bearer test-token"},
        json={
            "recommendation_type": "upsell",
            "recommendation_key": "upsell:test",
            "title": "Suggest cheese",
            "status": "accepted",
            "estimated_value": 20,
            "source_metrics": {"orders": 1},
        },
    )
    feedback = client.get(
        "/admin/ai/customer-feedback",
        headers={"Authorization": "Bearer test-token"},
    )
    created_feedback = client.post(
        "/admin/ai/customer-feedback",
        headers={"Authorization": "Bearer test-token"},
        json={
            "customer_name": "Aman",
            "channel": "app",
            "rating": 5,
            "feedback_text": "Great pizza and fast delivery.",
        },
    )
    assert insights.status_code == 200
    assert insights.json()["insights"][0]["text"] == "real metric"
    assert provider.status_code == 200
    assert provider.json()["provider_status"]["fallback_provider"] == "mock"
    assert logs.status_code == 200
    assert logs.json()["logs"][0]["provider"] == "mock"
    assert forecast.status_code == 200
    assert forecast.json()["forecast"]["method"] == "test"
    assert intelligence.status_code == 200
    assert intelligence.json()["ai"]["provider"] == "deterministic_mock"
    assert scenario.status_code == 200
    assert scenario.json()["scenario"]["method"] == "deterministic_margin_simulation"
    assert impact.status_code == 200
    assert impact.json()["impact"]["totals"]["accepted"] == 1
    assert event.status_code == 200
    assert event.json()["event"]["status"] == "accepted"
    assert feedback.status_code == 200
    assert feedback.json()["summary"]["status"] == "active"
    assert created_feedback.status_code == 200
    assert created_feedback.json()["feedback"]["sentiment_label"] == "positive"


def test_notifications_and_settings_routes(monkeypatch):
    user = _user(["admin.access", "audit.read"])
    client = _client(monkeypatch, user)
    notifications = client.get(
        "/admin/notifications", headers={"Authorization": "Bearer test-token"}
    )
    created = client.post(
        "/admin/notifications/mock",
        headers={"Authorization": "Bearer test-token"},
        json={
            "channel": "mock",
            "recipient": "9876543210",
            "template_name": "test",
            "payload": {"message": "hello"},
        },
    )
    settings = client.get(
        "/admin/settings", headers={"Authorization": "Bearer test-token"}
    )
    updated = client.put(
        "/admin/settings",
        headers={"Authorization": "Bearer test-token"},
        json={"values": {"restaurant_name": "SliceMatic"}},
    )
    assert notifications.status_code == 200
    assert created.json()["notification"]["status"] == "mocked"
    assert settings.status_code == 200
    assert updated.status_code == 200


def test_staff_create_update_and_discount_routes(monkeypatch):
    user = _user(["admin.access", "staff.manage", "discounts.manage"])
    client = _client(monkeypatch, user)
    staff = client.get("/admin/staff", headers={"Authorization": "Bearer test-token"})
    created = client.post(
        "/admin/staff",
        headers={"Authorization": "Bearer test-token"},
        json={
            "full_name": "Test Staff",
            "email": "test.staff@slicematic.local",
            "role_name": "Admin",
        },
    )
    updated = client.put(
        "/admin/staff/staff-1",
        headers={"Authorization": "Bearer test-token"},
        json={"full_name": "Test Staff", "role_name": "Admin", "is_active": True},
    )
    discount = client.put(
        "/admin/discounts",
        headers={"Authorization": "Bearer test-token"},
        json={
            "name": "Launch",
            "discount_percent": 10,
            "threshold_amount": 0,
            "is_active": True,
        },
    )
    assert staff.status_code == 200
    assert created.status_code == 200
    assert updated.status_code == 200
    assert discount.status_code == 200


def test_menu_create_update_delete_routes(monkeypatch):
    user = _user(["admin.access", "menu.manage"])
    client = _client(monkeypatch, user)
    menu = client.get("/admin/menu", headers={"Authorization": "Bearer test-token"})
    created = client.post(
        "/admin/menu",
        headers={"Authorization": "Bearer test-token"},
        json={
            "category": "pizza",
            "item_code": "PX",
            "name": "Test Pizza",
            "price": 199,
            "is_available": True,
        },
    )
    updated = client.put(
        "/admin/menu/menu-1",
        headers={"Authorization": "Bearer test-token"},
        json={"name": "Test Pizza", "price": 209, "is_available": True},
    )
    deleted = client.delete(
        "/admin/menu/menu-1", headers={"Authorization": "Bearer test-token"}
    )
    assert menu.status_code == 200
    assert created.status_code == 200
    assert updated.status_code == 200
    assert deleted.json()["item"]["is_deleted"] is True


def test_pricing_and_price_history_routes(monkeypatch):
    user = _user(["admin.access", "pricing.manage"])
    client = _client(monkeypatch, user)
    pricing = client.get("/admin/pricing", headers={"Authorization": "Bearer test-token"})
    history = client.get(
        "/admin/pricing/price-history",
        headers={"Authorization": "Bearer test-token"},
        params={"limit": 20},
    )
    updated = client.put(
        "/admin/pricing",
        headers={"Authorization": "Bearer test-token"},
        json={
            "gst_rate_percent": 18,
            "discount_rate_percent": 10,
            "discount_quantity_threshold": 5,
            "reason": "test",
        },
    )
    assert pricing.status_code == 200
    assert history.status_code == 200
    assert history.json()["price_history"][0]["new_price"] == 219
    assert updated.status_code == 200


def test_refund_decision_routes(monkeypatch):
    user = _user(["admin.access", "refunds.manage"])
    client = _client(monkeypatch, user)
    payments = client.get(
        "/admin/payments", headers={"Authorization": "Bearer test-token"}
    )
    refund = client.post(
        "/admin/refunds",
        headers={"Authorization": "Bearer test-token"},
        json={"order_id": "order-1", "amount": 10, "reason": "test"},
    )
    decided = client.put(
        "/admin/refunds/refund-1/decision",
        headers={"Authorization": "Bearer test-token"},
        json={"status": "Approved", "reason": "ok"},
    )
    assert payments.status_code == 200
    assert refund.json()["refund"]["status"] == "Requested"
    assert decided.json()["refund"]["status"] == "Approved"


def test_inventory_request_decision_routes(monkeypatch):
    user = _user(["admin.access", "inventory.manage"])
    client = _client(monkeypatch, user)
    inventory = client.get(
        "/admin/inventory", headers={"Authorization": "Bearer test-token"}
    )
    adjusted = client.post(
        "/admin/inventory/ingredient-1/adjust",
        headers={"Authorization": "Bearer test-token"},
        json={"transaction_type": "StockIn", "quantity": 2, "reason": "test"},
    )
    request = client.post(
        "/admin/inventory/requests",
        headers={"Authorization": "Bearer test-token"},
        json={
            "ingredient_id": "ingredient-1",
            "requested_quantity": 5,
            "reason": "test",
        },
    )
    decided = client.put(
        "/admin/inventory/requests/request-1/decision",
        headers={"Authorization": "Bearer test-token"},
        json={"status": "Approved", "reason": "ok"},
    )
    assert inventory.status_code == 200
    assert adjusted.status_code == 200
    assert request.json()["request"]["status"] == "Requested"
    assert decided.json()["request"]["status"] == "Approved"


def test_inventory_ingredient_crud_routes(monkeypatch):
    user = _user(["admin.access", "inventory.manage"])
    client = _client(monkeypatch, user)
    created = client.post(
        "/admin/inventory/ingredients",
        headers={"Authorization": "Bearer test-token"},
        json={
            "name": "Cheese",
            "unit": "kg",
            "stock_quantity": 3,
            "reorder_threshold": 1,
        },
    )
    updated = client.put(
        "/admin/inventory/ingredients/ingredient-1",
        headers={"Authorization": "Bearer test-token"},
        json={
            "name": "Cheese",
            "unit": "kg",
            "reorder_threshold": 2,
            "is_active": True,
        },
    )
    assert created.status_code == 200
    assert created.json()["ingredient"]["name"] == "Cheese"
    assert updated.status_code == 200


def test_inventory_recipe_mapping_routes(monkeypatch):
    user = _user(["admin.access", "inventory.manage"])
    client = _client(monkeypatch, user)
    upserted = client.put(
        "/admin/inventory/recipes",
        headers={"Authorization": "Bearer test-token"},
        json={
            "menu_item_id": "menu-1",
            "ingredient_id": "ingredient-1",
            "quantity_per_unit": 1,
            "reason": "test",
        },
    )
    deleted = client.delete(
        "/admin/inventory/recipes/recipe-1",
        headers={"Authorization": "Bearer test-token"},
    )
    assert upserted.status_code == 200
    assert upserted.json()["recipe"]["quantity_per_unit"] == 1
    assert deleted.status_code == 200
