from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.urls import reverse, resolve

from .context_processors import seo_defaults
from .models import Project
from .views import _search_projects, global_search, robots_txt


class SeoAndSearchTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='alice', password='testpass123')
        self.project = Project.objects.create(
            author=self.user,
            title='Python Bot Project',
            description='Telegram uchun aqlli bot loyihasi',
            image='project_thumbnails/test.jpg',
            youtube_link='https://youtu.be/dQw4w9WgXcQ',
            category='web',
            price=0,
            is_frozen=False,
        )

    def test_profile_by_username_route_works(self):
        url = reverse('profile_by_username', args=[self.user.username])
        self.assertEqual(url, f'/u/{self.user.username}/')

    def test_project_detail_route_uses_slug(self):
        url = reverse('project_detail', args=[self.project.slug])
        self.assertIn(self.project.slug, url)

    def test_home_search_helper_works_on_default_db(self):
        results = _search_projects('Python')
        self.assertTrue(results.filter(pk=self.project.pk).exists())

    def test_global_search_route_points_to_expected_view(self):
        match = resolve(reverse('global_search'))
        self.assertEqual(match.func, global_search)

    def test_robots_and_sitemap_endpoints(self):
        request = self.factory.get('/robots.txt', HTTP_HOST='testserver')
        response = robots_txt(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Sitemap:', response.content.decode('utf-8'))
        self.assertEqual(reverse('django.contrib.sitemaps.views.sitemap'), '/sitemap.xml')

    def test_seo_context_for_public_page(self):
        request = self.factory.get('/', HTTP_HOST='testserver')
        request.resolver_match = resolve('/')
        seo = seo_defaults(request)['seo']

        self.assertIn('DevTube', seo['title'])
        self.assertEqual(seo['robots'], 'index, follow')
        self.assertTrue(seo['canonical_url'].startswith('http'))

    def test_seo_context_for_private_page_is_noindex(self):
        request = self.factory.get('/inbox/', HTTP_HOST='testserver')
        request.resolver_match = resolve('/inbox/')
        seo = seo_defaults(request)['seo']

        self.assertEqual(seo['robots'], 'noindex, nofollow')

