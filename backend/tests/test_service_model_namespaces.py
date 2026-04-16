from service_models import (
    admin_ops_models,
    ai_execution_models,
    ai_route_models,
    catalog_content_models,
    eventing_models,
    identity_models,
    learner_profile_models,
    learning_core_models,
    notes_models,
)



def test_learning_core_models_expose_learning_owned_models():
    assert hasattr(learning_core_models, 'UserFavoriteWord')
    assert hasattr(learning_core_models, 'UserFamiliarWord')
    assert hasattr(learning_core_models, 'UserStudySession')
    assert hasattr(learning_core_models, 'UserWordMasteryState')
    assert not hasattr(learning_core_models, 'UserWordNote')



def test_notes_models_expose_notes_owned_models():
    assert hasattr(notes_models, 'NotesProjectionCursor')
    assert hasattr(notes_models, 'NotesProjectedPromptRun')
    assert hasattr(notes_models, 'NotesProjectedStudySession')
    assert hasattr(notes_models, 'NotesProjectedWrongWord')
    assert hasattr(notes_models, 'UserWordNote')
    assert hasattr(notes_models, 'UserLearningNote')
    assert hasattr(notes_models, 'UserDailySummary')
    assert not hasattr(notes_models, 'UserFavoriteWord')



def test_identity_models_expose_identity_owned_models():
    assert hasattr(identity_models, 'User')
    assert hasattr(identity_models, 'EmailVerificationCode')
    assert hasattr(identity_models, 'RateLimitBucket')
    assert not hasattr(identity_models, 'UserStudySession')



def test_ai_execution_models_expose_ai_owned_models():
    assert hasattr(ai_execution_models, 'AISpeakingAssessment')
    assert hasattr(ai_execution_models, 'AIProjectionCursor')
    assert hasattr(ai_execution_models, 'AIProjectedDailySummary')
    assert hasattr(ai_execution_models, 'AIProjectedWrongWord')
    assert hasattr(ai_execution_models, 'AIPromptRun')
    assert hasattr(ai_execution_models, 'AIWordImageAsset')
    assert hasattr(ai_execution_models, 'UserHomeTodoPlan')
    assert hasattr(ai_execution_models, 'UserHomeTodoItem')
    assert hasattr(ai_execution_models, 'UserConversationHistory')
    assert hasattr(ai_execution_models, 'UserMemory')
    assert hasattr(ai_execution_models, 'SearchCache')
    assert not hasattr(ai_execution_models, 'UserLearningNote')



def test_catalog_and_admin_model_namespaces_stay_explicit():
    assert hasattr(catalog_content_models, 'WordCatalogEntry')
    assert hasattr(catalog_content_models, 'CustomBook')
    assert hasattr(admin_ops_models, 'UserStudySession')
    assert hasattr(admin_ops_models, 'UserWrongWord')



def test_eventing_models_expose_outbox_and_inbox_state():
    assert hasattr(eventing_models, 'IdentityOutboxEvent')
    assert hasattr(eventing_models, 'LearningCoreInboxEvent')
    assert hasattr(eventing_models, 'AdminProjectionCursor')
    assert hasattr(eventing_models, 'AdminProjectedDailySummary')
    assert hasattr(eventing_models, 'AdminProjectedPromptRun')
    assert hasattr(eventing_models, 'AdminProjectedTTSMedia')
    assert hasattr(eventing_models, 'AdminProjectedWrongWord')
    assert hasattr(eventing_models, 'AdminProjectedStudySession')
    assert hasattr(eventing_models, 'AdminProjectedUser')
    assert hasattr(eventing_models, 'TTSMediaAsset')



def test_learner_profile_model_namespace_declares_cross_domain_reads_explicitly():
    assert hasattr(learner_profile_models, 'UserLearningNote')
    assert hasattr(learner_profile_models, 'CustomBook')
    assert hasattr(learner_profile_models, 'UserStudySession')



def test_ai_route_model_namespace_declares_cross_domain_reads_explicitly():
    assert hasattr(ai_route_models, 'UserWrongWord')
    assert hasattr(ai_route_models, 'UserWordMasteryState')
    assert hasattr(ai_route_models, 'UserLearningNote')
    assert hasattr(ai_route_models, 'WRONG_WORD_DIMENSIONS')
