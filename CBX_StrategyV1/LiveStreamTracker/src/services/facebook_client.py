import requests
import logging
import threading
import time
from src.config import config
from src.constants import EventType

logger = logging.getLogger(__name__)

class FacebookService:
    """
    Service to poll Facebook Graph API for live video comments and reactions.
    """
    def __init__(self, update_callback=None):
        self.page_token = config.facebook_page_token
        self.page_id = config.facebook_page_id
        self.live_video_id = None
        self.is_running = False
        self.update_callback = update_callback
        self._thread = None
        self.poll_interval = config.update_interval

    def start(self, live_video_id=None):
        """
        Starts polling for detailed live stats.
        If live_video_id is not provided, it tries to find the current live video on the page.
        """
        if not self.page_token:
            logger.error("Facebook Page Token not configured.")
            return

        self.live_video_id = live_video_id
        self.is_running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Started Facebook service polling")

    def stop(self):
        self.is_running = False
        logger.info("Stopped Facebook service")

    def _poll_loop(self):
        """Main polling loop."""
        while self.is_running:
            if not self.live_video_id:
                self.live_video_id = self._fetch_current_live_video()
            
            if self.live_video_id:
                self._fetch_comments()
                self._fetch_reactions()
                self._fetch_viewer_count()
            
            time.sleep(self.poll_interval)

    def _fetch_current_live_video(self):
        """Fetches the ID of the current live video on the page."""
        url = f"https://graph.facebook.com/v19.0/{self.page_id}/live_videos"
        params = {
            "status": "LIVE",
            "access_token": self.page_token
        }
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                live_id = data["data"][0]["id"]
                logger.info(f"Found live video ID: {live_id}")
                return live_id
        except Exception as e:
            logger.error(f"Error fetching live video: {e}")
        return None

    def _fetch_comments(self):
        """Fetches latest comments."""
        url = f"https://graph.facebook.com/v19.0/{self.live_video_id}/comments"
        params = {
            "order": "reverse_chronological",
            "limit": 10,
            "access_token": self.page_token
        }
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
            if "data" in data:
                # Process comments
                for comment in data["data"]:
                     if self.update_callback:
                        self.update_callback(EventType.FB_COMMENT, {
                            "user": comment.get("from", {}).get("name", "Unknown"),
                            "comment": comment.get("message", ""),
                            "id": comment.get("id")
                        })
        except Exception as e:
            logger.error(f"Error fetching FB comments: {e}")

    def _fetch_reactions(self):
        """Fetches reactions breakdown."""
        url = f"https://graph.facebook.com/v19.0/{self.live_video_id}/reactions"
        params = {
            "summary": "total_count",
            "access_token": self.page_token
        }
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
            # This endpoint returns individual reactions. 
            # To get summary by type (LIKE, LOVE, ANGRY), we'd need to aggregate manually or use 'type' param in loop.
            # For now, let's just log every new reaction as an event if needed, 
            # or simpler: just get the total count from the previous `_fetch_viewer_count` call 
            # if we only want "Total Reactions". 
            
            # Implementation for individual reaction stream:
            if "data" in data:
                for reaction in data["data"]:
                    # Reaction data usually has 'id', 'name', 'type'
                    if self.update_callback:
                        self.update_callback(EventType.FB_REACTION, {
                            "user": reaction.get("name", "Unknown"),
                            "type": reaction.get("type", "LIKE"),
                            "id": reaction.get("id")
                        })
        except Exception as e:
            logger.error(f"Error fetching FB reactions: {e}")

    def _fetch_viewer_count(self):
        """Fetches current viewer count (if available)."""
        # Note: 'live_views' field on the live video object
        url = f"https://graph.facebook.com/v19.0/{self.live_video_id}"
        params = {
            "fields": "live_views,reaction_count",
            "access_token": self.page_token
        }
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
            
            if "live_views" in data:
                views = data["live_views"]
                if self.update_callback:
                     self.update_callback("fb_viewers", {"count": views})

            # Also fetch total reactions here as a fallback or primary source
            if "reaction_count" in data:
                 # Note: Detailed reaction breakdown requires a different endpoint usually, 
                 # but this gives total count quickly.
                 pass

        except Exception as e:
            logger.error(f"Error fetching FB viewer count: {e}")
