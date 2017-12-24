from django.apps.config import AppConfig
import requests,datetime,sys
import pytz
from datetime import datetime, timedelta

TIME_ZONE = pytz.timezone('Europe/Paris')
class ObjConfig(AppConfig):
	name = 'objRequests'


