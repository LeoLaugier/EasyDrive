from django.db import models

# Create your models here.


class Device(models.Model):
    nom = models.CharField(max_length=100)
    device_id = models.IntegerField()
    def __str__(self):
        return str(self.nom)

class Trajet(models.Model):
    debut = models.DateTimeField()
    device = models.ForeignKey(Device)
    vitesse_moyenne = models.FloatField(null = True)
    duree = models.CharField(max_length=250,null=True)
    puissance = models.FloatField(null = True)
    distance = models.FloatField(null = True)
    note_eco = models.FloatField(null = True)
    note_secu = models.FloatField(null = True)
    note_conf = models.FloatField(null = True)
    note_vit = models.FloatField(null = True)
    note_glob = models.FloatField(null = True)
    def __str__(self):
        return str(self.debut)

class Mesure(models.Model):
    timestamp = models.DateTimeField()
    latitude = models.FloatField(null =True)
    longitude = models.FloatField(null =True)
    speed = models.IntegerField(null=True)
    rpm = models.IntegerField(null =True)
    maf = models.IntegerField(null =True)
    load = models.IntegerField(null=True)
    acceleration = models.FloatField(null =True)
    lacet =  models.IntegerField(null=True)
    trajet = models.ForeignKey(Trajet, null=True)
    count = models.IntegerField()
    vitesse_limite = models.IntegerField(null = True)
    def __str__(self):
        return str(self.timestamp)
class Dump(models.Model):
    content = models.CharField(max_length=250)


