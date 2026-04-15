"""Tests for the inter-agent inbox/messaging system."""

from __future__ import annotations

from swarmflow.engine.inbox import Inbox


class TestInbox:
    def test_send_message(self):
        inbox = Inbox()
        msg = inbox.send("leader", "worker1", "Do task A")
        assert msg.sender == "leader"
        assert msg.recipient == "worker1"
        assert msg.content == "Do task A"
        assert not msg.read
        assert len(inbox.all_messages) == 1

    def test_receive_marks_as_read(self):
        inbox = Inbox()
        inbox.send("leader", "worker1", "Task A")
        inbox.send("leader", "worker1", "Task B")
        inbox.send("leader", "worker2", "Task C")

        msgs = inbox.receive("worker1")
        assert len(msgs) == 2
        assert all(m.read for m in msgs)

        # Second receive should return empty (already read)
        msgs2 = inbox.receive("worker1")
        assert len(msgs2) == 0

    def test_peek_does_not_mark_read(self):
        inbox = Inbox()
        inbox.send("leader", "worker1", "Task A")

        msgs = inbox.peek("worker1")
        assert len(msgs) == 1
        assert not msgs[0].read

        # Peek again should still return the message
        msgs2 = inbox.peek("worker1")
        assert len(msgs2) == 1

    def test_broadcast(self):
        inbox = Inbox()
        # Seed some known agents by sending messages
        inbox.send("leader", "worker1", "init")
        inbox.send("leader", "worker2", "init")
        inbox.send("leader", "worker3", "init")

        # Clear reads
        inbox.receive("worker1")
        inbox.receive("worker2")
        inbox.receive("worker3")

        # Broadcast from leader
        sent = inbox.broadcast("leader", "Meeting at noon")
        assert len(sent) == 3
        assert all(m.sender == "leader" for m in sent)

    def test_get_conversation(self):
        inbox = Inbox()
        inbox.send("leader", "worker1", "Do X")
        inbox.send("worker1", "leader", "X done")
        inbox.send("leader", "worker2", "Do Y")

        convo = inbox.get_conversation("leader", "worker1")
        assert len(convo) == 2
        assert convo[0].content == "Do X"
        assert convo[1].content == "X done"

    def test_get_all_for(self):
        inbox = Inbox()
        inbox.send("leader", "worker1", "Task A")
        inbox.send("worker1", "leader", "Done A")
        inbox.send("leader", "worker2", "Task B")

        msgs = inbox.get_all_for("worker1")
        assert len(msgs) == 2

    def test_clear(self):
        inbox = Inbox()
        inbox.send("leader", "worker1", "Hello")
        inbox.send("worker1", "leader", "Hi")
        assert len(inbox.all_messages) == 2

        inbox.clear()
        assert len(inbox.all_messages) == 0
