from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


_FK_NAMING_CONVENTION = {
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
}


def _fallback_fk_name(table_name: str, fk: dict) -> str:
    column_name = str((fk.get('constrained_columns') or ['user_id'])[0])
    referred_table = str(fk.get('referred_table') or 'users')
    return f'fk_{table_name}_{column_name}_{referred_table}'


def drop_identity_user_foreign_keys(
    connection: sa.engine.Connection,
    *,
    table_names: Iterable[str],
) -> list[str]:
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    ops = Operations(MigrationContext.configure(connection))
    changes: list[str] = []

    for table_name in sorted(set(table_names) & existing_tables):
        matching_fks = [
            fk for fk in inspector.get_foreign_keys(table_name)
            if fk.get('referred_table') == 'users'
        ]
        if not matching_fks:
            continue

        with ops.batch_alter_table(
            table_name,
            naming_convention=_FK_NAMING_CONVENTION,
        ) as batch_op:
            for fk in matching_fks:
                fk_name = str(fk.get('name') or _fallback_fk_name(table_name, fk))
                batch_op.drop_constraint(fk_name, type_='foreignkey')
                changes.append(f'{table_name}.{fk_name}')

    return changes
