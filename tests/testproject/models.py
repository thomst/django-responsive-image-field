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

    # HashedResizedImage with dimension fields.
    hashed_resized_with_dimensions = fields.HashedResizedImageField(
        (120, 120),
        null=True,
        blank=True,
        width_field='hashed_resized_width',
        height_field='hashed_resized_height',
    )
    hashed_resized_width = models.SmallIntegerField(null=True, blank=True)
    hashed_resized_height = models.SmallIntegerField(null=True, blank=True)

    # Resized ImageField with dimension fields.
    resized_with_dimensions = fields.ResizedImageField(
        (80, 80),
        null=True,
        blank=True,
        width_field='resized_with_dimensions_width',
        height_field='resized_with_dimensions_height',
    )
    resized_with_dimensions_width = models.SmallIntegerField(null=True, blank=True)
    resized_with_dimensions_height = models.SmallIntegerField(null=True, blank=True)

    # Resized ImageField with dimension fields.
    hashed_with_dimensions = fields.HashedImageField(
        null=True,
        blank=True,
        width_field='hashed_with_dimensions_width',
        height_field='hashed_with_dimensions_height',
    )
    hashed_with_dimensions_width = models.SmallIntegerField(null=True, blank=True)
    hashed_with_dimensions_height = models.SmallIntegerField(null=True, blank=True)

    SIZES = dict(
        small=dict(size=(50, 50), format='AVIF'),
        medium=dict(size=(100, 100), format='AVIF'),
        large=dict(size=(150, 150), format='AVIF'),
    )
    responsive = fields.ResponsiveImageField(SIZES, null=True, blank=True)
