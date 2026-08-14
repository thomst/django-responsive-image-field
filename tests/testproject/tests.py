import os
from django.core.files.base import File
from django.db import models
from django.conf import settings
from django.test import TestCase
from responsive_image_field.utils import get_md5_hash
from .models import TestModel


# Using a relative path to prevent a SuspiciousFileOperation exception.
TEST_IMAGE = os.path.relpath(settings.MEDIA_ROOT / 'test-image-200x200.png')


class SetupImageFieldsMixin:

    @staticmethod
    def get_image_fields(obj):
        return [f for f in obj._meta.fields if isinstance(f, models.ImageField)]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.obj = TestModel()
        for field in cls.get_image_fields(cls.obj):
            with open(TEST_IMAGE, 'rb') as img:
                setattr(cls.obj, field.name, File(img))
        cls.obj.save()

    @classmethod
    def tearDownClass(cls):
        for field in cls.get_image_fields(cls.obj):
            getattr(cls.obj, field.name).delete()
        cls.obj.delete()
        del cls.obj
        super().tearDownClass()


class Test(SetupImageFieldsMixin, TestCase):

    def test_resized(self):
        image = self.obj.resized
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 150)
        self.assertEqual(image.height, 150)

    def test_resized_width_and_height(self):
        images = self.obj.resized_width, self.obj.resized_height
        for image in images:
            self.assertTrue(image.name.endswith('png'))
            self.assertEqual(image.width, 100)
            self.assertEqual(image.height, 100)

    def test_resized_converted(self):
        image = self.obj.resized_converted
        self.assertTrue(image.name.endswith('avif'))
        self.assertEqual(image.width, 120)
        self.assertEqual(image.height, 120)

    def test_not_resized_converted(self):
        image = self.obj.not_resized_converted
        self.assertTrue(image.name.endswith('avif'))
        self.assertEqual(image.width, 200)
        self.assertEqual(image.height, 200)

    def test_not_resized_not_converted(self):
        image = self.obj.not_resized_not_converted
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 200)
        self.assertEqual(image.height, 200)

    def test_quality(self):
        high, low = self.obj.converted_high_quality, self.obj.converted_low_quality
        for image in (high, low):
            self.assertTrue(image.name.endswith('avif'))
            self.assertEqual(image.width, 120)
            self.assertEqual(image.height, 120)
        high_size = os.path.getsize(high.path)
        low_size = os.path.getsize(low.path)
        self.assertGreater(high_size, low_size)

    def test_hashed_resized(self):
        image = self.obj.hashed_resized
        hash = get_md5_hash(image)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 120)
        self.assertEqual(image.height, 120)

    def test_hashed(self):
        image = self.obj.hashed
        hash = get_md5_hash(image)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 200)
        self.assertEqual(image.height, 200)
