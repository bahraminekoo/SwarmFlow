"""Inter-agent message bus for SwarmFlow."""

from __future__ import annotations

from swarmflow.models import Message


class Inbox:
    """In-memory inter-agent messaging system.

    Supports point-to-point messages and broadcast. Each agent has a
    named inbox. Messages are stored centrally and filtered by recipient.
    """

    def __init__(self):
        self._messages: list[Message] = []

    @property
    def all_messages(self) -> list[Message]:
        return list(self._messages)

    def send(self, sender: str, recipient: str, content: str) -> Message:
        """Send a message from one agent to another."""
        msg = Message(sender=sender, recipient=recipient, content=content)
        self._messages.append(msg)
        return msg

    def broadcast(
        self,
        sender: str,
        content: str,
        exclude: list[str] | None = None,
    ) -> list[Message]:
        """Broadcast a message to all agents (except sender and excluded)."""
        exclude = set(exclude or [])
        exclude.add(sender)
        recipients = self._get_known_recipients() - exclude
        sent = []
        for recipient in recipients:
            msg = self.send(sender, recipient, content)
            sent.append(msg)
        return sent

    def receive(self, recipient: str, mark_read: bool = True) -> list[Message]:
        """Get all unread messages for a recipient."""
        msgs = [
            m for m in self._messages
            if m.recipient == recipient and not m.read
        ]
        if mark_read:
            for m in msgs:
                m.read = True
        return msgs

    def peek(self, recipient: str) -> list[Message]:
        """Read messages without marking them as read."""
        return self.receive(recipient, mark_read=False)

    def get_conversation(self, agent1: str, agent2: str) -> list[Message]:
        """Get all messages between two agents, ordered by timestamp."""
        msgs = [
            m for m in self._messages
            if (m.sender == agent1 and m.recipient == agent2)
            or (m.sender == agent2 and m.recipient == agent1)
        ]
        return sorted(msgs, key=lambda m: m.timestamp)

    def get_all_for(self, agent_name: str) -> list[Message]:
        """Get all messages sent to or from an agent."""
        return [
            m for m in self._messages
            if m.sender == agent_name or m.recipient == agent_name
        ]

    def _get_known_recipients(self) -> set[str]:
        """Get all known agent names from message history."""
        names: set[str] = set()
        for m in self._messages:
            names.add(m.sender)
            names.add(m.recipient)
        return names

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
