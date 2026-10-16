import json
import time

from vortex_api.backends.mock import MockBackend
from vortex_api.registry import ModelSpec
from vortex_api.services.chat import GenerationRegistry, stream_completion

SPEC = ModelSpec(
    id="vortex-test", kind="chat", backend="mock", upstream_model="up", display_name="Test"
)


async def test_cancel_stops_stream_and_ends_cleanly():
    backend = MockBackend(delay=0.001)
    payload = {"model": "up", "messages": [{"role": "user", "content": "um dois tres " * 50}]}
    stream = backend.stream_chat(payload)
    generations = GenerationRegistry()
    cancel = generations.start("cid")
    records = []

    async def on_done(rec):
        records.append(rec)

    events = []
    async for event in stream_completion(
        first=None,
        stream=stream,
        spec=SPEC,
        completion_id="cid",
        cancel=cancel,
        include_usage=False,
        started=time.perf_counter(),
        on_done=on_done,
    ):
        events.append(event)
        if len(events) == 3:
            assert generations.cancel("cid")

    assert events[-1] == "data: [DONE]\n\n"
    final = json.loads(events[-2][6:])
    assert final["choices"][0]["finish_reason"] == "stop"
    assert len(events) < 20, "generation should stop shortly after cancel"
    assert records[0].status == "cancelled"
    assert records[0].ttft_ms is not None
