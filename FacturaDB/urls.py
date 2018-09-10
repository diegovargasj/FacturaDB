from django.urls import path

from FacturaDB import views

urlpatterns = [
	path('', views.search, name='search'),
	path('groupsearch', views.search_accum, name='search_groups'),
	path('search', views.search_all, name='search_all'),
]