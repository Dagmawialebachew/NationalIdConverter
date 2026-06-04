"""
apps/conversions/urls.py
========================
URL configuration for the conversions app.

Included in config/urls.py under the 'convert/' prefix:
    path("convert/", include("apps.conversions.urls", namespace="conversions")),

Resulting URLs:
    POST /convert/                        → UploadView   (name: conversions:upload)
    GET  /convert/result/<uuid>/          → ResultView   (name: conversions:result)
    GET  /convert/download/<uuid>/        → DownloadView (name: conversions:download)
"""

from django.urls import path

from apps.conversions import views

app_name = "conversions"

urlpatterns = [
    path(
        "",
        views.UploadView.as_view(),
        name="upload",
    ),
    path(
        "result/<uuid:pk>/",
        views.ResultView.as_view(),
        name="result",
    ),
    path(
        "download/<uuid:pk>/",
        views.DownloadView.as_view(),
        name="download",
    ),
    
    path('image/<uuid:pk>/', views.ImageView.as_view(), name='image'),
    path("adjust/<uuid:pk>/", views.AdjustView.as_view(), name="adjust"),
    path('api/credits/', views.get_current_credits_api, name='api_credits'),
]