from django import template
from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from ..middleware.last_activity import UNREAD_MESSAGES_KEY, \
                                        UNREAD_PURCHASE_POSTS_KEY, \
                                        UNREAD_SALE_POSTS_KEY

VERIFIED_BADGE_STATIC_IMAGE_PATH = static('img/verified.png')

register = template.Library()

# settings value
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")

@register.simple_tag(takes_context=True)
def has_unread_post(context, postType):
    # show notification is the default, it need to be hidden when no unread posts
    POST_TYPES = {
        'message': [UNREAD_MESSAGES_KEY],
        'purchase': [UNREAD_PURCHASE_POSTS_KEY],
        'sale': [UNREAD_SALE_POSTS_KEY],
        'any': [UNREAD_MESSAGES_KEY, UNREAD_SALE_POSTS_KEY, UNREAD_SALE_POSTS_KEY]
        }
    request = context['request']
    found_unread_post = False
    for session_var_name in POST_TYPES[postType]:
        if request.session[session_var_name] == 'Yes':
            found_unread_post = True
            break
    # hide notifications tag by appending ' hidden' class
    return ' hidden' if not found_unread_post else ''

@register.simple_tag()
def render_email_verified(profile):
    imgTag = ' <img src="' + VERIFIED_BADGE_STATIC_IMAGE_PATH + '">'
    if profile.vanitymail == settings.USER_EMAIL_PLACEHOLDER or not profile.emailverified:
        imgTag = ''
    return imgTag
