from django.test import TestCase
from bs4 import BeautifulSoup
from django.conf import settings
from sixerrapp.models import Profile, Gig, Purchase, Chatentry
from django.contrib.auth.models import User
from django.urls import reverse
import datetime
from .template_processors import category_choices_to_slugs

from django.http import HttpResponse

# **************************************************
# Wish list of features to be tested
# **************************************************
# - Can filter Gig thumbnails by game (category)
# - Can filter Gig thumbnails by search text
# - Can create a Gig
# - Can edit a Gig
# - Can not change Gig status to Active until publishing req. meet
# **************************************************

# 0) Index sanity test
class IndexViewSanityTestCase(TestCase):
    def test_browser_get_index_page_return_status_200(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

# 1) Site wide navigation and footer test
class SiteWideNavigationAndFooter(TestCase):
    '''
    Test there is a navigation fixed at the top and a footer at the end of
    all pages of the site
    '''
    def setUp(self):
        '''
        Test site wide navigation and footer
        Needs to be:
         - redered by base.html template
        '''
        resp = self.client.get('/')
        decodedResponse = resp.content.decode('utf-8')
        self.soup = BeautifulSoup(decodedResponse, 'html.parser')
        # Setuo assertions
        #
        # site wide presence assumed when the base.html template is used ...
        # ... because all other templates contains 'extends base.html'
        self.assertTemplateUsed(resp, 'base.html', count=1,
            msg_prefix = 'No site wide presence')

    def test_navbar(self):
        '''
        Test the navegation bar is at top of the page
        Needs to:
        - have .navbar-fixed-top class
        - be a nav tag
        '''
        nav_tag_at_top = self.soup.select_one('.navbar-fixed-top')
        self.assertTrue(nav_tag_at_top,
            'navbar-fixed-top class missing')
        self.assertEqual(
            nav_tag_at_top.name,
            'nav',
            "nav tag missing")

    def test_footer(self):
        '''
        Test the footer is last tag in body
        Needs to:
        - be a footer tag
        '''
        body_tags = self.soup.body.contents
        body_tags_qty = len(body_tags)
        self.assertGreaterEqual(
            body_tags_qty,
            2,
            "footer tag is alone in body or inexistent")
        last_body_tag = body_tags[body_tags_qty - 2]
        self.assertEqual(
            last_body_tag.name,
            'footer',
            "footer tag missing or is not the last tag in body")

# 1.1) NavBar components test
class NavBarComponents(TestCase):
    '''
    Test there is:
    - a logo that links back to 'home'
    - a search form
    - a login dropdown
    - a category selection row
    '''
    def setUp(self):
        resp = self.client.get('/')
        decodedResponse = resp.content.decode('utf-8')
        soup = BeautifulSoup(decodedResponse, 'html.parser')
        # Initialization
        self.nav_tag = soup.nav
        self.navbar_container = soup.select_one('.navbar .container')
        # Common assertion
        self.assertTrue(self.navbar_container,
            'container class inside navbar missing')


    def test_logo_link(self):
        '''
        Test there is a logo that links back to 'home'
        Needs to have:
        - .nav-brand class with an image link to 'home'
        - a .logo class for that image
        '''
        navbar_brand_anchor_tag = self.navbar_container.select_one('.navbar-header > a.navbar-brand')
        self.assertTrue(navbar_brand_anchor_tag,
            'navbar-brand class inside navbar-header missing')
        self.assertEqual(
            navbar_brand_anchor_tag['href'],
            '/',
            "Link to 'home' in navbar-brand missing")
        navbar_brand_logo_img_tag = navbar_brand_anchor_tag.select_one('.logo')
        self.assertEqual(
            navbar_brand_logo_img_tag.name,
            'img',
            "navbar_brand image tag inside anchor tag missing")
        self.assertEqual(
            '/static/img/' in navbar_brand_logo_img_tag['src'],
            True,
            "navbar_brand image path does not contains '/static/img/' string")

    def test_search_form(self):
        '''
        Test there is a search form
        Needs to:
        - have .navbar-form class
        - be a form tag
        - have an action url to '/search/'
        - have an input field with .form-control class and a placeholder text
        - have only one button tag
        '''
        navbar_form_tag = self.navbar_container.select_one('.navbar-form')
        self.assertTrue(navbar_form_tag,
            'navbar-form class missing')
        self.assertEqual(
            navbar_form_tag.name,
            'form',
            "search form tag missing")
        self.assertEqual(
            navbar_form_tag['action'],
            '/search/',
            "action to '/search/' in search form missing")
        navbar_form_fields = navbar_form_tag.select('.form-control')
        self.assertEqual(
            len(navbar_form_fields),
            1,
            "There should be one field exactly")
        navbar_form_input_tag = navbar_form_fields[0]
        self.assertEqual(
            navbar_form_input_tag.name,
            'input',
            "only form input field missing")
        self.assertTrue(navbar_form_input_tag['placeholder'],
            "input field placeholder text missing")
        buttons_in_form = navbar_form_tag.find_all('button')
        self.assertEqual(
            len(buttons_in_form),
            1,
            "There should be one button tag exactly")

    def test_login_dropdown(self):
        '''
        Test there is a login dropdown
        Needs to:
        - have .nav > .dropdown > a
        - have the word 'Login' exaclty
        - have attribute data-toggle="dropdown"
        '''
        dropdown_login_link = self.navbar_container.select_one('.nav > .dropdown > a.dropdown-toggle')
        self.assertTrue(dropdown_login_link,
            'Login .nav > .dropdown > a.dropdown-toggle link missing')
        self.assertEqual(
            dropdown_login_link.contents,
            ['Login'],
            "Link not exaclty the word 'Login'")
        self.assertEqual(
            dropdown_login_link['data-toggle'],
            'dropdown',
            'data-toggle="dropdown" missing')

    def test_category_selection(self):
        '''
        Test there is a category selection row
        Needs to:
        - have id="category"
        - have .nav class in a <ul> tag
        '''
        # Initialization
        categories = category_choices_to_slugs()
        # Assertions
        category_nav_tag = self.nav_tag.select_one('#category ul.nav')
        self.assertTrue(category_nav_tag,
            "<ul> tag missing")
        category_links = category_nav_tag.find_all('a')
        for link in category_links:
            found = False
            for category in categories:
                if link['href'] == '/' + category \
                and link.string == categories[category]['text']:
                    found = True
                    break
            self.assertTrue( found,
                "'" + str(link['href']) + "' is not a goog category link or '" \
                    + link.string + "' is not the correct category text")

# 1.2) Footer components test
class FooterComponents(TestCase):
    '''
    Test footer components (just links and copyright year)
    '''
    def setUp(self):
        resp = self.client.get('/')
        decodedResponse = resp.content.decode('utf-8')
        soup = BeautifulSoup(decodedResponse, 'html.parser')
        # Initialization
        self.footer_container = soup.select_one('.footer .container')
        # Common assertion
        self.assertTrue(self.footer_container,
            'container class inside footer missing')

    def test_footer_links(self):
        '''
        Test:
        - there is an Overview link
        - there are links to Terms of Service and Privicy Policy
        - there are few social links
        '''
        footer_container = self.footer_container
        # Build a long string with all the hrefs separated by commas
        combined_href_strings = ''
        for link in footer_container.find_all('a'):
            combined_href_strings += link.get('href') + ','
        self.assertIn( reverse('overview'),
            combined_href_strings,
            "Overview link missing")
        self.assertIn( reverse('termsofuse'),
            combined_href_strings,
            "'Terms of Use' link missing")
        self.assertIn( reverse('privacypolicy'),
            combined_href_strings,
            "'Privacy Policy' link missing")
        self.assertIn(settings.FACEBOOK_LINK,
            combined_href_strings,
            'Facebook link missing')
        self.assertIn(settings.TWITTER_LINK,
            combined_href_strings,
            'Twitter link missing')

    def test_copyright_year(self):
        '''
        Test copyright year
        '''
        copyright_tag = self.footer_container.select_one('.copyright')
        # prettify to handle copyright character as '&copy;'
        # print('copyright_tag = ', copyright_tag.prettify(formatter="html"))
        self.assertTrue(
            str(datetime.datetime.now().year) in copyright_tag.prettify(formatter="html"),
            'Actual year not present in copyright tag')

# 2) First gig thumbnail in home page test
class IndexViewFirstGigThumbnail(TestCase):
    fixtures = ['sixerrapp/fixtures/db.json']

    def setUp(self):
        self.test_user = User.objects.get(username='TonyStark')
        # Created here to avoid "UNIQUE constraint failed"
        Profile.objects.create(user=self.test_user,
                                displayname='TonyStark')

    def test_gig_thumbnails(self):
        '''
        Test for the first gig thumbnail
        Needs to have:
        - .thumbnail class
        - should be at least one but non with status = false
        - photo linked to gig detail
        - .caption class
        - title linked to gig detail
        - author linked to author profile
        - price with .dollar class
        - img tag with .verified-rank class and an image in '/static/img/' folder
        - author has a valid lolrank in Ranking model
        '''
        # Initialization
        test_user = self.test_user
        test_gig = Gig.objects.get(user=test_user)
        resp = self.client.get('/')
        decodedResponse = resp.content.decode('utf-8')
        soup = BeautifulSoup(decodedResponse, 'html.parser')
        # Assertions
        list_of_thumbnails = soup.select('.thumbnail')
        gigs_qty = Gig.objects.filter(status=1).count()
        self.assertEqual(len(list_of_thumbnails), gigs_qty,
            "No appropiate quantity of gig thumbnails shown")
        first_gig_thumbnail = soup.select_one('.thumbnail')
        first_gig_detail_anchor_tag = first_gig_thumbnail.select_one('a[href="/gigs=' + str(test_gig.id) + '/"]')
        # TODO: Remove hack
        # ... could be by simple assertTrue substring in string
        response_hack = HttpResponse(str(first_gig_detail_anchor_tag)) # hack so assertContains can be used
        self.assertContains(
            response_hack,
            '<a href="/gigs=' + str(test_gig.id) + '/">',
            msg_prefix="Link to gig detail missing",
            html=False)
        img_tag_inside_anchor_tag = first_gig_detail_anchor_tag.select_one('img')
        self.assertHTMLEqual(
            str(img_tag_inside_anchor_tag),
            '<img src="' + settings.MEDIA_ROOT + str(test_gig.photo) + '" />',
            "Image in gig detail link missing")
        first_gig_thumbnail_caption = soup.select_one('.thumbnail > .caption')
        title_anchor_tag = first_gig_thumbnail_caption.select_one('a[href="/gigs=' + str(test_gig.id) + '/"]')
        self.assertHTMLEqual(
            str(title_anchor_tag),
            '<a href="/gigs=' + str(test_gig.id) + '/">' + test_gig.title + '</a>',
            "Title linked to gig detail missing")
        author_anchor_tag = first_gig_thumbnail_caption.select_one('a[href="/profile/' + str(test_user) + '/"]')
        self.assertHTMLEqual(
            str(author_anchor_tag),
            '<a href="/profile/' + str(test_user) + '/">' + test_user.profile.displayname + '</a>',
            "Author displayname linked to gig detail missing")
        price = first_gig_thumbnail_caption.select_one('.dollar')
        self.assertHTMLEqual(
            price.get_text(strip=True),
            str(test_gig.price),
            "Gig price missing")
        badge_img_tag = first_gig_thumbnail_caption.select_one('.verified-rank')
        self.assertEqual(
            badge_img_tag.name,
            'img',
            "Verified rank badge image tag missing")
        self.assertEqual(
            '/static/img/' in badge_img_tag['src'],
            True,
            "Verified rank badge image path does not contains '/static/img/' string")
        self.assertHTMLEqual(
            str(badge_img_tag.next_sibling),
            test_user.ranking.get_lolrank_display(),
            "Gig author rank name missing")

# 3) Logged in dropdown menu and notification tests
class LoggedInAndNotificationTest(TestCase):
    fixtures = ['sixerrapp/fixtures/db.json']

    def setUp(self):
        self.test_user = User.objects.get(username='TonyStark')
        # Created here to avoid "UNIQUE constraint failed"
        Profile.objects.create(user=self.test_user,
                                displayname='TonyStark',
                                avatar='https://graph.facebook.com/110632479513964/picture?width=400&height=400')
        login = self.client.force_login(self.test_user)

    def test_logged_in_dropdown_menu(self):
        '''
        Test Logged in dropdown menu
        '''
        # Initialization
        resp = self.client.get('/')
        decodedResponse = resp.content.decode('utf-8')
        soup = BeautifulSoup(decodedResponse, 'html.parser')
        # Assertions
        dropdown_tag = soup.select_one('.navbar .container li.dropdown')
        # print('dropdown_tag = ',dropdown_tag)
        username_tag = dropdown_tag.select_one('.nav-username')
        self.assertTrue(username_tag,
                "username missing")
        dropdown_menu_tag = dropdown_tag.select_one('ul.dropdown-menu')
        self.assertTrue(dropdown_menu_tag,
                "dropdown-menu missing")
        # Build a long string with all the hrefs separated by commas
        combined_href_strings = ''
        for link in dropdown_menu_tag.find_all('a'):
            combined_href_strings += link.get('href') + ','
        self.assertIn( reverse('create_gig'),
            combined_href_strings,
            "'Create gig' link missing")
        self.assertIn( reverse('my_gigs'),
            combined_href_strings,
            "'My Gigs' link missing")
        # -------
        self.assertIn( reverse('my_sales'),
            combined_href_strings,
            "'My Sales' link missing")
        self.assertIn( reverse('my_purchases'),
            combined_href_strings,
            "'My Purchases' link missing")
        # -------
        self.assertIn( reverse('profile', kwargs={'username': self.test_user.username}),
            combined_href_strings,
            "'My Profile' link missing")
        self.assertIn( reverse('my_conversations'),
            combined_href_strings,
            "'My Conversations' link missing")
        # ------
        self.assertIn( reverse('auth:logout') + '?next=',
            combined_href_strings,
            "'Logout' link missing")

    def test_NO_notification(self):
        '''
        Test there is no red bubble notification when there are no unread posts
        '''
        # Initialization
        resp = self.client.get('/')
        decodedResponse = resp.content.decode('utf-8')
        soup = BeautifulSoup(decodedResponse, 'html.parser')
        # Assertions
        dropdown_tag = soup.select_one('.navbar .container li.dropdown')
        badge_tags = dropdown_tag.select('.badge')
        # print('badge_tags = ', badge_tags)
        # All badge tags must have 'hidden' class
        found_not_hidden = False
        for badge_tag in badge_tags:
            if not None is badge_tag.select_one('.hidden'):
                # print('badge_tag.select_one(".hidden") = ', badge_tag.select_one('.hidden'))
                found_not_hidden = True
                break
        self.assertFalse(found_not_hidden,
            "There is an unread notification badge when there are no unread posts")

    def test_notifications_when_unread_post(self):
        '''
        Test there notifications when there is at least one unread post
        Only check for:
        - There is a notification badge near the avatar and in 'My Sales' dropdown link
        - There is no notification badge in 'My Purchases' nor 'My Conversations' links
        Because, the user is the gig author and the post is from the buyer
        '''
        # Notification setUp
        test_buyer = User.objects.get(username='elingerojo')
        test_gig = Gig.objects.get(title='Cinderella shoe')
        test_purchase = Purchase.objects.create(gig=test_gig,
                                buyer=test_buyer,
                                status='OR',
                                title=test_gig.title,
                                category=test_gig.get_category_display,
                                description=test_gig.description,
                                photo=test_gig.photo)
        test_chatentry = Chatentry.objects.create(pid=test_purchase,
                                poster=test_buyer,
                                content='Hello')
        # Initialization
        resp = self.client.get('/')
        decodedResponse = resp.content.decode('utf-8')
        soup = BeautifulSoup(decodedResponse, 'html.parser')
        # Assertions
        dropdown_tag = soup.select_one('.navbar .container li.dropdown')
        avatar_badge_tag = dropdown_tag.select_one('.dropdown-toggle .badge')
        self.assertTrue(not avatar_badge_tag.select_one('.hidden'),
            "There is no unread notification badge near avatar when there is an unread purchase post")

        # 'hidden' class should NOT be present only in 'My Sales'
        # ...so my_sales_OK is the only boolean with the assignment inverted
        my_sales_OK = False
        my_purchases_OK = False
        my_conversations_OK = False
        dropdown_menu_tag = dropdown_tag.select_one('.dropdown-menu')
        for link in dropdown_menu_tag.find_all('a'):
            if link.get('href') == reverse('my_sales'):
                my_sales_OK = False if 'hidden' in link.select_one('.badge').get('class') else True
            if link.get('href') == reverse('my_purchases'):
                my_purchases_OK = True if 'hidden' in link.select_one('.badge').get('class') else False
            if link.get('href') == reverse('my_conversations'):
                my_conversations_OK = True if 'hidden' in link.select_one('.badge').get('class') else False
        self.assertTrue( my_sales_OK,
            "There is a post in 'My Sales' but notification is missing")
        self.assertTrue( my_purchases_OK,
            "There is no post in 'My Purchases' but there is a notification")
        self.assertTrue( my_conversations_OK,
            "There is no post in 'My Conversations' but there is a notification")
