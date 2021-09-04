from admin_cursor_paginator import CursorPaginatorAdmin
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from public_admin.admin import PublicModelAdmin
from isccr.core.models import Chain, IsccID
from public_admin.sites import PublicAdminSite, PublicApp
from django.db import connection
from isccr.utils import iscc_verify


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


class IsccIDAdmin(PublicModelAdmin):

    readonly_fields = [f.name for f in IsccID._meta.fields]
    actions = None
    list_per_page = 20
    search_fields = ["=iscc_id", "@iscc_code"]
    list_display = [
        "iscc_id",
        "src_chain",
        "iscc_code",
        "actor",
        "src_time",
        "revision",
    ]
    list_select_related = ["src_chain"]
    # ordering = ("-src_time",)

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

    def get_search_results(self, request, queryset, search_term):
        """Optimized Search"""
        clean = search_term.strip()
        if not clean:
            return queryset, False

        if clean.startswith("28") or clean.startswith("29"):
            return queryset.filter(iscc_id=clean), False

        try:
            if iscc_verify(search_term):
                return queryset.filter(iscc_code__search=search_term), False
        except ValueError:
            queryset = IsccID.objects.none()

        return queryset, False

    @cached_property
    def count(self):
        query = self.object_list.query
        if not query.where:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT reltuples FROM pg_class WHERE relname = %s",
                    [query.model._meta.db_table],
                )
                return int(cursor.fetchone()[0])
            except Exception as e:  # noqa
                pass

        return super().count


isccr_admin.register(IsccID, IsccIDAdmin)
