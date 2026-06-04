"""EventBus + Events のテスト"""

from __future__ import annotations

import pytest

from services.sdk.event_bus import EventBus
from services.sdk.events import (
    Event,
    GraphExported,
    GraphParsed,
    PluginLoaded,
)


class TestEvent:
    """Event dataclass のテスト"""

    def test_base_event(self) -> None:
        e = Event(source="core")
        assert e.source == "core"

    def test_graph_parsed(self) -> None:
        e = GraphParsed(source="core", node_count=10, relation_count=5, full_mode=True)
        assert e.node_count == 10
        assert e.relation_count == 5
        assert e.full_mode is True

    def test_graph_parsed_defaults(self) -> None:
        e = GraphParsed(source="core")
        assert e.node_count == 0
        assert e.relation_count == 0
        assert e.full_mode is False

    def test_graph_exported(self) -> None:
        e = GraphExported(source="core", format="yaml", output_path="/tmp/out.yaml")
        assert e.format == "yaml"
        assert e.output_path == "/tmp/out.yaml"

    def test_plugin_loaded(self) -> None:
        e = PluginLoaded(
            source="core",
            plugin_name="abaqus",
            capabilities=["parsers", "exporters"],
        )
        assert e.plugin_name == "abaqus"
        assert len(e.capabilities) == 2

    def test_events_are_frozen(self) -> None:
        e = Event(source="core")
        with pytest.raises(AttributeError):
            e.source = "changed"  # type: ignore[misc]


class TestEventBus:
    """EventBus のテスト"""

    def test_subscribe_and_publish(self) -> None:
        bus = EventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(GraphParsed, handler)
        event = GraphParsed(source="core", node_count=5, relation_count=3)
        bus.publish(event)

        assert len(received) == 1
        assert received[0] is event

    def test_multiple_handlers(self) -> None:
        bus = EventBus()
        results: list[str] = []

        bus.subscribe(GraphParsed, lambda e: results.append("a"))
        bus.subscribe(GraphParsed, lambda e: results.append("b"))

        bus.publish(GraphParsed(source="core"))
        assert results == ["a", "b"]

    def test_different_event_types(self) -> None:
        bus = EventBus()
        parsed_count = []
        exported_count = []

        bus.subscribe(GraphParsed, lambda e: parsed_count.append(1))
        bus.subscribe(GraphExported, lambda e: exported_count.append(1))

        bus.publish(GraphParsed(source="core"))
        bus.publish(GraphParsed(source="core"))
        bus.publish(GraphExported(source="core", format="yaml"))

        assert len(parsed_count) == 2
        assert len(exported_count) == 1

    def test_no_handlers_no_error(self) -> None:
        bus = EventBus()
        # ハンドラなしで publish しても例外が起きない
        bus.publish(GraphParsed(source="core"))

    def test_handler_exception_continues(self) -> None:
        bus = EventBus()
        results: list[str] = []

        def bad_handler(event: Event) -> None:
            raise ValueError("boom")

        def good_handler(event: Event) -> None:
            results.append("ok")

        bus.subscribe(GraphParsed, bad_handler)
        bus.subscribe(GraphParsed, good_handler)

        bus.publish(GraphParsed(source="core"))
        assert results == ["ok"]

    def test_unsubscribe(self) -> None:
        bus = EventBus()
        results: list[str] = []

        def handler(event: Event) -> None:
            results.append("called")

        bus.subscribe(GraphParsed, handler)
        assert bus.unsubscribe(GraphParsed, handler) is True

        bus.publish(GraphParsed(source="core"))
        assert results == []

    def test_unsubscribe_nonexistent(self) -> None:
        bus = EventBus()

        def handler(event: Event) -> None:
            pass

        assert bus.unsubscribe(GraphParsed, handler) is False

    def test_clear(self) -> None:
        bus = EventBus()
        bus.subscribe(GraphParsed, lambda e: None)
        bus.subscribe(GraphExported, lambda e: None)

        assert bus.handler_count == 2
        bus.clear()
        assert bus.handler_count == 0

    def test_handler_count(self) -> None:
        bus = EventBus()
        assert bus.handler_count == 0

        bus.subscribe(GraphParsed, lambda e: None)
        assert bus.handler_count == 1

        bus.subscribe(GraphExported, lambda e: None)
        assert bus.handler_count == 2

    def test_publish_subclass_not_base(self) -> None:
        """GraphParsed を publish しても Event ハンドラは呼ばれない"""
        bus = EventBus()
        base_results: list[str] = []
        parsed_results: list[str] = []

        bus.subscribe(Event, lambda e: base_results.append("base"))
        bus.subscribe(GraphParsed, lambda e: parsed_results.append("parsed"))

        bus.publish(GraphParsed(source="core"))
        assert base_results == []
        assert parsed_results == ["parsed"]
