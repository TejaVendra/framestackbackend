from rest_framework import generics
from .models import Template
from .serializers import TemplateSerializer



class TemplateListView(generics.ListAPIView):
    queryset = Template.objects.all().order_by('-created_at')
    serializer_class = TemplateSerializer
    
 
