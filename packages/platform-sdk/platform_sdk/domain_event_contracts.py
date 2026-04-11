from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainEventContract:
    topic: str
    publisher_service: str
    consumer_services: tuple[str, ...]
    aggregate_type: str
    description: str
    version: int = 1

    @property
    def routing_key(self) -> str:
        return self.topic


DOMAIN_EVENT_CONTRACTS: tuple[DomainEventContract, ...] = (
    DomainEventContract(
        topic='identity.user.registered',
        publisher_service='identity-service',
        consumer_services=('admin-ops-service',),
        aggregate_type='user',
        description='Published after a new user account is committed and available for downstream read models.',
    ),
    DomainEventContract(
        topic='learning.session.logged',
        publisher_service='learning-core-service',
        consumer_services=('admin-ops-service', 'notes-service'),
        aggregate_type='study-session',
        description='Published after a study session write so downstream dashboards and note flows can project learner activity.',
    ),
    DomainEventContract(
        topic='learning.wrong_word.updated',
        publisher_service='learning-core-service',
        consumer_services=('admin-ops-service', 'ai-execution-service', 'notes-service'),
        aggregate_type='wrong-word',
        description='Published after wrong-word state changes to keep projections and AI remediation flows current.',
    ),
    DomainEventContract(
        topic='notes.summary.generated',
        publisher_service='notes-service',
        consumer_services=('admin-ops-service', 'ai-execution-service'),
        aggregate_type='daily-summary',
        description='Published after a summary record is generated so other services can react without reading notes tables directly.',
    ),
    DomainEventContract(
        topic='tts.media.generated',
        publisher_service='tts-media-service',
        consumer_services=('admin-ops-service',),
        aggregate_type='tts-media',
        description='Published after TTS media generation or cache materialization completes.',
    ),
    DomainEventContract(
        topic='ai.prompt_run.completed',
        publisher_service='ai-execution-service',
        consumer_services=('admin-ops-service', 'notes-service'),
        aggregate_type='prompt-run',
        description='Published after a prompt run finishes so downstream audit and summary systems can project usage safely.',
    ),
)

DOMAIN_EVENT_CONTRACTS_BY_TOPIC = {
    contract.topic: contract
    for contract in DOMAIN_EVENT_CONTRACTS
}



def get_domain_event_contract(topic: str) -> DomainEventContract:
    try:
        return DOMAIN_EVENT_CONTRACTS_BY_TOPIC[topic]
    except KeyError as exc:
        raise KeyError(f'Unknown domain event contract: {topic}') from exc



def iter_domain_event_topics() -> tuple[str, ...]:
    return tuple(contract.topic for contract in DOMAIN_EVENT_CONTRACTS)



def validate_domain_event_contracts() -> list[str]:
    errors: list[str] = []
    topics = [contract.topic for contract in DOMAIN_EVENT_CONTRACTS]
    duplicate_topics = {topic for topic in topics if topics.count(topic) > 1}
    if duplicate_topics:
        errors.append(f'duplicate topics: {sorted(duplicate_topics)}')

    for contract in DOMAIN_EVENT_CONTRACTS:
        if not contract.publisher_service.endswith('-service'):
            errors.append(f'{contract.topic} publisher must be a service name')
        if not contract.consumer_services:
            errors.append(f'{contract.topic} must declare at least one consumer')

    return errors
