# messages/message_types/ping_message.py
from nostr_dvm.backends.mcp.messages.message_types.incrementing_id_message import IncrementingIDMessage

class PingMessage(IncrementingIDMessage):
    def __init__(self, start_id: int = None, **kwargs):
        super().__init__(prefix="ping", method="ping", start_id=start_id, **kwargs)
