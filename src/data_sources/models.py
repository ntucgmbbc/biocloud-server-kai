import hashlib
from django import forms
from django.conf import settings
from django.core.validators import (
    RegexValidator, MinLengthValidator, MaxLengthValidator
)
from django.db import models
from django.utils.translation import ugettext_lazy as _


class SHA256ChecksumField(models.CharField):
    default_validators = [
        MinLengthValidator(64),
        MaxLengthValidator(64),
        RegexValidator(
            regex=r'^[A-Fa-f0-9]+$',
            message=_(
                'Invalid SHA256 checksum format, expected only '
                'hexadecimal digits'
            ),
            code='sha256sum_non_hexadecimal',
        ),
    ]
    description = _("SHA256 checksum")

    def __init__(self, blank=False):
        # SHA-256 checksum in hexadecimal representation takes up 64 chars,
        # e.g. 4bit * 64 = 256bit (1 char represents only 4 bit here)
        super().__init__(blank=blank, max_length=64)

    @classmethod
    def get_hash_fun(cls):
        """Return the hash function in use.

        For this field sha256 is used.
        """
        return hashlib.sha256

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        return super().formfield(**{
            **kwargs,
            'form_class': forms.CharField
        })


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
    file_path = models.CharField(max_length=1023)

    checksum = SHA256ChecksumField(blank=True)

    def __str__(self):
        return (
            '%s/%s (owner: %s)' %
            (self.owner.pk, self.file_path, self.owner.name)
        )
