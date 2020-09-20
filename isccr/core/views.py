from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.base import RedirectView

from isccr.core.models import IsccID


def index(request):
    html = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>ISCC Resolver</title>
      </head>
      <body>
        <p>try /<iscc-id></p>
      </body>
    </html>
    """
    return HttpResponse(html)


def resovle(request, iscc_id):
    iscc_id_obj = get_object_or_404(IsccID, pk=iscc_id)

    return redirect(iscc_id_obj.get_admin_url())


class IsccRedirectView(RedirectView):

    permanent = False
    query_string = True
    pattern_name = "admin:core_isccid_change"

    def get_redirect_url(self, *args, **kwargs):
        article = get_object_or_404(IsccID, pk=kwargs["pk"])
        return super().get_redirect_url(*args, **kwargs)
