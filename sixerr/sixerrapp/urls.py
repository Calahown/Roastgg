from django.conf.urls import url
from sixerrapp import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^overview/$', views.overview, name='overview'),
    url(r'^webhooks/$', views.webhooks, name='webhooks'),
    url(r'^privacy-policy/$', views.privacypolicy, name="privacypolicy"),
    url(r'^terms-of-use/$', views.termsofuse, name="termsofuse"),
    url(r'^connecthooks/$', views.connecthooks, name='connecthooks'),
    url(r'^gigs=(?P<id>[0-9A-Fa-f-]+)/$', views.gig_detail, name='gig_detail'),
    url(r'^my_gigs/$', views.my_gigs, name='my_gigs'),
    url(r'^create_gig/$', views.create_gig, name='create_gig'),
    url(r'^edit_gig/(?P<id>[0-9A-Fa-f-]+)/$', views.edit_gig, name='edit_gig'),
    url(r'^profile/(?P<username>\w+)/$', views.profile, name='profile'),
    url(r'^validate_email/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                                    views.validate_email, name='validate_email'),
    url(r'^checkout/$', views.create_purchase, name='create_purchase'),
    url(r'^landingone/$',views.landing, name='landing'),
    #url(r'^create_purchase/$', views.create_purchase, name='create_purchase'),
    url(r'^my_sales/$', views.my_sales, name='my_sales'),
    url(r'^my_purchases/$', views.my_purchases, name='my_purchases'),
    url(r'^search/$',views.search, name='search'),
    #url(r'^purchases/(?P<id>[0-9A-Fa-f-]+)/$', views.transaction_detail, name='transaction_detail'),
    url(r'^sale=(?P<id>[0-9A-Fa-f-]+)/$', views.transaction_detail, name='transaction_detail'),
    url(r'^my_conversations/$', views.my_conversations, name='my_conversations'),
    url(r'^conversations/$', views.create_conversation, name='create_conversation'),
    url(r'^conversation=(?P<id>[0-9A-Fa-f-]+)/$', views.conversation_detail, name='conversation_detail'),
    url(r'^regions/$', views.get_country_data, name='get_country_data'),
    url(r'^stripe/$', views.create_purchase, name='create_purchase'),
    url(r'^taxes/$', views.get_tax_data, name='get_tax_data'),
    url(r'^(?P<link>[\w|-]+)/$', views.category, name='category')
]
