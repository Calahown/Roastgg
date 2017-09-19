from django.forms import ModelForm, ValidationError
from .models import Gig, Profile, Rankverify
# from django.core.exceptions import ValidationError
from django.conf import settings
import json
import re

# *******************
# Initialization code
# TODO: Find a better place for this code
# *******************

# Build 3 lists in memory
# 1 - countries - [ (code1, text1, regionlist1), ... ]
# 2 - available country codes (just for convenience) - [ code1, ... ]
# 3 - all regions by country [ {'country': code1, [ {'code': code1, 'text': text1}, ... ] }, ...]
STATES_DATA_PATH = 'sixerrapp/fixtures/states.json'
countries = []
available_country_codes = []
available_regions_per_country = {}
all_regions = []

with open(STATES_DATA_PATH, encoding='utf-8') as states_data_file:
    states_data = json.load(states_data_file)

for c in states_data['countries']:
    countries.append({'code': c['code'], 'text': c['text'], 'type': c['type']})
    # Make a list of available country codes just for convenience in Ajax validation
    available_country_codes.append(c['code'])
    regions = []
    just_region_values = [] # values are the region codes like 2-letter US states
    for r in c['regions']:
        regions.append({'value': r['value'], 'text': r['text']})
        just_region_values.append(r['value'])

    all_regions.append({'code': c['code'], 'type': c['type'], 'regions': regions})
    available_regions_per_country[c['code']] = just_region_values

# **************************
# End of initialization code
# ... continue with Forms
# *************************

class GigForm(ModelForm):
    class Meta:
        model = Gig
        fields = ['title', 'category', 'description', 'price', 'photo', 'status', 'sellmsg']

    # Validation for 'photo' field
    def clean_photo(self):
        data = self.cleaned_data['photo']

        # If empty, inject fixed placeholder image
        if not data:
            data = settings.MEDIA_PLACEHOLDER_IMAGE_PATH

        # Remember to always return the cleaned data.
        return data

    # Validation for 'status' field
    def clean_status(self):
        data = self.cleaned_data['status']

        # True only when select option value equal '1' otherwise False
        data = True if data == 1 else False

        # Remember to always return the cleaned data.
        return data

class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['displayname', 'about', 'slogan', 'zipcode', 'state', 'country', 'emailoptin']

    # Validation for 'country' field
    def clean_country(self):
        data = self.cleaned_data['country']

        if data and data not in available_country_codes:
            raise ValidationError('Invalid value: %(value)s',
                                    code='invalid',
                                    params={'value': data})
            data = None

        # Remember to always return the cleaned data.
        return data

    # Validation for 'state' field
    def clean_state(self):
        data = self.cleaned_data['state']

        if 'country' in self.cleaned_data and self.cleaned_data['country'] == 'US':
            if data not in available_regions_per_country['US']:
                raise ValidationError('Invalid value: %(value)s',
                                        code='invalid',
                                        params={'value': data})
                data = None

        # Remember to always return the cleaned data.
        return data

    # Validation for 'zipcode' field
    def clean_zipcode(self):
        data = self.cleaned_data['zipcode']

        if 'country' in self.cleaned_data and self.cleaned_data['country'] == 'US':
            if not re.match(r'^\d{5}(?:[-\s]\d{4})?$', data):
                raise ValidationError('Invalid value: %(value)s',
                                        code='invalid',
                                        params={'value': data})
                data = None

        # Remember to always return the cleaned data.
        return data

class RankverifyForm(ModelForm):
    class Meta:
        model = Rankverify
        fields = ['game', 'gameuser']


class EmailVerifyForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['vanitymail', 'emailverified']
