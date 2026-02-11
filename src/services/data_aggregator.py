from queue import Queue, Empty
from threading import Thread
import logging
import time
from src.services.sheet_manager import GoogleSheetClient
from datetime import datetime
from src.services.auto_reply import AutoReplyBot
from src.services.export_manager import ExportManager
from src.constants import Platform, EventType

logger = logging.getLogger(__name__)

BATCH_SIZE = 20
FLUSH_INTERVAL = 10  # Seconds

class DataAggregator:
    """
    Aggregates data from TikTok and Facebook services and processes it.
    Implements batching for Google Sheets to avoid rate limits.
    """
    def __init__(self, sheet_client: GoogleSheetClient):
        self.event_queue = Queue()
        self.sheet_client = sheet_client
        self.is_running = False
        self._thread = None
        self.auto_reply = AutoReplyBot()
        self.export_manager = ExportManager()
        self.session_events = []
        self.stats = {
            "tiktok_comments": 0,
            "tiktok_likes": 0,
            "tiktok_gifts": 0,
            "facebook_comments": 0,
            "facebook_reactions": 0,
        }
        
        # Batching buffers
        self.tiktok_buffer = []
        self.facebook_buffer = []
        self.last_flush_time = time.time()

    def start(self):
        self.is_running = True
        self.sheet_client.connect()
        self._thread = Thread(target=self._process_queue, daemon=True)
        self._thread.start()
        logger.info("Data Aggregator started")

    def stop(self):
        self.is_running = False
        # Final flush
        self._flush_buffers(force=True)
        logger.info("Data Aggregator stopped")

    def add_event(self, platform, event_type, data):
        """Adds an event to the processing queue."""
        self.event_queue.put({
            "platform": platform,
            "type": event_type,
            "data": data,
            "timestamp": datetime.now()
        })

    def _process_queue(self):
        while self.is_running:
            try:
                # Wait for 1 second to allow periodic flushing even if no events
                event = self.event_queue.get(timeout=1)
                self._handle_event(event)
            except Empty:
                pass
            
            self._flush_buffers()

    def _flush_buffers(self, force=False):
        current_time = time.time()
        time_diff = current_time - self.last_flush_time
        
        # Flush TikTok
        if self.tiktok_buffer and (force or len(self.tiktok_buffer) >= BATCH_SIZE or time_diff >= FLUSH_INTERVAL):
            self.sheet_client.log_tiktok_batch(list(self.tiktok_buffer))
            self.tiktok_buffer.clear()
            self.last_flush_time = current_time # Reset timer if flushed

        # Flush Facebook
        if self.facebook_buffer and (force or len(self.facebook_buffer) >= BATCH_SIZE or time_diff >= FLUSH_INTERVAL):
            self.sheet_client.log_facebook_batch(list(self.facebook_buffer))
            self.facebook_buffer.clear()
            self.last_flush_time = current_time

    def _handle_event(self, event):
        platform = event["platform"]
        event_type = event["type"]
        data = event["data"]
        timestamp = event["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

        # Add to session events for export
        self.session_events.append([timestamp, platform, event_type, str(data)])

        # Update comprehensive stats & buffer data
        if platform == Platform.TIKTOK:
            if event_type == EventType.COMMENT:
                self.stats["tiktok_comments"] += 1
                row = [timestamp, "Comment", data["user"], data["comment"]]
                self.tiktok_buffer.append(row)
                
                # Check Auto-Reply
                reply = self.auto_reply.check_and_reply(data["comment"])
                if reply:
                    logger.info(f"Should reply to {data['user']}: {reply}")
                    
            elif event_type == EventType.GIFT:
                self.stats["tiktok_gifts"] += data["count"]
                row = [timestamp, "Gift", data["user"], f"{data['gift']} x{data['count']}"]
                self.tiktok_buffer.append(row)
                
            elif event_type == EventType.LIKE:
                 self.stats["tiktok_likes"] = data["total_likes"]

        elif platform == Platform.FACEBOOK:
             if event_type == EventType.FB_COMMENT:
                self.stats["facebook_comments"] += 1
                row = [timestamp, "Comment", data["user"], data["comment"]]
                self.facebook_buffer.append(row)

    def export_session_data(self, format="csv", destination="local"):
        if destination == "local":
            if format == "csv":
                return self.export_manager.export_to_csv(self.session_events)
            elif format == "excel":
                return self.export_manager.export_to_excel(self.session_events)
        elif destination == "sheet":
            return self.sheet_client.log_report_data(self.session_events)
