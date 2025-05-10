import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid # For generating unique IDs if needed

# --- Configuration ---
load_dotenv()  # Load variables from .env file

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GIST_FILENAME = os.getenv("GIST_FILENAME")
APP_PASSWORD = os.getenv("APP_PASSWORD") # Load the app password

if not all([GITHUB_TOKEN, GIST_ID, GIST_FILENAME, APP_PASSWORD]):
    st.error("Missing one or more environment variables (GITHUB_TOKEN, GIST_ID, GIST_FILENAME, APP_PASSWORD). "
             "Please ensure your .env file is set up correctly and contains all four variables.")
    st.stop()

API_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'Content-Type': 'application/json' # For PATCH requests
}

# --- Helper Functions ---
def ensure_unique_id(item_list):
    """Ensures each item in the list has a unique '_app_id'."""
    for item in item_list:
        if isinstance(item, dict) and '_app_id' not in item:
            # If 'createdAt' is reliably unique, use that, otherwise generate UUID
            # For this example, we'll prefer createdAt if it exists, else UUID
            if 'createdAt' in item:
                 item['_app_id'] = str(item['createdAt']) # Assuming createdAt is unique enough
            else:
                 item['_app_id'] = str(uuid.uuid4())
    return item_list


def fetch_gist_data():
    try:
        response = requests.get(API_URL, headers={k: v for k, v in HEADERS.items() if k != 'Content-Type'})
        response.raise_for_status()
        gist = response.json()
        if gist.get("files") and gist["files"].get(GIST_FILENAME) and gist["files"][GIST_FILENAME].get("content"):
            content = gist["files"][GIST_FILENAME]["content"]
            loaded_data = json.loads(content)
            if isinstance(loaded_data, list):
                loaded_data = ensure_unique_id(loaded_data) # Add unique IDs
                for item in loaded_data:
                    if isinstance(item, dict) and 'money' in item:
                        try:
                            item['money'] = float(item['money'])
                        except (ValueError, TypeError):
                            item['money'] = 0.0
            return loaded_data
        else:
            st.warning(f"File '{GIST_FILENAME}' not found in Gist or content is empty. Returning empty list.")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching Gist data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                st.error(f"Response content: {e.response.json()}")
            except json.JSONDecodeError:
                st.error(f"Response content (not JSON): {e.response.text}")
        return None
    except json.JSONDecodeError:
        st.error("Error decoding JSON from Gist. The file content might be corrupted.")
        return []

def update_gist_data(data_to_save):
    if isinstance(data_to_save, list):
        for item in data_to_save:
            if isinstance(item, dict):
                if 'money' in item:
                    try:
                        item['money'] = float(item['money'])
                    except (ValueError, TypeError):
                        item['money'] = 0.0
                # item.pop('_app_id', None) # Optionally remove app-specific ID before saving to Gist
    payload = {
        "description": f"Updated {GIST_FILENAME} via Streamlit Gist Manager",
        "files": { GIST_FILENAME: { "content": json.dumps(data_to_save, indent=2) } }
    }
    try:
        response = requests.patch(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        st.success("Data saved to Gist successfully!")
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error updating Gist data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: st.error(f"Response content: {e.response.json()}")
            except json.JSONDecodeError: st.error(f"Response content (not JSON): {e.response.text}")
        return False

def check_password(entered_password):
    return entered_password == APP_PASSWORD

def main_app():
    st.sidebar.header("Actions")

    if st.sidebar.button("🔄 Load Data from Gist", key="load_data_btn"):
        with st.spinner("Loading data..."):
            data = fetch_gist_data()
            if data is not None:
                st.session_state.gist_data_original = data if isinstance(data, list) else []
                st.session_state.gist_data_filtered = st.session_state.gist_data_original
            else:
                st.session_state.gist_data_original = []
                st.session_state.gist_data_filtered = []
        st.session_state.search_term = ""
        st.session_state.editing_user_app_id = None # Reset editing state
        st.rerun()

    if st.sidebar.button("💾 Save Changes to Gist", type="primary", key="save_data_btn"):
        if not st.session_state.gist_data_original:
            st.sidebar.warning("No data to save or changes made from an empty Gist.")
        elif st.sidebar.checkbox("Confirm save? This will overwrite the Gist.", key="confirm_save_main_cb"):
            with st.spinner("Saving data..."):
                # Create a copy for saving to potentially remove _app_id
                data_to_save_copy = [dict(item) for item in st.session_state.gist_data_original]
                for item in data_to_save_copy:
                    item.pop('_app_id', None) # Remove internal ID before saving to Gist

                if update_gist_data(data_to_save_copy): # Save the copy without _app_id
                    st.sidebar.success("Data saved!")
                    # Reload data to get fresh _app_ids if they were based on createdAt
                    # This also ensures consistency if Gist was modified externally
                    # with st.spinner("Reloading data after save..."):
                    #    data = fetch_gist_data()
                    #    if data is not None:
                    #        st.session_state.gist_data_original = data if isinstance(data, list) else []
                    #        st.session_state.gist_data_filtered = st.session_state.gist_data_original
                else:
                    st.sidebar.error("Failed to save data.")
            st.session_state.search_term = ""
            st.session_state.editing_user_app_id = None
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("Search Users")
    search_term_input = st.sidebar.text_input("Search by username:", value=st.session_state.get("search_term", ""), key="search_input_key")
    if search_term_input != st.session_state.get("search_term", ""):
        st.session_state.search_term = search_term_input
        if st.session_state.search_term:
            st.session_state.gist_data_filtered = [
                user for user in st.session_state.gist_data_original
                if isinstance(user, dict) and user.get("username") and st.session_state.search_term.lower() in user["username"].lower()
            ]
        else:
            st.session_state.gist_data_filtered = st.session_state.gist_data_original
        st.session_state.editing_user_app_id = None # Reset editing if search changes
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.info(f"**Gist ID:** `{GIST_ID}`\n\n**Filename:** `{GIST_FILENAME}`")
    if st.sidebar.button("Logout", key="logout_btn"):
        st.session_state.logged_in = False
        st.session_state.password_attempt = ""
        # Clear sensitive session state on logout
        st.session_state.gist_data_original = []
        st.session_state.gist_data_filtered = []
        st.session_state.editing_user_app_id = None
        st.session_state.search_term = ""
        st.session_state.initial_load_attempted = False
        st.rerun()

    tab_titles = ["📊 View Data", "➕ Add New User", "📝 Edit User"]
    # Attempt to set default tab based on editing state
    active_tab_index = 0 # Default to View Data
    if st.session_state.editing_user_app_id is not None:
        active_tab_index = 2 # Edit User tab

    # Streamlit's st.tabs doesn't have a dynamic default_index after initialization.
    # The common workaround is to structure content such that the desired "tab" is shown.
    # Here, the edit form visibility is controlled by editing_user_app_id.
    
    view_tab, add_tab, edit_tab_container = st.tabs(tab_titles)

    with view_tab:
        st.header("Current User Data")
        if not st.session_state.gist_data_filtered:
            st.info("No data loaded, Gist is empty, or no users match search. Click 'Load Data' in sidebar.")
        else:
            for user_in_filtered in st.session_state.gist_data_filtered:
                if not isinstance(user_in_filtered, dict): continue
                
                app_id = user_in_filtered.get('_app_id')
                if not app_id:
                    st.warning(f"User {user_in_filtered.get('username', 'N/A')} missing _app_id, operations may fail.")
                    continue

                expander_title = f"User: {user_in_filtered.get('username', 'N/A')} (ID: {app_id[:8]}...)"
                with st.expander(expander_title, expanded=(st.session_state.gist_data_filtered.index(user_in_filtered) == 0 and not st.session_state.search_term)):
                    st.json({k: v for k, v in user_in_filtered.items() if k != '_app_id'}) # Don't show internal _app_id

                    col_actions = st.columns([0.8, 0.1, 0.1])
                    with col_actions[1]:
                        if st.button("✏️", key=f"edit_btn_{app_id}", help="Edit User"):
                            st.session_state.editing_user_app_id = app_id
                            st.rerun()
                    with col_actions[2]:
                        if st.button("🗑️", key=f"delete_btn_{app_id}", help="Delete User"):
                            # Confirmation for delete
                            st.session_state.pending_delete_app_id = app_id # Store which item is pending delete
                            st.rerun() # Rerun to show confirmation dialog

            # Confirmation dialog for delete, placed outside the loop but logically part of this tab
            if st.session_state.get("pending_delete_app_id"):
                user_to_delete = next((user for user in st.session_state.gist_data_original if user.get('_app_id') == st.session_state.pending_delete_app_id), None)
                if user_to_delete:
                    if st.checkbox(f"Confirm delete user: {user_to_delete.get('username', 'Unknown')}?", key=f"confirm_delete_cb_{st.session_state.pending_delete_app_id}"):
                        st.session_state.gist_data_original = [
                            user for user in st.session_state.gist_data_original if user.get('_app_id') != st.session_state.pending_delete_app_id
                        ]
                        # Re-filter
                        if st.session_state.search_term:
                            st.session_state.gist_data_filtered = [
                                u for u in st.session_state.gist_data_original if isinstance(u, dict) and u.get("username") and st.session_state.search_term.lower() in u["username"].lower()
                            ]
                        else:
                            st.session_state.gist_data_filtered = st.session_state.gist_data_original
                        
                        st.success(f"User '{user_to_delete.get('username', '')}' removed locally. Save to persist.")
                        st.session_state.pending_delete_app_id = None # Clear pending delete
                        st.rerun()
                    elif st.button("Cancel Delete", key=f"cancel_delete_btn_{st.session_state.pending_delete_app_id}"):
                         st.session_state.pending_delete_app_id = None
                         st.rerun()
                else: # Should not happen if logic is correct
                    st.session_state.pending_delete_app_id = None 


    with add_tab:
        st.header("Add New User")
        with st.form("add_user_form", clear_on_submit=True):
            username = st.text_input("Username", key="add_username_key")
            password = st.text_input("Password", type="password", key="add_password_key")
            money = st.number_input("Money", value=1000.0, step=1.0, format="%.2f", key="add_money_key")
            submitted = st.form_submit_button("Add User")

            if submitted:
                if not username or not password:
                    st.error("Username and Password cannot be empty.")
                else:
                    now_iso = datetime.utcnow().isoformat() + "Z"
                    new_user = {
                        "_app_id": str(now_iso), # Using createdAt as a simple unique ID source
                        "username": username,
                        "password": password,
                        "money": float(money),
                        "createdAt": now_iso,
                        "lastLogin": now_iso
                    }
                    st.session_state.gist_data_original.append(new_user)
                    if st.session_state.search_term and st.session_state.search_term.lower() in new_user["username"].lower():
                        st.session_state.gist_data_filtered.append(new_user) # Also add to filtered if matches
                    elif not st.session_state.search_term:
                        st.session_state.gist_data_filtered = st.session_state.gist_data_original
                    
                    st.success(f"User '{username}' added locally. Remember to save changes to Gist.")
                    st.rerun()

    with edit_tab_container: # Use a container for the edit form to control its visibility
        st.header("Edit User")
        if st.session_state.editing_user_app_id is not None:
            user_to_edit_list = [user for user in st.session_state.gist_data_original if user.get('_app_id') == st.session_state.editing_user_app_id]
            
            if user_to_edit_list:
                user_to_edit_original = user_to_edit_list[0] # Get the actual dict
                user_to_edit_form_copy = user_to_edit_original.copy() # Edit a copy for the form

                with st.form(f"edit_user_form_{st.session_state.editing_user_app_id}"):
                    st.subheader(f"Editing: {user_to_edit_form_copy.get('username', 'N/A')}")
                    edit_username = st.text_input("Username", value=user_to_edit_form_copy.get("username", ""), key=f"edit_uname_{st.session_state.editing_user_app_id}")
                    edit_password_display = st.text_input("Password (visible)", value=user_to_edit_form_copy.get("password", ""), key=f"edit_pwd_{st.session_state.editing_user_app_id}")
                    edit_money = st.number_input("Money",
                                                 value=float(user_to_edit_form_copy.get("money", 0.0)),
                                                 step=1.0, format="%.2f",
                                                 key=f"edit_money_{st.session_state.editing_user_app_id}")

                    col_form_btns = st.columns(2)
                    with col_form_btns[0]:
                        save_edit_button = st.form_submit_button("Save Changes to User", use_container_width=True)
                    with col_form_btns[1]:
                        cancel_edit_button = st.form_submit_button("Cancel Edit", use_container_width=True)

                    if save_edit_button:
                        if not edit_username:
                            st.error("Username cannot be empty.")
                        else:
                            # Find the index in the original list to update
                            original_idx_to_update = -1
                            for i, u in enumerate(st.session_state.gist_data_original):
                                if u.get('_app_id') == st.session_state.editing_user_app_id:
                                    original_idx_to_update = i
                                    break
                            
                            if original_idx_to_update != -1:
                                st.session_state.gist_data_original[original_idx_to_update].update({
                                    "username": edit_username,
                                    "password": edit_password_display,
                                    "money": float(edit_money),
                                    "lastLogin": datetime.utcnow().isoformat() + "Z"
                                })
                                # Re-filter
                                if st.session_state.search_term:
                                    st.session_state.gist_data_filtered = [
                                        u for u in st.session_state.gist_data_original if isinstance(u, dict) and u.get("username") and st.session_state.search_term.lower() in u["username"].lower()
                                    ]
                                else:
                                    st.session_state.gist_data_filtered = st.session_state.gist_data_original
                                
                                st.success(f"User '{edit_username}' updated locally. Save to persist.")
                                st.session_state.editing_user_app_id = None
                                st.rerun()
                            else:
                                st.error("Could not find user to update. Please try again.")


                    if cancel_edit_button:
                        st.session_state.editing_user_app_id = None
                        st.rerun()
            else:
                st.warning("User to edit not found. May have been deleted or data changed.")
                st.session_state.editing_user_app_id = None # Reset
        else:
            st.info("Select a user from the 'View Data' tab by clicking its '✏️' button to edit.")


    st.markdown("---")
    st.subheader("Raw Gist Data (Local Original State)")
    if st.session_state.gist_data_original:
        st.json(st.session_state.gist_data_original)
    else:
        st.caption("No data loaded.")

st.set_page_config(page_title="Gist Data Manager", layout="wide")
st.title("📄 Gist Data Manager")

# Initialize session state
default_session_state = {
    'logged_in': False,
    'gist_data_original': [],
    'gist_data_filtered': [],
    'editing_user_app_id': None, # Changed from editing_user_index
    'search_term': "",
    'password_attempt': "",
    'initial_load_attempted': False,
    'pending_delete_app_id': None # For delete confirmation
}
for key, value in default_session_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

if not st.session_state.logged_in:
    st.subheader("Login Required")
    with st.form("login_form_key"): # Added key to form
        password_input = st.text_input("Enter App Password:", type="password", key="login_password_input_field_key")
        login_button = st.form_submit_button("Login")
        if login_button:
            if check_password(password_input):
                st.session_state.logged_in = True
                st.session_state.password_attempt = ""
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
                st.session_state.password_attempt = password_input
else:
    if not st.session_state.initial_load_attempted:
        with st.spinner("Performing initial data load..."):
            data = fetch_gist_data()
            if data is not None:
                st.session_state.gist_data_original = data if isinstance(data, list) else []
                st.session_state.gist_data_filtered = st.session_state.gist_data_original
            st.session_state.initial_load_attempted = True
            st.rerun()
    main_app()