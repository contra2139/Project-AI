import gspread
import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from src.config import config

logger = logging.getLogger(__name__)

class GoogleSheetClient:
    """
    Client for interacting with Google Sheets using OAuth2 or Service Account.
    """
    def __init__(self):
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds = None
        self.client = None
        self.tiktok_sheet = None
        self.facebook_sheet = None

    def connect(self):
        """Authenticates and connects to Google Sheets."""
        try:
            creds_file = config.google_credentials_file
            token_file = 'token_sheets.json'

            # 1. Try Service Account first (if file looks like one)
            # Simple check: does it contain "type": "service_account"?
            # For now, we assume if it's named 'service_account.json' it is one.
            if "service_account" in creds_file:
                 self.client = gspread.service_account(filename=creds_file)
                 logger.info("Connected using Service Account")
                 return True

            # 2. Key fallback: OAuth flow (User Credentials)
            if os.path.exists(token_file):
                self.creds = Credentials.from_authorized_user_file(token_file, self.scopes)
            
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(creds_file):
                        logger.error(f"Credentials file not found: {creds_file}")
                        return False
                        
                    flow = InstalledAppFlow.from_client_secrets_file(creds_file, self.scopes)
                    # This will open a browser on the user's machine
                    self.creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_file, 'w') as token:
                    token.write(self.creds.to_json())

            self.client = gspread.authorize(self.creds)
            logger.info("Connected using OAuth Credentials")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False

    def _get_sheet(self, sheet_id, tab_name=None):
        """Helper to open a specific tab in a spreadsheet by ID."""
        if not self.client:
            return None
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            if tab_name:
                try:
                    return spreadsheet.worksheet(tab_name)
                except gspread.WorksheetNotFound:
                    logger.warning(f"Tab '{tab_name}' not found, creating it.")
                    return spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)
            else:
                return spreadsheet.sheet1
        except Exception as e:
            logger.error(f"Error opening sheet {sheet_id}: {e}")
            return None

    def log_tiktok_batch(self, rows: list):
        """Logs a batch of rows to the TikTok sheet."""
        if not rows:
            return

        if not self.tiktok_sheet and config.tiktok_sheet_id:
            self.tiktok_sheet = self._get_sheet(config.tiktok_sheet_id, "TikTok")
        
        if self.tiktok_sheet:
            try:
                self.tiktok_sheet.append_rows(rows)
                logger.info(f"Logged batch of {len(rows)} rows to TikTok sheet")
            except Exception as e:
                logger.error(f"Failed to log batch to TikTok sheet: {e}")

    def log_tiktok_data(self, data: list):
        # Kept for backward compatibility or single writes
        self.log_tiktok_batch([data])

    def log_facebook_batch(self, rows: list):
        """Logs a batch of rows to the Facebook sheet."""
        if not rows:
            return

        if not self.facebook_sheet and config.facebook_sheet_id:
            self.facebook_sheet = self._get_sheet(config.facebook_sheet_id, "Facebook")
        
        if self.facebook_sheet:
            try:
                self.facebook_sheet.append_rows(rows)
                logger.info(f"Logged batch of {len(rows)} rows to Facebook sheet")
            except Exception as e:
                logger.error(f"Failed to log batch to Facebook sheet: {e}")

    def log_facebook_data(self, data: list):
        self.log_facebook_batch([data])

    def log_report_data(self, data: list):
        """
        Logs report data to the 'Report' tab.
        Attempts to use TikTok ID first, then Facebook ID (assuming same file).
        """
        sheet_id = config.tiktok_sheet_id or config.facebook_sheet_id
        if not sheet_id:
            logger.error("No Sheet ID configured for Report export.")
            return

        report_sheet = self._get_sheet(sheet_id, "Report")
        
        if report_sheet:
            try:
                # Add header if empty
                if not report_sheet.get_all_values():
                     report_sheet.append_row(["Timestamp", "Platform", "Event Type", "Data"])
                
                # Bulk add rows
                report_sheet.append_rows(data)
                logger.info("Logged report data to Report sheet")
                return True
            except Exception as e:
                logger.error(f"Failed to log to Report sheet: {e}")
                return False
        return False
