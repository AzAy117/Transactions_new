import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

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

@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL", "https://rxviyapbachsokbcongc.supabase.co")
    key = st.secrets.get("SUPABASE_KEY", "sb_publishable_ipPMI5mrbu0dn8psVkAjTQ_xbwGqMBk")
    if not url or not key:
        return None
    return create_client(url, key)

supabase = init_supabase()

if "transactions" not in st.session_state:
    st.session_state.transactions = []

def fetch_transactions():
    if supabase:
        try:
            response = supabase.table("transactions").select("*").order("date", desc=False).execute()
            # Ensure response.data is actually a list
            if response.data and isinstance(response.data, list):
                return response.data
            return []
        except Exception as e:
            st.error(f"Database error: {e}")
            return []
    return st.session_state.transactions


def add_transaction(date, amount, reason, screenshot=""):
    if supabase:
        try:
            response = supabase.table("transactions").insert({
                "date": str(date),
                "amount": float(amount),
                "reason": reason,
                "screenshot": screenshot
            }).execute()

            return True, None

        except Exception as e:
            st.error(f"Failed to insert: {e}")
            return False, str(e)

    else:
        new_id = len(st.session_state.transactions) + 1

        st.session_state.transactions.append({
            "id": new_id,
            "date": str(date),
            "amount": float(amount),
            "reason": reason,
            "screenshot": screenshot
        })

        return True, None

def delete_transaction(tx_id):
    if supabase:
        try:
            supabase.table("transactions").delete().eq("id", tx_id).execute()
        except Exception as e:
            st.error(f"Failed to delete: {e}")
    else:
        st.session_state.transactions = [t for t in st.session_state.transactions if t["id"] != tx_id]

st.title("💸 Len-Den")
st.markdown("Your secure personal transaction ledger and tracker.")

transactions = fetch_transactions()

# Ensure transactions is always a list before running calculations
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
            if tx_file and supabase:
                try:
                    file_path = f"receipts/{datetime.now().timestamp()}_{tx_file.name}"
                    supabase.storage.from_("receipts").upload(file_path, tx_file.getvalue())
                    screenshot_url = supabase.storage.from_("receipts").get_public_url(file_path)
                except Exception as e:
                    st.sidebar.warning(f"Image upload failed: {e}")
            
            # Yahan return values ko capture karo!
            success, err_msg = add_transaction(tx_date, tx_amount, tx_reason, screenshot_url)
            
            if success:
                st.sidebar.success("Transaction added successfully!")
                st.rerun()
            else:
                # Ab error screen par permanently dikhega aur gayab nahi hoga
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
    table_html = '<div style="width: 100%; overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; background-color: white; font-family: sans-serif; font-size: 14px;"><thead><tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;"><th style="padding: 12px; text-align: left;">Date</th><th style="padding: 12px; text-align: left;">Amount</th><th style="padding: 12px; text-align: left;">Type</th><th style="padding: 12px; text-align: left;">Reason</th><th style="padding: 12px; text-align: left;">Receipt</th></tr></thead><tbody>'
    
    for t in filtered_txs:
        amt = t.get("amount", 0)
        row_bg = "#fef2f2" if amt >= 0 else "#f0fdf4"
        text_color = "#dc2626" if amt >= 0 else "#16a34a"
        type_label = "Gave (Sent)" if amt >= 0 else "Got (Received)"
        date_display = str(t.get("date", "")).split("T")[0]
        screenshot = t.get("screenshot", "")
        receipt_html = f"<a href='{screenshot}' target='_blank'>View</a>" if screenshot else "No Image"
        
        table_html += f'<tr style="border-bottom: 1px solid #e5e7eb; background-color: {row_bg};"><td style="padding: 12px;">{date_display}</td><td style="padding: 12px; font-weight: bold; color: {text_color};">₹{amt:.2f}</td><td style="padding: 12px; color: {text_color};">{type_label}</td><td style="padding: 12px;">{t.get("reason", "")}</td><td style="padding: 12px;">{receipt_html}</td></tr>'
        
    table_html += '</tbody></table></div>'
    st.markdown(table_html, unsafe_allow_html=True)
    
    st.write("")
    with st.expander("🗑️ Delete a Transaction"):
        del_options = {f"{t.get('date')} | {t.get('reason')} | ₹{t.get('amount')}": t.get('id') for t in filtered_txs if t.get('id')}
        if del_options:
            selected_to_delete = st.selectbox("Select transaction to delete", options=list(del_options.keys()))
            if st.button("Confirm Delete Selected"):
                tx_id_to_del = del_options[selected_to_delete]
                delete_transaction(tx_id_to_del)
                st.success("Deleted successfully!")
                st.rerun()
