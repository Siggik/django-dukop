# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Locations(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    street_address = models.CharField(max_length=255, blank=True, null=True)
    postcode = models.CharField(max_length=255, blank=True, null=True)
    town = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(
        max_digits=65535, decimal_places=65535, blank=True, null=True
    )
    longitude = models.DecimalField(
        max_digits=65535, decimal_places=65535, blank=True, null=True
    )
    link = models.CharField(max_length=1024, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "locations"


class Users(models.Model):
    email = models.CharField(unique=True, max_length=255)
    encrypted_password = models.CharField(max_length=255)
    reset_password_token = models.CharField(
        unique=True, max_length=255, blank=True, null=True
    )
    reset_password_sent_at = models.DateTimeField(blank=True, null=True)
    remember_created_at = models.DateTimeField(blank=True, null=True)
    sign_in_count = models.IntegerField()
    current_sign_in_at = models.DateTimeField(blank=True, null=True)
    last_sign_in_at = models.DateTimeField(blank=True, null=True)
    current_sign_in_ip = models.CharField(max_length=255, blank=True, null=True)
    last_sign_in_ip = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    username = models.CharField(unique=True, max_length=255, blank=True, null=True)
    confirmation_token = models.CharField(
        unique=True, max_length=255, blank=True, null=True
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)
    confirmation_sent_at = models.DateTimeField(blank=True, null=True)
    unconfirmed_email = models.CharField(max_length=255, blank=True, null=True)
    is_admin = models.BooleanField(blank=True, null=True)
    is_anonymous = models.BooleanField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "users"


class EventSeries(models.Model):
    title = models.CharField(max_length=1024, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.CharField(max_length=1024, blank=True, null=True)
    cancelled = models.BooleanField(blank=True, null=True)
    user = models.ForeignKey(Users, on_delete=models.SET_NULL, blank=True, null=True)
    location = models.ForeignKey(
        Locations, on_delete=models.SET_NULL, blank=True, null=True
    )
    comments_enabled = models.BooleanField(blank=True, null=True)
    link = models.CharField(max_length=1024, blank=True, null=True)
    picture_file_name = models.CharField(max_length=1024, blank=True, null=True)
    picture_content_type = models.CharField(max_length=1024, blank=True, null=True)
    picture_file_size = models.IntegerField(blank=True, null=True)
    picture_updated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    rule = models.CharField(max_length=1024, blank=True, null=True)
    days = models.CharField(max_length=1024, blank=True, null=True)
    expiry = models.DateField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    published = models.BooleanField(blank=True, null=True)
    expiring_warning_sent = models.BooleanField(blank=True, null=True)
    expired_warning_sent = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "event_series"

    @property
    def short_description(self):
        return self.description

    @property
    def long_description(self):
        return None

    def __str__(self):
        return "EventSeries object {}: {}-{}".format(
            self.title, self.start_time, self.end_time
        )


class Events(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    short_description = models.TextField(blank=True, null=True)
    long_description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    price = models.CharField(max_length=255, blank=True, null=True)
    cancelled = models.BooleanField(blank=True, null=True)
    user = models.ForeignKey(Users, on_delete=models.SET_NULL, blank=True, null=True)
    location = models.ForeignKey(
        Locations, on_delete=models.SET_NULL, blank=True, null=True
    )
    comments_enabled = models.BooleanField(blank=True, null=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    picture_file_name = models.CharField(max_length=255, blank=True, null=True)
    picture_content_type = models.CharField(max_length=255, blank=True, null=True)
    picture_file_size = models.IntegerField(blank=True, null=True)
    picture_updated_at = models.DateTimeField(blank=True, null=True)
    event_series = models.ForeignKey(
        EventSeries, on_delete=models.SET_NULL, blank=True, null=True
    )
    featured = models.BooleanField(blank=True, null=True)
    published = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "events"

    def __str__(self):
        return "Event object {}: {}-{}".format(
            self.title, self.start_time, self.end_time
        )


class Categories(models.Model):
    danish = models.CharField(unique=True, max_length=255, blank=True, null=True)
    english = models.CharField(unique=True, max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "categories"


class CategoriesEventSeries(models.Model):
    event_series = models.ForeignKey(
        EventSeries, on_delete=models.CASCADE, blank=True, null=True
    )
    category = models.ForeignKey(
        Categories, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "categories_event_series"


class CategoriesEvents(models.Model):
    event = models.ForeignKey(Events, on_delete=models.CASCADE, blank=True, null=True)
    category = models.ForeignKey(
        Categories, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "categories_events"


class EventSeriesCategories(models.Model):
    event_series = models.ForeignKey(
        EventSeries, on_delete=models.CASCADE, blank=True, null=True
    )
    category = models.ForeignKey(
        Categories, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "event_series_categories"


class Visits(models.Model):
    visit_token = models.CharField(unique=True, max_length=1024, blank=True, null=True)
    visitor_token = models.CharField(max_length=1024, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    referrer = models.TextField(blank=True, null=True)
    landing_page = models.TextField(blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    referring_domain = models.CharField(max_length=1024, blank=True, null=True)
    search_keyword = models.CharField(max_length=1024, blank=True, null=True)
    browser = models.CharField(max_length=1024, blank=True, null=True)
    os = models.CharField(max_length=1024, blank=True, null=True)
    device_type = models.CharField(max_length=1024, blank=True, null=True)
    utm_source = models.CharField(max_length=1024, blank=True, null=True)
    utm_medium = models.CharField(max_length=1024, blank=True, null=True)
    utm_term = models.CharField(max_length=1024, blank=True, null=True)
    utm_content = models.CharField(max_length=1024, blank=True, null=True)
    utm_campaign = models.CharField(max_length=1024, blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "visits"


####################
# Not imported
####################


class Comments(models.Model):
    content = models.TextField(blank=True, null=True)
    hidden = models.BooleanField(blank=True, null=True)
    event_id = models.IntegerField(blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "comments"


class Posts(models.Model):
    title = models.CharField(max_length=1024, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    featured = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "posts"


class SimpleCaptchaData(models.Model):
    key = models.CharField(max_length=40, blank=True, null=True)
    value = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "simple_captcha_data"


class AhoyEvents(models.Model):
    visit_id = models.IntegerField(blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=1024, blank=True, null=True)
    properties = models.TextField(blank=True, null=True)  # This field type is a guess.
    time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "ahoy_events"
