from django.contrib import admin
from .models import Profile, Gig, Purchase, Review, Ranking

# Register your models here.
admin.site.register(Profile)
admin.site.register(Gig)
admin.site.register(Purchase)
admin.site.register(Review)
admin.site.register(Ranking)
