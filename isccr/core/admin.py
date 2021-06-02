from admin_cursor_paginator import CursorPaginatorAdmin
from django.utils.safestring import mark_safe
from public_admin.admin import PublicModelAdmin
from isccr.core.models import Chain, IsccID
from public_admin.sites import PublicAdminSite, PublicApp


public_app = PublicApp("core", models=("IsccID", "Chain"))


class ISCCAdminSite(PublicAdminSite):
    site_header = "ISCC-ID Resolver"
    site_title = "ISCC-ID Resolver"
    index_title = ""
    enable_nav_sidebar = False


isccr_admin = ISCCAdminSite("isccr-admin", public_app)


class ChainAdmin(PublicModelAdmin):

    list_display = ("id", "slug")


isccr_admin.register(Chain, ChainAdmin)


class IsccIDAdmin(PublicModelAdmin, CursorPaginatorAdmin):

    readonly_fields = [f.name for f in IsccID._meta.fields]
    actions = None
    list_per_page = 20
    search_fields = ["=iscc_id", "@iscc_code", "=actor"]
    list_display = [
        "iscc_id",
        "src_chain",
        "iscc_code",
        "actor",
        "src_time",
        "revision",
    ]
    list_select_related = ["src_chain"]

    fieldsets = (
        (
            "Core Data",
            {
                "fields": (
                    "iscc_id",
                    "iscc_code",
                    "actor",
                    "revision",
                ),
            },
        ),
        (
            "Seed Metadata (Immutable)",
            {
                "fields": ["iscc_seed_title", "iscc_seed_extra"],
            },
        ),
        (
            "Ledger Reference",
            {
                "fields": (
                    "admin_ledger_link",
                    "src_chain",
                    "src_chain_idx",
                    "src_block_hash",
                    "src_tx_hash",
                    "src_tx_out_idx",
                )
            },
        ),
        (
            "Mutable Metadata",
            {
                "fields": ["iscc_mutable_metadata"],
            },
        ),
    )

    def admin_ledger_link(self, obj):
        if not obj:
            return ""
        if obj.src_tx_out_idx is not None:
            url = obj.src_chain.url_template.format(obj.src_tx_hash, obj.src_tx_out_idx)
        else:
            url = obj.src_chain.url_template.format(obj.src_tx_hash)
        html = f'<a href="{url}" target="top">{url}</a>'
        return mark_safe(html)

    admin_ledger_link.short_description = "Ledger URL"


isccr_admin.register(IsccID, IsccIDAdmin)
