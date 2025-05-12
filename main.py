import os
import base64
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === CONFIG ===
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_USER= os.getenv("GRAFANA_USER")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD")
GRAFANA_API_TOKEN = f"Basic {base64.b64encode(f'{GRAFANA_USER}:{GRAFANA_PASSWORD}').decode('utf-8')}"  # Admin token
GRAFANA_HEADERS = {
    "Authorization": GRAFANA_API_TOKEN,
    "Content-Type": "application/json"
}

SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")  # Google Workspace service account
ADMIN_EMAIL = os.getenv("DELGATED_ADMIN_EMAIL")  # Delegated admin
SCOPES = ["https://www.googleapis.com/auth/admin.directory.group.readonly"]
CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN")  # Your org domain

# === SETUP GOOGLE ADMIN SDK ===
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
delegated_creds = creds.with_subject(ADMIN_EMAIL)
service = build("admin", "directory_v1", credentials=delegated_creds)

# === UTILS ===

def get_user_groups(email):
    """Fetch Google groups for a user."""
    try:
        results = service.groups().list(userKey=email).execute()
        return [group["email"].split("@")[0] for group in results.get("groups", [])]
    except Exception as e:
        print(f"Failed to fetch groups for {email}: {e}")
        return []

def get_grafana_users():
    """Fetch all users from Grafana."""
    r = requests.get(f"{GRAFANA_URL}/api/users", headers=GRAFANA_HEADERS)
    return r.json() if r.ok else []

def get_grafana_teams():
    """Fetch all teams from Grafana."""
    r = requests.get(f"{GRAFANA_URL}/api/teams/search", headers=GRAFANA_HEADERS)
    return {team["email"]: team["id"] for team in r.json().get("teams", [])}

def create_grafana_team(name, email):
    """Create a new team in Grafana."""
    r = requests.post(f"{GRAFANA_URL}/api/teams", json={"email": email, "name": name}, headers=GRAFANA_HEADERS)
    if r.ok:
        return r.json()["teamId"]
    print(f"Failed to create team {name}: {r.text}")
    return None

def add_user_to_team(user_id, team_id, team_members_cache):
    """Add a user to a Grafana team if not already a member."""
    if team_id not in team_members_cache:
        team_members_cache[team_id] = get_team_members(team_id)

    if any(member["userId"] == user_id for member in team_members_cache[team_id]):
        print(f"User {user_id} is already a member of team {team_id}. Skipping.")
        return

    r = requests.post(
        f"{GRAFANA_URL}/api/teams/{team_id}/members",
        json={"userId": user_id},
        headers=GRAFANA_HEADERS
    )
    if not r.ok:
        print(f"Failed to add user {user_id} to team {team_id}: {r.text}")

def get_team_members(team_id):
    """Fetch members of a Grafana team."""
    r = requests.get(f"{GRAFANA_URL}/api/teams/{team_id}/members", headers=GRAFANA_HEADERS)
    return r.json() if r.ok else []

def reflect_users_not_in_groups():
    """Flag users who are in Grafana teams but no longer belong to the corresponding Google groups."""
    user_groups_cache = {}
    for team_email, team_id in existing_teams.items():
        team_members = get_team_members(team_id)
        group_name = team_email.split("@")[0]  # Extract group name from team email

        for member in team_members:
            user_email = member.get("email")
            if not user_email or not user_email.endswith(CUSTOM_DOMAIN):
                continue

            # Cache user groups to avoid redundant API calls
            if user_email not in user_groups_cache:
                user_groups_cache[user_email] = get_user_groups(user_email)

            user_groups = user_groups_cache[user_email]
            if group_name not in user_groups:
                print(f"User {user_email} is in Grafana team {team_email} but no longer belongs to the corresponding Google group.")

# === MAIN SCRIPT ===

grafana_users = get_grafana_users()
existing_teams = get_grafana_teams()

def main():
    group_count = 0
    user_count = 0
    team_members_cache = {}

    # Step 1: Pre-create all groups in Grafana
    all_groups = set()
    for user in grafana_users:
        email = user.get("email")
        if not email or not email.endswith(CUSTOM_DOMAIN):
            continue

        user_groups = get_user_groups(email)
        all_groups.update(user_groups)

    for group in all_groups:
        group_modifier = f"{group}@{CUSTOM_DOMAIN}"
        if group_modifier not in existing_teams:
            print(f"Creating missing Grafana team for group: {group_modifier}")
            team_id = create_grafana_team(group, group_modifier)
            if team_id:
                existing_teams[group_modifier] = team_id

    # Step 2: Process users and assign them to teams
    for user in grafana_users:
        email = user.get("email")
        if not email or not email.endswith(CUSTOM_DOMAIN):
            continue

        user_count += 1
        groups = get_user_groups(email)
        user_id = user["id"]

        for group in groups:
            group_modifier = f"{group}@{CUSTOM_DOMAIN}"
            print(f"Processing user {email} for group {group_modifier}")
            team_id = existing_teams.get(group_modifier)
            if team_id:
                add_user_to_team(user_id, team_id, team_members_cache)

    group_count += len(groups)
    reflect_users_not_in_groups()
    print(f"Sync complete. Processed {user_count} users and {group_count} groups.")

if __name__ == "__main__":
    main()