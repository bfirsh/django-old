"""
Tests for the search() queryset method and the __search field lookup.
"""

import datetime
from django.db import models

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline', search_index=True, search_weight=1)
    pub_date = models.DateTimeField()
    body = models.TextField(search_index=True, search_weight=0.3)

    class Meta:
        ordering = ('pub_date','headline')

    def __unicode__(self):
        return self.headline

__test__ = {'API_TESTS': """
>>> Article.objects.search('alpha')
[<Article: Django 1.1 alpha 1 released>, <Article: Django 1.1 beta released, wombat>]

>>> Article.objects.search('alpha').filter(headline__search='beta')
[<Article: Django 1.1 beta released, wombat>]

>>> Article.objects.search('django').search('perfectionists')
[<Article: Django 1.0 released!>]

>>> Article.objects.search('beta').order_by('-search__relevance')
[<Article: Django 1.1 beta released, wombat>, <Article: Django 1.1 alpha 1 released>]

>>> Article.objects.search('beta')[0].search__relevance > 0
True

>>> Article.objects.filter(pub_date__lt=datetime.date(2009, 1, 1)).search('django')
[<Article: Django 1.0 released!>, <Article: Django 1.0.1 released!>, <Article: Django 1.0.2 released>]

>>> Article.objects.search('beta').count()
2

>>> Article.objects.filter(body__search='prague')
[<Article: EuroDjangoCon 2009>]

>>> Article.objects.filter(headline__search='prague')
[]

>>> Article.objects.filter(headline__search='alpha').count()
1

"""
}

from django.conf import settings

building_docs = getattr(settings, 'BUILDING_DOCS', False)

if building_docs or 'postgresql' in settings.DATABASE_ENGINE:
    __test__['API_TESTS'] += """
# Search weighting on headline
>>> Article.objects.search('wombat').order_by('-search__relevance')
[<Article: Django 1.1 beta released, wombat>, <Article: Django 1.1 alpha 1 released>]

"""