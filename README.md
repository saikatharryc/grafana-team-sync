# Grafana Team Sync

This project synchronizes Google Workspace groups with Grafana teams. It ensures that users in Google groups are added to the corresponding Grafana teams and flags users who are in Grafana teams but no longer belong to the corresponding Google groups.

## Features

- Automatically creates Grafana teams for Google Workspace groups.
- Adds users to Grafana teams based on their group membership.
- Flags users in Grafana teams who no longer belong to the corresponding Google groups.

## Prerequisites

1. **Python**: Ensure you have Python 3.7 or higher installed.
2. **Google Workspace Admin SDK**: A service account with the necessary permissions to read group and user data.
3. **Grafana API**: Admin credentials (`GRAFANA_USER` and `GRAFANA_PASSWORD`) for accessing the Grafana API.

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/your-repo/grafana-team-sync.git
   cd grafana-team-sync