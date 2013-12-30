from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings as django_settings
from cropper import settings
from PIL import Image
import os
import uuid
from storages.backends.s3boto import S3BotoStorage
import  cStringIO, StringIO
import urllib

from django.core.files.uploadedfile import InMemoryUploadedFile

def dimension_validator(image):
    """
    """
    if settings.MAX_WIDTH != 0 and image.width > settings.MAX_WIDTH:
        raise ValidationError(_('Image width greater then allowed'))

    if settings.MAX_HEIGHT != 0 and image.height > settings.MAX_HEIGHT:
        raise ValidationError(_('Image height greater then allowed'))


class Original(models.Model):
    def upload_image(self, filename):
        return u'{path}/{name}.{ext}'.format(path=settings.ROOT,
                                             name=uuid.uuid4().hex,
                                             ext=os.path.splitext(filename)[1].strip('.'))     

    def __unicode__(self):
        return unicode(self.image)

    @models.permalink
    def get_absolute_url(self):
        return 'cropper_crop', [self.pk]

    def save(self, *args, **kwargs):
      storage = self.image.storage
      source_url = self.image.url
      paths = source_url.split('media/')
      if len(paths) > 0:
        target = paths[1]      
        Image.open(source).save(target, quality=quality)
        #storage.save(target, out_image)


    image = models.ImageField(_('Original image'),
                              upload_to=upload_image,
                              width_field='image_width',
                              height_field='image_height',
                              validators=[dimension_validator],
                              storage=S3BotoStorage(location=django_settings.STORAGE_ROOT))

    image_width = models.PositiveIntegerField(_('Image width'),
                                              editable=False,
                                              default=0)
    image_height = models.PositiveIntegerField(_('Image height'),
                                               editable=False,
                                               default=0)


class Cropped(models.Model):
    def __unicode__(self):
        return u'%s-%sx%s' % (self.original, self.w, self.h)

    def upload_image(self, filename):
        return '%s/crop-%s' % (settings.ROOT, filename)

    def save(self, *args, **kwargs):
        storage = S3BotoStorage(location=django_settings.STORAGE_ROOT)
        source_url = self.original.image.url
        filename = os.path.basename(self.original.image.name)
        target = self.upload_image(filename)
	
        fp = urllib.urlopen(source_url)
        source = cStringIO.StringIO(fp.read())

        mod_image = Image.open(source).crop([
            self.x,             # Left
            self.y,             # Top
            self.x + self.w,    # Right
            self.y + self.h     # Bottom
        ])#.save(django_settings.MEDIA_URL + target)

        out_image = StringIO.StringIO()
        out_image.seek(0)
        mod_image.save(out_image, 'JPEG')

        newFile = InMemoryUploadedFile(out_image, None, os.path.basename(target), 'image/jpeg', out_image.len, None)
        storage.save(target, out_image)
        self.image = target

        super(Cropped, self).save(*args, **kwargs)

    original = models.ForeignKey(Original,
                                 related_name='cropped',
                                 verbose_name=_('Original image'))
    image = models.ImageField(_('Image'),
                              upload_to=upload_image,
                              editable=False,
                              storage=S3BotoStorage(location=django_settings.STORAGE_ROOT)
				)
    x = models.PositiveIntegerField(_('offset X'),
                                   default=0)
    y = models.PositiveIntegerField(_('offset Y'),
                                   default=0)
    w = models.PositiveIntegerField(_('cropped area width'),
                                    blank=True,
                                    null=True,
                                    default=0)
    h = models.PositiveIntegerField(_('cropped area height'),
                                    blank=True,
                                    null=True,
                                    default=0)

    class Meta(object):
        verbose_name = _('cropped image')
        verbose_name_plural = _('cropped images')

