import streamlit as st
import pandas as pd
import altair as alt
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="Restaurant POS", layout="wide")

# ---------------------- GLOBAL GRAYSCALE THEME ----------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    filter: grayscale(100%) !important;
}
body {
    background-color: #E5E5E5 !important;
}
.block-container {
    background-color: #F2F2F2 !important;
    padding: 2rem;
    border-radius: 8px;
}
.stButton>button {
    background-color: #555 !important;
    color: white !important;
    border-radius: 6px;
    border: 1px solid #333 !important;
}
.stButton>button:hover {
    background-color: #333 !important;
}
input, textarea, select {
    background-color: #FAFAFA !important;
    border: 1px solid #999 !important;
    color: #333 !important;
}
.stTabs [role="tab"] {
    background-color: #D9D9D9 !important;
    color: #333 !important;
    border-radius: 6px;
    padding: 8px 16px;
}
.stTabs [role="tab"][aria-selected="true"] {
    background-color: #BFBFBF !important;
    color: black !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------- DATABASE SETUP ----------------------
conn = sqlite3.connect("restaurant.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    order_id INTEGER,
    item_name TEXT,
    category TEXT,
    qty INTEGER,
    price REAL,
    line_total REAL
)
""")

# ---------------------- HELPERS ----------------------
def load_tables():
    return pd.read_sql("SELECT * FROM tables", conn)

def load_orders():
    return pd.read_sql("SELECT * FROM orders", conn)

def load_order_items():
    return pd.read_sql("SELECT * FROM order_items", conn)

def create_table(name):
    cursor.execute("INSERT INTO tables (table_name) VALUES (?)", (name,))
    conn.commit()

def update_table(table_id, name, people, remarks, status):
    cursor.execute("""
        UPDATE tables SET customer_name=?, people=?, remarks=?, status=? WHERE id=?
    """, (name, people, remarks, status, table_id))
    conn.commit()

def create_order(table_id):
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO orders (table_id, opened_at, status, total)
        VALUES (?, ?, 'Open', 0)
    """, (table_id, now))
    conn.commit()
    return cursor.lastrowid

def get_open_order(table_id):
    cursor.execute("""
        SELECT * FROM orders WHERE table_id=? AND status='Open'
    """, (table_id,))
    row = cursor.fetchone()
    if row:
        cols = [c[0] for c in cursor.description]
        return dict(zip(cols, row))
    return None

def add_item(order_id, item, category, qty, price):
    total = qty * price
    cursor.execute("""
        INSERT INTO order_items (order_id, item_name, category, qty, price, line_total)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, item, category, qty, price, total))
    cursor.execute("UPDATE orders SET total = total + ? WHERE id=?", (total, order_id))
    conn.commit()

def close_order(order_id):
    now = datetime.now().isoformat()
    cursor.execute("""
        UPDATE orders SET status='Closed', closed_at=? WHERE id=?
    """, (now, order_id))
    conn.commit()

# ---------------------- MENU (Editable) ----------------------
if "MENU" not in st.session_state:
    st.session_state.MENU = [
        {"item": "Margherita Pizza", "category": "Food", "price": 12.0},
        {"item": "Pasta Carbonara", "category": "Food", "price": 14.0},
        {"item": "Coke", "category": "Drink", "price": 3.0},
        {"item": "Espresso", "category": "Drink", "price": 3.5},
    ]

MENU = st.session_state.MENU

# ---------------------- UI ----------------------
st.title("🍽️ Restaurant POS (Grayscale Edition)")

tab1, tab2, tab3 = st.tabs(["🪑 Tables", "🧾 Orders & Menu", "📊 Sales Report"])

# ---------------------- TABLES TAB ----------------------
with tab1:
    st.subheader("Manage Tables")

    new_table = st.text_input("New Table Name (e.g., T1)")
    if st.button("Add Table"):
        create_table(new_table)
        st.success("Table added.")
        st.rerun()

    tables = load_tables()
    st.dataframe(tables, use_container_width=True)

# ---------------------- ORDERS & MENU TAB ----------------------
with tab2:
    st.subheader("Menu Management")

    menu_df = pd.DataFrame(MENU)
    edited = st.data_editor(menu_df, num_rows="dynamic", use_container_width=True)

    if st.button("Save Menu"):
        st.session_state.MENU = edited.to_dict(orient="records")
        st.success("Menu updated.")
        st.rerun()

    st.markdown("---")
    st.subheader("Table Ordering")

    tables = load_tables()
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
        status = st.selectbox("Status", ["Available", "Seated"], index=1 if t["status"] == "Seated" else 0)

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
            st.write(f"### Active Order #{order['id']} — Total: ${order['total']:.2f}")

            menu_df = pd.DataFrame(st.session_state.MENU)
            st.dataframe(menu_df, use_container_width=True)

            item = st.selectbox("Item", menu_df["item"])
            qty = st.number_input("Qty", min_value=1, value=1)

            if st.button("Add Item"):
                row = menu_df[menu_df["item"] == item].iloc[0]
                add_item(order["id"], row["item"], row["category"], qty, row["price"])
                st.success("Added.")
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
with tab3:
    st.subheader("Sales Report")

    orders = load_orders()
    closed = orders[orders["status"] == "Closed"]

    if closed.empty:
        st.info("No closed orders yet.")
    else:
        closed["closed_at"] = pd.to_datetime(closed["closed_at"])

        start = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        end = st.date_input("End Date", datetime.now())

        mask = (closed["closed_at"].dt.date >= start) & (closed["closed_at"].dt.date <= end)
        filtered = closed[mask]

        st.metric("Total Revenue", f"${filtered['total'].sum():.2f}")
        st.metric("Closed Orders", len(filtered))

        st.dataframe(filtered, use_container_width=True)

        chart = (
            alt.Chart(filtered)
            .mark_line(point=True)
            .encode(x="closed_at:T", y="total:Q")
        )
        st.altair_chart(chart, use_container_width=True)
