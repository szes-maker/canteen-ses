from django.urls import path

from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.login, name='login'),
    path('query/<int:year>/<int:month>/', views.query, name='query'),
    path('menu/<int:year>/<int:month>/<int:day>/', views.menu, name='menu'),
    path('submit/<int:year>/<int:month>/<int:day>/', views.submit, name='submit'),
    path('logout/', views.logout, name='logout'),
]
