from django.conf.urls.defaults import *
from NAGMAP.map.views import *
urlpatterns = patterns('',
    # Example:
    # (r'^NAGMAP/', include('NAGMAP.foo.urls')),

    # Uncomment this for admin:
#     (r'^admin/', include('django.contrib.admin.urls')),
    (r'^dnagmap/graph/$','NAGMAP.map.views.graph'),
    (r'^dnagmap/graph/(?P<start>.*)/$','NAGMAP.map.views.graph'),
    (r'^dnagmap/stree/$','NAGMAP.map.views.tree'),
    (r'^dnagmap/stree/(?P<start>.*)/$','NAGMAP.map.views.tree'),
    (r'^dnagmap/tree/$','NAGMAP.map.views.tree'),
    (r'^dnagmap/tree/(?P<start>.*)/$','NAGMAP.map.views.tree'),
)

#from NAGMAP.map.models import *