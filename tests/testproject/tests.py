import os
from django.core.files.base import File
from django.db import models
from django.conf import settings
from django.test import TestCase
from responsive_image_field.utils import get_md5_hash
from .models import TestModel


# Using a relative path to prevent a SuspiciousFileOperation exception.
TEST_IMAGE = os.path.relpath(settings.BASE_DIR / 'test-image.png')


def save_image_to_field(names):
    def decorator(test):

        def test_wrapper(self):

            # Save images to the fields.
            with open(TEST_IMAGE, 'rb') as img:
                for name in names:
                    setattr(self.obj, name, File(img))
                self.obj.save()

            # Run the test.
            try:
                test(self)
            except:
                raise
            finally:
                # Delete image files and set image fields to None.
                for name in names:
                    field = getattr(self.obj, name).field
                    if hasattr(field, 'fields'):
                        for name_ in field.fields.values():
                            getattr(self.obj, name_).delete()
                            setattr(self.obj, name_, None)
                    getattr(self.obj, name).delete()
                    setattr(self.obj, name, None)
                self.obj.save()

        return test_wrapper

    return decorator


class Test(TestCase):

    def setUp(self):
        self.obj = TestModel()
        self.obj.save()

    def tearDown(self):
        self.obj.delete()

    @save_image_to_field(['resized'])
    def test_resized(self):
        image = self.obj.resized
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 150)
        self.assertEqual(image.height, 150)

    @save_image_to_field(['resized_width', 'resized_height'])
    def test_resized_width_and_height(self):
        images = self.obj.resized_width, self.obj.resized_height
        for image in images:
            self.assertTrue(image.name.endswith('png'))
            self.assertEqual(image.width, 100)
            self.assertEqual(image.height, 100)

    @save_image_to_field(['resized_converted'])
    def test_resized_converted(self):
        image = self.obj.resized_converted
        self.assertTrue(image.name.endswith('avif'))
        self.assertEqual(image.width, 120)
        self.assertEqual(image.height, 120)

    @save_image_to_field(['not_resized_converted'])
    def test_not_resized_converted(self):
        image = self.obj.not_resized_converted
        self.assertTrue(image.name.endswith('avif'))
        self.assertEqual(image.width, 200)
        self.assertEqual(image.height, 200)

    @save_image_to_field(['not_resized_not_converted'])
    def test_not_resized_not_converted(self):
        image = self.obj.not_resized_not_converted
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 200)
        self.assertEqual(image.height, 200)

    @save_image_to_field(['converted_high_quality', 'converted_low_quality'])
    def test_quality(self):
        high, low = self.obj.converted_high_quality, self.obj.converted_low_quality
        for image in (high, low):
            self.assertTrue(image.name.endswith('avif'))
            self.assertEqual(image.width, 120)
            self.assertEqual(image.height, 120)
        high_size = os.path.getsize(high.path)
        low_size = os.path.getsize(low.path)
        self.assertGreater(high_size, low_size)

    @save_image_to_field(['hashed_resized'])
    def test_hashed_resized(self):
        image = self.obj.hashed_resized
        hash = get_md5_hash(image)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 120)
        self.assertEqual(image.height, 120)

    @save_image_to_field(['hashed'])
    def test_hashed(self):
        image = self.obj.hashed
        hash = get_md5_hash(image)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 200)
        self.assertEqual(image.height, 200)

    @save_image_to_field(['hashed_resized_with_dimensions'])
    def test_hashed_resized_with_dimensions(self):
        image = self.obj.hashed_resized_with_dimensions
        hash = get_md5_hash(image)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(self.obj.hashed_resized_width, image.width)
        self.assertEqual(self.obj.hashed_resized_height, image.height)
        self.assertEqual(image.width, 120)
        self.assertEqual(image.height, 120)

    @save_image_to_field(['hashed_with_dimensions'])
    def test_hashed_with_dimensions(self):
        image = self.obj.hashed_with_dimensions
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(self.obj.hashed_with_dimensions_width, image.width)
        self.assertEqual(self.obj.hashed_with_dimensions_height, image.height)

    @save_image_to_field(['resized_with_dimensions'])
    def test_resized_with_dimensions(self):
        image = self.obj.resized_with_dimensions
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(self.obj.resized_with_dimensions_width, image.width)
        self.assertEqual(self.obj.resized_with_dimensions_height, image.height)
        self.assertEqual(image.width, 80)
        self.assertEqual(image.height, 80)

    @save_image_to_field(['responsive'])
    def test_responsive(self):
        image = self.obj.responsive
        self.assertTrue(image.name.endswith('png'))
        self.assertEqual(image.width, 200)
        self.assertEqual(image.height, 200)

        image = self.obj.responsive.large
        hash = get_md5_hash(image)
        self.assertEqual(image, self.obj.responsive_large)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('avif'))
        self.assertEqual(image.width, 150)
        self.assertEqual(image.height, 150)

        image = self.obj.responsive.medium
        hash = get_md5_hash(image)
        self.assertEqual(image, self.obj.responsive_medium)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('avif'))
        self.assertEqual(image.width, 100)
        self.assertEqual(image.height, 100)

        image = self.obj.responsive.small
        hash = get_md5_hash(image)
        self.assertEqual(image, self.obj.responsive_small)
        self.assertTrue(hash in image.name)
        self.assertTrue(image.name.endswith('avif'))
        self.assertEqual(image.width, 50)
        self.assertEqual(image.height, 50)
