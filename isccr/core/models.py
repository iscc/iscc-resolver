from django.db import models
from django.urls import reverse
from model_utils.models import TimeStampedModel


class Chain(models.Model):
    """An observed Blockchain"""

    id = models.PositiveIntegerField(primary_key=True)
    slug = models.SlugField()
    url_template = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.slug

    def __repr__(self):
        return f"Chain(id={self.id}, name={self.slug})"

    class Meta:
        verbose_name = "Chain"
        verbose_name_plural = "Chains"


class IsccID(TimeStampedModel):
    """An ISCC-ID minted from a declaration."""

    # Core Data

    iscc_id = models.CharField(
        verbose_name="ISCC-ID",
        max_length=32,
        primary_key=True,
        help_text="ISCC-ID - digital asset identifier",
    )
    iscc_code = models.CharField(
        verbose_name="ISCC-CODE",
        max_length=256,
        help_text="ISCC-CODE - digital asset descriptor",
    )

    iscc_tophash = models.CharField(
        max_length=256,
        verbose_name="ISCC-TOPHASH",
        help_text="Cryptographic hash of digital asset",
    )

    actor = models.CharField(
        max_length=256,
        help_text="PUBLIC-KEY or WALLET-ADDRESS of DECLARING PARTY",
    )

    # Seed Metadata (Immutable)

    iscc_seed_title = models.CharField(
        verbose_name="title",
        max_length=128,
        blank=True,
    )

    iscc_seed_extra = models.TextField(
        verbose_name="extra",
        max_length=4096,
        blank=True,
    )

    # Mutable Metadata

    iscc_mutable_metadata = models.JSONField(
        verbose_name="mutable metadata",
        null=True,
    )

    # Ledger Reference Data

    src_chain = models.ForeignKey(
        Chain,
        verbose_name="Ledger",
        on_delete=models.CASCADE,
        help_text="Source Ledger/Blockchain",
    )
    src_chain_idx = models.PositiveBigIntegerField(
        verbose_name="ledger index",
        help_text="N-th ISCC Decleration on source ledger",
    )
    src_block_hash = models.CharField(
        verbose_name="block hash",
        max_length=128,
        help_text="Hash of block that includes the ISCC-DECLARATION",
    )
    src_tx_hash = models.CharField(
        verbose_name="transaction hash",
        max_length=128,
        help_text="Hash of transaction that includes the ISCC-DECLERATION",
    )
    src_tx_out_idx = models.PositiveSmallIntegerField(
        verbose_name="transaction output",
        null=True,
        help_text="Output index that includes ISCC-DECLERATION (UTXO based chains)",
    )
    src_time = models.DateTimeField()
    revision = models.PositiveIntegerField(
        default=0, help_text="Number of times updated"
    )

    def get_admin_url(self):
        # the url to the Django admin form for the model instance
        info = (self._meta.app_label, self._meta.model_name)
        return reverse("admin:%s_%s_change" % info, args=(self.pk,))

    class Meta:
        verbose_name = "ISCC-ID"
        verbose_name_plural = "ISCC-IDs"
        constraints = [
            models.UniqueConstraint(
                name="unique-entry",
                fields=["iscc_id", "iscc_code", "actor"],
                deferrable=models.Deferrable.IMMEDIATE,
            )
        ]

    def __str__(self):
        return self.iscc_id
