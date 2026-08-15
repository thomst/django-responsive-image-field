from django.db import models
from responsive_image_field import fields


class TestModel(models.Model):
    resized = fields.ResizedImageField((150, 300), null=True, blank=True)
    resized_width = fields.ResizedImageField((100, None), null=True, blank=True)
    resized_height = fields.ResizedImageField((None, 100), null=True, blank=True)
    resized_converted = fields.ResizedImageField((120, 120), 'AVIF', null=True, blank=True)
    not_resized_converted = fields.ResizedImageField((300, 300), 'AVIF', null=True, blank=True)
    not_resized_not_converted = fields.ResizedImageField((300, 300), 'PNG', null=True, blank=True)
    converted_high_quality = fields.ResizedImageField((120, 120), 'AVIF', quality=100, null=True, blank=True)
    converted_low_quality = fields.ResizedImageField((120, 120), 'AVIF', quality=10, null=True, blank=True)
    hashed_resized = fields.HashedResizedImageField((120, 120), null=True, blank=True)
    hashed = fields.HashedImageField(null=True, blank=True)
