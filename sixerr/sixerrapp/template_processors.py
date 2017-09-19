from .models import Gig
from django.utils.text import slugify
from collections import OrderedDict

class SimpleNamespace (object):
    def __init__ (self, **kwargs):
        self.__dict__.update(kwargs)

def category_choices_to_slugs():
    # Convert the CATEGORY_CHOICES from models into a dictionary with slugs for links
    pseudo_obj = SimpleNamespace()
    idx = 0
    for category in Gig.CATEGORY_CHOICES:
        # build pseudo object
        # key = slug, value = dictionary with render text, db code and index for order
        setattr(pseudo_obj, slugify(category[1]), {'text': category[1],
                                                    'code': category[0],
                                                    'index': idx})
        idx = idx +1
    # Return a real object (real unordered dictionary)
    return vars(pseudo_obj)

def category_names(request):
    categories = category_choices_to_slugs()
    ordered_categories = OrderedDict(sorted(categories.items(),
                                  key=lambda kv: kv[1]['index']))
    return {'ordered_categories': ordered_categories}
