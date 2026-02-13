from django.db import models

class AppLanguage(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    code = models.CharField(unique=True, max_length=10)
    is_active = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_language'

class AppServicetype(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_hours = models.IntegerField()
    cancellation_policy = models.TextField()
    requires_certification = models.IntegerField()
    active = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_servicetype'

class AppContactmessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField()
    processed = models.IntegerField()
    processed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    processed_by = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_contactmessage'

class AppNotification(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    content = models.TextField()
    read = models.IntegerField()
    link = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField()
    recipient = models.ForeignKey('AppUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_notification'

class AppNotificationpreference(models.Model):
    id = models.BigAutoField(primary_key=True)
    email_quote_updates = models.IntegerField()
    email_assignment_updates = models.IntegerField()
    email_payment_updates = models.IntegerField()
    sms_enabled = models.IntegerField()
    quote_notifications = models.IntegerField()
    assignment_notifications = models.IntegerField()
    payment_notifications = models.IntegerField()
    system_notifications = models.IntegerField()
    notification_frequency = models.CharField(max_length=20)
    preferred_language = models.ForeignKey(AppLanguage, models.DO_NOTHING, blank=True, null=True)
    user = models.OneToOneField('AppUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_notificationpreference'

class AppAuditlog(models.Model):
    id = models.BigAutoField(primary_key=True)
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50)
    changes = models.JSONField()
    ip_address = models.CharField(max_length=39, blank=True, null=True)
    timestamp = models.DateTimeField()
    user = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_auditlog'
