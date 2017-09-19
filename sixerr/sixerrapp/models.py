from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.core.validators import MinLengthValidator, MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db.models import Lookup

# Custom lookup used in helpers.py by Chatentry and ConversationMsg
class NotEqual(Lookup):
    lookup_name = 'ne'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return '%s <> %s' % (lhs, rhs), params

from django.db.models.fields import Field
Field.register_lookup(NotEqual)

# Create your models here.

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    displayname = models.CharField(max_length=150, null=True,blank=True, unique=True)
    avatar = models.CharField(max_length=500)
    about = models.TextField(max_length=2000, blank=True, null=True)
    slogan = models.CharField(max_length=500, blank = True, null=True)
    last_login = models.DateTimeField(default=timezone.now)
    avgstars = models.FloatField(blank=True, null=True)
    buystars = models.FloatField(blank=True, null=True)
    stripe = models.CharField(max_length=50,blank=True, null=True)
    striperefresh = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    zipcode = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=2, blank=True, null=True)
    vanitymail = models.CharField(max_length=128, default="replace.me@roast.gg")
    emailoptin = models.BooleanField(default=True)
    emailverified = models.BooleanField(default=True)

    def __str__ (self):
        return self.user.username

class Ranking(models.Model):
    user=models.OneToOneField(User, on_delete=models.CASCADE)
    # gamechoice=CATEGORY_CHOICES = (
    #     ("LL", "League of Legends"),
    #     ("OW", "Overwatch")
    # )
    # game = models.CharField(max_length=2, choices=gamechoice)
    owrankchoices = (("BR", "Bronze"), ("SV", "Silver"), ("GD", "Gold"),("PT", "Platinum"), ("DI", "Diamond"), ("MA", "Master"), ("GM", "Grandmaster"), ("UR", "Unranked"))
    lolrankchoices = (("BR", "Bronze"), ("SV", "Silver"), ("GD", "Gold"),("PT", "Platinum"), ("DI", "Diamond"), ("MA", "Master"), ("CH", "Challenger"), ("UR", "Unranked"))
    #rankchoices = (("BR", "Bronze"), ("SV", "Silver"), ("GD", "Gold"),("PT", "Platinum"), ("DI", "Diamond"), ("MA", "Master"), ("CH", "Challenger (League Of Legends)"), ("GM", "Grandmaster (Overwatch)"),("UR", "Unranked"))
    owusername = models.CharField(max_length=64, blank=True,null=True)
    owrank = models.CharField(max_length=2, blank=True,null=True, choices = owrankchoices)
    lolusername = models.CharField(max_length=64, blank=True,null=True)
    lolrank = models.CharField(max_length=2, choices= lolrankchoices, null=True,blank=True)

    def __str__(self):
        return self.user.username

class Gig(models.Model):
    CATEGORY_CHOICES = (
        ("LL", "League of Legends"),
        ("OW", "Overwatch")
        )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500, validators=[MinLengthValidator(2,"length less than two")])
    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES)
    description = models.TextField(max_length=2000, validators=[MinLengthValidator(2,"length less than two")])
    price = models.IntegerField(default=6, validators=[ \
                    MinValueValidator(1,"minimum allowable $1"), \
                    MaxValueValidator(settings.MAX_GIG_PRICE,"more than max allowable price")])
    photo=models.CharField(max_length=250, blank=True) # clean_photo() injects placeholder
    status = models.BooleanField(default=True)
    user=models.ForeignKey(User)
    create_time = models.DateTimeField(default=timezone.now)
    boughttimes = models.IntegerField(default=0)
    sellmsg = models.TextField(max_length = 1000, blank=True, default='Please provide link to VOD')
    avgstars = models.FloatField(blank=True,null=True)

    def __str__ (self):
        return self.title

class Purchase(models.Model):
    STATUS_CHOICES = (
        ("OR","Purchased"),
        ("VS","VOD Received"),
        ("SS","Roast Delivered"),
        ("AC","Roast Accepted"),
        ("CO","Completed")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gig = models.ForeignKey(Gig)
    buyer = models.ForeignKey(User)
    time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=2,choices=STATUS_CHOICES)
    title = models.CharField(max_length=500)
    category = models.CharField(max_length=50)
    description = models.TextField(max_length=2000)
    price = models.IntegerField(default=6)
    photo = models.CharField(max_length=250)
    stars = models.IntegerField(default = 0, blank=True, null=True,validators=[
            MaxValueValidator(5),
            MinValueValidator(0)
        ])
    buystars = models.IntegerField(default=0, blank=True,null=True,validators=[MaxValueValidator(5), MinValueValidator(0)])
    taxamount = models.IntegerField(default=0)

    def __str__ (self):
        return self.gig.title

class Tempinfo(models.Model):
    user = models.ForeignKey(User)
    address1 = models.CharField(max_length=128)
    address2 = models.CharField(max_length=128,null=True,blank=True)
    zipcode = models.CharField(max_length=16)
    state = models.CharField(max_length=128)
    country = models.CharField(max_length=2)
    city = models.CharField(max_length=128)

class Review(models.Model):
    purchase = models.ForeignKey(Purchase)
    reviewer = models.ForeignKey(User, related_name = "reviewer")
    reviewee = models.ForeignKey(User, related_name = "reviewee")
    content = models.TextField(max_length = 2000)
    time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.content

class Chatentry(models.Model):
    pid = models.ForeignKey(Purchase)
    poster = models.ForeignKey(User)
    content = models.TextField(max_length=2000)
    time = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(blank=True, default=False)

    def __str__(self):
        return self.content

class Conversation(models.Model):
    id = models.AutoField(primary_key=True)
    gig = models.ForeignKey(Gig, blank=True, null=True)
    sender = models.ForeignKey(User, related_name = "sender")
    receiver = models.ForeignKey(User, related_name = "receiver")
    starttime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.sender

class ConversationMsg(models.Model):
    id = models.AutoField(primary_key=True)
    parent = models.ForeignKey(Conversation)
    author = models.ForeignKey(User)
    content = models.TextField(max_length = 2000)
    read = models.BooleanField(blank=True, default=False)
    time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.content

class Disconnectedhooks(models.Model):
    event = models.CharField(max_length=40, primary_key=True)

class Rankverify(models.Model):
    gamechoice=CATEGORY_CHOICES = (
        ("LL", "League of Legends"),
        ("OW", "Overwatch")
    )
    game = models.CharField(max_length=2, choices=gamechoice)
    user = models.ForeignKey(User)
    gameuser = models.CharField(max_length=64)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.gameuser
