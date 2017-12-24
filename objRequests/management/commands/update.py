from django.core.management.base import BaseCommand, CommandError
from objRequests.models import Device, Dump, Trajet, Mesure
import django.utils.timezone as tmzone
import requests,datetime,sys
import pytz
from datetime import datetime, timedelta


TIME_ZONE = pytz.timezone('Europe/Paris')
class Command(BaseCommand):
  help = 'Get last data from objenious'


  def handle(self, *args, **options):
    r_vit = None
    print('')
    print('Initialisation de la bas de donnee', end='\n')
    url = 'https://api.objenious.com/v1/devices'
    url_vit = 'http://route.st.nlp.nokia.com/routing/7.2/getlinkinfo.json?app_id=DemoAppId01082013GAL&app_code=AJKnXv84fjrb0KIHawS0Tg' 
    headers = {'apikey' : 'VBOw9QjJfj0UTzuZq1rhtnr3Uoxk376LKfHdh16BG2LZrnSTQWsrncaN+DWnweVG5Ul6MQ5h+z1ifqSS8J+poA==  '}
    #     params ={'since':'2017-05-31T00:00:00Z', 'limit': '150000'}
    params ={'since':(datetime.now()-timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"), 'limit': '150000'}
#    print((datetime.now()-timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    r = requests.get(url,headers = headers)
    devices = r.json()
    for k in range(len(devices)):
      device_id = int(devices [k] ['id'])
      nom = devices [k] ['label']
      device,d_created=Device.objects.get_or_create(device_id=device_id,nom = nom)
      if not (d_created):
        device.save()
      #print('device : ',device_id)
      response = requests.get(url+'/'+str(device_id)+'/messages', headers=headers,params=params)
      print(response)
      messages = response.json()['messages']
      messages = list(reversed(messages))

      for i in range(len(messages)):
        vitesse_limite = None
        tmstamp = messages [i] ['timestamp']

        m_type = messages [i] ['type']
        continuite = False
        beign = datetime.now()

        if m_type =='uplink':
          if len(messages [i]['payload_cleartext'])<=78:
            try :
              data = messages [i]['payload_cleartext']
              lat = int(data[:8],16)/1000000
              lng = int(data[8:16],16)/1000000
              speeds = [int(data [16:18], 16), int(data [18:20], 16), int(data [20:22], 16), int(data [22:24], 16), int(data [24:26], 16)]
              rpms = [32*int(data [26:28], 16), 32*int(data [28:30], 16), 32*int(data [30:32], 16), 32*int(data [32:34], 16), 32*int(data [34:36], 16)]
              loads =[int(data [36:38], 16), int(data [38:40], 16), int(data [40:42], 16),int(data [42:44], 16), int(data [44:46], 16)]
              mafs =[4*int(data [46:48], 16), 4*int(data [48:50], 16), 4*int(data [50:52], 16), 4*int(data [52:54], 16), 4*int(data [54:56], 16)]
              cf = 128*16000**2/(9.81**2)
              accs =[int(data [56:58], 16)/cf, int(data [58:60], 16)/cf, cf*int(data [60:62], 16)/cf,int(data [62:64], 16)/cf,int(data [64:66], 16)/cf]
              lacets =[int(data [66:68], 16), int(data [68:70], 16), int(data [70:72], 16), int(data [72:74], 16), int(data [74:76], 16)]
              message_ok =data[76:78]
              if message_ok =='2f':
                try :
                  latest_m = Mesure.objects.filter(count=1).latest('timestamp')
                  begin = latest_m.timestamp-timedelta (seconds = 8)

                except Exception as e:
                  exc_type, exc_obj, exc_tb = sys.exc_info()
                  print(e,exc_tb.tb_lineno)
                  pass
                count = messages [i] ['count']
                nouveau_trajet = False
                if count == 1 :
                  nouveau_trajet = True
                #print(count)
                if lat !=0 and lng !=0 :
                  params_vit ={'waypoint' : str(lat)+','+str(lng)}
                  r_vit = requests.get(url = url_vit, params = params_vit)
                  r_vit = r_vit.json()
                  vitesse_limite =int(r_vit['response']['link'][0]['speedLimit']*3.6)
                for j in range(len(speeds)):
                  if (lng==0 or lat==0) and not(count==1):
                    break
                  if speeds [j] == 255:
                    speeds [j] = None
                  if rpms [j] == 224 :
                    rpms [j] = None
                  if mafs [j] == 252 :
                    mafs [j] = None
                  if loads [j] == 255 :
                    loads [j] = None
              
                  if nouveau_trajet :
                    trj,created_trj= Trajet.objects.get_or_create(debut = tmzone.make_aware(datetime.strptime(tmstamp[:-1], '%Y-%m-%dT%H:%M:%S')+timedelta(hours=2),timezone = TIME_ZONE),device = device)
                    if not (created_trj):
                      trj.save()
                    tsp = tmzone.make_aware(datetime.strptime(tmstamp[:-1], '%Y-%m-%dT%H:%M:%S')+ timedelta (hours=2,seconds = j*2),timezone =TIME_ZONE)
                    print(tsp)
                    mesure,created = Mesure.objects.get_or_create(
                                timestamp = tsp,
                                latitude = lat,
                                longitude = lng,
                                speed = speeds [j],
                                rpm = rpms [j],
                                load = loads [j],
                                maf=mafs [j],
                                acceleration = accs [j],
                                lacet = lacets [j],
                                count = count,
                                trajet = trj,
                                vitesse_limite = vitesse_limite
                           )
                    if not (created):
                      mesure.save()
                  else :
                    trj2=Trajet.objects.get(debut = begin, device = device)
                    tsp2 = begin + timedelta (seconds = (count-1)*10+j*2)

                    if list(Mesure.objects.filter(
                                latitude = lat,
                                longitude = lng,
                                speed = speeds [j],
                                rpm = rpms [j],
                                load = loads [j],
                                maf = mafs [j],
                                acceleration = accs [j],
                                lacet = lacets [j],
                                count = count,
                                vitesse_limite = vitesse_limite)) ==[]:
                      mesure, created  = Mesure.objects.get_or_create(
                                  timestamp = tsp2 ,
                                  latitude = lat,
                                  longitude = lng,
                                  speed = speeds [j],
                                  rpm = rpms [j],
                                  load = loads [j],
                                  maf = mafs [j],
                                  acceleration = accs [j],
                                  lacet = lacets [j],
                                  trajet = trj2,
                                  count = count,
                                  vitesse_limite = vitesse_limite
                             )
                      if not (created):
                        mesure.save()
              else :
                print('message decale')

            except Exception as e:
              exc_type, exc_obj, exc_tb = sys.exc_info()
              print(e,exc_tb.tb_lineno)
              Dump(content=data).save()
            print('Nombre de mesures :',Mesure.objects.count())

