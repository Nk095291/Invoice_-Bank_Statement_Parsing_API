from django.urls import path

from documents.views import DocumentDetailView, DocumentUploadView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('<uuid:doc_id>/', DocumentDetailView.as_view(), name='document-detail'),
]
