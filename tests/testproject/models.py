from django.db import models
from responsive_image_field import fields


class TestModel(models.Model):
    resized = fields.ResizedImageField((150, 300))
    resized_width = fields.ResizedImageField((100, None))
    resized_height = fields.ResizedImageField((None, 100))
    resized_converted = fields.ResizedImageField((120, 120), 'AVIF')
    not_resized_converted = fields.ResizedImageField((300, 300), 'AVIF')
    not_resized_not_converted = fields.ResizedImageField((300, 300), 'PNG')
    converted_high_quality = fields.ResizedImageField((120, 120), 'AVIF', quality=100)
    converted_low_quality = fields.ResizedImageField((120, 120), 'AVIF', quality=10)
    hashed_resized = fields.HashedResizedImageField((120, 120))
    hashed = fields.HashedImageField()
