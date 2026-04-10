from platform_sdk.domain_event_contracts import (
    DOMAIN_EVENT_CONTRACTS,
    get_domain_event_contract,
    iter_domain_event_topics,
    validate_domain_event_contracts,
)



def test_domain_event_contracts_validate_cleanly():
    assert validate_domain_event_contracts() == []



def test_domain_event_contract_topics_match_wave5_contract_set():
    assert set(iter_domain_event_topics()) == {
        'identity.user.registered',
        'learning.session.logged',
        'learning.wrong_word.updated',
        'notes.summary.generated',
        'tts.media.generated',
        'ai.prompt_run.completed',
    }



def test_learning_wrong_word_contract_keeps_learning_core_as_publisher():
    contract = get_domain_event_contract('learning.wrong_word.updated')

    assert contract.publisher_service == 'learning-core-service'
    assert 'ai-execution-service' in contract.consumer_services
    assert contract.routing_key == 'learning.wrong_word.updated'



def test_every_contract_declares_a_consumer_and_unique_topic():
    topics = [contract.topic for contract in DOMAIN_EVENT_CONTRACTS]

    assert len(topics) == len(set(topics))
    assert all(contract.consumer_services for contract in DOMAIN_EVENT_CONTRACTS)
