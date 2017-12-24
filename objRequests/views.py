from django.shortcuts import render, HttpResponse, get_object_or_404, redirect, reverse
from objRequests.models import Mesure, Device, Dump, Trajet
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from objRequests.forms import LoginForm, PaginationForm
from django.contrib.auth import authenticate, login
import binascii
import json
import datetime,json
from statistics import variance, mean
import  django.utils.timezone as tmzone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage,PageNotAnInteger
from graphos.sources.simple import SimpleDataSource
from graphos.renderers.gchart import LineChart
from django import template
from math import sqrt
register = template.Library()


##Paramètres de notation

def param_acc(accs):
    try :
        var = variance(accs)
        if var<=25 :
            param_acc = 10-variance(accs)/2.5
        else : 
            param_acc = 0
    except :
        param_acc = None
    return(param_acc)


def param_vit(speeds,limites_no_none):
    ratio_depassement_total = 0
    pas_de_limite=0
    for j in range(len(speeds)):
        try :
            if speeds[j]>limites_no_none[j]:
                ratio_depassement_total+=(speeds[j]-limites_no_none[j])/limites_no_none[j]
        except :
            pas_de_limite+=1

    if pas_de_limite != len(speeds):
        param_vit = ratio_depassement_total/(len(speeds)-pas_de_limite)
        param_vit = (10*(1-param_vit/0.2))
    else :
        param_vit = None
    return (param_vit)

def param_vir(lacets,accs):
    virages = 0
    virages_dangereux = 0
    try :
        for i in range(len(lacets)):
            if lacets[i] and accs[i]:
                if lacets[i] > 10 :
                    virages +=1
                if lacets [i] * accs [i] > 700 :
                    virages_dangereux +=1
        if virages !=0 :
            param_vir =  (1-virages_dangereux/virages)*10
        else :
            param_vir = 10
    except : 
        param_vir = None
    return(param_vir)

def param_rpm(rpms):
    seuil_min = 300**2
    seuil_max = 800**2
    try :
        var = variance(rpms)
        if var<=seuil_min:
            param_rpm=10
        elif var>=seuil_max:  
            param_rpm = 0
        else:
            param_rpm =10/(seuil_min-seuil_max) * (var - seuil_max)
    except :
        param_rpm = None
    return(param_rpm)

##Notes

def note_ecoconduite(p_acc,p_rpm):
    if (p_rpm != None) & (p_acc != None) :
        note = 0.7*p_rpm + 0.3*p_acc
    elif p_acc != None :
        note = p_acc
    elif p_rpm != None :
        note = p_rpm
    else : 
        note = None
    return (note)

def note_securite(p_vit,p_acc):
    if (p_acc != None) & (p_vit != None) :
        note = 0.5*p_vit + 0.5*p_acc
    elif p_acc!=None :
        note = p_acc
    elif p_vit!=None :
        note = p_vit
    else : 
        note = None
    return (note)

def note_confort(p_vir,p_acc):
    if (p_acc != None) & (p_vir != None) :
        note = 0.7*p_vir + 0.3*p_acc
    elif p_acc!= None :
        note = p_acc
    elif p_vir!= None :
        note = p_vir
    else : 
        note = None
    return (note)

def note_vitesse(p_vit):
    return(p_vit)

def note_globale(note_eco,note_secu,note_conf,note_vit):
    notes = [note_eco,note_secu,note_conf,note_vit]
    notes_no_none = []
    try :
        for note in notes:
            if note != None :
                notes_no_none.append(note)

        return(mean(notes_no_none))
    except : 
        return(None)

@register.inclusion_tag('objRequests/menu.html')
def show_menu():
    devices= Device.objects.all()
    return {'devices':devices}
@register.filter_function
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)
key_maps = 'AIzaSyC5Js3A2ykOhdy5ssY6BxkZBNy3a4oKQ_k'
@csrf_exempt
def message_reception(request):
    data = json.loads(str(request.body, 'utf-8'))
    device, created = Device.objects.get_or_create(device_id=int(data['device_id']))
        
    tmstamp = data['timestamp'].split('.')[0]
    m_type = data['type']
    message = data
    continuite = False
    beign = datetime.datetime.now()
    if m_type =='uplink':
      #try :
        data = data['payload_cleartext']
        lat = int(data[:8],16)/1000000
        lng = int(data[8:16],16)/1000000
        speeds = [int(data [16:18], 16), int(data [18:20], 16), int(data [20:22], 16), int(data [22:24], 16), int(data [24:26], 16)]
        rpms = [64*int(data [26:28], 16), 64*int(data [28:30], 16), 64*int(data [30:32], 16), 64*int(data [32:34], 16), 64*int(data [34:36], 16)]
        loads =[int(data [36:38], 16), int(data [38:40], 16), int(data [40:42], 16),int(data [42:44], 16), int(data [44:46], 16)]
        mafs =[4*int(data [46:48], 16), 4*int(data [48:50], 16), 4*int(data [50:52], 16), 4*int(data [52:54], 16), 4*int(data [54:56], 16)]
        cf = 128*16000**2/(9.81**2)
        accs =[sqrt(int(data [56:58], 16)/cf), sqrt(int(data [58:60], 16)/cf), sqrt(int(data [60:62], 16)/cf), sqrt(nt(data [62:64], 16)/cf), sqrt(int(data [64:66], 16)/cf)]
        lacets =[128*int(data [66:68], 16), 128*int(data [68:70], 16), 128*int(data [70:72], 16), 128*int(data [72:74], 16), 128*int(data [74:76], 16)]
        try :
            latest_m = Mesure.objects.filter(count=1).latest('timestamp')
            begin = latest_m.timestamp-datetime.timedelta (seconds = 8)
        except Exception as e:
            pass
        count = message['count']
        nouveau_trajet = False
        if count == 1 :
            nouveau_trajet = True
        for j in range(len(speeds)):
                if nouveau_trajet :
                    sys.stderr.write(tmstamp[:-1])
                    trj,created_trj= Trajet.objects.get_or_create(debut = tmzone.make_aware(datetime.datetime.strptime(tmstamp, '%Y-%m-%dT%H:%M:%S'),timezone = tmzone.get_current_timezone()),device = device)
                    if not (created_trj):
                        trj.save()
                    tsp = tmzone.make_aware(datetime.datetime.strptime(tmstamp[:-1], '%Y-%m-%dT%H:%M:%S')+ datetime.timedelta (seconds = j*2),timezone = tmzone.get_current_timezone())
                    mesure,created = Mesure.objects.get_or_create(device=device,
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
                                trajet = trj
                           )
                    if not (created):
                        mesure.save()
                else :
                    trj2=Trajet.objects.filter(device = device).last()
                    tsp2 = begin + datetime.timedelta (seconds = (count-1)*10+j*2)
                    mesure, created  = Mesure.objects.get_or_create(device=device,
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
                                count = count 
                           )
                    if not (created):
                        mesure.save()
    #except Exception as e:
    #exc_type, exc_obj, exc_tb = sys.exc_info()
    #Dump(content=data).save()
    return HttpResponse("")



def login_view(request):
    error = False
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
            else:
                error = True
    else:
        form = LoginForm()

    return render(request, 'objRequests/login_form.html', locals())


@login_required
def index_view(request):
    return redirect(reverse('objRequests:devices'))


@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse('objRequests:login_view'))


@login_required
def devices_index(request):
    devices = Device.objects.all()
    return render(request, 'objRequests/devices_index.html',  locals())

@login_required
def messages_index(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    messages = Mesure.objects.filter(device=device)
    return render(request, 'objRequests/messages_index.html', locals())


@login_required
def trajet(request,trajet_id,page = 1):
    if request.method == "POST":
        form = PaginationForm(request.POST)
        if form.is_valid():
            page = form.cleaned_data["page"]
            return redirect(reverse('objRequests:trajet', kwargs={'trajet_id':trajet_id,'page':page}))
    else:
        form = PaginationForm()
    trajet = get_object_or_404(Trajet, id = trajet_id)
    mesures = Mesure.objects.all().filter(trajet = trajet).order_by('timestamp')
    mesures_pag = Paginator(mesures,10)
    carte_non_dispo = False
    graphe1_non_dispo = False
    graphe2_non_dispo = False

    ## Pagination

    try :
        mesures = mesures_pag.page(page)
    except PageNotAnInteger :
        mesures = mesures_pag.page(1)
    except EmptyPage:
        mesures = mesures_pag.page(mesures_pag.num_pages)
        ##print(mesures)
    try :
        lat_debut = Mesure.objects.filter(Q(trajet = trajet)&~Q(latitude=0)&~Q(longitude=0)).first().latitude
        long_debut = Mesure.objects.filter(Q(trajet = trajet)&~Q(latitude=0)&~Q(longitude=0)).first().longitude
        lat_fin = Mesure.objects.filter(Q(trajet = trajet)&~Q(latitude=0)&~Q(longitude=0)).last().latitude
        long_fin = Mesure.objects.filter(Q(trajet = trajet)&~Q(latitude=0)&~Q(longitude=0)).last().longitude
        
    except :
        carte_non_dispo = True
    if trajet.mesure_set.count() <15 :
        carte_non_dispo =True


    rpms = list(Mesure.objects.filter(trajet = trajet).values_list('rpm'))
    rpms =[item[0] for item in rpms if item[0]]
    limites = list(Mesure.objects.filter(trajet = trajet).values_list('vitesse_limite'))
    lim =limites
    limites =[item[0] for item in limites ]
    limites_no_none =[item[0] for item in lim if item[0] ]
    accs = list(Mesure.objects.filter(trajet = trajet).values_list('acceleration'))
    accs =[item[0] for item in accs ]
    lacets = list(Mesure.objects.filter(trajet = trajet).values_list('lacet'))
    lacets =[item[0] for item in lacets ]
    speeds = list(Mesure.objects.filter(trajet = trajet).values_list('speed'))
    speeds =[item[0] for item in speeds ]
    mafs = list(Mesure.objects.filter(trajet = trajet).values_list('maf'))
    mafs =[item[0] for item in mafs ]
    loads = list(Mesure.objects.filter(trajet = trajet).values_list('load'))
    loads =[item[0] for item in loads ]
    
    ## Diesel ou essence
    try : 
        if mafs[0] != None :
            carburant = "Diesel"
        else : 
            carburant = "essence"
    except :
        carburant = "essence"

    ## Paramètres
    p_acc=param_acc(accs)
    p_vit=param_vit(speeds,limites_no_none)
    p_vir=param_vir(lacets,accs)
    p_rpm=param_rpm(rpms)

    note_eco = note_ecoconduite(p_acc,p_rpm)
    note_secu = note_securite(p_vit,p_acc)
    note_conf = note_confort(p_vir,p_acc)
    note_vit = note_vitesse(p_vit)
    note_glob = note_globale(note_eco,note_secu,note_conf,note_vit)

    ## Note éco 
    if note_eco != None :
        progress_bar_eco = "width:"+str(note_eco*10)+"%"
        trajet.note_eco = round(note_eco,2) 
        trajet.save()
        if note_eco < 2:
            message_eco = "L'environnement a beaucoup souffert de ce trajet"
        elif note_eco>=2 and note_eco<4 :
            message_eco = "Ce trajet ne respecte pas les critères de l'éco-conduite..."
        elif note_eco>=4 and note_eco<6 :
            message_eco = "Éco-conduite initiée, mais imparfaite"
        elif note_eco>=6 and note_eco<8 :
            message_eco = "Éco-conduite acceptable mais perfectible"
        else : 
            message_eco = "La planète remercie le chauffeur de ce trajet"
    else :
        progress_bar_eco = "width: 0%"
        message_eco = "Note non-disponible"
    
    ## Note secu

    if note_secu != None :
        trajet.note_secu = round(note_secu,2)
        trajet.save()
        if note_secu < 2:
            message_secu = "Le trajet a été très dangereux"
        elif note_secu>=2 and note_secu<4 :
            message_secu = "Ce trajet ne respecte pas les critères de sécurité ..."
        elif note_secu>=4 and note_secu<6 :
            message_secu = "Attention aux fortes accélérations et aux coups de freins"
        elif note_secu >=6 and note_secu<8 :
            message_secu = "Sécurité acceptable mais perfectible"
        else : message_secu = "Conduite sûre"
     
        progress_bar_secu = "width:"+str(note_secu*10)+"%"
    else :
        progress_bar_secu = "width: 0%"
        message_secu = "Note non-disponible"
 
    ## Note confort

    if note_conf !=None :
        trajet.note_conf = round(note_conf,2)
        trajet.save()
        progress_bar_conf= "width:"+str(note_conf*10)+"%"
        if note_conf < 2:
            message_conf = "Le trajet a été très inconfortable"
        elif note_conf>=2 and note_conf<4 :
            message_conf = "Ce trajet ne respecte pas les critères de confort ..."
        elif note_conf>=4 and note_conf<6 :
            message_conf = "Confort de conduite initié, mais imparfaite"
        elif note_conf >=6 and note_conf<8 :
            message_conf = "Confort acceptable mais perfectible"
        else : message_conf = "Conduite confortable"
    else :
        progress_bar_conf = "width: 0%"
        message_conf ='Note non-disponible'
    
    ##Note vitesse

    if note_vit != None:
        trajet.note_vit = round(note_vit,2)
        trajet.save()
        if note_vit < 2 :
            message_vit = "Les limitations de vitesses n'ont pas été respectées"
        elif note_vit>=2 and note_vit<4 :
            message_vit = "Ce trajet ne respecte pas le code de la route ..."
        elif note_vit>=4 and note_vit<6 :
            message_vit = "Respect des limitations de vitesse initié mais imparfait"
        elif note_vit >=6 and note_vit<8 :
            message_vit = "Conduite à allure mesurée mais perfectible"
        else : message_vit = "Conduite respectant les limitations de vitesse"

        progress_bar_vit = "width:"+str(note_vit*10)+"%"

    else :
        progress_bar_vit = "width: 0%"
        message_vit = "Note non-disponible"

    if note_glob != None:
        trajet.note_glob = round(note_glob,2)
        trajet.save()
        if note_glob < 2 :
            message_glob = "Conduite inacceptable"
            logo_glob = "fa fa-warning"
        elif note_glob>=2 and note_glob<4 :
            logo_glob = "fa fa-thumbs-down"
            message_glob = "Mauvaise conduite"
        elif note_glob>=4 and note_glob<6 :
            message_glob = "Conduite moyenne"
            logo_glob = "fa fa-meh-o"
        elif note_glob >=6 and note_glob<8 :
            message_glob = "Bonne conduite"
            logo_glob = "fa fa-thumbs-up"
        else : 
            message_glob = "Excellente conduite"
            logo_glob = "fa fa-star"


        progress_bar_glob = "width:"+str(note_glob*10)+"%"

    else :
        progress_bar_glob = "width: 0%"
        message_glob = "Note non-disponible"    

    ##Graphique et info map
   
    latitudes = list(Mesure.objects.filter(trajet = trajet).values_list('latitude'))
    latitudes = [item[0] for item in latitudes if item[0]!=0]
    longitudes = list(Mesure.objects.filter(trajet = trajet).values_list('longitude'))
    longitudes = [item[0] for item in longitudes if item[0]!=0]
    len_lat =len(latitudes)
    dates = list(Mesure.objects.filter(trajet = trajet).values_list('timestamp'))
    dates =[item[0]+datetime.timedelta(hours=2) for item in dates]
    

    #data1 = [['date','Vitesse (en km/h)', 'Accélération² (en (m/s²)²)','Limitation de vitesse (en km/h) ']]
 
    data1 = [['date','V', 'L']]
    for i in range(len(dates)):
        ##print(i)
        data1.append( [str(dates[i])[10:16],speeds[i],limites[i]])
    if len(data1)==1 :
        graphe1_non_dispo =True

    data2 = [['date','rpms (en tr/min)']]
    for i in range(len(rpms)):
        data2.append( [str(dates[i])[10:16],rpms[i]])
    if len(data2) ==1:
        graphe2_non_dispo =True

    data3 = [['date','M', 'C']]
    for i in range(len(rpms)):
        data3.append( [str(dates[i])[10:16],mafs[i], loads[i]])
    if len(data3) ==1:
        graphe3_non_dispo =True

    data4 = [['date','A']]
    for i in range(len(dates)):
        ##print(i)
        data4.append( [str(dates[i])[10:16],sqrt(accs[i])])
    if len(data4)==1 :
        graphe4_non_dispo =True

    data5 = [['date', 'lacet (en rad/s)']]
    for i in range(len(dates)):
        data5.append( [str(dates[i])[10:16], lacets[i]])
    if len(data5) ==1:
        graphe5_non_dispo =True

    ###print(graphe1_non_dispo, graphe2_non_dispo,data1,data2,'data')
    #print(data1)
    chart1 = LineChart(SimpleDataSource(data=data1),options={'title': 'Vitesse (km/h) et limitation (km/h)','explorer': { 
    'actions': ['dragToZoom', 'rightClickToReset'],
    'axis': 'vertical',
    'maxZoomIn': '10.0'},
        'legend':{'position': 'bottom'},
        'width':'600',
        'height':'400',
        
    })


    chart2 = LineChart(SimpleDataSource(data=data2),options={'title': 'Régime moteur','explorer': { 
            'actions': ['dragToZoom', 'rightClickToReset'],
            'keepInBounds': 'true',
            'maxZoomIn': '10.0'},
        'legend':{'position': 'bottom'},
        'width':'600',
        'height':'400'
    })

    chart3 = LineChart(SimpleDataSource(data=data3),options={'title': 'M (g/s) et C (%)','explorer': {
        'maxZoomOut':'10.0',
        'keepInBounds': 'true'},
        'legend':{'position': 'bottom'},
        'width':'600',
        'height':'400'
    })

    chart4 = LineChart(SimpleDataSource(data=data4),options={'title': 'Accélération (m/s²)','explorer': {
        'maxZoomOut':'10.0',
        'keepInBounds': 'true'},
        'legend':{'position': 'bottom'},
        'width':'600',
        'height':'400'
    })

    chart5 = LineChart(SimpleDataSource(data=data5),options={'title': 'Lacet (°/s)','explorer': {
        'maxZoomOut':'10.0',
        'keepInBounds': 'true'},
        'legend':{'position': 'bottom'},
        'width':'600',
        'height':'400'
    })

    if len(latitudes)!=0:
        pas =int(len(latitudes)/23)
        json_latitudes = json.dumps([latitudes[pas*i] for i in range(23)] )
        json_longitudes = json.dumps([longitudes[pas*i] for i in range(23)] )
        json_mesures =json.dumps([ list(mesures.object_list.values_list('latitude', flat=True))[0],list(mesures.object_list.values_list('longitude', flat=True))[0] ])
    else :
        json_latitude =[]
        json_longitude = []
        json_mesures =[]
    return render(request, 'objRequests/trajet.html',locals())


@login_required
def trajets_index(request, device_id, page=1):
    device = get_object_or_404(Device, id=device_id)
    trajets = device.trajet_set.order_by("-id").all()
    pas_trajet = False
    if request.method == "POST":
        form = PaginationForm(request.POST)
        if form.is_valid():
            page = form.cleaned_data["page"]
            return redirect(reverse('objRequests:trajet_inde', kwargs={'trajet_id':device_id,'page':page}))
    else:
        form = PaginationForm()
    for trajet in trajets :
        if not (trajet.vitesse_moyenne):
            vitesses = [item[0] for item in Mesure.objects.filter(Q(trajet = trajet)&~Q(speed =None)).values_list('speed')]
            if vitesses !=[]:
                trajet.vitesse_moyenne = round(mean(vitesses),2)
                trajet.save()
       
        duree = str(Mesure.objects.filter(Q(trajet = trajet)).last().timestamp-Mesure.objects.filter(Q(trajet = trajet)).first().timestamp)

        if duree != '0:00:00':
            trajet.duree = duree
            trajet.save()

        if  trajet.vitesse_moyenne:

            try :
                seconde = int(trajet.duree[-2:])
                
            except Exception as e:

                seconde = 0
            try :
                minute = int(trajet.duree[-5:-3])
                
            except :
                minute = 0
            try :
                heure = int(trajet.duree[:-6])

                
            except :
                heure = 0

            trajet.distance = round((seconde/3600+minute/60+heure)*trajet.vitesse_moyenne,4)

            trajet.save()
            

        rpms = list(Mesure.objects.filter(trajet = trajet).values_list('rpm'))
        rpms =[item[0] for item in rpms if item[0]]
        limites = list(Mesure.objects.filter(trajet = trajet).values_list('vitesse_limite'))
        lim =limites
        limites =[item[0] for item in limites ]
        limites_no_none =[item[0] for item in lim if item[0]]
        accs = list(Mesure.objects.filter(trajet = trajet).values_list('acceleration'))
        accs =[item[0] for item in accs ]
        lacets = list(Mesure.objects.filter(trajet = trajet).values_list('lacet'))
        lacets =[item[0] for item in lacets ]
        speeds = list(Mesure.objects.filter(trajet = trajet).values_list('speed'))
        speeds =[item[0] for item in speeds ]    


        ## Paramètres
        p_acc=param_acc(accs)
        p_vit=param_vit(speeds,limites_no_none)
        p_vir=param_vir(lacets,accs)
        p_rpm=param_rpm(rpms)


        ## Note éco 
        
        try :
            note_eco = note_ecoconduite(p_acc,p_rpm)
            trajet.note_eco = round(note_eco,2) 
            trajet.save()
        except :
            note_eco =None


        ## Note secu
        try :
            accs = list(Mesure.objects.filter(trajet = trajet).values_list('acceleration'))
            accs =[item[0] for item in accs ]
            note_secu = note_securite(p_vit,p_acc)
            trajet.note_secu = round(note_secu,2)
            trajet.save()    
        except :
            note_secu = None

        ## Note confort
        note_conf = note_confort(p_vir,p_acc)
        try :
            trajet.note_conf = round(note_conf,2)
            trajet.save()
        except :
            note_conf = None
            
        ##Note vitesse
        note_vit = note_vitesse(p_vit)
        try : 
            trajet.note_vit = round(note_vit,2)
            trajet.save()
        except : 
            note_vit = None

        note_glob = note_globale(note_eco,note_secu,note_conf,note_vit)
        try : 
            trajet.note_glob = round(note_glob,2)
            trajet.save()
        except : 
            note_glob = None


    
    if Trajet.objects.filter(device=device).order_by('-id').count() >2: 
        notes_eco = list(Trajet.objects.values_list('note_eco'))
        notes_conf = list(Trajet.objects.values_list('note_conf'))
        notes_vit = list(Trajet.objects.values_list('note_vit'))
        notes_secu = list(Trajet.objects.values_list('note_secu'))
        notes_glob = list(Trajet.objects.values_list('note_glob'))
        dates = list(Trajet.objects.values_list('debut'))
        dates = [item[0] for item in dates]
        notes_eco =[item[0] for item in notes_eco]
        notes_conf =[item[0] for item in notes_conf]
        notes_vit =[item[0] for item in notes_vit]
        notes_secu =[item[0] for item in notes_secu]
        notes_glob=[item[0] for item in notes_glob]


        data2 = [['date','Note écoconduite', 'Note confort', 'Note vitesse','Note sécurité']]
        ##print(notes_eco)
        for i in range(len(notes_eco)):
            data2.append( [str(dates[i])[:10],notes_eco[i],notes_conf[i],notes_vit[i],notes_secu[i]])
        if len(data2) ==1:
            graphe2_non_dispo =True
        #print(data2)
        chart2 = LineChart(SimpleDataSource(data=data2),options={'title': 'Notes en fonction du temps','explorer': {
            'maxZoomOut':2,
            'axis': 'horizontal',
            'keepInBounds': 'true'},
            'legend':{'position': 'bottom'},
            'width':'600',
            'height':'400'
        })
        var_note_eco =round(10*(Trajet.objects.filter(device=device).order_by('-id')[0].note_eco-Trajet.objects.filter(device=device).order_by('-id')[1].note_eco),2)
        var_note_vit =round(10*(Trajet.objects.filter(device=device).order_by('-id')[0].note_vit-Trajet.objects.filter(device=device).order_by('-id')[1].note_vit),2)
        var_note_conf =round(10*(Trajet.objects.filter(device=device).order_by('-id')[0].note_conf-Trajet.objects.filter(device=device).order_by('-id')[1].note_conf),2)
        var_note_secu =round(10*(Trajet.objects.filter(device=device).order_by('-id')[0].note_secu-Trajet.objects.filter(device=device).order_by('-id')[1].note_secu),2)
        var_note_glob =round(10*(Trajet.objects.filter(device=device).order_by('-id')[0].note_glob-Trajet.objects.filter(device=device).order_by('-id')[1].note_glob),2)
    else :
        pas_trajet = True

    pag = Paginator(trajets,10)
     ## Pagination

    try :
        trajets = pag.page(page)
    except PageNotAnInteger :
        trajets = pag.page(1)
    except EmptyPage:
        trajets = pag.page(mesures_pag.num_pages)
        ##print(mesures)
    return render(request, 'objRequests/trajet_index.html', locals())

    





