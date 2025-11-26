from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, DashboardView, ChatbotView, RegistrarVentaView # Asegúrate de importar RegistrarVentaView si la tienes en views

router = DefaultRouter()
router.register(r'productos', ProductoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view()), # <--- NUEVA RUTA DASHBOARD
    path('chat/', ChatbotView.as_view()),        # <--- NUEVA RUTA CHAT
    # path('vender/', RegistrarVentaView.as_view()), # Descomenta si tienes la vista de venta
]