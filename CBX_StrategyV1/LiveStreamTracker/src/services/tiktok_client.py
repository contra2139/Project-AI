from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, GiftEvent, LikeEvent, JoinEvent
from src.config import config
from src.constants import EventType
import logging
import threading
import asyncio

logger = logging.getLogger(__name__)

class TikTokService:
    """
    Service to handle TikTok Live connection and events.
    """
    def __init__(self, update_callback=None):
        self.username = config.tiktok_username
        self.client: TikTokLiveClient = None
        self.is_running = False
        self.update_callback = update_callback  # Function to call with new data
        self._thread = None

    def start(self):
        """Starts the TikTok Live client in a separate thread."""
        if not self.username:
            logger.error("TikTok username not configured.")
            return

        self.client = TikTokLiveClient(unique_id=self.username)
        self._register_events()
        
        self.is_running = True
        self._thread = threading.Thread(target=self._run_client, daemon=True)
        self._thread.start()
        logger.info(f"Started TikTok service for {self.username}")

    def stop(self):
        """Stops the client."""
        if self.client and self.client.connected:
            self.client.stop()
        self.is_running = False
        logger.info("Stopped TikTok service")

    def _run_client(self):
        """Internal method to run the client blocking call."""
        try:
            # TikTokLive run method is blocking
            self.client.run()
        except Exception as e:
            logger.error(f"TikTok client error: {e}")
            self.is_running = False

    def _register_events(self):
        """Registers event handlers."""
        
        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            logger.info(f"Connected to Room ID: {event.room_id}")
            if self.update_callback:
                self.update_callback("status", {"status": "Connected"})

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            logger.info(f"{event.user.nickname}: {event.comment}")
            if self.update_callback:
                self.update_callback(EventType.COMMENT, {
                    "user": event.user.nickname,
                    "comment": event.comment,
                    "avatar": event.user.avatar.urls[0] if event.user.avatar else ""
                })

        @self.client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            logger.info(f"{event.user.nickname} sent a {event.gift.info.name}!")
            if self.update_callback:
                self.update_callback(EventType.GIFT, {
                    "user": event.user.nickname,
                    "gift": event.gift.info.name,
                    "count": event.gift.count
                })

        @self.client.on(LikeEvent)
        async def on_like(event: LikeEvent):
            if self.update_callback:
                self.update_callback(EventType.LIKE, {
                    "user": event.user.nickname,
                    "count": event.count,
                    "total_likes": event.total_likes
                })

        @self.client.on(JoinEvent)
        async def on_join(event: JoinEvent):
             if self.update_callback:
                self.update_callback(EventType.JOIN, {
                    "user": event.user.nickname
                })
