# projects/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Project
class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        # Faqat sizda ANIQ BOR bo'lgan sahifalar nomini yozing:
        return ['home', 'trending', 'contact', 'help', 'announcements']

    def location(self, item):
        return reverse(item)

class ProjectSitemap(Sitemap):
    priority = 0.9  # Loyihalar muhimroq
    changefreq = 'weekly'

    def items(self):
        # Faqat muzlatilmagan (yashirilmagan) loyihalarni Googlega beramiz
        return Project.objects.filter(is_frozen=False).order_by('-created_at')

    def lastmod(self, obj):
        return obj.created_at