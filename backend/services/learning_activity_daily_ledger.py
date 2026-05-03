from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert as postgres_insert

from service_models.learning_core_models import UserLearningDailyLedger, db


LEDGER_SCOPE_COLUMNS = (
    'user_id',
    'book_id',
    'mode',
    'chapter_id',
    'learning_date',
)


def get_or_create_daily_ledger(
    *,
    user_id: int,
    book_id: str,
    mode: str,
    chapter_id: str,
    learning_date: str,
) -> UserLearningDailyLedger:
    filters = {
        'user_id': user_id,
        'book_id': book_id,
        'mode': mode,
        'chapter_id': chapter_id,
        'learning_date': learning_date,
    }
    ledger = UserLearningDailyLedger.query.filter_by(**filters).first()
    if ledger is not None:
        return ledger

    bind = db.session.get_bind()
    if bind is not None and bind.dialect.name == 'postgresql':
        table = UserLearningDailyLedger.__table__
        inserted_id = db.session.execute(
            postgres_insert(table)
            .values(**filters)
            .on_conflict_do_nothing(index_elements=LEDGER_SCOPE_COLUMNS)
            .returning(table.c.id),
        ).scalar()
        if inserted_id is not None:
            return db.session.get(UserLearningDailyLedger, inserted_id)
        return UserLearningDailyLedger.query.filter_by(**filters).one()

    ledger = UserLearningDailyLedger(**filters)
    db.session.add(ledger)
    return ledger
