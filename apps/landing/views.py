"""
Landing app views.

LandingView — TemplateView serving the homepage (index.html).
              Passes pricing plan context for the pricing section.
              No login required.
"""
from django.views.generic import TemplateView

class LandingView(TemplateView):
    template_name = "landing/index.html"
