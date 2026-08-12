import hashlib
import os
from io import BytesIO
from django.db import models
from django.db.models.fields import files
from PIL import Image
from PIL.Image import Resampling


class HashedFileNameMixin:
    """
    Mixin for Django FieldFile and ImageFieldFile that incorporates an MD5 hash
    of the file content into the filename.

    This ensures that:
    - Files with identical content get the same hash (deduplication)
    - Files are uniquely identified by their content
    """

    def save(self, name, content, save=True):
        if file_hash := self._hash_content(content):
            name, ext = os.path.splitext(name)
            name = f'{name}.{file_hash}{ext}'
        return super().save(name, content, save=save)

    def _hash_content(self, content):
        """
        Compute MD5 hash from file-like content.
        """
        try:
            # Read and hash in chunks.
            md5_hash = hashlib.md5()
            for chunk in iter(lambda: content.read(8192), b''):
                md5_hash.update(chunk)

            # Seek back to 0.
            content.seek(0)
        except Exception:
            return None
        else:
            return md5_hash.hexdigest()


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

    def _get_format(self, name, content):
        _, ext = os.path.splitext(name)

        # If format given use it.
        if self.field.format:
            return format

        # Otherwise try to get the original format from content.
        elif format := getattr(content, format, None):
            return format

        # Or try to get the original format from the file extension.
        elif ext in self.EXT_TO_FORMATS:
            return self.EXT_TO_FORMATS[ext]

        # As a fallback we use the first specified format in our formats mapping.
        else:
            self.FORMATS_TO_EXT.keys()[0]

    def _get_name(self, name, format):
        ext = self.FORMATS_TO_EXT[format]
        name, _ = os.path.splitext(name)
        return f'{name}{ext}'

    def _resize_content(self, name, content):
        image = Image.open(content)
        width, height = self.field.size

        # Use original values as fallback.
        width, height = (width or image.width, height or image.height)

        # At least one value should be smaller to not increasing the image.
        if width < image.width or height < image.height:
            image.thumbnail((width, height), self.field.resample)

        # Save image with new format. The quality keyword will be ignored for
        # formats not supporting it.
        format = self._get_format(name, content)
        new_content = BytesIO()
        image.save(new_content, format=format, quality=self.field.quality)

        # Fix the filename extension due to the new format.
        name = self._get_name(name, format)
        return name, new_content


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


class HashedResizedImageField(ResizedImageFieldMixin, models.ImageField):
    """
    The same as :class:`~.ResizedImageField`. But also incorporate the md5 hash
    of the image into its filename.

    This is useful for an efficient caching mechanism using immutable resources.
    """
    attr_class = HashedResizedImageFieldFile
