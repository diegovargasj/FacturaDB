import os

from django.db import models

# Create your models here.
from django.db.models import PROTECT

from Facturas.settings import MEDIA_ROOT


class Factura(models.Model):
	path = models.FilePathField()
	file = models.CharField(max_length=50)
	monto = models.IntegerField()
	num = models.CharField(max_length=12)
	client = models.ForeignKey('Client', on_delete=PROTECT)
	fecha = models.DateField()
	fecha_cancelado = models.DateField(default=None)
	pagada = models.BooleanField(default=False)

	def __str__(self):
		print("{}, ${}, {}, {}, {}".format(self.file, self.monto, self.num,
		                                   self.fecha, self.pagada))

	def get_path(self):
		return os.path.normpath(self.path)


class Rut(models.Model):
	digits = models.BigIntegerField(primary_key=True)
	verify = models.CharField(max_length=1)

	def __init__(self, dig, ver, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.digits = int(dig)
		self.verify = ver

	def __str__(self):
		return str(self.digits) + "-" + self.verify


class Client(models.Model):
	name = models.CharField(max_length=128)
	rut = models.OneToOneField('Rut', primary_key=True, on_delete=PROTECT)
