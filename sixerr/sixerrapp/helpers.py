# ****************
# Helper functions
# ****************

from .models import Purchase

# --------------
# Initial values
#---------------

# list of button actions
STATUS_CODES = ["OR", "VS", "SS", "AC", "CO"]

# Enable primary button per role (dummy added to avoid index out of range when COMPLETED)
ENABLED_STEP_ROLES = ['not used', 'seller', 'seller', 'buyer', 'not used', 'dummy']

# Status messages (dummy added to avoid index out of range when COMPLETED)
STATUS_MESSAGES = ['not used', 'to acknowledge VOD received', 'to deliver', 'to accept delivery', 'reviews', 'dummy']

# List human readable status
STATUS_TEXT = []
for code in STATUS_CODES:
    # Append just first element found
    STATUS_TEXT.append([item[1] for item in Purchase.STATUS_CHOICES if item[0] == code][0])

# Helper to
# fill buttons classes and content depending on user role and actual purchase status
def status_to_buttons(role, status):
    # validate input
    if role not in ["buyer", "seller"] or status not in STATUS_CODES:
        return []

    stutus_qty = len(STATUS_CODES)
    actual_step_num = STATUS_CODES.index(status) + 1

    # Start with no buttons
    buttons = []

    # Append success buttons (all buttons already used in previous status)
    for k in range(actual_step_num):
        buttons.append({'class': 'success', 'disabled': 'disabled', 'text': STATUS_TEXT[k], 'glyphicon': 'ok'})

    # If not the last step (COMPLETED), append one primary button (may be disabled depending on role)
    if actual_step_num < stutus_qty - 1:
        buttons.append({'next': STATUS_CODES[actual_step_num], 'class': 'primary', 'disabled': '' if (role == ENABLED_STEP_ROLES[actual_step_num]) else 'disabled', 'text': STATUS_TEXT[actual_step_num], 'glyphicon': 'unchecked'})

    # Append disabled buttons (all buttons remaining to be used in future status)
    for k in range(actual_step_num + 1, stutus_qty - 1):
        buttons.append({'class': 'info', 'disabled': 'disabled', 'text': STATUS_TEXT[k], 'glyphicon': 'unchecked'})

    return buttons


# Helper to
# get personalized status messages depending on status
def get_status_message(purchase):
    message_index = STATUS_CODES.index(purchase.status) + 1
    buyer_seller_word = ENABLED_STEP_ROLES[message_index]

    # Three possible cases: "buyer", "seller" or other string
    prepend_msg = purchase.buyer.profile.displayname if buyer_seller_word == 'buyer' else ''
    prepend_msg = purchase.gig.user.profile.displayname if buyer_seller_word == 'seller' else prepend_msg
    return prepend_msg + ' ' + STATUS_MESSAGES[message_index]


# Helper to
# count the unread message to render a notification red dot in the avatar
from .models import Conversation
from django.db.models import Q, F, Count, Case, When

def get_conversation_plus_unread_msgs_count(user):
    # Convesations where user is either sender or receiver
    # Add unread field with related `Conversationmsg.read == False` count
    conversations = Conversation.objects.filter(
                        Q(sender=user) | Q(receiver=user)
                    ).annotate(
                        unread=Count(
                            Case(
                                When(
                                    conversationmsg__author__id__ne=user.id,
                                    conversationmsg__read=0,
                                    then=1
                                )
                            )
                        )
                    )

    return conversations


# Helper to
# count the unread post to render a notification red dot in the avatar
from .models import Purchase
# from django.db.models import Q, F, Count, Case, When

def get_purchase_plus_unread_posts_count(role, user):
    # Python argument expansion for 'buyer=user', 'gig__user=user'
    kwargs = { '{0}'.format(role): user }

    # Purchases where user is role ('buyer','gig__user')
    # Add unread field with related `Chatentry.read == False` count
    purchases = Purchase.objects.filter(**kwargs).annotate(
                        unread=Count(
                            Case(
                                When(
                                    chatentry__poster__id__ne=user.id,
                                    chatentry__read=0,
                                    then=1
                                )
                            )
                        )
                    )

    return purchases

import json
import taxjar
from django.conf import settings
client = taxjar.Client(api_key=settings.TAXJAR_KEY)

def get_order_tax(fromObj, toObj, productID, productPrice):
    order = {
                'from_country': fromObj['country'],
                'to_country': toObj['country'],
                'to_city': toObj['city'],
                'to_street': toObj['street'],
                'shipping': 0,
                'line_items': [
                    {
                        'id': productID,
                        'quantity': 1,
                        'product_tax_code': 31000,
                        'unit_price': int(productPrice),
                        'discount': 0
                    }
                ]
            }

    # From US and CA special cases
    if fromObj['country'] == 'US' or fromObj['country'] == 'CA':
        order['from_state'] = fromObj['state']

    if fromObj['country'] == 'US':
        order['from_zip'] = fromObj['zipcode']

    # To US and CA special cases
    if toObj['country'] == 'US' or toObj['country'] == 'CA':
        order['to_state'] = toObj['state']

    if toObj['country'] == 'US':
        order['to_zip'] = toObj['zipcode']

    print ('+++++++++++++++++++++')
    print ('In "get_order_tax()" - order = %s' % order)
    print ('---------------------')

    try:
        taxes = client.tax_for_order( order )

    except Exception as e:
        # TODO: Improve error logging and handling
        print('TaxJar Exception = %s' % str(e))
        return None

    print ('=-=-=-=-=-=-=-=-=-=-=-=-=-=')
    print ('In "get_order_tax()" - taxes = %s' % taxes)
    print ('* * * * * * * * * * * * * *')

    return taxes

def isBillingCountryIncomplete(profile):
    # Billing country is considered incomplete if country does not exists or ...
    # ... if the country is US and does not have both zipcode and state
    # True is bad, False is good
    return True if (not profile.country or
                        (profile.country == 'US' and
                            (not profile.zipcode or
                                not profile.state))) else False
