from django.contrib import admin
from django.urls import path
from website.views import testar_celery

urlpatterns = [
    path('admin/', admin.site.urls),
    path('testar-celery/<int:configuracao_id>/', testar_celery, name='testar_celery'),
]
