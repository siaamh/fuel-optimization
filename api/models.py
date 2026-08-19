from django.db import models

# Create your models here.
class FuelStation(models.Model):
    opis_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=4
    )
    latitude = models.FloatField()
    longitude = models.FloatField()