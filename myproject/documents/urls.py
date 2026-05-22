from django.urls import path

from documents.views import DocumentDetailView, DocumentListView, DocumentUploadView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('', DocumentListView.as_view(), name='document-list'),
    path('<str:doc_id>/', DocumentDetailView.as_view(), name='document-detail'),
]
