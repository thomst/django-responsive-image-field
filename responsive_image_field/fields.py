import os
from io import BytesIO
from PIL import Image
from PIL.Image import Resampling
from django.db import models
from django.core.files.base import File
from django.db.models.fields import files
from .utils import get_md5_hash


class HashedNameMixin:
    """
    TODO
    """
    def __set__(self, instance, value):
        # We use the previous value technique to avoid updating the resized
        # images on instance initialization. See the comments in the `__set__`
        # method of the `ImageFileDescriptor` class of django's source code.
        previous_value = instance.__dict__.get(self.field.attname)
        if previous_value is not None and isinstance(value, File):
            _, ext = os.path.splitext(value.name)
            value.name = f'{get_md5_hash(value)}{ext}'
        super().__set__(instance, value)


class ResizedImageMixin:
    """
    Mixin for ImageFileDescriptor. Resizing the image assigned to the image
    field.
    """

    EXT_TO_FORMATS = {
        '.avif': 'AVIF',
        '.jpeg': 'JPEG',
        '.jpg': 'JPEG',
        '.png': 'PNG',
        '.webp': 'WEBP',
        '.gif': 'GIF',
        '.tiff': 'TIFF',
        '.bmp': 'BMP',
    }

    FORMATS_TO_EXT = {
        'AVIF': '.avif',
        'JPEG': '.jpg',
        'JPG': '.jpg',
        'PNG': '.png',
        'WEBP': '.webp',
        'GIF': '.gif',
        'TIFF': '.tiff',
        'BMP': '.bmp',
    }

    def __set__(self, instance, value):
        # We use the previous value technique to avoid updating the resized
        # images on instance initialization. See the comments in the `__set__`
        # method of the `ImageFileDescriptor` class of django's source code.
        previous_value = instance.__dict__.get(self.field.attname)
        if previous_value is not None and isinstance(value, File):
            name, value = self._resize_content(value.name, value)
            value.name = name
        super().__set__(instance, value)

    def _guess_original_format(self, name, content):
        _, ext = os.path.splitext(name)

        # Try to get the original format from content or file extension.
        if format := getattr(content, 'format', None):
            return format
        elif ext in self.EXT_TO_FORMATS:
            return self.EXT_TO_FORMATS[ext]

    def _get_format(self, name, content):
        # If the format was set use it.
        if self.field.format:
            return self.field.format

        # Otherwise try to guess the original format.
        elif format := self._guess_original_format(name, content):
            return format

        # As a fallback take the first format of our formats mapping.
        else:
            self.FORMATS_TO_EXT.keys()[0]

    def _fix_file_extension(self, name, format):
        ext = self.FORMATS_TO_EXT[format]
        name, _ = os.path.splitext(name)
        return f'{name}{ext}'

    def _resize_content(self, name, content):
        image = Image.open(content.open())

        # Get and check size. Use original size as fallback. Be sure to only
        # downscale the image.
        width, height = self.field.size
        width, height = (width or image.width, height or image.height)
        do_resizing = bool(width < image.width or height < image.height)

        # Get original and target format. Check if the image must be converted.
        original_format = self._guess_original_format(name, content)
        target_format = self._get_format(name, content)
        do_conversion = bool(target_format != original_format)

        if do_resizing:
            image.thumbnail((width, height), self.field.resample)

        if do_resizing or do_conversion:
            # Setup parameter for saving the image.
            params = dict(format=target_format)
            if self.field.quality:
                params['quality'] = self.field.quality

            # Saving the image using the target format.
            new_content = BytesIO()
            image.save(new_content, **params)
            new_content.seek(0)

            # Fix the file extension and return new name and content.
            new_name = self._fix_file_extension(name, target_format)
            return new_name, File(new_content)
        else:
            return name, content


class HashedNameImageFileDescriptor(HashedNameMixin, files.ImageFileDescriptor):
    """
    TODO
    """


class ResizedImageFileDescriptor(ResizedImageMixin, files.ImageFileDescriptor):
    """
    TODO
    """


class HashedResizedImageFileDescriptor(ResizedImageMixin, HashedNameMixin, files.ImageFileDescriptor):
    """
    TODO
    """


class ResizedImageFieldMixin:
    """
    ImageField mixin taking size, format, quality and resample arguments for
    resizing the image.
    """

    def __init__(self, size, format=None, quality=None, resample=Resampling.LANCZOS,
                 *args, **kwargs):
        self.size = size
        self.format = format.upper() if format else None
        self.quality = quality
        self.resample = resample
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['size'] = self.size
        if self.format:
            kwargs["format"] = self.format
        if self.quality:
            kwargs["quality"] = self.quality
        if self.resample != Resampling.LANCZOS:
            kwargs["resample"] = self.resample
        return name, path, args, kwargs


class HashedImageField(models.ImageField):
    """
    The same as :class:`~.ResizedImageField`. But also incorporate the md5 hash
    of the image into its filename.

    This is useful for an efficient caching mechanism using immutable resources.
    """
    descriptor_class = HashedNameImageFileDescriptor


class ResizedImageField(ResizedImageFieldMixin, models.ImageField):
    """
    Image field that resizes the image before storing it.

    Resizing is done via Pillow's thumbnail method using the given size and
    resample. Width or height value might be None. In this case the original
    size will used instead. The image will never be increased and its ratio
    aspects will be preserved.

    The image will be saved using the given format and quality. The quality
    parameter will be ignored for formats not supporting it. See the save
    method's documentation.

    :param tuple size: tuple of width and height values as pixel
    :param str format: format to save image as (optional)
    :param int quality: quality in percentage to save image with (optional)
    :param Resampling resample: resampling filter used for resizing
                                (optional, defaults to LANCZOS)
    """
    descriptor_class = ResizedImageFileDescriptor


class HashedResizedImageField(ResizedImageFieldMixin, models.ImageField):
    """
    The same as :class:`~.ResizedImageField`. But also incorporate the md5 hash
    of the image into its filename.

    This is useful for an efficient caching mechanism using immutable resources.
    """
    descriptor_class = HashedResizedImageFileDescriptor


class ResponsiveImageFieldFile(files.ImageFieldFile):
    """
    TODO
    """
    def __getattr__(self, key):
        try:
            return self.field.get_resized_image(self.instance, key)
        except KeyError:
            msg = f"type object '{type(self).__name__}' has no attribute '{key}'"
            raise AttributeError(msg)

    def delete(self, save=True):
        self.field.delete_resized_images(self.instance, save=save)
        super().delete(save=save)


class ResponsiveImageFileDescriptor(files.ImageFileDescriptor):
    """
    TODO
    """
    def __set__(self, instance, value):
        # We use the previous value technique to avoid updating the resized
        # images on instance initialization. See the comments in the `__set__`
        # method of the `ImageFileDescriptor` class of django's source code.
        previous_value = instance.__dict__.get(self.field.attname)
        super().__set__(instance, value)
        if previous_value is None:
            pass
        elif isinstance(value, File) or value is None:
            self.field.update_resized_images(instance, value)


class OriginalResponsiveImageField(models.ImageField):
    """
    TODO
    """
    attr_class = ResponsiveImageFieldFile
    descriptor_class = ResponsiveImageFileDescriptor

    def __init__(self, fields, **kwargs):
        super().__init__(**kwargs)
        self._fields = fields

    @property
    def fields(self):
        return self._fields

    def update_resized_images(self, instance, value):
        for name in self._fields.values():
            setattr(instance, name, value)

    def delete_resized_images(self, instance, save=True):
        for name in self._fields.values():
            getattr(instance, name).delete(save=save)

    def get_resized_image(self, instance, key):
        return getattr(instance, self._fields[key])

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        args += (self._fields,)
        return name, path, args, kwargs


class ResizedResponsiveImageField(HashedResizedImageField):
    def formfield(self, **kwargs):
        formfield = super().formfield(**kwargs)
        formfield.disabled = True
        return formfield


class ResponsiveImageField:
    """
    A responsive image field stores resized copys of an image using the
    :class:`~.HashedResizedImageField`.

    It takes a `sizes` argument which is a dictonary mapping field names to
    arguments the :class:`~.HashedResizedImageField` is initialized with. This can be
    a tuple of width and height which will be passed as the image field's size
    argument. Or - if you want to be more specific - a dictonary of multiple
    keyword arguments (inclusive the size).

    Based on the `sizes` argument image fields are autogenerated. They will be
    accessible using their names as attributes on the ResponsiveImageField::

    TODO
    """

    original_image_field_class = OriginalResponsiveImageField
    image_field_class = ResizedResponsiveImageField
    dimension_field_class = models.SmallIntegerField

    def __init__(self, sizes, **kwargs):
        self.sizes = sizes
        self.kwargs = kwargs

    def _add_rezised_image_field(self, cls, name, key, kwargs):
        common_kwargs = dict(
            blank=True,
            null=self.kwargs.get('null', False),
        )

        # Create image field.
        field_name = f'{name}_{key}'
        size = f'{kwargs["size"][0]} x {kwargs["size"][1]}'
        kwargs.update(dict(
            **common_kwargs,
            verbose_name=f'{name} [{key}: {size}]',
            width_field=f'{field_name}_width',
            height_field=f'{field_name}_height',
        ))
        field = self.image_field_class(**kwargs)
        field.contribute_to_class(cls, field_name)

        # Create dimension fields.
        for dimension in ['width', 'height']:
            dimension_field_name = f'{field_name}_{dimension}'
            dimension_kwargs = dict(
                verbose_name=f'{name} [{key}-{dimension}]',
                editable=False,
                **common_kwargs,
            )
            dimension_field = self.dimension_field_class(**dimension_kwargs)
            dimension_field.contribute_to_class(cls, dimension_field_name)

    def contribute_to_class(self, cls, name):
        # Create image field for original image.
        # Mind: It is crucial to create the original field first. Otherwise
        # everything works fine except saving the resized images' paths to the
        # database. For any reason we only get the original image name saved.
        kwargs = self.kwargs.copy()
        kwargs['fields'] = dict((k, f'{name}_{k}') for k in self.sizes.keys())
        original_field = self.original_image_field_class(**kwargs)
        original_field.contribute_to_class(cls, name)

        # Create image and dimension fields for resized images.
        for key, kwargs in self.sizes.items():
            self._add_rezised_image_field(cls, name, key, kwargs)
