from django.db import models
from django.utils.translation import gettext_lazy as _

class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # ISO code
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        db_table = 'app_language'

    def __str__(self):
        return self.name

class Languagee(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # ISO code
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        db_table = 'app_languagee'

    def __str__(self):
        return self.name

class InterpreterLanguage(models.Model):
    class Proficiency(models.TextChoices):
        NATIVE = 'NATIVE', _('Natif')
        FLUENT = 'FLUENT', _('Courant')
        PROFESSIONAL = 'PROFESSIONAL', _('Professionnel')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermédiaire')

    interpreter = models.ForeignKey('Interpreter', on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    proficiency = models.CharField(max_length=20, choices=Proficiency.choices)
    is_primary = models.BooleanField(default=False)
    certified = models.BooleanField(default=False)
    certification_details = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['interpreter', 'language']
        db_table = 'app_interpreterlanguage'
