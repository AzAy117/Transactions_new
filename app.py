import streamlit as st
import pandas as pd
from datetime import datetime
import requests

st.set_page_config(
    page_title="Len-Den - Transaction Ledger",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #f3f4f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://rxviyapbachsokbcongc.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_ipPMI5mrbu0dn8psVkAjTQ_xbwGqMBk")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

if "transactions" not in st.session_state:
    st.session_state.transactions = []

if "editing_tx" not in st.session_state:
    st.session_state.editing_tx = None

def fetch_transactions():
    try:
        url = f"{SUPABASE_URL}/rest/v1/transactions?select=*&order=date.desc,id.desc"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
        return []
    except Exception as e:
        st.error(f"Database error: {e}")
        return []

def add_transaction(date, amount, reason, screenshot=""):
    try:
        url = f"{SUPABASE_URL}/rest/v1/transactions"
        payload = {
            "date": str(date),
            "amount": float(amount),
            "reason": reason,
            "screenshot": screenshot
        }
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code in [200, 201]:
            return True, None
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def update_transaction(tx_id, date, amount, reason, screenshot=""):
    try:
        url = f"{SUPABASE_URL}/rest/v1/transactions?id=eq.{tx_id}"
        payload = {
            "date": str(date),
            "amount": float(amount),
            "reason": reason,
            "screenshot": screenshot
        }
        response = requests.patch(url, headers=HEADERS, json=payload)
        if response.status_code in [200, 204]:
            return True, None
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def delete_transaction(tx_id):
    try:
        url = f"{SUPABASE_URL}/rest/v1/transactions?id=eq.{tx_id}"
        requests.delete(url, headers=HEADERS)
    except Exception as e:
        st.error(f"Failed to delete: {e}")

st.title("💸 Len-Den")
st.markdown("Your secure personal transaction ledger and tracker.")

transactions = fetch_transactions()
if not isinstance(transactions, list):
    transactions = []

total_income = sum(t["amount"] for t in transactions if isinstance(t, dict) and t.get("amount", 0) > 0)
total_expenses = sum(abs(t["amount"]) for t in transactions if isinstance(t, dict) and t.get("amount", 0) < 0)
net_balance = sum(t["amount"] for t in transactions if isinstance(t, dict))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Sent (You Gave)", f"₹{total_income:.2f}")
with col2:
    st.metric("Total Received (You Got)", f"₹{total_expenses:.2f}")
with col3:
    st.metric("Net Balance", f"₹{net_balance:.2f}")

st.divider()

if st.session_state.editing_tx:
    st.sidebar.header("✏️ Edit Transaction")
    etx = st.session_state.editing_tx
    with st.sidebar.form("edit_form"):
        try:
            default_date = datetime.strptime(etx.get("date", "2026-01-01").split("T")[0], "%Y-%m-%d").date()
        except:
            default_date = datetime.today().date()
            
        edit_date = st.date_input("Date", value=default_date)
        edit_amount = st.number_input("Amount", value=float(etx.get("amount", 0.0)), step=1.00, format="%.2f")
        edit_reason = st.text_input("Reason / Name", value=etx.get("reason", ""))
        edit_file = st.file_uploader("Upload New Receipt (Optional)", type=["png", "jpg", "jpeg"])
        
        col_save, col_cancel = st.columns(2)
        save_btn = col_save.form_submit_button("Save Changes")
        cancel_btn = col_cancel.form_submit_button("Cancel")
        
        if save_btn:
            screenshot_url = etx.get("screenshot", "")
            if edit_file:
                try:
                    file_path = f"receipts/{datetime.now().timestamp()}_{edit_file.name}"
                    storage_url = f"{SUPABASE_URL}/storage/v1/object/receipts/{file_path}"
                    storage_headers = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": edit_file.type
                    }
                    requests.post(storage_url, headers=storage_headers, data=edit_file.getvalue())
                    screenshot_url = f"{SUPABASE_URL}/storage/v1/object/public/receipts/{file_path}"
                except Exception as e:
                    st.sidebar.warning(f"Image upload failed: {e}")
            
            success, err_msg = update_transaction(etx["id"], edit_date, edit_amount, edit_reason, screenshot_url)
            if success:
                st.session_state.editing_tx = None
                st.sidebar.success("Updated successfully!")
                st.rerun()
            else:
                st.sidebar.error(f"Error: {err_msg}")
        
        if cancel_btn:
            st.session_state.editing_tx = None
            st.rerun()
else:
    st.sidebar.header("Add New Transaction")
    with st.sidebar.form("add_form", clear_on_submit=True):
        tx_date = st.date_input("Date", value=datetime.today())
        tx_amount = st.number_input("Amount (Use negative for Received/Got)", value=0.0, step=1.00, format="%.2f")
        tx_reason = st.text_input("Reason / Name")
        tx_file = st.file_uploader("Upload Receipt / Screenshot", type=["png", "jpg", "jpeg"])
        
        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            if not tx_reason:
                st.sidebar.error("Please enter a reason.")
            else:
                screenshot_url = ""
                if tx_file:
                    try:
                        file_path = f"receipts/{datetime.now().timestamp()}_{tx_file.name}"
                        storage_url = f"{SUPABASE_URL}/storage/v1/object/receipts/{file_path}"
                        storage_headers = {
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}",
                            "Content-Type": tx_file.type
                        }
                        requests.post(storage_url, headers=storage_headers, data=tx_file.getvalue())
                        screenshot_url = f"{SUPABASE_URL}/storage/v1/object/public/receipts/{file_path}"
                    except Exception as e:
                        st.sidebar.warning(f"Image upload failed: {e}")
                
                success, err_msg = add_transaction(tx_date, tx_amount, tx_reason, screenshot_url)
                if success:
                    st.sidebar.success("Transaction added successfully!")
                    st.rerun()
                else:
                    st.sidebar.error(f"Error: {err_msg}")

st.subheader("Search & Filter Transactions")
f_col1, f_col2, f_col3 = st.columns(3)
with f_col1:
    search_query = st.text_input("Search by reason", "")
with f_col2:
    min_amt = st.number_input("Min Amount", value=0.0, step=10.0)
with f_col3:
    max_amt = st.number_input("Max Amount", value=100000.0, step=10.0)

filtered_txs = [
    t for t in transactions 
    if isinstance(t, dict) 
    and search_query.lower() in str(t.get("reason", "")).lower() 
    and min_amt <= abs(t.get("amount", 0)) <= max_amt
]

if filtered_txs:
    df_export = pd.DataFrame(filtered_txs)
    csv_data = df_export.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Export Filtered Data as CSV", data=csv_data, file_name="lenden_transactions.csv", mime="text/csv")

st.divider()
st.subheader("Transaction History")

if not filtered_txs:
    st.info("No transactions found or database is empty. Add one using the sidebar!")
else:
    for idx, t in enumerate(filtered_txs):
        amt = t.get("amount", 0)
        row_bg = "#f0fdf4" if idx % 2 == 0 else "#f8fafd"
        text_color = "#16a34a" if amt >= 0 else "#dc2626"
        
        raw_date = str(t.get("date", "")).split("T")[0]
        try:
            date_display = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            date_display = raw_date
            
        reason = t.get("reason", "")
        tx_id = t.get('id', idx)
        
        with st.container():
            col_date, col_amt, col_reason, col_edit, col_del = st.columns([2, 2, 5, 0.7, 0.7])
            with col_date:
                st.markdown(f"<div style='padding: 10px 0; color: #111827;'>{date_display}</div>", unsafe_allow_html=True)
            with col_amt:
                st.markdown(f"<div style='padding: 10px 0; font-weight: 600; color: {text_color};'>₹{amt:.2f}</div>", unsafe_allow_html=True)
            with col_reason:
                st.markdown(f"<div style='padding: 10px 0; color: #111827;'>{reason}</div>", unsafe_allow_html=True)
            with col_edit:
                if st.button("✏️", key=f"edit_{tx_id}_{idx}", help="Edit Transaction"):
                    st.session_state.editing_tx = t
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{tx_id}_{idx}", help="Delete Transaction"):
                    delete_transaction(tx_id)
                    st.success("Deleted!")
                    st.rerun()
            
            st.markdown(f"<div style='border-bottom: 1px solid #e5e7eb; margin-top: 2px; margin-bottom: 2px;'></div>", unsafe_allow_html=True)
