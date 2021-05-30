from django.core import serializers
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.base import RedirectView

from isccr.core.models import IsccID


def index(request):
    html = """
    <!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hello Bulma!</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.2/css/bulma.min.css">
  </head>
  <body>
  <section class="section">
    <div class="container">
      <h1 class="title">
        ISCC MetaRegistry - MVP
      </h1>
      <p class="subtitle">
        Try https://iscc.in/&lt;iscc-id&gt; or <a href="/browse/">/browse</a> ISCC Short-IDs
      </p>
    </div>
  </section>
  </body>
</html>
"""
    return HttpResponse(html)


def resovle(request, iscc_id):
    iscc_id_obj = get_object_or_404(IsccID, pk=iscc_id)

    return redirect(iscc_id_obj.get_admin_url())


def lookup(request, iscc_code, actor):
    iscc_id_obj = get_object_or_404(IsccID, iscc_code=iscc_code, actor=actor)
    return JsonResponse(
        {"iscc_id": iscc_id_obj.iscc_id},
    )


class IsccRedirectView(RedirectView):

    permanent = False
    query_string = True
    pattern_name = "admin:core_isccid_change"

    def get_redirect_url(self, *args, **kwargs):
        article = get_object_or_404(IsccID, pk=kwargs["pk"])
        return super().get_redirect_url(*args, **kwargs)
