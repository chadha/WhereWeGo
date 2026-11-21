"""Amazon SQS event publisher (not wired in the local slice).

Using it requires an approved SQS queue (infra/approval-gates.md). It is kept here so
business logic depends only on the ``EventPublisher`` protocol, never on boto3.
"""

from __future__ import annotations

from typing import Any

from moment_intelligence.domain.contracts import BehavioralEvent


class SqsEventPublisher:
    def __init__(self, sqs_client: Any, queue_url: str) -> None:
        self._client = sqs_client  # boto3.client("sqs"), injected; IAM role auth only
        self._queue_url = queue_url

    def publish(self, event: BehavioralEvent) -> bool:
        if not event.consent_state.analytics:
            return False
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=event.model_dump_json(),
            MessageAttributes={
                "event_type": {"DataType": "String", "StringValue": event.event_type},
                "schema_version": {"DataType": "String", "StringValue": event.schema_version},
            },
        )
        return True
