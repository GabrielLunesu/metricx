"""
Redis Pub/Sub Streaming
=======================

**Version**: 1.0.0
**Created**: 2025-12-03

Real-time streaming of agent responses via Redis Pub/Sub.
Enables token-by-token typing effect in the frontend.

WHY THIS FILE EXISTS
--------------------
The agent generates responses token by token. Instead of waiting for the
full response, we stream each token to the frontend via Redis Pub/Sub.

STREAMING FLOW
--------------
```
Worker (agent)           Redis Pub/Sub         API (SSE)            Frontend
     |                        |                    |                    |
     |-- publish token ------>|                    |                    |
     |                        |-- notify --------->|                    |
     |                        |                    |-- SSE event ------>|
     |                        |                    |                    |
     |-- publish token ------>|                    |                    |
     |                        |-- notify --------->|                    |
     |                        |                    |-- SSE event ------>|
```

EVENT TYPES
-----------
- thinking: Agent is processing ("Analyzing your question...")
- tool_call: Agent is calling a tool (show spinner)
- tool_result: Tool returned data (can show preview)
- answer: Answer token (typing effect)
- visual: Chart/table spec (render progressively)
- done: Complete, final result
- error: Something went wrong

RELATED FILES
-------------
- app/agent/graph.py: Publishes events
- app/routers/qa.py: Subscribes and sends SSE
- app/workers/agent_worker.py: Creates publisher
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional, Any, Dict
from enum import Enum

import redis

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of streaming events."""
    THINKING = "thinking"       # Agent is processing
    TOOL_CALL = "tool_call"     # Agent called a tool
    TOOL_RESULT = "tool_result" # Tool returned result
    ANSWER = "answer"           # Answer token (for typing effect)
    VISUAL = "visual"           # Chart/table spec
    DONE = "done"               # Complete
    ERROR = "error"             # Error occurred


@dataclass
class StreamEvent:
    """
    Single streaming event.

    WHAT: Represents one event in the stream.

    WHY: Structured format for all streaming messages.

    FIELDS:
        type: Event type (thinking, answer, etc.)
        data: Event payload (depends on type)
        is_final: True if this is the last event
    """
    type: EventType
    data: Any
    is_final: bool = False

    def to_json(self) -> str:
        """Serialize to JSON for Redis."""
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "is_final": self.is_final,
        })

    @classmethod
    def from_json(cls, json_str: str) -> "StreamEvent":
        """Deserialize from JSON."""
        payload = json.loads(json_str)
        return cls(
            type=EventType(payload["type"]),
            data=payload["data"],
            is_final=payload.get("is_final", False),
        )


class StreamPublisher:
    """
    Publishes streaming events to Redis.

    WHAT: Used by agent to publish events.

    WHY: Decouples agent from HTTP layer. Agent publishes,
    API subscribes and forwards to client.

    USAGE:
        publisher = StreamPublisher(redis_client, job_id)
        publisher.thinking("Analyzing your question...")
        publisher.answer_token("Your")
        publisher.answer_token(" ROAS")
        publisher.done(final_result)
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        job_id: str,
        channel_prefix: str = "qa",
    ):
        """
        Initialize publisher.

        PARAMETERS:
            redis_client: Redis connection
            job_id: Unique job ID (used in channel name)
            channel_prefix: Prefix for channel name
        """
        self.redis = redis_client
        self.job_id = job_id
        self.channel = f"{channel_prefix}:{job_id}:stream"
        logger.info(f"[STREAM] Publisher created for channel: {self.channel}")

    def publish(self, event: StreamEvent) -> None:
        """
        Publish an event.

        PARAMETERS:
            event: StreamEvent to publish
        """
        try:
            self.redis.publish(self.channel, event.to_json())
            logger.debug(f"[STREAM] Published: {event.type.value}")
        except Exception as e:
            logger.error(f"[STREAM] Failed to publish: {e}")

    def thinking(self, text: str) -> None:
        """Publish thinking event."""
        self.publish(StreamEvent(
            type=EventType.THINKING,
            data={"text": text},
        ))

    def tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Publish tool call event."""
        self.publish(StreamEvent(
            type=EventType.TOOL_CALL,
            data={"tool": tool_name, "args": args},
        ))

    def tool_result(self, tool_name: str, preview: str) -> None:
        """Publish tool result event."""
        self.publish(StreamEvent(
            type=EventType.TOOL_RESULT,
            data={"tool": tool_name, "preview": preview},
        ))

    def answer_token(self, token: str) -> None:
        """Publish single answer token (for typing effect)."""
        self.publish(StreamEvent(
            type=EventType.ANSWER,
            data={"token": token},
        ))

    def answer_chunk(self, chunk: str) -> None:
        """Publish answer chunk (multiple tokens)."""
        self.publish(StreamEvent(
            type=EventType.ANSWER,
            data={"chunk": chunk},
        ))

    def visual(self, spec: Dict[str, Any], partial: bool = False) -> None:
        """Publish visual spec."""
        self.publish(StreamEvent(
            type=EventType.VISUAL,
            data={"spec": spec, "partial": partial},
        ))

    def done(self, result: Dict[str, Any]) -> None:
        """Publish done event with final result."""
        self.publish(StreamEvent(
            type=EventType.DONE,
            data=result,
            is_final=True,
        ))

    def error(self, message: str, code: Optional[str] = None) -> None:
        """Publish error event."""
        self.publish(StreamEvent(
            type=EventType.ERROR,
            data={"message": message, "code": code},
            is_final=True,
        ))


class StreamSubscriber:
    """
    Subscribes to streaming events from Redis.

    WHAT: Used by API to receive events.

    WHY: Allows SSE endpoint to forward events to client.

    USAGE:
        subscriber = StreamSubscriber(redis_client, job_id)
        for event in subscriber.listen():
            yield f"data: {event.to_json()}\n\n"
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        job_id: str,
        channel_prefix: str = "qa",
        timeout: float = 60.0,
    ):
        """
        Initialize subscriber.

        PARAMETERS:
            redis_client: Redis connection
            job_id: Unique job ID
            channel_prefix: Prefix for channel name
            timeout: Timeout for listening (seconds)
        """
        self.redis = redis_client
        self.job_id = job_id
        self.channel = f"{channel_prefix}:{job_id}:stream"
        self.timeout = timeout
        self.pubsub = None
        logger.info(f"[STREAM] Subscriber created for channel: {self.channel}")

    def listen(self):
        """
        Listen for events.

        YIELDS:
            StreamEvent objects as they arrive

        NOTE:
            This is a generator that blocks until events arrive.
            Use in an async context or separate thread.
        """
        try:
            self.pubsub = self.redis.pubsub()
            self.pubsub.subscribe(self.channel)
            logger.info(f"[STREAM] Subscribed to: {self.channel}")

            # Skip the subscription confirmation message
            self.pubsub.get_message(timeout=1.0)

            while True:
                message = self.pubsub.get_message(timeout=self.timeout)

                if message is None:
                    # Timeout - send keepalive or check if job still running
                    continue

                if message["type"] != "message":
                    continue

                try:
                    event = StreamEvent.from_json(message["data"])
                    yield event

                    if event.is_final:
                        logger.info(f"[STREAM] Received final event, closing")
                        break

                except json.JSONDecodeError as e:
                    logger.error(f"[STREAM] Failed to parse event: {e}")
                    continue

        finally:
            if self.pubsub:
                self.pubsub.unsubscribe(self.channel)
                self.pubsub.close()
                logger.info(f"[STREAM] Unsubscribed from: {self.channel}")

    def close(self) -> None:
        """Close the subscription."""
        if self.pubsub:
            self.pubsub.unsubscribe(self.channel)
            self.pubsub.close()


def create_publisher(job_id: str, redis_url: Optional[str] = None) -> StreamPublisher:
    """
    Factory function to create a publisher.

    PARAMETERS:
        job_id: Job ID for channel name
        redis_url: Redis URL (defaults to localhost)

    RETURNS:
        StreamPublisher ready to use
    """
    import os
    url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
    client = redis.from_url(url)
    return StreamPublisher(client, job_id)


def create_subscriber(job_id: str, redis_url: Optional[str] = None) -> StreamSubscriber:
    """
    Factory function to create a subscriber.

    PARAMETERS:
        job_id: Job ID for channel name
        redis_url: Redis URL (defaults to localhost)

    RETURNS:
        StreamSubscriber ready to use
    """
    import os
    url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
    client = redis.from_url(url)
    return StreamSubscriber(client, job_id)
