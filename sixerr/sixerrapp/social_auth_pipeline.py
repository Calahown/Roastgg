from .models import Profile
from django.contrib.staticfiles.templatetags.staticfiles import static
import stripe
import json
import random

def save_avatar(backend,user,response,*args,**kwargs):
    try:
        profile = Profile.objects.get(user_id=user.id)
    except Profile.DoesNotExist:
        profile = Profile(user_id=user.id)

    if backend.name == 'facebook':
        profile.avatar = 'https://graph.facebook.com/%s/picture?width=400&height=400 ' % response['id']
        if not profile.displayname:
            if Profile.objects.get(displayname=user.username):
                user.username = user.username + str(random.randint(1,999999))
            profile.displayname = user.username

        if profile.vanitymail == "replace.me@roast.gg":
            if user.email != None:
                profile.vanitymail = user.email

    if backend.name == 'twitch':
        if not profile.displayname:
            if Profile.objects.get(displayname=user.username):
                user.username = user.username + str(random.randint(1,999999))
            profile.displayname = user.username

        if profile.vanitymail == "replace.me@roast.gg":
            if user.email != None:
                profile.vanitymail = user.email

        if response['logo']:
            profile.avatar = response['logo']
        else:
            profile.avatar = static('img/twitch_upload_placeholder.png')

        if profile.vanitymail == "replace.me@roast.gg":
            if user.email != None:
                profile.vanitymail = user.email

    if backend.name == 'stripe':
        if response['stripe_user_id']:
            connect_user_id = response['stripe_user_id']
            profile.stripe=connect_user_id
            profile.striperefresh= response['refresh_token']

    profile.save()
