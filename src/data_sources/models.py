import logging
from pathlib import Path
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .fields import SHA256ChecksumField




class DataSource(models.Model):
    """A model to store user's data sources.

    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='data_sources',
    )

    # Don't use FilePathField, not that useful.
    # Only check file existence at forms
    file_path = models.CharField(
        max_length=1023,
        verbose_name=_("file path"),
        help_text=_("Relative path under user's data source directory."),
    )
    checksum = SHA256ChecksumField(
        blank=True,
        verbose_name=_("SHA256 checksum"),
        help_text=_(
            "Hexadecimal checksum generated by SHA256 hash algorithm."
        ),
    )

    class Meta:
        verbose_name = _('data source')
        verbose_name_plural = _('data sources')
        unique_together = ('owner', 'file_path')

    def __str__(self):
        return (
            '%s (owner: %s)' %
            (self.get_rel_file_path(), self.owner.name)
        )

    def get_rel_file_path(self):
        return Path(str(self.owner.pk), self.file_path)

    def get_full_file_path(self):
        full_file_path = settings.BIOCLOUD_DATA_SOURCES_DIR.joinpath(
            str(self.owner.pk), self.file_path
        )
        return full_file_path

