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

    THINKING = "thinking"  # Agent is processing
    TOOL_START = "tool_start"  # Tool execution started (with args)
    TOOL_END = "tool_end"  # Tool execution finished (with result)
    TOOL_CALL = "tool_call"  # Legacy: Agent called a tool (deprecated, use TOOL_START)
    TOOL_RESULT = (
        "tool_result"  # Legacy: Tool returned result (deprecated, use TOOL_END)
    )
    ANSWER = "answer"  # Answer token (for typing effect)
    VISUAL = "visual"  # Chart/table spec
    DONE = "done"  # Complete
    ERROR = "error"  # Error occurred


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
        return json.dumps(
            {
                "type": self.type.value,
                "data": self.data,
                "is_final": self.is_final,
            }
        )

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
        self.publish(
            StreamEvent(
                type=EventType.THINKING,
                data={"text": text},
            )
        )

    def tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Publish tool call event."""
        self.publish(
            StreamEvent(
                type=EventType.TOOL_CALL,
                data={"tool": tool_name, "args": args},
            )
        )

    def tool_result(self, tool_name: str, preview: str) -> None:
        """Publish tool result event."""
        self.publish(
            StreamEvent(
                type=EventType.TOOL_RESULT,
                data={"tool": tool_name, "preview": preview},
            )
        )

    def answer_token(self, token: str) -> None:
        """Publish single answer token (for typing effect)."""
        self.publish(
            StreamEvent(
                type=EventType.ANSWER,
                data={"token": token},
            )
        )

    def answer_chunk(self, chunk: str) -> None:
        """Publish answer chunk (multiple tokens)."""
        self.publish(
            StreamEvent(
                type=EventType.ANSWER,
                data={"chunk": chunk},
            )
        )

    def visual(self, spec: Dict[str, Any], partial: bool = False) -> None:
        """Publish visual spec."""
        self.publish(
            StreamEvent(
                type=EventType.VISUAL,
                data={"spec": spec, "partial": partial},
            )
        )

    def done(self, result: Dict[str, Any]) -> None:
        """Publish done event with final result."""
        self.publish(
            StreamEvent(
                type=EventType.DONE,
                data=result,
                is_final=True,
            )
        )

    def error(self, message: str, code: Optional[str] = None) -> None:
        """Publish error event."""
        self.publish(
            StreamEvent(
                type=EventType.ERROR,
                data={"message": message, "code": code},
                is_final=True,
            )
        )


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


# =============================================================================
# ASYNC QUEUE PUBLISHER (for direct SSE without Redis)
# =============================================================================


def _get_tool_description(tool_name: str, args: Dict[str, Any]) -> str:
    """Generate human-readable description of what a tool is doing.

    WHAT: Converts tool name + args into a user-friendly message
    WHY: Users should understand what the agent is doing without seeing raw JSON

    EXAMPLES:
        query_metrics + {metrics: ["spend", "roas"]} -> "Fetching spend and roas from database"
        google_ads_query + {query_type: "campaigns"} -> "Querying Google Ads for campaigns"
    """
    if tool_name == "query_metrics":
        metrics = args.get("metrics", [])
        time_range = args.get("time_range", "7d")
        if metrics:
            metrics_str = ", ".join(metrics[:3])
            if len(metrics) > 3:
                metrics_str += f" (+{len(metrics) - 3} more)"
            return f"Fetching {metrics_str} for {time_range}"
        return "Fetching metrics from database"

    elif tool_name == "google_ads_query":
        query_type = args.get("query_type", "data")
        return f"Querying Google Ads for {query_type}"

    elif tool_name == "meta_ads_query":
        query_type = args.get("query_type", "data")
        return f"Querying Meta Ads for {query_type}"

    elif tool_name == "list_entities":
        level = args.get("level", "campaign")
        return f"Finding {level}s in your account"

    elif tool_name == "get_business_context":
        return "Getting your business profile"

    else:
        return f"Running {tool_name}"


class AsyncQueuePublisher:
    """
    Publisher that pushes events to an asyncio.Queue.

    WHAT: Used for direct SSE streaming without Redis.

    WHY: When running the agent in the same process as the API,
         we don't need Redis Pub/Sub. We can use an async queue instead.

    USAGE:
        queue = asyncio.Queue()
        publisher = AsyncQueuePublisher(queue)

        # In agent:
        publisher.thinking("Analyzing...")
        publisher.tool_call("query_metrics", {"metrics": ["spend"]})
        publisher.token("Your")
        publisher.token(" spend")
        publisher.done(result)

        # In SSE generator:
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
    """

    def __init__(self, queue):
        """
        Initialize publisher.

        PARAMETERS:
            queue: asyncio.Queue to push events to
        """
        import asyncio

        self.queue = queue
        self._loop = None
        logger.info("[STREAM] AsyncQueuePublisher created")

    def _get_loop(self):
        """Get event loop, handling threading."""
        import asyncio

        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    def _put_event(self, event: Dict[str, Any]) -> None:
        """Put event in queue (handles sync/async context)."""
        import asyncio

        loop = self._get_loop()
        if loop and loop.is_running():
            # We're in an async context but this method is sync
            # Use call_soon_threadsafe if in different thread
            try:
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.queue.put(event))
                )
            except RuntimeError:
                # If that fails, try direct put_nowait
                try:
                    self.queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("[STREAM] Queue full, dropping event")
        else:
            # Sync context - use put_nowait
            try:
                self.queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("[STREAM] Queue full, dropping event")

    async def put_event_async(self, event: Dict[str, Any]) -> None:
        """Put event in queue (async version)."""
        await self.queue.put(event)
        logger.debug(f"[STREAM] Queued event: {event.get('type')}")

    def thinking(self, text: str) -> None:
        """Publish thinking event."""
        self._put_event({"type": "thinking", "data": text})

    def tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Publish tool call event (legacy - use tool_start)."""
        self.tool_start(tool_name, args)

    def tool_result(self, tool_name: str, preview: str, success: bool = True) -> None:
        """Publish tool result event (legacy - use tool_end)."""
        self.tool_end(tool_name, preview, success=success)

    def tool_start(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Publish tool start event with arguments.

        WHAT: Emits when a tool begins execution
        WHY: Shows user what the agent is doing in real-time
        """
        self._put_event(
            {
                "type": "tool_start",
                "data": {
                    "tool": tool_name,
                    "args": args,
                    "description": _get_tool_description(tool_name, args),
                },
            }
        )

    def tool_end(
        self,
        tool_name: str,
        preview: str,
        success: bool = True,
        duration_ms: Optional[int] = None,
        data_source: Optional[str] = None,
    ) -> None:
        """Publish tool end event with result preview and timing.

        WHAT: Emits when a tool finishes execution
        WHY: Shows user the result and how long it took

        PARAMETERS:
            tool_name: Name of the tool
            preview: Short preview of the result
            success: Whether the tool succeeded
            duration_ms: How long the tool took in milliseconds
            data_source: Where the data came from (e.g., "snapshots", "live_google_ads")
        """
        self._put_event(
            {
                "type": "tool_end",
                "data": {
                    "tool": tool_name,
                    "preview": preview,
                    "success": success,
                    "duration_ms": duration_ms,
                    "data_source": data_source,
                },
            }
        )

    def token(self, text: str) -> None:
        """Publish single answer token (for typing effect)."""
        self._put_event({"type": "token", "data": text})

    def answer_token(self, token: str) -> None:
        """Alias for token() for compatibility."""
        self.token(token)

    def visual(self, spec: Dict[str, Any]) -> None:
        """Publish visual spec."""
        self._put_event({"type": "visual", "data": spec})

    def done(self, result: Dict[str, Any]) -> None:
        """Publish done event with final result."""
        self._put_event({"type": "done", "data": result, "is_final": True})

    def error(self, message: str) -> None:
        """Publish error event."""
        self._put_event({"type": "error", "data": message, "is_final": True})


def create_async_queue_publisher(queue) -> AsyncQueuePublisher:
    """
    Factory function to create an async queue publisher.

    WHAT: Creates a publisher that pushes events to an asyncio.Queue.

    WHY: For direct SSE streaming without Redis (same-process agent).

    PARAMETERS:
        queue: asyncio.Queue instance

    RETURNS:
        AsyncQueuePublisher ready to use

    EXAMPLE:
        queue = asyncio.Queue()
        publisher = create_async_queue_publisher(queue)

        # Run agent with publisher
        result = await run_agent_async(..., publisher=publisher)

        # Meanwhile, in SSE generator:
        async for event in queue_to_events(queue):
            yield f"data: {json.dumps(event)}\n\n"
    """
    return AsyncQueuePublisher(queue)
