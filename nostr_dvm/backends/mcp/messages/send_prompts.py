# messages/prompts.py
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from send_message import send_message
from message_types.prompts_messages import PromptsListMessage

async def send_prompts_list(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
) -> list:
    """Send a 'prompts/list' message and return the list of prompts."""
    message = PromptsListMessage()

    # send the message
    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        message=message,
    )

    # return the result
    return response.get("result", [])
