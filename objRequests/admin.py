from django.contrib import admin

# Register your models here.
from .models import Device,Mesure,Trajet, Dump

admin.site.register(Device)
admin.site.register(Trajet)
admin.site.register(Dump)
class MesureAdmin(admin.ModelAdmin):
   list_display   = ( 'timestamp','latitude','longitude', 'trajet','count','vitesse_limite','acceleration')
   list_filter    = ('trajet','count',)
   date_hierarchy = 'timestamp'
   ordering       = ('-timestamp', )
   search_fields  = ('timestamp',)

admin.site.register(Mesure,MesureAdmin)
