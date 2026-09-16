"""Persist role permissions and approved local model registry."""
from alembic import op
from backend.argus.db import Role,AIModel
revision='0002'
down_revision='0001'
def upgrade():
    Role.__table__.create(op.get_bind(),checkfirst=True)
    AIModel.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():
    AIModel.__table__.drop(op.get_bind())
    Role.__table__.drop(op.get_bind())
