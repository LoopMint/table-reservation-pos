import streamlit as st
import pandas as pd
import altair as alt
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="Restaurant POS SaaS", layout="wide")

# ---------------------- DATABASE SETUP ----------------------
conn = sqlite3.connect("restaurant_saas.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT,
    table_name TEXT,
    status TEXT DEFAULT 'Available',
    customer_name TEXT,
    people INTEGER DEFAULT 0,
    remarks TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT,
    table_id INTEGER,
    opened_at TEXT,
    closed_at TEXT,
    status TEXT DEFAULT 'Open',
    total REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT,
    order_id INTEGER,
    item_name TEXT,
    category TEXT,
    qty INTEGER,
    price REAL,
    line_total REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT,
    item TEXT,
    category TEXT,
    price REAL
)
""")

conn.commit()

# ---------------------- TENANT / RESTAURANT CONTEXT ----------------------
if "restaurant_id" not in st.session_state:
    st.session_state.restaurant_id = "demo"

st.sidebar.title("SaaS Workspace")
restaurant_id = st.sidebar.text_input("Restaurant ID (workspace)", value=st.session_state.restaurant_id)
if st.sidebar.button("Switch Workspace"):
    st.session_state.restaurant_id = restaurant_id.strip() or "demo"
    st.rerun()

current_restaurant = st.session_state.restaurant_id
st.sidebar.markdown(f"**Active workspace:** `{current_restaurant}`")

# ---------------------- HELPERS ----------------------
def load_tables():
    return pd.read_sql(
        "SELECT * FROM tables WHERE restaurant_id = ?",
        conn,
        params=(current_restaurant,)
    )

def load_orders():
    return pd.read_sql(
        "SELECT * FROM orders WHERE restaurant_id = ?",
        conn,
        params=(current_restaurant,)
    )

def load_order_items():
    return pd.read_sql(
        "SELECT * FROM order_items WHERE restaurant_id = ?",
        conn,
        params=(current_restaurant,)
    )

def load_menu():
    return pd.read_sql(
        "SELECT * FROM menus WHERE restaurant_id = ?",
        conn,
        params=(current_restaurant,)
    )

def create_table(name):
    cursor.execute(
        "INSERT INTO tables (restaurant_id, table_name) VALUES (?, ?)",
        (current_restaurant, name)
    )
    conn.commit()

def update_table(table_id, name, people, remarks, status):
    cursor.execute("""
        UPDATE tables
        SET customer_name=?, people=?, remarks=?, status=?
        WHERE id=? AND restaurant_id=?
    """, (name, people, remarks, status, table_id, current_restaurant))
    conn.commit()

def create_order(table_id):
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO orders (restaurant_id, table_id, opened_at, status, total)
        VALUES (?, ?, ?, 'Open', 0)
    """, (current_restaurant, table_id, now))
    conn.commit()
    return cursor.lastrowid

def get_open_order(table_id):
    cursor.execute("""
        SELECT * FROM orders
        WHERE restaurant_id=? AND table_id=? AND status='Open'
        ORDER BY id DESC LIMIT 1
    """, (current_restaurant, table_id))
    row = cursor.fetchone()
    if row:
        cols = [c[0] for c in cursor.description]
        return dict(zip(cols, row))
    return None

def add_item(order_id, item, category, qty, price):
    total = qty * price
    cursor.execute("""
        INSERT INTO order_items (restaurant_id, order_id, item_name, category, qty, price, line_total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (current_restaurant, order_id, item, category, qty, price, total))
    cursor.execute("""
        UPDATE orders SET total = total + ?
        WHERE id=? AND restaurant_id=?
    """, (total, order_id, current_restaurant))
    conn.commit()

def close_order(order_id):
    now = datetime.now().isoformat()
    cursor.execute("""
        UPDATE orders
        SET status='Closed', closed_at=?
        WHERE id=? AND restaurant_id=?
    """, (now, order_id, current_restaurant))
    conn.commit()

def init_default_menu_if_empty():
    df = load_menu()
    if df.empty:
        defaults = [
            ("Margherita Pizza", "Food", 12.0),
            ("Pasta Carbonara", "Food", 14.0),
            ("Coke", "Drink", 3.0),
            ("Espresso", "Drink", 3.5),
        ]
        cursor.executemany("""
            INSERT INTO menus (restaurant_id, item, category, price)
            VALUES (?, ?, ?, ?)
        """, [(current_restaurant, i, c, p) for (i, c, p) in defaults])
        conn.commit()

init_default_menu_if_empty()

# ---------------------- UI ----------------------
st.title("🍽️ Restaurant POS SaaS")
st.caption(f"Workspace: `{current_restaurant}`")

tab_tables, tab_menu, tab_orders, tab_report = st.tabs(
    ["🪑 Tables", "📋 Menu", "🧾 Orders", "📊 Sales Report"]
)

# ---------------------- TABLES TAB ----------------------
with tab_tables:
    st.subheader("Manage Tables")

    new_table = st.text_input("New Table Name (e.g., T1)")
    if st.button("Add Table"):
        if new_table.strip():
            create_table(new_table.strip())
            st.success("Table added.")
            st.rerun()
        else:
            st.warning("Enter a table name.")

    tables = load_tables()
    if tables.empty:
        st.info("No tables yet. Add one above.")
    else:
        st.dataframe(tables, use_container_width=True)

# ---------------------- MENU TAB ----------------------
with tab_menu:
    st.subheader("Menu Management")

    menu_df = load_menu()
    if menu_df.empty:
        st.info("No menu items yet. Add some below.")

    editable = menu_df[["id", "item", "category", "price"]].copy() if not menu_df.empty else pd.DataFrame(
        columns=["id", "item", "category", "price"]
    )

    edited = st.data_editor(
        editable,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "item": "Item Name",
            "category": st.column_config.SelectboxColumn("Category", options=["Food", "Drink"]),
            "price": st.column_config.NumberColumn("Price ($)", min_value=0.0, step=0.5),
        },
        disabled=["id"],
    )

    if st.button("💾 Save Menu Changes"):
        cursor.execute("DELETE FROM menus WHERE restaurant_id=?", (current_restaurant,))
        for _, row in edited.iterrows():
            if pd.isna(row["item"]) or pd.isna(row["category"]) or pd.isna(row["price"]):
                continue
            cursor.execute("""
                INSERT INTO menus (restaurant_id, item, category, price)
                VALUES (?, ?, ?, ?)
            """, (current_restaurant, str(row["item"]), str(row["category"]), float(row["price"])))
        conn.commit()
        st.success("Menu updated.")
        st.rerun()

    st.markdown("### Quick Add New Item")
    col1, col2, col3 = st.columns(3)
    with col1:
        new_item_name = st.text_input("Item Name")
    with col2:
        new_item_cat = st.selectbox("Category", ["Food", "Drink"])
    with col3:
        new_item_price = st.number_input("Price", min_value=0.0, step=0.5)

    if st.button("➕ Add Item"):
        if new_item_name.strip():
            cursor.execute("""
                INSERT INTO menus (restaurant_id, item, category, price)
                VALUES (?, ?, ?, ?)
            """, (current_restaurant, new_item_name.strip(), new_item_cat, float(new_item_price)))
            conn.commit()
            st.success("Item added.")
            st.rerun()
        else:
            st.warning("Enter an item name.")

# ---------------------- ORDERS TAB ----------------------
with tab_orders:
    st.subheader("Table Ordering")

    tables = load_tables()
    if tables.empty:
        st.info("No tables defined. Create tables in the Tables tab.")
    else:
        cols = st.columns(4)
        selected_table = st.session_state.get("selected_table")

        for idx, row in tables.iterrows():
            if cols[idx % 4].button(f"{row['table_name']} ({row['status']})"):
                st.session_state.selected_table = row["id"]
                selected_table = row["id"]

        if not selected_table:
            st.info("Select a table above.")
        else:
            t = tables[tables["id"] == selected_table].iloc[0]
            st.write(f"### Table {t['table_name']}")

            name = st.text_input("Customer Name", value=t["customer_name"] or "")
            people = st.number_input("People", min_value=0, value=int(t["people"] or 0))
            remarks = st.text_area("Remarks", value=t["remarks"] or "")
            status = st.selectbox("Status", ["Available", "Seated"],
                                  index=1 if t["status"] == "Seated" else 0)

            if st.button("Save Table Info"):
                update_table(selected_table, name, people, remarks, status)
                st.success("Saved.")
                st.rerun()

            order = get_open_order(selected_table)

            if not order:
                if status == "Seated":
                    if st.button("Open Order"):
                        oid = create_order(selected_table)
                        st.success(f"Order #{oid} opened.")
                        st.rerun()
                else:
                    st.info("Set status to 'Seated' to open an order.")
            else:
                st.write(f"### Active Order #{order['id']} — Total: ${order['total']:.2f}")

                menu_df = load_menu()
                if menu_df.empty:
                    st.info("No menu items. Configure menu in the Menu tab.")
                else:
                    st.dataframe(menu_df[["item", "category", "price"]], use_container_width=True)

                    item_name = st.selectbox("Item", menu_df["item"])
                    qty = st.number_input("Qty", min_value=1, value=1)

                    if st.button("Add Item to Order"):
                        row = menu_df[menu_df["item"] == item_name].iloc[0]
                        add_item(order["id"], row["item"], row["category"], qty, row["price"])
                        st.success("Item added.")
                        st.rerun()

                    items = load_order_items()
                    items = items[items["order_id"] == order["id"]]
                    st.dataframe(items, use_container_width=True)

                    if st.button("Close Order"):
                        close_order(order["id"])
                        update_table(selected_table, "", 0, "", "Available")
                        st.success("Order closed.")
                        st.rerun()

# ---------------------- SALES REPORT TAB ----------------------
with tab_report:
    st.subheader("Sales Report")

    orders = load_orders()
    closed = orders[orders["status"] == "Closed"]

    if closed.empty:
        st.info("No closed orders yet.")
    else:
        closed["closed_at"] = pd.to_datetime(closed["closed_at"], errors="coerce")

        start = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        end = st.date_input("End Date", datetime.now())

        mask = (closed["closed_at"].dt.date >= start) & (closed["closed_at"].dt.date <= end)
        filtered = closed[mask]

        if filtered.empty:
            st.info("No sales in this period.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Revenue", f"${filtered['total'].sum():.2f}")
            with col2:
                st.metric("Closed Orders", len(filtered))

            st.dataframe(filtered, use_container_width=True)

            chart = (
                alt.Chart(filtered)
                .mark_line(point=True)
                .encode(x="closed_at:T", y="total:Q")
            )
            st.altair_chart(chart, use_container_width=True)
