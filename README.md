# 🍽️ Restaurant Table‑Ordering POS (Streamlit + SQLite)

A lightweight, web‑based restaurant POS system built with **Streamlit** and **SQLite**, designed for fast table management, customer seating, and simple food/drink ordering. This project demonstrates clean UI/UX patterns, real‑time order handling, and a complete sales analytics dashboard — all running in the browser with no external backend.

---

## 🚀 Features

### 🪑 Table & Seating Management
- Create and label tables (T1, T2, T3…)
- Click a table to load its details
- Assign customer name, number of people, and remarks
- Set table status: **Available** or **Seated**
- Automatically link tables to active orders

### 🧾 Table Ordering
- Open an order when a table is seated
- Add food and drink items with quantity
- Simple predefined menu (Pizza, Pasta, Drinks, etc.)
- Real‑time order summary with running totals
- Close order → frees table + saves sales record

### 📊 Sales Report Dashboard
- Filter closed orders by date range
- Metrics: **Total Revenue**, **Closed Orders**
- Revenue‑over‑time line chart (Altair)
- Top items sold table
- Clean, modern analytics layout

---

## 🗂️ Tech Stack

- **Python 3**
- **Streamlit** (web UI)
- **SQLite** (local database)
- **Pandas** (data handling)
- **Altair** (charts)

---

## 📦 Installation

```bash
pip install -r requirements.txt
