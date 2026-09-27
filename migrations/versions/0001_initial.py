"""Create the PostgreSQL flight-operations ledger.

Revision ID: 0001_initial
Revises:
"""
from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
    op.execute(
        """
        CREATE FUNCTION enforce_flight_cabin_totals() RETURNS trigger AS $$
        DECLARE
            target_flight_id bigint;
            declared_capacity integer;
            cabin_count integer;
            cabin_total bigint;
        BEGIN
            IF TG_TABLE_NAME = 'flights' THEN
                target_flight_id := COALESCE(NEW.id, OLD.id);
            ELSE
                target_flight_id := COALESCE(NEW.flight_id, OLD.flight_id);
            END IF;
            SELECT capacity INTO declared_capacity FROM flights WHERE id = target_flight_id;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;
            SELECT count(*), coalesce(sum(capacity), 0)
              INTO cabin_count, cabin_total
              FROM seat_inventory
             WHERE flight_id = target_flight_id;
            IF cabin_count <> 3 OR cabin_total <> declared_capacity THEN
                RAISE EXCEPTION 'flight % must have exactly three cabin allocations summing to capacity % (got % across % cabins)',
                    target_flight_id, declared_capacity, cabin_total, cabin_count
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        CREATE CONSTRAINT TRIGGER flights_cabin_capacity_check
        AFTER INSERT OR UPDATE ON flights
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION enforce_flight_cabin_totals();
        CREATE CONSTRAINT TRIGGER inventory_cabin_capacity_check
        AFTER INSERT OR UPDATE OR DELETE ON seat_inventory
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION enforce_flight_cabin_totals();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS inventory_cabin_capacity_check ON seat_inventory")
    op.execute("DROP TRIGGER IF EXISTS flights_cabin_capacity_check ON flights")
    op.execute("DROP FUNCTION IF EXISTS enforce_flight_cabin_totals()")
    Base.metadata.drop_all(bind=op.get_bind())
