import logging

logger = logging.getLogger(__name__)

class AutoReplyBot:
    """
    Simple keyword-based auto-reply logic.
    """
    def __init__(self):
        self.rules = {
            "giá": "Sản phẩm này có giá ưu đãi hôm nay ạ! Inbox shop để biết chi tiết nhé.",
            "ship": "Shop miễn phí vận chuyển cho đơn từ 200k nha!",
            "địa chỉ": "Shop ở Hà Nội, ship toàn quốc 2-3 ngày ạ."
        }

    def check_and_reply(self, message):
        """
        Checks if message contains keywords and returns a reply if matched.
        Returns None if no match.
        """
        message_lower = message.lower()
        for keyword, reply in self.rules.items():
            if keyword in message_lower:
                logger.info(f"Auto-reply triggered for keyword '{keyword}'")
                return reply
        return None
