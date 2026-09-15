"""VPS V4 infrastructure profiles, pinning, IP pool and mutation journal.

Revision ID: f4a7c2d9e610
Revises: a3f7c214e8b9
Create Date: 2026-09-12

The migration is additive. It preserves all legacy Vultr/gateway columns and
only backfills rows for which a non-empty `vultr_id` is direct evidence.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "f4a7c2d9e610"
down_revision = "a3f7c214e8b9"
branch_labels = None
depends_on = None

VULTR_PROFILE_ID = "00000000-0000-4000-8000-000000000401"
OVH_PROFILE_ID = "00000000-0000-4000-8000-000000000402"


def upgrade() -> None:
    op.create_table(
        "vps_infrastructure_profile",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False,
                  server_default="production"),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default="STANDBY"),
        sa.Column("accept_new", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("is_default", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("compute_backend_type", sa.String(32), nullable=False),
        sa.Column("public_ip_backend_type", sa.String(32), nullable=False),
        sa.Column("gateway_backend_type", sa.String(32), nullable=False),
        sa.Column("compute_config", sa.JSON(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("network_config", sa.JSON(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("provider_config", sa.JSON(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("credential_ref", sa.String(128), nullable=False,
                  server_default=""),
        sa.Column("config_version", sa.Integer(), nullable=False,
                  server_default="1"),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('ACTIVE','DRAINING','STANDBY','DISABLED')",
            name="ck_vps_profile_status"),
        sa.CheckConstraint("status = 'ACTIVE' OR accept_new = false",
                           name="ck_vps_profile_accept_only_active"),
        sa.CheckConstraint(
            "is_default = false OR (status = 'ACTIVE' AND accept_new = true)",
            name="ck_vps_profile_default_active"),
    )
    op.create_index("ix_vps_profile_region", "vps_infrastructure_profile", ["region"])
    op.create_index("ix_vps_profile_status", "vps_infrastructure_profile", ["status"])
    op.create_index(
        "ix_vps_profile_selector", "vps_infrastructure_profile",
        ["region", "status", "accept_new"])
    op.create_index(
        "uq_vps_profile_one_default", "vps_infrastructure_profile", ["is_default"],
        unique=True, postgresql_where=sa.text("is_default IS TRUE"),
        sqlite_where=sa.text("is_default = 1"))

    now = datetime.now(timezone.utc)
    profile_table = sa.table(
        "vps_infrastructure_profile",
        sa.column("id", sa.String), sa.column("slug", sa.String),
        sa.column("name", sa.String), sa.column("region", sa.String),
        sa.column("environment", sa.String), sa.column("status", sa.String),
        sa.column("accept_new", sa.Boolean), sa.column("is_default", sa.Boolean),
        sa.column("compute_backend_type", sa.String),
        sa.column("public_ip_backend_type", sa.String),
        sa.column("gateway_backend_type", sa.String),
        sa.column("compute_config", sa.JSON), sa.column("network_config", sa.JSON),
        sa.column("provider_config", sa.JSON), sa.column("credential_ref", sa.String),
        sa.column("config_version", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(profile_table, [
        {
            "id": VULTR_PROFILE_ID, "slug": "vultr-sgp", "name": "VULTR-SGP",
            "region": "sgp", "environment": "production", "status": "STANDBY",
            "accept_new": False, "is_default": False,
            "compute_backend_type": "proxmox",
            "public_ip_backend_type": "vultr_reserved_ip",
            "gateway_backend_type": "nft",
            "compute_config": {"credential_ref": "LTT_VPS_PROXMOX",
                               "runtime_ref": "LTT_VPS_MACHINE_B_RUNTIME"},
            "network_config": {"gateway_credential_ref": "LTT_VPS_GATEWAY",
                               "router_credential_ref": "LTT_VPS_ROUTER",
                               "mapping_strategy": "ltt_nft_maps"},
            "provider_config": {"region": "sgp"},
            "credential_ref": "LTT_VULTR", "config_version": 1,
            "created_at": now, "updated_at": now,
        },
        {
            "id": OVH_PROFILE_ID, "slug": "ovh-sgp-prod",
            "name": "OVH-SGP-PROD", "region": "sgp",
            "environment": "production", "status": "STANDBY",
            "accept_new": False, "is_default": False,
            "compute_backend_type": "proxmox",
            "public_ip_backend_type": "ovh_static_pool",
            "gateway_backend_type": "nft",
            "compute_config": {"credential_ref": "LTT_VPS_PROXMOX",
                               "runtime_ref": "LTT_OVH_MACHINE_B_RUNTIME"},
            "network_config": {"gateway_credential_ref": "LTT_OVH_GATEWAY",
                               "router_credential_ref": "LTT_OVH_ROUTER",
                               "mapping_strategy": "ovh_gwnat"},
            "provider_config": {"acquisition": "operator_only"},
            "credential_ref": "LTT_OVH", "config_version": 1,
            "created_at": now, "updated_at": now,
        },
    ])

    # Batch mode keeps the same additive migration executable on SQLite
    # test/restore databases and PostgreSQL production.
    with op.batch_alter_table("vps_instance") as batch_op:
        batch_op.add_column(sa.Column(
            "infrastructure_profile_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column(
            "profile_resolution_state", sa.String(16), nullable=False,
            server_default="NEEDS_REVIEW"))
        batch_op.create_foreign_key(
            "fk_vps_instance_profile", "vps_infrastructure_profile",
            ["infrastructure_profile_id"], ["id"], ondelete="RESTRICT")
        batch_op.create_index(
            "ix_vps_instance_infrastructure_profile_id",
            ["infrastructure_profile_id"])
        batch_op.create_index(
            "ix_vps_instance_profile_resolution_state",
            ["profile_resolution_state"])
        batch_op.create_check_constraint(
            "ck_vps_instance_profile_resolution",
            "profile_resolution_state IN ('NEEDS_REVIEW','PINNED')")

    with op.batch_alter_table("vps_gateway") as batch_op:
        batch_op.add_column(sa.Column(
            "infrastructure_profile_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key(
            "fk_vps_gateway_profile", "vps_infrastructure_profile",
            ["infrastructure_profile_id"], ["id"], ondelete="RESTRICT")
        batch_op.create_index(
            "ix_vps_gateway_infrastructure_profile_id",
            ["infrastructure_profile_id"])

    with op.batch_alter_table("vps_ip") as batch_op:
        batch_op.add_column(sa.Column(
            "infrastructure_profile_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column(
            "backend_resource_id", sa.String(128), nullable=False,
            server_default=""))
        batch_op.add_column(sa.Column(
            "state", sa.String(16), nullable=False,
            server_default="QUARANTINED"))
        batch_op.add_column(sa.Column(
            "reservation_token", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column(
            "reserved_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column(
            "bound_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column(
            "last_observed_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column(
            "billing_mode", sa.String(24), nullable=False, server_default=""))
        batch_op.add_column(sa.Column(
            "monthly_cost_minor", sa.Integer(), nullable=False,
            server_default="0"))
        batch_op.add_column(sa.Column(
            "provider_metadata", sa.JSON(), nullable=False,
            server_default=sa.text("'{}'")))
        batch_op.create_foreign_key(
            "fk_vps_ip_profile", "vps_infrastructure_profile",
            ["infrastructure_profile_id"], ["id"], ondelete="RESTRICT")
        batch_op.create_index(
            "ix_vps_ip_infrastructure_profile_id", ["infrastructure_profile_id"])
        batch_op.create_index("ix_vps_ip_state", ["state"])
        batch_op.create_unique_constraint(
            "uq_vps_ip_reservation_token", ["reservation_token"])
        batch_op.create_check_constraint(
            "ck_vps_ip_state",
            "state IN ('FREE','RESERVED','BOUND','QUARANTINED')")

    # Direct evidence only. Rows without a provider resource remain NEEDS_REVIEW.
    op.execute(sa.text(
        "UPDATE vps_ip SET infrastructure_profile_id = :profile, "
        "backend_resource_id = vultr_id, "
        "state = CASE WHEN instance_id IS NULL THEN 'QUARANTINED' ELSE 'BOUND' END "
        "WHERE vultr_id IS NOT NULL AND vultr_id <> ''"
    ).bindparams(profile=VULTR_PROFILE_ID))
    op.execute(sa.text(
        "UPDATE vps_instance SET infrastructure_profile_id = :profile, "
        "profile_resolution_state = 'PINNED' WHERE EXISTS ("
        "SELECT 1 FROM vps_ip WHERE vps_ip.instance_id = vps_instance.id "
        "AND vps_ip.vultr_id IS NOT NULL AND vps_ip.vultr_id <> '')"
    ).bindparams(profile=VULTR_PROFILE_ID))

    op.create_table(
        "vps_profile_health",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("infrastructure_profile_id", sa.String(36), nullable=False),
        sa.Column("component", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["infrastructure_profile_id"],
                                ["vps_infrastructure_profile.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('UNKNOWN','STALE','HEALTHY','DEGRADED','CRITICAL')",
            name="ck_vps_profile_health_status"),
    )
    op.create_index("ix_vps_profile_health_profile", "vps_profile_health",
                    ["infrastructure_profile_id"])
    op.create_index(
        "ix_vps_profile_health_latest", "vps_profile_health",
        ["infrastructure_profile_id", "component", "observed_at"])

    op.create_table(
        "vps_external_mutation",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("operation_id", sa.String(96), nullable=False),
        sa.Column("instance_id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("step", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="INTENT"),
        sa.Column("request_fingerprint", sa.String(64), nullable=False, server_default=""),
        sa.Column("external_ref", sa.String(190), nullable=False, server_default=""),
        sa.Column("provider_metadata", sa.JSON(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(64), nullable=False, server_default=""),
        sa.Column("last_error_detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("compensated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["vps_infrastructure_profile.id"],
                                ondelete="RESTRICT"),
        sa.UniqueConstraint("idempotency_key", name="uq_vps_external_mutation_idem"),
        sa.CheckConstraint(
            "state IN ('INTENT','REQUESTED','OBSERVED','COMPENSATED','FAILED','NEEDS_REVIEW')",
            name="ck_vps_external_mutation_state"),
    )
    op.create_index("ix_vps_external_mutation_operation", "vps_external_mutation",
                    ["operation_id"])
    op.create_index("ix_vps_external_mutation_instance", "vps_external_mutation",
                    ["instance_id"])
    op.create_index("ix_vps_external_mutation_profile", "vps_external_mutation",
                    ["profile_id"])
    op.create_index("ix_vps_external_mutation_state", "vps_external_mutation", ["state"])
    op.create_index(
        "ix_vps_external_mutation_instance_step", "vps_external_mutation",
        ["instance_id", "step"])


def downgrade() -> None:
    op.drop_table("vps_external_mutation")
    op.drop_table("vps_profile_health")

    with op.batch_alter_table("vps_ip") as batch_op:
        batch_op.drop_constraint("ck_vps_ip_state", type_="check")
        batch_op.drop_constraint("uq_vps_ip_reservation_token", type_="unique")
        batch_op.drop_index("ix_vps_ip_state")
        batch_op.drop_index("ix_vps_ip_infrastructure_profile_id")
        batch_op.drop_constraint("fk_vps_ip_profile", type_="foreignkey")
        for column in (
            "provider_metadata", "monthly_cost_minor", "billing_mode",
            "last_observed_at", "bound_at", "reserved_at", "reservation_token",
            "state", "backend_resource_id", "infrastructure_profile_id",
        ):
            batch_op.drop_column(column)

    with op.batch_alter_table("vps_instance") as batch_op:
        batch_op.drop_constraint(
            "ck_vps_instance_profile_resolution", type_="check")
        batch_op.drop_index("ix_vps_instance_profile_resolution_state")
        batch_op.drop_index("ix_vps_instance_infrastructure_profile_id")
        batch_op.drop_constraint("fk_vps_instance_profile", type_="foreignkey")
        batch_op.drop_column("profile_resolution_state")
        batch_op.drop_column("infrastructure_profile_id")
    with op.batch_alter_table("vps_gateway") as batch_op:
        batch_op.drop_index("ix_vps_gateway_infrastructure_profile_id")
        batch_op.drop_constraint("fk_vps_gateway_profile", type_="foreignkey")
        batch_op.drop_column("infrastructure_profile_id")
    op.drop_table("vps_infrastructure_profile")
