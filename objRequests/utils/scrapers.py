from ..models import Devices
import datetime
from django.db.models import Max
from django.contrib.auth.models import User
from django.utils import timezone
import requests
def scraper_example():
     payload = {'apikey' : 'VBOw9QjJfj0UTzuZq1rhtnr3Uoxk376LKfHdh16BG2LZrnSTQWsrncaN+DWnweVG5Ul6MQ5h+z1ifqSS8J+poA==     '}
     res = False
     r = requests.get('https://api.objenious.com/v1/devices', headers=payload)
     for i in range(len(r.json())) :
     	rep=Devices.objects.get_or_create(nom=r.json()[i]['label'])
     	if rep[1]==True:
     		res=True
     return res
