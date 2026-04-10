from platform_sdk.outbox_runtime import (
    begin_inbox_processing,
    claim_outbox_events,
    mark_inbox_event_failed,
    mark_inbox_event_processed,
    mark_outbox_event_failed,
    mark_outbox_event_published,
    queue_outbox_event,
    register_inbox_event,
)

from models import AdminOpsInboxEvent, IdentityOutboxEvent, db


def test_queue_outbox_event_persists_contract_metadata(app):
    with app.app_context():
        record = queue_outbox_event(
            IdentityOutboxEvent,
            producer_service='identity-service',
            topic='identity.user.registered',
            aggregate_id='user-1',
            payload={'user_id': 1},
            headers={'request_id': 'req-1'},
        )
        db.session.commit()

        assert record.exchange_name == 'ielts-vocab.domain'
        assert record.routing_key == 'identity.user.registered'
        assert record.aggregate_type == 'user'
        assert record.producer_service == 'identity-service'


def test_queue_outbox_event_rejects_wrong_publisher(app):
    with app.app_context():
        try:
            queue_outbox_event(
                IdentityOutboxEvent,
                producer_service='notes-service',
                topic='identity.user.registered',
                payload={'user_id': 1},
            )
        except ValueError as exc:
            assert 'identity-service' in str(exc)
        else:
            raise AssertionError('expected publisher validation error')


def test_claim_and_publish_outbox_events(app):
    with app.app_context():
        queue_outbox_event(
            IdentityOutboxEvent,
            producer_service='identity-service',
            topic='identity.user.registered',
            payload={'user_id': 2},
        )
        db.session.commit()

        records = claim_outbox_events(IdentityOutboxEvent, worker_name='identity-publisher')
        assert len(records) == 1
        assert records[0].claimed_by == 'identity-publisher'
        assert records[0].attempt_count == 1

        mark_outbox_event_published(records[0])
        db.session.commit()

        assert records[0].published_at is not None
        assert records[0].last_error is None


def test_failed_outbox_events_return_to_retry_queue(app):
    with app.app_context():
        queue_outbox_event(
            IdentityOutboxEvent,
            producer_service='identity-service',
            topic='identity.user.registered',
            payload={'user_id': 9},
        )
        db.session.commit()

        records = claim_outbox_events(IdentityOutboxEvent, worker_name='identity-publisher')
        assert len(records) == 1

        mark_outbox_event_failed(records[0], error_message='temporary broker outage')
        db.session.commit()

        retried = claim_outbox_events(IdentityOutboxEvent, worker_name='identity-publisher')
        assert len(retried) == 1
        assert retried[0].attempt_count == 2
        assert retried[0].last_error is None


def test_register_inbox_event_is_idempotent(app):
    with app.app_context():
        first, created = register_inbox_event(
            AdminOpsInboxEvent,
            consumer_service='admin-ops-service',
            event_id='evt-1',
            topic='identity.user.registered',
            producer_service='identity-service',
            payload={'user_id': 3},
        )
        db.session.commit()

        second, created_again = register_inbox_event(
            AdminOpsInboxEvent,
            consumer_service='admin-ops-service',
            event_id='evt-1',
            topic='identity.user.registered',
            producer_service='identity-service',
            payload={'user_id': 3},
        )

        assert created is True
        assert created_again is False
        assert first.id == second.id


def test_register_inbox_event_rejects_wrong_publisher(app):
    with app.app_context():
        try:
            register_inbox_event(
                AdminOpsInboxEvent,
                consumer_service='admin-ops-service',
                event_id='evt-bad-producer',
                topic='identity.user.registered',
                producer_service='notes-service',
                payload={'user_id': 3},
            )
        except ValueError as exc:
            assert 'identity-service' in str(exc)
        else:
            raise AssertionError('expected publisher validation error')


def test_inbox_processing_marks_status_and_errors(app):
    with app.app_context():
        record, created = register_inbox_event(
            AdminOpsInboxEvent,
            consumer_service='admin-ops-service',
            event_id='evt-2',
            topic='learning.session.logged',
            producer_service='learning-core-service',
            payload={'session_id': 1},
        )
        assert created is True

        begin_inbox_processing(record)
        mark_inbox_event_failed(record, error_message='projection timeout')
        assert record.status == 'failed'
        assert record.attempt_count == 1
        assert record.last_error == 'projection timeout'

        begin_inbox_processing(record)
        mark_inbox_event_processed(record)
        db.session.commit()

        assert record.status == 'processed'
        assert record.attempt_count == 2
        assert record.processed_at is not None
