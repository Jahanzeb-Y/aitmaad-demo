import streamlit as st
import pymongo
import streamlit_authenticator as stauth
import pandas as pd

# Set page config
st.set_page_config(page_title="Aitmaad", page_icon="🛡️", layout="wide")

# Custom CSS for Navy/Gold Theme
st.markdown("""
    <style>
    .stApp { background-color: #000080; color: #FFD700; }
    h1, h2, h3 { color: #FFD700; }
    .stButton>button { background-color: #FFD700; color: #000080; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #000040; }
    </style>
""", unsafe_allow_html=True)

# 1. MongoDB Connection
client = pymongo.MongoClient(st.secrets["MONGO_URI"])
db = client["User_Details"]
collection = db["users"]

# 2. Helper to get credentials
def fetch_credentials():
    users = list(collection.find())
    credentials = {"usernames": {}}
    for u in users:
        credentials["usernames"][u["username"]] = {
            "name": u["name"],
            "password": u["password"]
        }
    return credentials

# 3. Setup Authenticator
config = {
    "cookie": {"name": "rep_app", "key": "random_key", "expiry_days": 30},
    "credentials": fetch_credentials()
}
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

# 4. App UI
st.title("🛡️ Aitmaad: TrustChain")


# Sidebar: Leaderboard
with st.sidebar:
    st.markdown("### 🏆 Top Trust Leaders")
    top_users = list(collection.find().sort("score", -1).limit(5))
    for i, u in enumerate(top_users, 1):
        st.write(f"**{i}. {u['name']}**")
        st.metric("Trust Rating", u.get('score', 0))
    st.markdown("---")

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    authenticator.login()
    if st.session_state.get("authentication_status"):
        st.success(f"Welcome {st.session_state['name']}!")
        authenticator.logout("Logout", "main")
        
        st.write("---")
        st.subheader("Community Reputation Board")
        
        for u in collection.find():
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 2])
                col1.write(f"👤 **{u['username']}**")
                col2.metric("Trust Rating", u.get('score', 0))
                
                b = u.get('breakdown', {'payment_consistency': 0, 'honesty': 0, 'quality_of_work': 0})
                with st.expander("View Trust Breakdown"):
                    st.write(f"💰 Payments: {b.get('payment_consistency', 0)} pts")
                    st.write(f"⭐ Honesty: {b.get('honesty', 0)} pts")
                    st.write(f"🛠 Quality: {b.get('quality_of_work', 0)} pts")
                    chart_data = pd.DataFrame({
                        "Category": ["Payments", "Honesty", "Quality"],
                        "Score": [b.get('payment_consistency', 0), b.get('honesty', 0), b.get('quality_of_work', 0)]
                    })
                    st.bar_chart(chart_data.set_index("Category"))
                
                if u['username'] != st.session_state.get('username'):
                    vouch_cat = col3.selectbox("Category", ["Payment Consistency", "Honesty", "Quality of Work"], key=f"select_{u['username']}")
                    sub_col1, sub_col2, sub_col3 = col3.columns(3)
                    
                    field_map = {"Payment Consistency": "payment_consistency", "Honesty": "honesty", "Quality of Work": "quality_of_work"}
                    db_field = f"breakdown.{field_map[vouch_cat]}"
                    
                    if sub_col1.button("👍 Vouch", key=f"up_{u['username']}"):
                        if st.session_state['username'] not in u.get('vouched_by', []):
                            collection.update_one({"username": u['username']}, {
                                "$inc": {"score": 10, db_field: 10},
                                "$push": {"vouched_by": st.session_state['username']},
                                "$pull": {"downvoted_by": st.session_state['username']}
                            })
                            if st.session_state['username'] in u.get('downvoted_by', []):
                                collection.update_one({"username": u['username']}, {"$inc": {"score": 10, db_field: 10}})
                            st.rerun()
                        else: st.toast("Already vouched!")
                    
                    if sub_col2.button("👎 Down", key=f"down_{u['username']}"):
                        if st.session_state['username'] not in u.get('downvoted_by', []):
                            collection.update_one({"username": u['username']}, {
                                "$inc": {"score": -10, db_field: -10},
                                "$push": {"downvoted_by": st.session_state['username']},
                                "$pull": {"vouched_by": st.session_state['username']}
                            })
                            if st.session_state['username'] in u.get('vouched_by', []):
                                collection.update_one({"username": u['username']}, {"$inc": {"score": -10, db_field: -10}})
                            st.rerun()
                        else: st.toast("Already downvoted!")
                    
                    sub_col3.link_button("Hire", "https://wa.me/your-number")
                    col3.link_button("Chat via WhatsApp", "https://wa.me/your-number")

    elif st.session_state.get("authentication_status") is False:
        st.error("Invalid username/password")

with tab2:
    with st.form("register_form"):
        new_user = st.text_input("Username")
        new_name = st.text_input("Full Name")
        new_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Register"):
            if collection.find_one({"username": new_user}): st.error("Username taken")
            else:
                collection.insert_one({
                    "username": new_user, "name": new_name, "password": stauth.Hasher().hash(new_pass),
                    "score": 0, "breakdown": {'payment_consistency': 0, 'honesty': 0, 'quality_of_work': 0},
                    "vouched_by": [], "downvoted_by": []
                })
                st.success("User created!")