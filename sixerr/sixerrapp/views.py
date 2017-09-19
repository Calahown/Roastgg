from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Gig, Profile, Purchase, Review, Chatentry, Conversation, ConversationMsg, Ranking, Rankverify
# from .forms import GigForm, ProfileForm
from sixerrapp import forms
from django.db.models import Avg
from django.core.mail import send_mail
from django.conf import settings
import datetime
from django.utils import timezone
from django.conf.urls import url
from .helpers import status_to_buttons, get_status_message, \
                        get_conversation_plus_unread_msgs_count, \
                        get_purchase_plus_unread_posts_count, \
                        get_order_tax, \
                        isBillingCountryIncomplete
from .template_processors import category_choices_to_slugs
from django.http import HttpResponseRedirect , HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from django.contrib.staticfiles.templatetags.staticfiles import static
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta as td
import stripe
import json
from django.views.decorators.http import require_POST, require_GET
from .postpone import postpone

from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .tokens import account_activation_token
import re
import requests

stripe.api_key = settings.SOCIAL_AUTH_STRIPE_SECRET
endpoint_secret = settings.ENDPOINT_SECRET


#To activate time conversion
#timezone.activate("America/Los_Angeles")

# Create chat bot user but NOT when running "makemigrations" because ...
# ... "auth_user" table has not been created and causes "OperationalError"
try:
    CHAT_BOT_USER, created = User.objects.get_or_create(username='rosty', \
                                                        email=settings.EMAIL_HOST_USER)
# Catch any error
except:
    created = False

if created:
    CHAT_BOT_USER.set_password(settings.EMAIL_HOST_PASSWORD)
    CHAT_BOT_USER.save()

    try:
        profile = Profile.objects.get(user_id=CHAT_BOT_USER.id)
    except Profile.DoesNotExist:
        profile = Profile(user_id=CHAT_BOT_USER.id)

    profile.avatar = static('img/logo.png')
    profile.save()

# Create your views here.
def home(request):
    gigs = Gig.objects.filter(status = True).order_by('-boughttimes')

    return render(request, 'home.html', {"gigs":gigs})

def overview(request):
    # Render plain html overview page
    return render(request, 'overview.html')

def get_country_data(request):
    # Ajax handling
    if request.is_ajax() and 'selected_country' in request.POST:
        selected_country = request.POST['selected_country']
        if selected_country in forms.available_country_codes:
            # Get the country regions from all regions only for the selected country
            r = next((item for item in forms.all_regions if item["code"] == selected_country), None)
            # Return country code, type and regions if available
            res = r if r else {}
        else:
            res = {}

        return JsonResponse(json.dumps(res), safe=False)

    return render(request, 'overview.html')

def get_tax_data(request):
    # Ajax handling
    if request.is_ajax() and 'from_country' in request.POST:

        try:
            gig = Gig.objects.get(id = request.POST['gig_id'])
        except Gig.DoesNotExist:
            return JsonResponse(json.dumps({
                                            'type': 'error',
                                            'text': 'Gig does not exists'
                                            }), safe=False)

        from_country = request.POST['from_country']

        if from_country == 'US':
            fromObj =   {
                            # 'country': str(gig.user.profile.country),
                            # 'zipcode': str(gig.user.profile.zipcode),
                            # 'state': str(gig.user.profile.state)
                            'country': from_country,
                            'zipcode': request.POST['from_zipcode'],
                            'state': request.POST['from_state']
                        }
        else:
            fromObj =   {
                            'country': from_country
                        }

        toObj =   {
                        'country': request.POST['country'],
                        'zipcode': request.POST['address_zip'],
                        'state': request.POST['address_state'],
                        'city': request.POST['address_city'],
                        'street': request.POST['address_line1']
                    }

        taxes = get_order_tax(fromObj, toObj, str(gig.id), gig.price)

        return JsonResponse(json.dumps({
                'type': 'tax',
                'rate': taxes.rate * 100,
                'amount': "{:.2f}".format(taxes.amount_to_collect),
                'total': "{:.2f}".format(gig.price + taxes.amount_to_collect)}), safe=False)

    return render(request, 'overview.html')

def gig_detail(request, id):
    try:
        gig = Gig.objects.get(id=id)
    except Gig.DoesNotExist:
        return redirect('/')

    # Create review if is a POST, is logged in, has bought and content is not empty
    if request.method == "POST" and not request.user.is_anonymous() \
    and Purchase.objects.filter(gig_id=id,buyer=request.user).count() > 0 \
    and'content' in request.POST and request.POST['content'].strip() != '':
        Review.objects.create(content=request.POST['content'], gig_id=id, user=request.user)

    # Warn if already bought
    if request.user.is_anonymous() \
    or Purchase.objects.filter(gig_id=id, buyer=request.user).count() == 0:
        warning_message = False
    else:
        warning_message = 'You have already bought it'

    # Warn when user does not have a verified email
    email_not_verified_warning = False
    if not request.user.is_anonymous():
        try:
            is_email_verified = Profile.objects.get(user = request.user).emailverified
        except Exception as e:
            is_email_verified = None

        if not is_email_verified:
            email_not_verified_warning = """
            You do not have an email in your profile.
            We can not contact you.
            You can still purchase but you will need to follow your account notifications for updates.
            """

    # Do not let auto purchases
    if gig.user == request.user:
        is_auto_purchase = True
    else:
        is_auto_purchase = False

    reviews = Review.objects.filter(reviewee=gig.user)

    author_profile = gig.user.profile
    from_country = author_profile.country if author_profile.country else 'US'
    from_zipcode = author_profile.zipcode if author_profile.zipcode else '78045'
    from_state = author_profile.state if author_profile.state else 'TX'

    return render(request, 'gig_detail.html', { "gig":gig,
                                                "is_auto_purchase":is_auto_purchase,
                                                "reviews":reviews.order_by("-id")[:5],
                                                # "show_post_review":show_post_review,
#                                                "profile": profile,
                                                "countries": forms.countries,
#                                                "has_billing": has_billing,
#                                                "billing": billing,
#                                                "rate": rate,
#                                                "tax": tax,
#                                                "amount": amount,
                                                'from_country': from_country,
                                                'from_state': from_state,
                                                'from_zipcode': from_zipcode,
                                                'email_not_verified_warning': email_not_verified_warning,
                                                "warning_message": warning_message})

@login_required(login_url="/")
def create_gig(request):
    error = ''

    try:
        profile = Profile.objects.get(user = request.user)
    except Profile.DoesNotExist:
        return redirect('/')

    if request.method == 'POST':
        gig_form = forms.GigForm(request.POST, request.FILES)
        if gig_form.is_valid():
            gig = gig_form.save(commit=False)
            gig.user = request.user
            gig.save()
            return redirect('my_gigs')
        else:
#            error = "Data is not valid"
            error = gig_form.errors

    gig_form = forms.GigForm()

    if request.user == profile.user:
        noStripeAccountYet = True if not request.user.profile.stripe else False
        noCompleteBillingCountry = isBillingCountryIncomplete(request.user.profile)
    else:
        noCompleteBillingCountry  = True
        noStripeAccountYet = True

    canNotPublishGig = noCompleteBillingCountry or noStripeAccountYet

    return render(request, 'create_gig.html',{"error":error,
                                "canNotPublishGig": canNotPublishGig,
                                "noStripeAccountYet": noStripeAccountYet,
                                "noCompleteBillingCountry": noCompleteBillingCountry})

@login_required(login_url="/")
def my_gigs(request):
    try:
        profile = Profile.objects.get(user = request.user)
    except Profile.DoesNotExist:
        return redirect('/')

    if request.user == profile.user:
        noStripeAccountYet = True if not request.user.profile.stripe else False
        noCompleteBillingCountry = isBillingCountryIncomplete(request.user.profile)
    else:
        noCompleteBillingCountry  = True
        noStripeAccountYet = True

    canNotPublishGig = noCompleteBillingCountry or noStripeAccountYet

    gigs = Gig.objects.filter(user=request.user)
    return render(request, 'my_gigs.html',{"gigs":gigs,
                                "canNotPublishGig": canNotPublishGig,
                                "noStripeAccountYet": noStripeAccountYet,
                                "noCompleteBillingCountry": noCompleteBillingCountry})

@login_required(login_url="/")
def edit_gig(request, id):
    try:
        profile = Profile.objects.get(user = request.user)
    except Profile.DoesNotExist:
        return redirect('/')
    try:
        gig = Gig.objects.get(id=id,user=request.user)
        error = ''
        if request.method == "POST":
            gig_form = forms.GigForm(request.POST,request.FILES, instance=gig)
            if gig_form.is_valid():
                gig.save()
                return redirect('my_gigs')
            else:
                error = "Data is not valid"

        if request.user == profile.user:
            noStripeAccountYet = True if not request.user.profile.stripe else False
            noCompleteBillingCountry = isBillingCountryIncomplete(request.user.profile)
        else:
            noCompleteBillingCountry  = True
            noStripeAccountYet = True

        canNotPublishGig = noCompleteBillingCountry or noStripeAccountYet

        return render(request, 'edit_gig.html', {"gig":gig ,
                                                "error":error,
                                "canNotPublishGig": canNotPublishGig,
                                "noStripeAccountYet": noStripeAccountYet,
                                "noCompleteBillingCountry": noCompleteBillingCountry})

    except Gig.DoesNotExist:
        return redirect('/')

def profile(request, username):
    try:
        profile = Profile.objects.get(displayname = username)
    except Profile.DoesNotExist:
        return redirect('/')

    # Explore if user has any rank verified
    try:
        ranking = Ranking.objects.get(user__profile__displayname = username)
    except Ranking.DoesNotExist:
        ranking = None

    postError = ''
    if request.method == "POST" and 'profile_form' in request.POST:
        profile_form = forms.ProfileForm(request.POST, instance=profile)
        if profile_form.is_valid():
            profile.save()
        else:
            postError = "Data is not valid"

    if request.method == "POST" and 'rankverify_form' in request.POST:
        rankverify_form = forms.RankverifyForm(request.POST)
        if rankverify_form.is_valid():
            print('is_valid')
            rankverify = rankverify_form.save(commit=False)
            rankverify.user = request.user
            rankverify.save()
            return redirect('profile', username = username)
        else:
            postError = "Data is not valid"

    if request.method == "POST" and 'emailvalidate_form' in request.POST:
        vanitymail = request.POST['vanitymail'] if 'vanitymail' in request.POST else 'noEmail'
        confirm_vanitymail = request.POST['confirm_vanitymail'] if 'confirm_vanitymail' in request.POST else 'noConfiramtion'
        match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', vanitymail)

        if match and vanitymail == confirm_vanitymail:

            ''' Begin reCAPTCHA validation '''
            recaptcha_response = request.POST.get('g-recaptcha-response')
            data = {
                'secret': settings.RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
            result = r.json()
            ''' End reCAPTCHA validation '''

            if result['success']:

                profile.vanitymail = vanitymail
                profile.emailverified = False
                profile.save()
                # Verify email message template
                msg =       'Hello {username},\n'
                msg = msg + 'Please click on the link to confirm your registration.\n'
                msg = msg + settings.HOST_URL + '/validate_email/' +'{uidb64}/{token}\n'
                msg = msg + '\n'
                msg = msg + signature(username)

                # Fill message template
                msg = msg.format(username = username,
                                uidb64 = urlsafe_base64_encode(force_bytes(profile.user.pk)).decode('ascii'),
                                token = account_activation_token.make_token(profile.user) )

                send_mail('Verify your email for Roast.gg',     # subject
                        msg,                                    # content
                        settings.EMAIL_HOST_USER,               # from
                        [vanitymail],                           # to
                        fail_silently=False)
                return redirect('profile', username = username)
            else:
                # It is a Robot
                return redirect('home')
        else:
            postError = "Email or Confiramtion error"

    pendingRankverify = Rankverify.objects.filter(user=profile.user)

    gigs = Gig.objects.filter(user=profile.user, status=True)

    sreviews = Review.objects.filter(reviewee=profile.user, purchase__gig__user=profile.user)
    breviews = Review.objects.filter(reviewee=profile.user, purchase__buyer=profile.user)

    if request.user == profile.user:
        # show all gigs (does not matter whether active or not)
        gigs = Gig.objects.filter(user=profile.user)
        overlayEnabled = True
        noStripeAccountYet = True if not request.user.profile.stripe else False
        noCompleteBillingCountry = isBillingCountryIncomplete(request.user.profile)
    else:
        # show only active gigs
        gigs = Gig.objects.filter(user=profile.user, status=True)
        overlayEnabled = False
        noCompleteBillingCountry  = True
        noStripeAccountYet = True

    canNotPublishGig = noCompleteBillingCountry or noStripeAccountYet

    return render(request, 'profile.html', {"profile":profile, "gigs": gigs,
                            "ranking": ranking,
                            "pendingRankverify": pendingRankverify.order_by('-id'),
                            "sreviews": sreviews.order_by('-id'),
                            "breviews": breviews.order_by('-id'),
                            "countries": forms.countries,
                            "overlayEnabled": overlayEnabled,
                            "canNotPublishGig": canNotPublishGig,
                            "noStripeAccountYet": noStripeAccountYet,
                            "noCompleteBillingCountry": noCompleteBillingCountry,
                            "postError": postError})

@require_GET
@csrf_exempt
def validate_email(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and profile is not None and account_activation_token.check_token(user, token):
        user.profile.emailverified = True
        user.profile.save()
        message = """
Thank you for your email confirmation.
Now you can receive messages from us according to your notification preferences.
"""
        # return redirect('home')
        return render(request, 'standAloneTemplates/thankyou.html', {"message": message})
    else:
        return HttpResponse('Activation link is invalid!')

def process_payment(request):
    # Ajax handling
    if request.is_ajax() and 'card_token' in request.POST:
        card_token = request.POST['card_token']

        return JsonResponse(json.dumps(res), safe=False)

    return render(request, 'overview.html')

@login_required(login_url="/")
def create_purchase(request):
    # Ajax handling
    if request.is_ajax() and 'card_token' in request.POST and \
                                'gig_id' in request.POST:
        card_token = request.POST['card_token']

        try:
            gig = Gig.objects.get(id = request.POST['gig_id'])
        except Gig.DoesNotExist:
            return JsonResponse(json.dumps({
                                            'type': 'error',
                                            'text': 'Gig does not exists'
                                            }), safe=False)

        # TODO: Validate that the token has not been used already, could be ...
        #       ... by verifing not in Session and saveing it (in Session)

        author_profile = gig.user.profile
        from_country = author_profile.country if author_profile.country else 'US'
        from_zipcode = author_profile.zipcode if author_profile.zipcode else '78045'
        from_state = author_profile.state if author_profile.state else 'TX'

        if from_country == 'US':
            fromObj =   {
                            'country': from_country,
                            'zipcode': from_zipcode,
                            'state': from_state
                        }
        else:
            fromObj =   {
                            'country': from_country
                        }

        toObj =   {
                        'country': request.POST['country'],
                        'zipcode': request.POST['address_zip'],
                        'state': request.POST['address_state'],
                        'city': request.POST['address_city'],
                        'street': request.POST['address_line1']
                    }

        taxes = get_order_tax(fromObj, toObj, str(gig.id), gig.price)
        tax_amount_in_cents = getattr(taxes, 'amount_to_collect', 0)*100

        try:
            result = stripe.Charge.create(
                amount = int(gig.price*100 + tax_amount_in_cents),
                currency = "usd",
                application_fee = (gig.price*10 + 30),
                source = card_token,
                destination = gig.user.profile.stripe,
                description = str("Purchase of " + gig.title),
                receipt_email = request.user.email
            )

        except Exception as e:
            # TODO: Improve error logging and handling
            #       'https://stripe.com/docs/api#error_handling'
            print( 'stripe.error = %s' % str(e) )
            # Inform error to user
            return JsonResponse(json.dumps({
                                            'type': 'error',
                                            'text': str(e)
                                            }), safe=False)

        if result.paid:
            purchase = Purchase.objects.create(gig=gig, buyer=request.user, status="OR", \
                                    title=gig.title, category=gig.get_category_display(), \
                                    description=gig.description, price=gig.price, \
                                    photo=gig.photo, taxamount = tax_amount_in_cents)

            gig.boughttimes = gig.boughttimes + 1
            gig.save()

            # transfer = stripe.Transfer.create(
            # amount = (result.amount*.95)-30,
            # currency="usd",
            # destination = gig.user.profile.stripe,
            # source_transaction = result.id)

            # Creates first CHAT entry always used as "seller to buyer instructions"
            Chatentry.objects.create(pid=purchase, poster = purchase.gig.user, \
                        content = gig.sellmsg if gig.sellmsg else \
                        'Use CHAT to send your video link so I can start')

            # Chat bot initial message
            msg =       'Hi {buyer},\n'
            msg = msg + 'Please follow above instructions so {seller} can start working\n'
            msg = msg + '\n'
            msg = msg + 'If you have any questions, use this CHAT to talk to {seller}'

            # Fill Chat bot initial message template
            msg = msg.format(buyer=request.user.profile.displayname, seller=gig.user.profile.displayname)

            Chatentry.objects.create(pid=purchase,poster = CHAT_BOT_USER, content = msg)

            if purchase.gig.user.profile.emailverified:
                # Message template to seller
                msg =       'Hello {seller},\n'
                msg = msg + 'You have have sold "{title}" at {time}\n'
                msg = msg + 'The buyer is: {buyer}\n'
                msg = msg + 'You can review your sales at {link}\n'
                msg = msg + '\n'
                msg = msg + 'Congratulations,\n'
                msg = msg + signature(gig.user.profile.displayname)

                # Fill message template
                msg = msg.format(seller=gig.user.profile.displayname, title=gig.title, \
                                time=datetime.datetime.now(), buyer=request.user.profile.displayname, \
                                link=settings.HOST_URL + '/sale=' + str(purchase.id) + '/')

                send_mail('You sold "' + gig.title + '" gig!',  # subject
                        msg,                                    # content
                        settings.EMAIL_HOST_USER,               # from
                        [purchase.gig.user.profile.vanitymail], # to
                        fail_silently=False)

            if purchase.buyer.profile.emailverified:
                # Message template to buyer
                msg = 'Hello {buyer},\n\n'
                msg = msg + 'Thank you for your purchase of {title} \n'
                msg = msg + 'Please proceed to the purchase screen to comunicate directly with {seller}.\n'
                msg = msg + 'The next step is to provide with a gameplay vod.\n'
                msg = msg + 'We recommend a recording, but using a popular streaming platform will work in most cases.\n'
                msg = msg + 'Best of luck in your games. \n'
                msg = msg + 'Purchase screen: {link} \n\n'

                msg = msg + signature(purchase.buyer)

                msg = msg.format(seller=gig.user.profile.displayname, title=gig.title, \
                                 buyer=purchase.buyer.profile.displayname, \
                                link=settings.HOST_URL + '/sale=' + str(purchase.id) + '/')

                send_mail('Thank you for your purchase!',  # subject
                        msg,                                    # content
                        settings.EMAIL_HOST_USER,               # from
                        [purchase.buyer.profile.vanitymail],    # to
                        fail_silently=False)

            # return redirect('transaction_detail', id=purchase.id)
            return JsonResponse(json.dumps({
                                            'type': 'paid',
                                            'id': str(purchase.id)
                                            }), safe=False)

        else:
            # TODO: error email maybe

            return JsonResponse(json.dumps({
                                            'type': 'unpaid',
                                            'text': result.outcome.reason,
                                            }), safe=False)
    # Not a good ajax request
    return render(request, 'overview.html')

@login_required(login_url="/")
def my_sales(request):
    purchases = get_purchase_plus_unread_posts_count('gig__user', request.user)

    # Is there at least one unread sale post?
    # (Set to strings so can have 3 cases. None, 'Yes', 'No')
    request.session['unread-sale-posts'] = 'Yes' if purchases.exclude(unread=0).exists() else 'No'

    return render(request, 'my_sales.html', {"purchases": purchases})

@login_required(login_url="/")
def my_purchases(request):
    purchases = get_purchase_plus_unread_posts_count('buyer', request.user)

    # Is there at least one unread purchase post?
    # (Set to strings so can have 3 cases. None, 'Yes', 'No')
    request.session['unread-purchase-posts'] = 'Yes' if purchases.exclude(unread=0).exists() else 'No'

    return render(request, 'my_purchases.html', {"purchases": purchases})

def category(request, link):
#    categories = {
#        "leagueoflegends": "LL",
#        "overwatch": "OW",
#        "counterstrike": "CS"
#    }
    categories = category_choices_to_slugs()
    print('categories = %s' % categories)
    try:
        gigs = Gig.objects.filter(category=categories[link]['code'], status=True)
        return render(request, 'home.html', {"gigs": gigs})
    except KeyError:
        return redirect("home")

def search(request):
    if 'title' not in request.GET:
        return redirect("home")

    gigs = Gig.objects.filter(title__icontains=request.GET['title'], status=True)
    return render(request,'home.html',{'gigs':gigs})


def termsofuse(request):
    return render(request,'termsofuse.html')

def privacypolicy(request):
    return render(request,'privacypolicy.html')

@login_required(login_url="/")
def transaction_detail(request, id):

    try:
        purchase = Purchase.objects.get(id=id)
    except Purchase.DoesNotExist:
        return redirect('/')

    if not user_belongs_to_transaction(request.user, purchase):
        return redirect("home")

    # Define who is "speaking" (role) and who is in "listening" (the_other_user)
    role = 'buyer' if request.user == purchase.buyer else 'seller'
    the_other_user = purchase.gig.user if role == 'buyer' else purchase.buyer

    # Get all post for this purchase
    chatentries = Chatentry.objects.filter(pid=purchase)
    # Change any unread posts to read, except those made by present user
    unread = chatentries.exclude(poster=request.user) # Note using `exclude`
    if unread:
        unread.update(read=True)

    # Is there a new post in the chat?
    if(request.POST.get('chattext')):
        # Is the_other_user still logged?
        other_last_activity = Profile.objects.filter(user=the_other_user).values_list('last_login', flat=True)[0]
        too_old_time = timezone.now() - td(minutes=settings.IDLE_MINUTES_CONSIDERED_LOGGED)
        other_not_logged = other_last_activity < too_old_time

        # Do present user have unread post?
        # (or... Find out whether this is the first post since last read by the_other_user or not)
        # (if the_other_user is not logged, then it does not matter if it is the first unread post, set to False anyway)
        is_first_unread_post = not chatentries.filter(poster=request.user, read=False).exists() if other_not_logged else False

        Chatentry.objects.create(pid=purchase, poster=request.user, content=request.POST.get('chattext').strip())

        if other_not_logged \
        and is_first_unread_post \
        and the_other_user.profile.emailverified \
        and the_other_user.profile.emailoptin:
            # Send mail to the_other_user
            msg = "Hello " + str(the_other_user.profile.displayname) + ". \n"
            msg = msg + str(request.user.profile.displayname) + " has posted in the chat. \n"
            msg = msg + "\n"
            msg = msg + "You can go directly to your roast by following this link: \n"
            msg = msg + settings.HOST_URL + "/sale=" + str(purchase.id) + "/ \n"
            msg = msg + "\n"

            msg = msg + signature(the_other_user)

            send_mail("Your roast " + str(purchase.title) + " has a new post in the chat", #subjectline
                    str(msg),                               # content
                    settings.EMAIL_HOST_USER,               # from
                    [the_other_user.profile.vanitymail],    #t o the_other_user
                    fail_silently=False)

        # Redirect here (transaction_detail) using HttpResponseRedirect to avoid rePOST
        return HttpResponseRedirect(reverse('transaction_detail', args=[id]))

    if(request.POST.get('mybtn')):
        stat = request.POST.get('entry')
        if purchase.status != stat:
            purchase.status = stat
            purchase.save()
            send_transaction_email(purchase)

        # Redirect here (transaction_detail) using HttpResponseRedirect to avoid rePOST
        return HttpResponseRedirect(reverse('transaction_detail', args=[id]))

    status_msg = get_status_message(purchase)
    buttons = status_to_buttons(role, purchase.status)
    disablebtn = False
    if (request.POST.get('reviewbtn')):
        Review.objects.create(purchase=purchase, reviewer=request.user, reviewee=the_other_user, content=request.POST.get('reviewbtn'))
        if request.user == purchase.buyer:
            if request.POST.get('rating'):
                purchase.buystars = request.POST.get('rating')
            else:
                purchase.buystars=0
            purchase.save()
            purchase.buyer.profile = round(Purchase.objects.filter(buyer=purchase.buyer).exclude(buystars=0).aggregate(Avg('buystars'))['buystars__avg'],1)
        else:
            if request.POST.get('rating'):
                purchase.stars=request.POST.get('rating')
            else:
                purchase.stars=0
            purchase.save()
            if Purchase.objects.filter(gig=purchase.gig).exclude(stars=0).count() > 3:
                purchase.gig.avgstars = Purchase.objects.filter(gig=purchase.gig).exclude(stars=0).aggregate(Avg('stars'))
                purchase.gig.avgstars = round(purchase.gig.avgstars['stars__avg'],1)
                purchase.gig.save()
            if Purchase.objects.filter(gig__user=purchase.gig.user).exclude(stars=0).count() >5:
                purchase.gig.user.profile.avgstars = Purchase.objects.filter(gig__user=purchase.gig.user).exclude(stars=0).aggregate(Avg('stars'))
                purchase.gig.user.profile.avgstars = round(purchase.gig.user.profile.avgstars['stars__avg'],1)
                purchase.gig.user.profile.save()


        return redirect("profile", username = str(the_other_user))

    if Review.objects.filter(purchase=purchase, reviewer=request.user):
        disablebtn = True

    return render(request, 'transaction_detail.html', \
        { "view_as": "Purchase", "purchase":purchase, "chatentries":chatentries.order_by("id"), \
        "status_msg": status_msg, "buttons": buttons, "disablebtn":disablebtn})

# Send emails just after changing purchase status
def send_transaction_email(purchase):

    # Seller clicked "VOD received" button
    if purchase.status == "VS":
        # Create event CHAT entry as "roasty"
        Chatentry.objects.create(pid=purchase, poster = CHAT_BOT_USER, \
                    content = str(purchase.gig.user.profile.displayname) + " has received the VOD to review")

        if purchase.buyer.profile.emailverified:
            # Send email to buyer
            msg = "Hello " + str(purchase.buyer.profile.displayname) + ". \n"
            msg = msg + str(purchase.gig.user.profile.displayname) + " has received your VOD to review. \n"
            msg = msg + "\n"
            msg = msg + "This eMail is just informative. No need for futher action. \n"
            msg = msg + settings.HOST_URL + "/sale=" + str(purchase.id) + "/ \n"

            msg = msg + signature(purchase.buyer.profile.displayname)

            send_mail("Confiramtion that your VOD has been received by " + str(purchase.gig.user.profile.displayname), #subjectline
                    str(msg),                               # content
                    settings.EMAIL_HOST_USER,               # from
                    [purchase.buyer.profile.vanitymail],    # to
                    fail_silently=False)

        return

    # Seller clicked "Roast Delivered" button
    if purchase.status == "SS":
        # Create event CHAT entry as "roasty"
        Chatentry.objects.create(pid=purchase, poster = CHAT_BOT_USER, \
                    content = str(purchase.gig.user.profile.displayname) + " has delivered the roast")

        if purchase.buyer.profile.emailverified:
            # Send email to seller
            msg = "Hello " + str(purchase.buyer.profile.displayname) + ". \n"
            msg = msg + "The full roast for your purchase " + str(purchase.title) + " is now available. \n"
            msg = msg + "The link is available in the purchase chat. \n"
            msg = msg + "Do not forget to ACCEPT the roast when done so " + str(purchase.gig.user.profile.displayname) + " can receive the funds. \n"
            msg = msg + "\n"
            msg = msg + "If you feel apropriate, chat with " + str(purchase.gig.user.profile.displayname) + \
                        " for any changes or reviews to the roast until you are completelly satisfied. \n"
            msg = msg + "\n"
            msg = msg + "Thank you for your patronage, and good luck in your future games. \n"
            msg = msg + settings.HOST_URL + "/sale=" + str(purchase.id) + "/ \n"

            msg = msg + signature(purchase.buyer.profile.displayname)

            send_mail("Your roast " + str(purchase.title) + " is ready.", #subjectline
                    str(msg),                       #content
                    settings.EMAIL_HOST_USER,       #from
                    [purchase.buyer.profile.vanitymail],    # to
                    fail_silently=False)

        return

    # Buyer clicked "Roast Accepted" button
    if purchase.status == "AC":
        # Create event CHAT entry as "roasty"
        Chatentry.objects.create(pid=purchase, poster = CHAT_BOT_USER, \
                    content = str(purchase.buyer.profile.displayname) + " has accepted the roast")

        if purchase.gig.user.profile.emailverified:
            # Send email to seller
            msg = "Hello " + str(purchase.gig.user.profile.displayname) + ". \n"
            msg = msg + "The link you submitted for " + str(purchase.title) + " to " + str(purchase.buyer.profile.displayname) + " has been accepted. \n"
            msg = msg + "Congratulations on the sale, please allow 3 business days for payment. \n"
            msg = msg + settings.HOST_URL + "/sale=" + str(purchase.id) + "/ \n"

            msg = msg + signature(purchase.gig.user.profile.displayname)

            send_mail("Roast accepted for " + str(purchase.title) + ".", #subjectline
                    str(msg),                               # content
                    settings.EMAIL_HOST_USER,               # from
                    [purchase.gig.user.profile.vanitymail], # to
                    fail_silently=False)

        return

def signature(profile_username):
    return """
- The Roast.gg team

Notice: You are receiving this email per your request as part of our Terms of Use.
You can change your email preferences by log in and editing your profile in the following link:
""" + settings.HOST_URL + "/profile/" + str(profile_username) + "/" + """

Do not reply. The notifications email is not monitored.

If you are receiving this email in error, please contact us at contact.us@roast.gg so we can correct it immediately.
"""

def landing(request):
    return render(request, 'landingone.html')


# transaction_detail helper
def user_belongs_to_transaction(user, purchase):
    return user == purchase.buyer or user == purchase.gig.user or user.is_superuser

# ------------
# Convesations
# ------------

@login_required(login_url="/")
def create_conversation(request):
    if request.method == "POST":

        try:
            # If Gig exist then add reference to it (and grab receiver from it)
            gig = Gig.objects.get(id=request.POST.get('gig_id'))
            conversation = Conversation.objects.create(gig=gig, sender=request.user, \
                                    receiver=gig.user, starttime=timezone.now())

            add_initial_roasty_msg(conversation, gig.user.profile.displayname)

            return redirect('conversation_detail', id=conversation.id)
        except Gig.DoesNotExist:
            # No Gig to reference, grab receiver from Form POST hidden field
            if User.objects.filter(id=request.POST.get('user_id')).exists():
                profile_user = User.objects.get(id=request.POST['user_id'])
                conversation = Conversation.objects.create(sender=request.user, \
                                        receiver=profile_user, starttime=timezone.now())

                add_initial_roasty_msg(conversation, profile_user.profile.displayname)

                return redirect('conversation_detail', id=conversation.id)

    return redirect('/')

# create_conversation helper
def add_initial_roasty_msg(conversation, username):
    ConversationMsg.objects.create(parent=conversation, author=CHAT_BOT_USER,
                content=conversation.sender.profile.displayname + ', post your message to start the conversation with ' + username, read=True)

@login_required(login_url="/")
# TODO: Create @belong_to_conversation_required
def conversation_detail(request, id):

    try:
        conversation = Conversation.objects.get(id=id)
    except Conversation.DoesNotExist:
        return redirect('/')

    # Get all post for this conversation
    messages = ConversationMsg.objects.filter(parent=conversation)
    # Change any unread messages to read, except those made by present user
    unread = messages.exclude(author=request.user) # Note using `exclude`
    if unread:
        unread.update(read=True)

    # Is there a new msg in the chat?
    if(request.POST.get('messagetext')):

        ConversationMsg.objects.create(parent=conversation, author=request.user,
                                        content=request.POST.get('messagetext').strip())

        # Redirect here (conversation) using HttpResponseRedirect to avoid rePOST
        return HttpResponseRedirect(reverse('conversation_detail', args=[id]))

    return render(request, 'conversation_detail.html', { "messages":messages.order_by("id") })

@login_required(login_url="/")
def my_conversations(request):
    conversations = get_conversation_plus_unread_msgs_count(request.user)

    # Is there at least one unread message?
    # (Set to strings so can have 3 cases. None, 'Yes', 'No')
    request.session['unread-messages'] = 'Yes' if conversations.exclude(unread=0).exists() else 'No'

    return render(request, 'my_conversations.html', {"conversations": conversations.order_by('id')})

@require_POST
@csrf_exempt
def webhooks(request):

  event = json.loads(request.body)
  long_process(event)

  return HttpResponse(status=200)


@require_POST
@csrf_exempt
def connecthooks(request):

    event = json.loads(request.body)
    print(event)
    print(event['id'])

    try:
        vevent=stripe.Event.retrieve(str(event['id']), stripe_account = str(event['account']))
    except stripe.error.PermissionError as e:
        print(e)
        if event['type'] == 'account.application.deauthorized':
            print("deauthorized")
            if norepeat(event['id']):
                listo = Gig.objects.filter(user__profile__stripe = event['account'])
                for r in listo:
                    r.status=False
                    r.save()

                listo2 = Profile.objects.filter(stripe = event['account'])
                for r in listo2:
                    r.stripe = None
                    r.striperefresh = None
                    r.save()

        return HttpResponse(status=200)
    print("vevent")
    print(vevent)

    long_procconnect(event)

    return HttpResponse(status=200)

@postpone
def long_process(event):

    vevent = stripe.Event.retrieve(str(event['id']))

    return

@postpone
def long_procconnect(event):
    try:
        vevent=stripe.Event.retrieve(str(event['id']), stripe_account = str(event['account']))
    except stripe.error.PermissionError as e:
        print(e)
        if event['type'] == 'account.application.deauthorized':
            print("deauthorized")

        return
    print("vevent")
    print(vevent)

    return

def norepeat(id):
    if Disconnectedhooks.objects.filter(event=id):
        return 0

    return 1
