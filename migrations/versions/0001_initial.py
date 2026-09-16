"""Initial ARGUS relational schema; media stays on filesystem."""
from alembic import op
from backend.argus.db import Base
revision='0001'
down_revision=None

def upgrade():
    bind=op.get_bind()
    if bind.dialect.name=='postgresql': op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    Base.metadata.create_all(bind=bind)

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
