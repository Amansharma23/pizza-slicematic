import os
import sys
import uuid
import random
import json
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.getcwd())

from api import security

def generate_random_name():
    first_names = [
        "Aarav", "Vihaan", "Vivaan", "Ananya", "Diya", "Priya", "Rahul", "Aditya",
        "Sai", "Arjun", "Rohan", "Kabir", "Meera", "Neha", "Ishaan", "Aanya",
        "Karan", "Siddharth", "Aisha", "Dev", "Sneha", "Riya", "Amit", "Pooja",
        "Vikram", "Sunita", "Rajesh", "Kiran", "Sanjay", "Geeta", "Vijay", "Anita",
        "Ramesh", "Deepa", "Suresh", "Lata", "Anil", "Rekha", "Sunil", "Maya",
        "Harish", "Shanti", "Jitendra", "Kusum", "Pradeep", "Usha", "Manish", "Prem",
        "Alok", "Sudha"
    ]
    last_names = [
        "Sharma", "Verma", "Gupta", "Iyer", "Nair", "Singh", "Patel", "Mehta",
        "Reddy", "Kumar", "Rao", "Joshi", "Sen", "Das", "Roy", "Banerjee",
        "Mukherjee", "Chatterjee", "Mishra", "Pandey", "Trivedi", "Pathak", "Dubey",
        "Kulkarni", "Deshmukh", "Pillai", "Menon", "Bose", "Dutta", "Choudhury",
        "Saxena", "Srivastava", "Malhotra", "Kapoor", "Khanna", "Chawla", "Bhasin",
        "Grover", "Anand", "Gill", "Bahl", "Dhillon", "Sodhi", "Johar", "Seth",
        "Nangia", "Wadhwa", "Juneja", "Madan", "Chhabra"
    ]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_delhi_address():
    areas = [
        "Sector 15, Dwarka", "Sector 62, Noida", "Mayur Vihar Phase 1", 
        "Laxmi Nagar", "Preet Vihar", "Indirapuram, Ghaziabad", 
        "Vasundhara Enclave", "Connaught Place", "Saket", "Vasant Kunj",
        "Rajouri Garden", "Karol Bagh", "Shalimar Bagh", "Pitampura",
        "Rohini Sector 9", "Janakpuri", "Defence Colony", "Greater Kailash 2",
        "Green Park", "South Extension"
    ]
    blocks = ["A", "B", "C", "D", "E", "F", "G", "H", "Pocket-1", "Pocket-2", "Flat-A", "Flat-B"]
    house_num = random.randint(1, 250)
    return f"{random.choice(blocks)}-{house_num}, {random.choice(areas)}, New Delhi 110096"

def main():
    target_dir = os.path.join(os.getcwd(), "Aman", "Bulk Update Queries")
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"Creating SQL bulk update queries under {target_dir}...")
    
    # ---------------------------------------------------------
    # Definitions
    # ---------------------------------------------------------
    cat_base_id = "e9971727-ee4b-4254-ab6b-12517d3e1eb5"
    cat_pizza_id = "688e7faf-5151-4eb9-b4c3-6d98c8953ad1"
    cat_topping_id = "1254d2df-4652-405b-b3d0-95d8c709cc11"
    cat_side_id = "1a22512c-f578-4bfb-8a06-1c31693a08d9"

    new_bases = [
        ("B1", "Thin Crust", 149, "e1b10000-0000-0000-0000-000000000001"),
        ("B2", "Thick Crust", 179, "e1b10000-0000-0000-0000-000000000002"),
        ("B3", "Cheese Burst", 229, "e1b10000-0000-0000-0000-000000000003"),
        ("B4", "Whole Wheat", 159, "e1b10000-0000-0000-0000-000000000004"),
        ("B5", "Multigrain", 169, "e1b10000-0000-0000-0000-000000000005"),
        ("B6", "Gluten Free", 199, "e1b10000-0000-0000-0000-000000000006"),
        ("B7", "Garlic Parmesan Crust", 189, "e1b10000-0000-0000-0000-000000000007")
    ]
    new_pizzas = [
        ("P1", "Margherita", 299, "e1a10000-0000-0000-0000-000000000001"),
        ("P2", "Chicago Deep Dish", 349, "e1a10000-0000-0000-0000-000000000002"),
        ("P3", "Greek Mediterranean", 329, "e1a10000-0000-0000-0000-000000000003"),
        ("P4", "California Veggie", 339, "e1a10000-0000-0000-0000-000000000004"),
        ("P5", "Farm House", 319, "e1a10000-0000-0000-0000-000000000005"),
        ("P6", "Pepperoni Classic", 369, "e1a10000-0000-0000-0000-000000000006"),
        ("P7", "BBQ Chicken", 379, "e1a10000-0000-0000-0000-000000000007"),
        ("P8", "Paneer Tikka", 349, "e1a10000-0000-0000-0000-000000000008"),
        ("P9", "Chicken Golden Delight", 399, "e1a10000-0000-0000-0000-000000000009"),
        ("P10", "Spicy Triple Tango", 329, "e1a10000-0000-0000-0000-000000000010"),
        ("P11", "Veggie Paradise", 339, "e1a10000-0000-0000-0000-000000000011"),
        ("P12", "Double Cheese Margherita", 349, "e1a10000-0000-0000-0000-000000000012"),
        ("P13", "Tandoori Chicken Tikka", 389, "e1a10000-0000-0000-0000-000000000013"),
        ("P14", "Meat Ultima", 429, "e1a10000-0000-0000-0000-000000000014")
    ]
    new_toppings = [
        ("T1", "Black Olives", 49, "e1c10000-0000-0000-0000-000000000001"),
        ("T2", "Extra Cheese", 69, "e1c10000-0000-0000-0000-000000000002"),
        ("T3", "Button Mushrooms", 49, "e1c10000-0000-0000-0000-000000000003"),
        ("T4", "Green Peppers", 39, "e1c10000-0000-0000-0000-000000000004"),
        ("T5", "Jalapenos", 39, "e1c10000-0000-0000-0000-000000000005"),
        ("T6", "Sun-Dried Tomatoes", 59, "e1c10000-0000-0000-0000-000000000006"),
        ("T7", "Caramelised Onions", 49, "e1c10000-0000-0000-0000-000000000007"),
        ("T8", "Sweet Corn", 39, "e1c10000-0000-0000-0000-000000000008"),
        ("T9", "Roasted Garlic", 49, "e1c10000-0000-0000-0000-000000000009"),
        ("T10", "Peri-Peri Drizzle", 59, "e1c10000-0000-0000-0000-000000000010"),
        ("T11", "Red Paprika", 49, "e1c10000-0000-0000-0000-000000000011"),
        ("T12", "Paneer Cubes", 59, "e1c10000-0000-0000-0000-000000000012"),
        ("T13", "Chicken Keema", 79, "e1c10000-0000-0000-0000-000000000013"),
        ("T14", "Onion Rings", 29, "e1c10000-0000-0000-0000-000000000014"),
        ("T15", "Baby Corn", 39, "e1c10000-0000-0000-0000-000000000015")
    ]
    new_sides = [
        ("S1", "Garlic Breadsticks", 129, "e1d10000-0000-0000-0000-000000000001"),
        ("S2", "Peri Peri Fries", 149, "e1d10000-0000-0000-0000-000000000002"),
        ("S3", "Cheese Dip", 39, "e1d10000-0000-0000-0000-000000000003"),
        ("S4", "Jalapeno Dip", 39, "e1d10000-0000-0000-0000-000000000004"),
        ("S5", "Chocolate Brownie", 119, "e1d10000-0000-0000-0000-000000000005"),
        ("S6", "Coke 500ml", 59, "e1d10000-0000-0000-0000-000000000006"),
        ("S7", "Sprite 500ml", 59, "e1d10000-0000-0000-0000-000000000007"),
        ("S8", "Iced Tea", 89, "e1d10000-0000-0000-0000-000000000008"),
        ("S9", "Stuffed Garlic Bread", 159, "e1d10000-0000-0000-0000-000000000009"),
        ("S10", "Onion Rings", 99, "e1d10000-0000-0000-0000-000000000010"),
        ("S11", "Lava Cake", 129, "e1d10000-0000-0000-0000-000000000011"),
        ("S12", "Fanta 500ml", 59, "e1d10000-0000-0000-0000-000000000012"),
        ("S13", "Water Bottle 1L", 29, "e1d10000-0000-0000-0000-000000000013")
    ]

    ingredients = [
        ("Mozzarella Cheese", "kg", 8.0, 5.0, "f0000000-0000-0000-0000-000000000001"),
        ("Pizza Sauce", "litre", 6.0, 4.0, "f0000000-0000-0000-0000-000000000002"),
        ("Thin Crust Base", "piece", 18.0, 20.0, "f0000000-0000-0000-0000-000000000003"),
        ("Paneer Cubes", "kg", 4.0, 3.0, "f0000000-0000-0000-0000-000000000004"),
        ("Chicken Tikka", "kg", 3.0, 4.0, "f0000000-0000-0000-0000-000000000005"),
        ("Sweet Corn", "kg", 5.0, 2.0, "f0000000-0000-0000-0000-000000000006")
    ]
    ingredient_by_name = {ing[0]: ing[4] for ing in ingredients}

    # ---------------------------------------------------------
    # 01_menu_and_ingredients.sql
    # ---------------------------------------------------------
    sql1 = []
    sql1.append("-- FILE: 01_menu_and_ingredients.sql")
    sql1.append("-- Sets up category nodes, premium menu items, and ingredient lists.")
    sql1.append("BEGIN;")
    
    sql1.append("\n-- Clear all existing data to prevent foreign key conflicts on custom UUID seeding")
    sql1.append("DELETE FROM public.order_inventory_deductions;")
    sql1.append("DELETE FROM public.stock_transactions;")
    sql1.append("DELETE FROM public.inventory_requests;")
    sql1.append("DELETE FROM public.refunds;")
    sql1.append("DELETE FROM public.payments;")
    sql1.append("DELETE FROM public.order_status_history;")
    sql1.append("DELETE FROM public.customer_feedback;")
    sql1.append("DELETE FROM public.ai_recommendation_events;")
    sql1.append("DELETE FROM public.orders;")
    sql1.append("DELETE FROM public.messages;")
    sql1.append("DELETE FROM public.sessions;")
    sql1.append("DELETE FROM public.menu_item_ingredients;")
    sql1.append("DELETE FROM public.price_history;")
    sql1.append("DELETE FROM public.menu_items;")
    sql1.append("DELETE FROM public.ingredients;")
    sql1.append("DELETE FROM public.discount_rule_conditions;")
    sql1.append("DELETE FROM public.discount_rules;")
    
    sql1.append("\n-- 1. Insert Menu Categories")
    sql1.append(f"INSERT INTO public.menu_categories (id, code, name, sort_order) VALUES ('{cat_base_id}', 'base', 'Pizza Bases', 1) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, sort_order = EXCLUDED.sort_order;")
    sql1.append(f"INSERT INTO public.menu_categories (id, code, name, sort_order) VALUES ('{cat_pizza_id}', 'pizza', 'Pizzas', 2) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, sort_order = EXCLUDED.sort_order;")
    sql1.append(f"INSERT INTO public.menu_categories (id, code, name, sort_order) VALUES ('{cat_topping_id}', 'topping', 'Toppings', 3) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, sort_order = EXCLUDED.sort_order;")
    sql1.append(f"INSERT INTO public.menu_categories (id, code, name, sort_order) VALUES ('{cat_side_id}', 'side', 'Sides', 4) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, sort_order = EXCLUDED.sort_order;")

    sql1.append("\n-- 2. Insert Menu Items")
    # Bases
    for code, name, price, uid in new_bases:
        sql1.append(f"INSERT INTO public.menu_items (id, item_code, category_id, name, price, is_available, is_deleted) VALUES ('{uid}', '{code}', '{cat_base_id}', '{name}', {price}, true, false) ON CONFLICT (item_code) DO UPDATE SET name = EXCLUDED.name, price = EXCLUDED.price, is_deleted = false;")
    # Pizzas
    for code, name, price, uid in new_pizzas:
        sql1.append(f"INSERT INTO public.menu_items (id, item_code, category_id, name, price, is_available, is_deleted) VALUES ('{uid}', '{code}', '{cat_pizza_id}', '{name}', {price}, true, false) ON CONFLICT (item_code) DO UPDATE SET name = EXCLUDED.name, price = EXCLUDED.price, is_deleted = false;")
    # Toppings
    for code, name, price, uid in new_toppings:
        sql1.append(f"INSERT INTO public.menu_items (id, item_code, category_id, name, price, is_available, is_deleted) VALUES ('{uid}', '{code}', '{cat_topping_id}', '{name}', {price}, true, false) ON CONFLICT (item_code) DO UPDATE SET name = EXCLUDED.name, price = EXCLUDED.price, is_deleted = false;")
    # Sides
    for code, name, price, uid in new_sides:
        sql1.append(f"INSERT INTO public.menu_items (id, item_code, category_id, name, price, is_available, is_deleted) VALUES ('{uid}', '{code}', '{cat_side_id}', '{name}', {price}, true, false) ON CONFLICT (item_code) DO UPDATE SET name = EXCLUDED.name, price = EXCLUDED.price, is_deleted = false;")

    sql1.append("\n-- 3. Insert Ingredients")
    for name, unit, qty, thresh, uid in ingredients:
        sql1.append(f"INSERT INTO public.ingredients (id, name, unit, stock_quantity, reorder_threshold, is_active) VALUES ('{uid}', '{name}', '{unit}', {qty}, {thresh}, true) ON CONFLICT (name) DO UPDATE SET stock_quantity = EXCLUDED.stock_quantity, reorder_threshold = EXCLUDED.reorder_threshold, is_active = true;")

    sql1.append("\n-- 4. Recipe Ingredients (menu_item_ingredients)")
    recipes = [
        ("B1", "Thin Crust Base", 1.0), ("B2", "Thin Crust Base", 1.0), ("B3", "Thin Crust Base", 1.0),
        ("B4", "Thin Crust Base", 1.0), ("B5", "Thin Crust Base", 1.0), ("B6", "Thin Crust Base", 1.0),
        ("B7", "Thin Crust Base", 1.0),
        ("P1", "Mozzarella Cheese", 0.12), ("P1", "Pizza Sauce", 0.08),
        ("P2", "Mozzarella Cheese", 0.16), ("P2", "Pizza Sauce", 0.10),
        ("P3", "Mozzarella Cheese", 0.12), ("P3", "Pizza Sauce", 0.08),
        ("P4", "Mozzarella Cheese", 0.12), ("P4", "Pizza Sauce", 0.08),
        ("P5", "Mozzarella Cheese", 0.12), ("P5", "Pizza Sauce", 0.08),
        ("P6", "Mozzarella Cheese", 0.14), ("P6", "Pizza Sauce", 0.08),
        ("P7", "Chicken Tikka", 0.18), ("P7", "Mozzarella Cheese", 0.10),
        ("P8", "Paneer Cubes", 0.16), ("P8", "Mozzarella Cheese", 0.10),
        ("T2", "Mozzarella Cheese", 0.05),
        ("T8", "Sweet Corn", 0.04)
    ]
    for mi_code, ing_name, qty_per in recipes:
        mi_uid = next(uid for code, name, price, uid in (new_bases + new_pizzas + new_toppings + new_sides) if code == mi_code)
        ing_uid = ingredient_by_name[ing_name]
        sql1.append(f"INSERT INTO public.menu_item_ingredients (id, menu_item_id, ingredient_id, quantity_per_unit) VALUES ('{str(uuid.uuid4())}', '{mi_uid}', '{ing_uid}', {qty_per}) ON CONFLICT (menu_item_id, ingredient_id) DO UPDATE SET quantity_per_unit = EXCLUDED.quantity_per_unit;")

    sql1.append("\n-- 5. Discount Rules and conditions")
    dr_id1 = "d1000000-0000-0000-0000-000000000001"
    dr_id2 = "d1000000-0000-0000-0000-000000000002"
    sql1.append(f"INSERT INTO public.discount_rules (id, name, discount_percent, threshold_amount, start_date, is_active, coupon_code, description) VALUES ('{dr_id1}', 'Diwali Festive Combo', 18.0, 999.0, '2026-11-01', true, 'DIWALI18', 'Get 18% off on orders above 999 Rs') ON CONFLICT (id) DO NOTHING;")
    sql1.append(f"INSERT INTO public.discount_rules (id, name, discount_percent, threshold_amount, start_date, is_active, coupon_code, description) VALUES ('{dr_id2}', 'Afternoon Slow Hour', 15.0, 499.0, '2026-02-01', true, 'SLOWHOUR15', 'Get 15% off during afternoon slow hours') ON CONFLICT (id) DO NOTHING;")
    
    sql1.append(f"INSERT INTO public.discount_rule_conditions (discount_rule_id, min_quantity, no_min_quantity, no_min_value) VALUES ('{dr_id1}', 1, false, false) ON CONFLICT DO NOTHING;")
    sql1.append(f"INSERT INTO public.discount_rule_conditions (discount_rule_id, min_quantity, no_min_quantity, no_min_value) VALUES ('{dr_id2}', 1, false, false) ON CONFLICT DO NOTHING;")

    sql1.append("COMMIT;")
    
    with open(os.path.join(target_dir, "01_menu_and_ingredients.sql"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sql1))

    # ---------------------------------------------------------
    # 02_users_and_sessions.sql
    # ---------------------------------------------------------
    sql2 = []
    sql2.append("-- FILE: 02_users_and_sessions.sql")
    sql2.append("-- Sets up customers, administrative seed users, sessions and conversations.")
    sql2.append("BEGIN;")
    
    sql2.append("\n-- 1. Insert admin, staff, and customer users")
    admin_hash = security.hash_secret("SliceMatic@Admin1")
    user_hash = security.hash_secret("123456")
    
    admin_uid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    sql2.append(f"INSERT INTO public.app_users (id, role, name, full_name, email, phone, secret_hash, is_active, status) VALUES ('{admin_uid}', 'admin', 'SliceMatic Admin', 'SliceMatic Admin', 'admin@slicematic.in', '9876543211', '{admin_hash}', true, 'active') ON CONFLICT (email) DO UPDATE SET secret_hash = EXCLUDED.secret_hash, status = 'active';")
    
    staff1_uid = "e1000000-0000-0000-0000-000000000001"
    staff2_uid = "e1000000-0000-0000-0000-000000000002"
    staff3_uid = "e1000000-0000-0000-0000-000000000003"
    
    sql2.append(f"INSERT INTO public.app_users (id, role, name, full_name, phone, emp_id, secret_hash, is_active, status) VALUES ('{staff1_uid}', 'staff', 'Rohan Verma', 'Rohan Verma', '9811111111', 'SMEMP001', '{user_hash}', true, 'active') ON CONFLICT (emp_id) DO NOTHING;")
    sql2.append(f"INSERT INTO public.app_users (id, role, name, full_name, phone, emp_id, secret_hash, is_active, status) VALUES ('{staff2_uid}', 'kitchen_staff', 'Priya Nair', 'Priya Nair', '9822222222', 'SMEMP002', '{user_hash}', true, 'active') ON CONFLICT (emp_id) DO NOTHING;")
    sql2.append(f"INSERT INTO public.app_users (id, role, name, full_name, phone, emp_id, secret_hash, is_active, status) VALUES ('{staff3_uid}', 'delivery', 'Vikram Singh', 'Vikram Singh', '9833333333', 'SMEMP003', '{user_hash}', true, 'active') ON CONFLICT (emp_id) DO NOTHING;")

    sql2.append("\n-- 2. Insert 50 customers")
    generated_users = []
    for i in range(1, 51):
        uid = f"c0000000-0000-0000-0000-{i:012d}"
        name = generate_random_name()
        phone = f"9000002{i:03d}"
        addr = [{
            "id": "home",
            "label": "Home",
            "line": generate_delhi_address(),
            "isDefault": True
        }]
        addr_str = json.dumps(addr).replace("'", "''")
        sql2.append(f"INSERT INTO public.app_users (id, role, name, full_name, phone, secret_hash, address, is_active, status) VALUES ('{uid}', 'user', '{name}', '{name}', '{phone}', '{user_hash}', '{addr_str}'::jsonb, true, 'active') ON CONFLICT (phone) DO UPDATE SET address = EXCLUDED.address;")
        generated_users.append({"id": uid, "name": name, "phone": phone, "address": addr[0]["line"]})

    sql2.append("\n-- 3. Insert 120 Sessions")
    start_date = datetime(2026, 2, 1, tzinfo=timezone.utc)
    end_date = datetime(2026, 7, 4, tzinfo=timezone.utc)
    total_days = (end_date - start_date).days
    
    session_list = []
    for i in range(1, 121):
        sess_id = f"dummy-session-{i:04d}"
        day_offset = random.randint(0, total_days)
        time_hour = random.choice([12, 13, 14, 19, 20, 21, 22] * 4 + list(range(0, 24)))
        time_minute = random.randint(0, 59)
        started_at = start_date + timedelta(days=day_offset, hours=time_hour, minutes=time_minute)
        
        user = generated_users[(i - 1) % len(generated_users)]
        channel = random.choice(["chat", "chat", "voice"])
        lang = random.choice(["en", "en", "hi"])
        status = random.choice(["ordered"] * 10 + ["abandoned"] * 1 + ["escalated"] * 1)
        
        last_activity = started_at + timedelta(minutes=random.randint(3, 10))
        end_val = f"'{last_activity.isoformat()}'" if status == "ordered" else "NULL"
        
        meta = json.dumps({"seed": "dummy"})
        sql2.append(f"INSERT INTO public.sessions (id, channel, language, customer_name, customer_phone, status, human_escalated, started_at, last_activity_at, ended_at, metadata) VALUES ('{sess_id}', '{channel}', '{lang}', '{user['name']}', '{user['phone']}', '{status}', {str(status == 'escalated').lower()}, '{started_at.isoformat()}', '{last_activity.isoformat()}', {end_val}, '{meta}'::jsonb) ON CONFLICT (id) DO NOTHING;")
        session_list.append({"id": sess_id, "channel": channel, "language": lang, "status": status, "started_at": started_at, "customer_name": user["name"], "customer_phone": user["phone"], "user_id": user["id"], "delivery_address": user["address"]})

    sql2.append("\n-- 4. Insert Messages for Sessions")
    for s in session_list:
        sess_id = s["id"]
        started = s["started_at"]
        if s["status"] == "ordered":
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'user', 'Hi, I want to order a Margherita pizza.', '{s['channel']}', '{started.isoformat()}', 10, 0);")
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'assistant', 'Sure! Which base would you like? Thin Crust or Cheese Burst?', '{s['channel']}', '{(started + timedelta(seconds=30)).isoformat()}', 20, 15);")
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'user', 'Cheese burst base with extra cheese topping.', '{s['channel']}', '{(started + timedelta(seconds=60)).isoformat()}', 15, 0);")
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'assistant', 'Perfect, I have placed your order. Payment mode is Cash.', '{s['channel']}', '{(started + timedelta(seconds=90)).isoformat()}', 25, 20);")
        elif s["status"] == "escalated":
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'user', 'I received a burnt pizza last night and want to speak to support.', '{s['channel']}', '{started.isoformat()}', 15, 0);")
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'assistant', 'I am so sorry to hear that. Connecting you to a store manager right now.', '{s['channel']}', '{(started + timedelta(seconds=30)).isoformat()}', 30, 25);")
        else: # abandoned
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'user', 'Are you currently delivering in Ashok Nagar?', '{s['channel']}', '{started.isoformat()}', 12, 0);")
            sql2.append(f"INSERT INTO public.messages (id, session_id, role, content, channel, created_at, prompt_tokens, completion_tokens) VALUES ('{str(uuid.uuid4())}', '{sess_id}', 'assistant', 'Yes, we are! What would you like to order today?', '{s['channel']}', '{(started + timedelta(seconds=30)).isoformat()}', 18, 12);")

    sql2.append("COMMIT;")
    
    with open(os.path.join(target_dir, "02_users_and_sessions.sql"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sql2))

    # ---------------------------------------------------------
    # 03_orders_and_analytics.sql
    # ---------------------------------------------------------
    sql3 = []
    sql3.append("-- FILE: 03_orders_and_analytics.sql")
    sql3.append("-- Seeds exactly 150 orders (linking to sessions when ordered), payments, history, reviews, recommendations, summaries, and forecasting logs.")
    sql3.append("BEGIN;")
    
    # Extract only ordered sessions
    ordered_sessions = [s for s in session_list if s["status"] == "ordered"]
    
    orders_to_generate = []
    
    # 150 orders
    for idx in range(1, 151):
        order_uuid = f"00000000-0000-0000-0000-{idx:012d}"
        order_no = f"SM-DUMMY-{idx:05d}"
        
        # Link to session if possible (first 100 orders get linked, 50 are direct)
        if idx <= len(ordered_sessions):
            sess = ordered_sessions[idx - 1]
            sess_id = sess["id"]
            user_id = sess["user_id"]
            customer_name = sess["customer_name"]
            customer_phone = sess["customer_phone"]
            source = sess["channel"]
            created_at = sess["started_at"] + timedelta(minutes=2)
            address = sess["delivery_address"]
            lang = sess["language"]
        else:
            sess_id = None
            user = random.choice(generated_users)
            user_id = user["id"]
            customer_name = user["name"]
            customer_phone = user["phone"]
            source = random.choice(["app", "api", "staff_pos"])
            # Date distribution
            day_offset = random.randint(0, total_days)
            time_hour = random.choice([12, 13, 14, 19, 20, 21, 22] * 4 + list(range(0, 24)))
            time_minute = random.randint(0, 59)
            created_at = start_date + timedelta(days=day_offset, hours=time_hour, minutes=time_minute)
            address = user["address"]
            lang = "en"
            
        # Select items
        pizza = random.choice(new_pizzas)
        base = random.choice(new_bases)
        toppings = random.sample(new_toppings, random.randint(1, 3))
        
        pizza_unit_price = float(pizza[2]) + float(base[2]) + sum(float(t[2]) for t in toppings)
        quantity = random.choice([1, 1, 2, 3, 5])
        pizza_total = pizza_unit_price * quantity
        
        cart_items = [{
            "pizza": pizza[1],
            "base": base[1],
            "toppings": [t[1] for t in toppings],
            "quantity": quantity,
            "unit_price": pizza_unit_price,
            "line_total": pizza_total
        }]
        subtotal = pizza_total
        
        if random.random() < 0.4:
            side = random.choice(new_sides)
            side_qty = random.randint(1, 2)
            side_total = float(side[2]) * side_qty
            cart_items.append({
                "side": side[1],
                "quantity": side_qty,
                "price": float(side[2]),
                "line_total": side_total
            })
            subtotal += side_total

        # Discount
        discount = 0.0
        if quantity >= 5 or subtotal >= 500:
            discount = round(subtotal * 0.10, 2)
            
        gst = round((subtotal - discount) * 0.18, 2)
        total = round(subtotal - discount + gst, 2)
        payment_mode = random.choice(["UPI", "Card", "Cash"])
        
        # Status
        status_rand = random.random()
        if status_rand < 0.90:
            status = "delivered"
        elif status_rand < 0.95:
            status = "cancelled"
        elif status_rand < 0.98:
            status = "out_for_delivery"
        else:
            status = "preparing"
            
        preparing_at = None
        ready_at = None
        out_for_delivery_at = None
        delivered_at = None
        
        if status in ["preparing", "ready_for_pickup", "out_for_delivery", "delivered"]:
            preparing_at = (created_at + timedelta(minutes=random.randint(2, 5)))
        if status in ["ready_for_pickup", "out_for_delivery", "delivered"]:
            ready_at = (created_at + timedelta(minutes=random.randint(12, 20)))
        if status in ["out_for_delivery", "delivered"] and source != "staff_pos":
            out_for_delivery_at = (created_at + timedelta(minutes=random.randint(15, 25)))
        if status == "delivered" and source != "staff_pos":
            delivered_at = (created_at + timedelta(minutes=random.randint(30, 45)))
            
        orders_to_generate.append({
            "id": order_uuid,
            "order_no": order_no,
            "session_id": sess_id,
            "source": source,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "user_id": user_id,
            "base_name": base[1],
            "pizza_name": pizza[1],
            "topping_name": ", ".join(t[1] for t in toppings),
            "unit_price": pizza_unit_price,
            "quantity": quantity,
            "subtotal": subtotal,
            "discount": discount,
            "gst": gst,
            "total": total,
            "payment_mode": payment_mode,
            "items": cart_items,
            "language": lang,
            "status": status,
            "delivery_address": address,
            "type": "in-store" if source == "staff_pos" else "online",
            "created_at": created_at,
            "preparing_at": preparing_at,
            "ready_at": ready_at,
            "out_for_delivery_at": out_for_delivery_at,
            "delivered_at": delivered_at
        })

    sql3.append("\n-- 1. Insert Orders")
    for o in orders_to_generate:
        items_str = json.dumps(o["items"]).replace("'", "''")
        prep_val = f"'{o['preparing_at'].isoformat()}'" if o['preparing_at'] else "NULL"
        ready_val = f"'{o['ready_at'].isoformat()}'" if o['ready_at'] else "NULL"
        out_val = f"'{o['out_for_delivery_at'].isoformat()}'" if o['out_for_delivery_at'] else "NULL"
        deliv_val = f"'{o['delivered_at'].isoformat()}'" if o['delivered_at'] else "NULL"
        addr_val = f"'{o['delivery_address'].replace(chr(39), chr(39)+chr(39))}'" if o['delivery_address'] else "NULL"
        sess_val = f"'{o['session_id']}'" if o['session_id'] else "NULL"
        
        sql3.append(f"INSERT INTO public.orders (id, order_no, session_id, source, customer_name, customer_phone, user_id, base_name, pizza_name, topping_name, unit_price, quantity, subtotal, discount, gst, total, payment_mode, items, language, status, delivery_address, type, logged_at, created_at, preparing_at, ready_at, out_for_delivery_at, delivered_at) VALUES ('{o['id']}', '{o['order_no']}', {sess_val}, '{o['source']}', '{o['customer_name']}', '{o['customer_phone']}', '{o['user_id']}', '{o['base_name']}', '{o['pizza_name']}', '{o['topping_name'].replace(chr(39), chr(39)+chr(39))}', {o['unit_price']}, {o['quantity']}, {o['subtotal']}, {o['discount']}, {o['gst']}, {o['total']}, '{o['payment_mode']}', '{items_str}'::jsonb, '{o['language']}', '{o['status']}', {addr_val}, '{o['type']}', '{o['created_at'].isoformat()}', '{o['created_at'].isoformat()}', {prep_val}, {ready_val}, {out_val}, {deliv_val}) ON CONFLICT (id) DO NOTHING;")

    sql3.append("\n-- 2. Insert Payments")
    for idx, o in enumerate(orders_to_generate):
        p_id = f"e2000000-0000-0000-0000-{idx+1:012d}"
        payment_status = "Paid" if o["status"] != "cancelled" else "Failed"
        paid_at_val = f"'{o['created_at'].isoformat()}'" if payment_status == "Paid" else "NULL"
        sql3.append(f"INSERT INTO public.payments (id, order_id, payment_mode, payment_status, amount_paid, transaction_reference, paid_at, created_at) VALUES ('{p_id}', '{o['id']}', '{o['payment_mode']}', '{payment_status}', {0.0 if payment_status == 'Failed' else o['total']}, 'TXN-{o['order_no']}', {paid_at_val}, '{o['created_at'].isoformat()}') ON CONFLICT (id) DO NOTHING;")

    sql3.append("\n-- 3. Insert Order Status History")
    for idx, o in enumerate(orders_to_generate):
        # Always had 'received'
        hist_received_id = f"e3000000-0000-0000-0001-{idx+1:012d}"
        sql3.append(f"INSERT INTO public.order_status_history (id, order_id, old_status, new_status, changed_by, changed_at, reason) VALUES ('{hist_received_id}', '{o['id']}', NULL, 'received', '{admin_uid}', '{o['created_at'].isoformat()}', 'Order submitted by customer') ON CONFLICT (id) DO NOTHING;")
        
        if o["status"] in ["preparing", "ready_for_pickup", "out_for_delivery", "delivered"] and o["preparing_at"]:
            hist_prep_id = f"e3000000-0000-0000-0002-{idx+1:012d}"
            sql3.append(f"INSERT INTO public.order_status_history (id, order_id, old_status, new_status, changed_by, changed_at, reason) VALUES ('{hist_prep_id}', '{o['id']}', 'received', 'preparing', '{admin_uid}', '{o['preparing_at'].isoformat()}', 'Kitchen kitchen queue processing') ON CONFLICT (id) DO NOTHING;")
        if o["status"] in ["ready_for_pickup", "out_for_delivery", "delivered"] and o["ready_at"]:
            hist_ready_id = f"e3000000-0000-0000-0003-{idx+1:012d}"
            sql3.append(f"INSERT INTO public.order_status_history (id, order_id, old_status, new_status, changed_by, changed_at, reason) VALUES ('{hist_ready_id}', '{o['id']}', 'preparing', 'ready_for_pickup', '{admin_uid}', '{o['ready_at'].isoformat()}', 'Pizza cooked and boxed') ON CONFLICT (id) DO NOTHING;")
        if o["status"] == "delivered" and o["delivered_at"]:
            hist_deliv_id = f"e3000000-0000-0000-0004-{idx+1:012d}"
            sql3.append(f"INSERT INTO public.order_status_history (id, order_id, old_status, new_status, changed_by, changed_at, reason) VALUES ('{hist_deliv_id}', '{o['id']}', 'ready_for_pickup', 'delivered', '{admin_uid}', '{o['delivered_at'].isoformat()}', 'Delivered to customer address') ON CONFLICT (id) DO NOTHING;")
        if o["status"] == "cancelled":
            hist_cancel_id = f"e3000000-0000-0000-0005-{idx+1:012d}"
            sql3.append(f"INSERT INTO public.order_status_history (id, order_id, old_status, new_status, changed_by, changed_at, reason) VALUES ('{hist_cancel_id}', '{o['id']}', 'received', 'cancelled', '{admin_uid}', '{(o['created_at'] + timedelta(minutes=5)).isoformat()}', 'Cancelled by user/system') ON CONFLICT (id) DO NOTHING;")

    sql3.append("\n-- 4. Insert Refunds")
    refund_idx = 1
    for o in orders_to_generate:
        if o["status"] == "cancelled" and random.random() < 0.6:
            r_id = f"e4000000-0000-0000-0000-{refund_idx:012d}"
            pay_id = f"e2000000-0000-0000-0000-{orders_to_generate.index(o)+1:012d}"
            sql3.append(f"INSERT INTO public.refunds (id, order_id, payment_id, amount, reason, status, requested_by, approved_by, requested_at, decided_at) VALUES ('{r_id}', '{o['id']}', '{pay_id}', {o['total']}, 'Customer cancelled order - pre-auth release', 'Paid', '{admin_uid}', '{admin_uid}', '{(o['created_at'] + timedelta(minutes=6)).isoformat()}', '{(o['created_at'] + timedelta(minutes=10)).isoformat()}') ON CONFLICT (id) DO NOTHING;")
            refund_idx += 1

    sql3.append("\n-- 5. Insert Customer Feedback")
    feedbacks = [
        (5, "Amazing cheese burst pizza! Arrived hot and fast.", "positive", 0.94, ["taste", "temperature", "delivery"]),
        (5, "Tandoori chicken pizza is a must try! Super delicious.", "positive", 0.91, ["taste", "quality"]),
        (4, "The base crust is thin and crunchy, but delayed 5 mins.", "positive", 0.72, ["taste", "delivery"]),
        (3, "Average taste. Breadsticks were slightly cold.", "neutral", 0.05, ["taste", "temperature"]),
        (2, "Incorrect toppings. Ordered mushrooms, received olives.", "negative", -0.71, ["accuracy"]),
        (1, "The pizza was burnt, cold and delivered in 1.5 hours.", "negative", -0.96, ["temperature", "delivery", "quality"])
    ]
    feedback_idx = 1
    for o in orders_to_generate:
        if o["status"] == "delivered" and random.random() < 0.5:
            rating, text, label, score, topics = feedbacks[feedback_idx % len(feedbacks)]
            fb_id = f"f0000000-0000-0000-0000-{feedback_idx:012d}"
            topics_str = json.dumps(topics)
            meta_str = json.dumps({"seed": "dummy"})
            sql3.append(f"INSERT INTO public.customer_feedback (id, order_id, customer_name, customer_phone, channel, rating, feedback_text, sentiment_label, sentiment_score, topics, source_metadata, created_by, created_at) VALUES ('{fb_id}', '{o['id']}', '{o['customer_name']}', '{o['customer_phone']}', 'app', {rating}, '{text}', '{label}', {score}, '{topics_str}'::jsonb, '{meta_str}'::jsonb, '{admin_uid}', '{(o['created_at'] + timedelta(hours=1)).isoformat()}') ON CONFLICT (id) DO NOTHING;")
            feedback_idx += 1

    sql3.append("\n-- 6. Insert AI Recommendation Events")
    recs = [
        ("upsell", "dummy:upsell:cheese", "Suggest Extra Cheese", "Upsell presented based on Margherita select", "accepted", 69.0),
        ("upsell", "dummy:upsell:garlicbread", "Suggest Garlic Breadsticks", "Cross-sell side recommendation", "presented", 0.0),
        ("coupon", "dummy:coupon:slow", "SLOWHOUR15 campaign offer", "Off-peak hour builder coupon", "accepted", 45.0),
        ("churn", "dummy:churn:winback", "Repeat Customer Thank You", "Churn risk prevention winback", "rejected", 0.0)
    ]
    rec_idx = 1
    for o in orders_to_generate:
        if random.random() < 0.4:
            rtype, key_base, title, detail, def_status, est_val = recs[rec_idx % len(recs)]
            rec_id = f"a0000000-0000-0000-0000-{rec_idx:012d}"
            status = random.choice(["presented", "accepted", "rejected"])
            actual_val = est_val if status == "accepted" else 0.0
            meta_str = json.dumps({"seed": "dummy", "order_no": o["order_no"]})
            sql3.append(f"INSERT INTO public.ai_recommendation_events (id, recommendation_type, recommendation_key, title, detail, status, estimated_value, source_metrics, related_entity_type, related_entity_id, created_by, created_at) VALUES ('{rec_id}', '{rtype}', '{key_base}:{rec_idx}', '{title}', '{detail}', '{status}', {actual_val}, '{meta_str}'::jsonb, 'orders', '{o['id']}', '{admin_uid}', '{(o['created_at'] - timedelta(minutes=5)).isoformat()}') ON CONFLICT (id) DO NOTHING;")
            rec_idx += 1

    sql3.append("\n-- 7. Insert Order Inventory Deductions & Stock Transactions")
    ded_idx = 1
    tx_idx = 1
    for o in orders_to_generate:
        # Check if we can map ingredients
        if "Thin" in o["base_name"] or "Margherita" in o["pizza_name"]:
            ing_uid = ingredient_by_name["Thin Crust Base"] if "Thin" in o["base_name"] else ingredient_by_name["Mozzarella Cheese"]
            ded_id = f"d0000000-0000-0000-0000-{ded_idx:012d}"
            sql3.append(f"INSERT INTO public.order_inventory_deductions (id, order_id, ingredient_id, quantity, deducted_at, deducted_by) VALUES ('{ded_id}', '{o['id']}', '{ing_uid}', {float(o['quantity']) * 0.12}, '{o['created_at'].isoformat()}', '{admin_uid}') ON CONFLICT (id) DO NOTHING;")
            ded_idx += 1
            
            # StockOut Transaction
            tx_id = f"e5000000-0000-0000-0000-{tx_idx:012d}"
            sql3.append(f"INSERT INTO public.stock_transactions (id, ingredient_id, transaction_type, quantity, old_quantity, new_quantity, reason, performed_by, performed_at) VALUES ('{tx_id}', '{ing_uid}', 'StockOut', {float(o['quantity']) * 0.12}, 25.0, {25.0 - float(o['quantity']) * 0.12}, 'Dummy seed deduction for order {o['order_no']}', '{admin_uid}', '{o['created_at'].isoformat()}') ON CONFLICT (id) DO NOTHING;")
            tx_idx += 1

    sql3.append("\n-- 8. Daily Sales Summaries")
    # Group orders by date
    orders_by_date = {}
    for o in orders_to_generate:
        d_str = o["created_at"].date().isoformat()
        if d_str not in orders_by_date:
            orders_by_date[d_str] = []
        orders_by_date[d_str].append(o)
        
    for d_str, o_list in orders_by_date.items():
        total_orders = len(o_list)
        rev = sum(float(o["subtotal"] - o["discount"]) for o in o_list)
        gst = sum(float(o["gst"]) for o in o_list)
        disc = sum(float(o["discount"]) for o in o_list)
        aov = rev / total_orders
        sql3.append(f"INSERT INTO public.daily_sales_summary (summary_date, total_orders, revenue, gst, discount, average_order_value) VALUES ('{d_str}', {total_orders}, {rev}, {gst}, {disc}, {aov}) ON CONFLICT (summary_date) DO UPDATE SET total_orders = EXCLUDED.total_orders, revenue = EXCLUDED.revenue, gst = EXCLUDED.gst, discount = EXCLUDED.discount, average_order_value = EXCLUDED.average_order_value;")

    sql3.append("\n-- 9. Hourly Sales Summaries")
    # Group orders by date and hour
    orders_by_hour = {}
    for o in orders_to_generate:
        key = (o["created_at"].date().isoformat(), o["created_at"].hour)
        if key not in orders_by_hour:
            orders_by_hour[key] = []
        orders_by_hour[key].append(o)
        
    for (d_str, hour), o_list in orders_by_hour.items():
        total_orders = len(o_list)
        rev = sum(float(o["subtotal"] - o["discount"]) for o in o_list)
        sql3.append(f"INSERT INTO public.hourly_sales_summary (summary_date, hour, total_orders, revenue) VALUES ('{d_str}', {hour}, {total_orders}, {rev}) ON CONFLICT (summary_date, hour) DO UPDATE SET total_orders = EXCLUDED.total_orders, revenue = EXCLUDED.revenue;")

    sql3.append("\n-- 10. Menu Item Sales Summaries")
    # Group orders by pizza name
    pizza_sales = {}
    for o in orders_to_generate:
        p_name = o["pizza_name"]
        if p_name not in pizza_sales:
            pizza_sales[p_name] = {"qty": 0, "rev": 0.0}
        pizza_sales[p_name]["qty"] += o["quantity"]
        pizza_sales[p_name]["rev"] += float(o["subtotal"])
        
    for p_name, data in pizza_sales.items():
        sql3.append(f"INSERT INTO public.menu_item_sales_summary (item_name, item_type, quantity, revenue, summary_from, summary_to) VALUES ('{p_name}', 'pizza', {data['qty']}, {data['rev']}, '2026-02-01', '2026-07-04') ON CONFLICT (item_name, item_type, summary_from, summary_to) DO UPDATE SET quantity = EXCLUDED.quantity, revenue = EXCLUDED.revenue;")

    sql3.append("\n-- 11. AI Forecast Results")
    # Generate daily forecasts for the next 7 days (July 5 to July 11)
    forecast_start = datetime(2026, 7, 5, tzinfo=timezone.utc)
    for k in range(7):
        f_date = (forecast_start + timedelta(days=k)).date().isoformat()
        predicted_ord = random.randint(30, 45)
        predicted_rev = predicted_ord * 420.0
        factors = json.dumps({"weekend_multiplier": 1.2 if k in [5, 6] else 1.0, "marketing_boost": 1.05})
        f_id = f"f1000000-0000-0000-0000-00000000000{k+1}"
        sql3.append(f"INSERT INTO public.forecast_results (id, forecast_date, forecast_type, predicted_orders, predicted_revenue, method, factors, created_by, created_at) VALUES ('{f_id}', '{f_date}', 'daily_demand', {predicted_ord}, {predicted_rev}, 'rule_based_7_day_average', '{factors}'::jsonb, '{admin_uid}', '2026-07-04T18:00:00Z') ON CONFLICT (id) DO NOTHING;")

    sql3.append("\n-- 12. AI Insight Logs")
    insight_text = "Analysis of the last 150 orders shows a 12% increase in Cheese Burst base preference during weekend dinner peaks (7 PM - 9 PM). Suggest activating a DIWALI18 coupon booster to push the average order value past 600 Rs."
    metrics = json.dumps({"total_analyzed_orders": 150, "cheese_burst_percentage": 34.5})
    ins_id = "e6000000-0000-0000-0000-000000000001"
    sql3.append(f"INSERT INTO public.ai_insight_logs (id, provider, insight_type, input_metrics, insight_text, created_by, created_at) VALUES ('{ins_id}', 'gemini', 'operational_insights', '{metrics}'::jsonb, '{insight_text}', '{admin_uid}', '2026-07-04T18:05:00Z') ON CONFLICT (id) DO NOTHING;")

    sql3.append("COMMIT;")
    
    with open(os.path.join(target_dir, "03_orders_and_analytics.sql"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sql3))
        
    print("All three SQL split files successfully generated under Aman/Bulk Update Queries/!")

if __name__ == "__main__":
    main()
