# Setting up profiles & progress tracking (Google Sheets)

The app stores profiles and completed-session history in a Google Sheet, so
it survives app restarts on Streamlit Cloud and works across everyone's
phones. This is a one-time setup (about 10 minutes).

## 1. Create the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) and create a new,
   blank spreadsheet. Name it e.g. "SportYourMind Data".
2. Rename the first tab (bottom-left) to exactly: `profiles`
   - In row 1, add two headers: `name` | `created_at`
3. Add a second tab (the `+` button next to the tab name) named exactly:
   `history`
   - In row 1, add these headers: `profile` | `week_id` | `week_title` | `seance_id` | `seance_title` | `block_ref` | `completed_at`
4. Copy the Sheet's URL from your browser's address bar (you'll need it in
   step 3 below).

## 2. Create a Google Service Account (so the app can read/write the Sheet)

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and
   create a new project (or use an existing one).
2. In the search bar, search for **"Google Sheets API"** and click
   **Enable**. Do the same for **"Google Drive API"**.
3. Go to **APIs & Services > Credentials**.
4. Click **Create Credentials > Service account**. Give it any name (e.g.
   "sportyourmind-app"), click through the remaining steps with defaults.
5. Once created, click on the service account, go to the **Keys** tab,
   click **Add Key > Create new key > JSON**. This downloads a `.json` file
   -- keep it safe, you'll copy values from it next.
6. Open that JSON file. It contains a `client_email` field
   (something like `sportyourmind-app@your-project.iam.gserviceaccount.com`).

## 3. Share the Sheet with the service account

1. Go back to your Google Sheet, click **Share** (top-right).
2. Paste the `client_email` from the JSON file, give it **Editor** access,
   and share (uncheck "notify people" if asked).

## 4. Add the secrets to Streamlit

**On Streamlit Community Cloud:**
1. Go to your app on [share.streamlit.io](https://share.streamlit.io),
   click the "..." menu > **Settings > Secrets**.
2. Paste the following, filling in each value from your downloaded JSON
   file (the field names match exactly) and your Sheet's URL:

```toml
[connections.gsheets]
spreadsheet = "PASTE_YOUR_GOOGLE_SHEET_URL_HERE"
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "..."
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

3. Save. The app restarts automatically with profiles enabled.

**For local testing:** create a file `.streamlit/secrets.toml` in the
project with the same content -- and make sure it's in `.gitignore` so you
never accidentally upload it to GitHub (it contains a private key).

## Done

Once this is set up, the **Profile** page in the app lets anyone create a
name and see their completed-session history and a weekly progress chart.
No password -- it's just a name, so keep the app link private if that
matters to you.

## Already set up? One small update needed

If you configured this before the block-by-block progress tracking was
added, open your Google Sheet's `history` tab and add a new column header
in cell **G1**: `block_ref` (after `seance_title`, before `completed_at` if
you want to keep the order tidy -- the exact position doesn't matter, only
the header name does). That's it, no other change needed.
