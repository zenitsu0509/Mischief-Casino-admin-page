import streamlit as st
import requests
import json
import os
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GIST_FILENAME = os.getenv("GIST_FILENAME")
APP_PASSWORD = os.getenv("APP_PASSWORD")

# App configuration
st.set_page_config(
    page_title="GitHub Gist Manager",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        padding: 10px;
        border: none;
        border-radius: 4px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    .stTextInput>div>div>input {
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Authentication function
def check_password():
    """Returns `True` if the user had the correct password."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        
    if st.session_state.authenticated:
        return True
    
    # Center the login form
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 Admin Login</h1>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'>Please enter your password to continue</div>", unsafe_allow_html=True)
        
        password_input = st.text_input(
            "Password", 
            type="password", 
            key="password_input",
            label_visibility="collapsed"
        )
        
        if st.button("Login", use_container_width=True):
            if password_input == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            elif password_input:
                st.error("❌ Incorrect password")
                return False
    return False

# Function to fetch gist data
def fetch_gist_data():
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
    
    if response.status_code == 200:
        gist_data = response.json()
        content = gist_data["files"][GIST_FILENAME]["content"]
        return json.loads(content)
    else:
        st.error(f"Failed to fetch gist: {response.status_code}")
        return None

# Function to update gist data
def update_gist_data(data):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "files": {
            GIST_FILENAME: {
                "content": json.dumps(data, indent=2)
            }
        }
    }
    
    response = requests.patch(f"https://api.github.com/gists/{GIST_ID}", 
                             headers=headers, 
                             data=json.dumps(payload))
    
    if response.status_code == 200:
        st.success("Data updated successfully!")
        return True
    else:
        st.error(f"Failed to update gist: {response.status_code}")
        return False

# Function to create a new user
def create_user(username, password, money=0):
    users = fetch_gist_data()
    
    # Check if username already exists
    if any(user["username"] == username for user in users):
        st.error("Username already exists!")
        return False
    
    # Create new user
    new_user = {
        "username": username,
        "password": password,
        "money": float(money),
        "createdAt": datetime.now().isoformat(),
        "lastLogin": datetime.now().isoformat()
    }
    
    users.append(new_user)
    return update_gist_data(users)

# Main app
def main():
    if not check_password():
        st.stop()
    
    st.title("GitHub Gist User Manager")
    
    # Tabs for different functions
    tab1, tab2, tab3 = st.tabs(["View Users", "Add User", "Edit User"])
    
    # Load data
    data = fetch_gist_data()
    
    if data:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(data)
        
        # Tab 1: View Users
        with tab1:
            st.header("User Database")
            
            # Search functionality
            search_query = st.text_input("🔍 Search by username", key="search_query")
            
            filtered_df = df
            if search_query:
                filtered_df = df[df['username'].str.contains(search_query, case=False)]
            
            # Display data
            st.dataframe(filtered_df, use_container_width=True)
            
            # Save changes button
            if st.button("💾 Save All Changes", use_container_width=True):
                if update_gist_data(data):
                    st.success("All changes saved successfully!")
        
        # Tab 2: Add User
        with tab2:
            st.header("Add New User")
            
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_money = st.number_input("Initial Balance", value=0.0, step=100.0)
                
                submit_button = st.form_submit_button("➕ Add User")
                
                if submit_button:
                    if new_username and new_password:
                        if create_user(new_username, new_password, new_money):
                            st.success(f"✅ User '{new_username}' created successfully!")
                            st.rerun()
                    else:
                        st.error("❌ Username and password are required!")
        
        # Tab 3: Edit User
        with tab3:
            st.header("Edit User")
            
            # Add search functionality for Edit User tab
            edit_search = st.text_input("🔍 Search user to edit", key="edit_search")
            
            # Filter usernames based on search
            usernames = df['username'].tolist()
            if edit_search:
                usernames = [username for username in usernames if edit_search.lower() in username.lower()]
            
            if not usernames:
                st.warning("No users found matching your search criteria")
                st.stop()
            
            # Select user to edit
            selected_user = st.selectbox("Select a user to edit", usernames)
            
            # Get the selected user data
            user_data = df[df['username'] == selected_user].iloc[0].to_dict()
            
            with st.form("edit_user_form"):
                edit_password = st.text_input("Password", value=user_data['password'])
                edit_money = st.number_input("Balance", value=float(user_data['money']), step=100.0)
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_edit = st.form_submit_button("💾 Update User")
                with col2:
                    delete_user = st.form_submit_button("🗑️ Delete User", type="primary")
                
                if submit_edit:
                    # Update the user data
                    for i, user in enumerate(data):
                        if user['username'] == selected_user:
                            data[i]['password'] = edit_password
                            data[i]['money'] = float(edit_money)
                            data[i]['lastLogin'] = datetime.now().isoformat()
                            
                            if update_gist_data(data):
                                st.success(f"✅ User '{selected_user}' updated successfully!")
                                st.rerun()
                
                if delete_user:
                    if st.session_state.get('delete_confirmed', False):
                        for i, user in enumerate(data):
                            if user['username'] == selected_user:
                                data.pop(i)
                                if update_gist_data(data):
                                    st.success(f"✅ User '{selected_user}' deleted successfully!")
                                    st.rerun()
                    else:
                        st.warning("⚠️ Please confirm deletion by clicking the delete button again")
                        st.session_state.delete_confirmed = True

if __name__ == "__main__":
    main()