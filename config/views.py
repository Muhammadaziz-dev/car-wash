# Add to urls.py temporarily
from django.urls import get_resolver


def debug_urls(request):
    from django.http import HttpResponse
    url_list = sorted([str(pattern) for pattern in get_resolver().url_patterns])
    return HttpResponse("<br>".join(url_list))


# Add to urlpatterns
