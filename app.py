import streamlit as st
import pymongo
import streamlit_authenticator as stauth

# 1. MongoDB Connection
client = pymongo.MongoClient(st.secrets["MONGO_URI"])
db = client["User_Details"]
collection = db["users"]

# 2. Helper to get credentials for the authenticator
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
st.title("TrustChain: Reputation Demo")
tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    authenticator.login()
    
    if st.session_state["authentication_status"]:
        st.success(f"Welcome {st.session_state['name']}!")
        
        # Use the built-in logout method which handles session clearing correctly
        authenticator.logout("Logout", "main")
        
        # --- REPUTATION BOARD START ---
        st.write("---")
        st.subheader("Community Reputation Board")
        
        all_users = list(collection.find())
        
        for u in all_users:
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(f"👤 **{u['username']}**")
            col2.write(f"Score: **{u.get('score', 0)}**")
            
            # Vouch logic
            if u['username'] != st.session_state['username']:
                if col3.button("Vouch", key=f"vouch_{u['username']}"):
                    if st.session_state['username'] not in u.get('vouched_by', []):
                        collection.update_one(
                            {"username": u['username']},
                            {"$inc": {"score": 10}, "$push": {"vouched_by": st.session_state['username']}}
                        )
                        st.rerun()
                    else:
                        st.toast("Already vouched for this user!")
            else:
                col3.write("*(Self)*")
        # --- REPUTATION BOARD END ---

    elif st.session_state["authentication_status"] is False:
        st.error("Invalid username/password")
    elif st.session_state["authentication_status"] is None:
        st.warning("Please enter your username and password")

with tab2:
    with st.form("register_form"):
        new_user = st.text_input("Username")
        new_name = st.text_input("Full Name")
        new_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Register"):
            if collection.find_one({"username": new_user}):
                st.error("Username already taken")
            else:
                # Use the hash method directly on the password string
                hashed_pw = stauth.Hasher().hash(new_pass)  
                collection.insert_one({
                    "username": new_user,
                    "name": new_name,
                    "password": hashed_pw,
                    "score": 0,
                    "vouched_by": []
                })
                st.success("User created! Go to Login tab.")