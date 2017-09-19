from datetime import timedelta as td
from django.utils import timezone
from django.conf import settings
from dateutil.parser import parse
from sixerrapp.models import Profile
from sixerrapp.helpers import get_conversation_plus_unread_msgs_count, \
                                get_purchase_plus_unread_posts_count

LAST_ACTIVITY_KEY = "last-activity"
UNREAD_MESSAGES_KEY = "unread-messages"
UNREAD_PURCHASE_POSTS_KEY = "unread-purchase-posts"
UNREAD_SALE_POSTS_KEY = "unread-sale-posts"

class LastUserActivityMiddleware(object):

    def process_request(self, request):
        if request.user.is_authenticated():

            # Handle last activity time to help estimate whether logged or not
            last_activity = request.session.get(LAST_ACTIVITY_KEY)

            # If key is old enough, update database.
            too_old_time = timezone.now() - td(seconds=settings.LAST_ACTIVITY_INTERVAL_SECS)
            if not last_activity or parse(last_activity) < too_old_time:
                Profile.objects.filter(user=request.user.pk).update(
                        last_login=timezone.now())

            request.session[LAST_ACTIVITY_KEY] = timezone.now().isoformat()

            # --------------------------------------
            # Setup unread-messages once when logged
            unread_messages = request.session.get(UNREAD_MESSAGES_KEY)

            # Ignore if set
            if not unread_messages:
                conversations = get_conversation_plus_unread_msgs_count(request.user)

                # Is there at least one unread message?
                # (Set to strings so can have 3 cases. None, 'Yes', 'No')
                request.session[UNREAD_MESSAGES_KEY] = 'Yes' if conversations.exclude(unread=0).exists() else 'No'

            # --------------------------------------
            # Setup unread-purchase-posts once when logged
            unread_purchase_posts = request.session.get(UNREAD_PURCHASE_POSTS_KEY)

            # Ignore if set
            if not unread_purchase_posts:
                purchases = get_purchase_plus_unread_posts_count('buyer', request.user)

                # Is there at least one unread message?
                # (Set to strings so can have 3 cases. None, 'Yes', 'No')
                request.session[UNREAD_PURCHASE_POSTS_KEY] = 'Yes' if purchases.exclude(unread=0).exists() else 'No'

            # --------------------------------------
            # Setup unread-sale-posts once when logged
            unread_sale_posts = request.session.get(UNREAD_SALE_POSTS_KEY)

            # Ignore if set
            if not unread_sale_posts:
                purchases = get_purchase_plus_unread_posts_count('gig__user', request.user)

                # Is there at least one unread message?
                # (Set to strings so can have 3 cases. None, 'Yes', 'No')
                request.session[UNREAD_SALE_POSTS_KEY] = 'Yes' if purchases.exclude(unread=0).exists() else 'No'

        return None
