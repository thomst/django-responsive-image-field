import hashlib
import os
from io import BytesIO
from django.db import models
from django.core.files.base import File
from django.db.models.fields import files
from PIL import Image
from PIL.Image import Resampling
from .utils import get_md5_hash


class HashedFileNameMixin:
    """
    Mixin for Django FieldFile and ImageFieldFile that incorporates an MD5 hash
    of the file content into the filename.

    This ensures that:
    - Files with identical content get the same hash (deduplication)
    - Files are uniquely identified by their content
    """

    def save(self, name, content, save=True):
        if hash := get_md5_hash(content):
            name, ext = os.path.splitext(name)
            name = f'{name}.{hash}{ext}'
        return super().save(name, content, save=save)


class ResizedImageMixin:
    """
    Mixin for Django ImageFieldFile .
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

    def save(self, name, content, save=True):
        name, content = self._resize_content(name, content)
        return super().save(name, content, save)

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


class HashedImageFieldFile(HashedFileNameMixin, files.ImageFieldFile):
    """
    ImageFieldFile that incorporates MD5 file content hash into the filename.
    """


class ResizedImageFieldFile(ResizedImageMixin, files.ImageFieldFile):
    """
    ImageFieldFile that incorporates MD5 file content hash into the filename.
    """


class HashedResizedImageFieldFile(ResizedImageMixin, HashedFileNameMixin, files.ImageFieldFile):
    """
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
        if self.resample:
            kwargs["resample"] = self.resample
        return name, path, args, kwargs


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
    attr_class = ResizedImageFieldFile


class HashedImageField(models.ImageField):
    """
    The same as :class:`~.ResizedImageField`. But also incorporate the md5 hash
    of the image into its filename.

    This is useful for an efficient caching mechanism using immutable resources.
    """
    attr_class = HashedImageFieldFile


class HashedResizedImageField(ResizedImageFieldMixin, models.ImageField):
    """
    The same as :class:`~.ResizedImageField`. But also incorporate the md5 hash
    of the image into its filename.

    This is useful for an efficient caching mechanism using immutable resources.
    """
    attr_class = HashedResizedImageFieldFile
