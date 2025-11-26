from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction  # <--- IMPORTANTE
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta

# Importamos tus modelos y serializers
from .models import Producto, Venta, DetalleVenta, Empresa
from .serializers import ProductoSerializer, VentaSerializer
from .odoo_service import OdooClient

# =================================================
# 1. GESTIÓN DE PRODUCTOS (INVENTARIO + ODOO)
# =================================================
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all().order_by('-id')
    serializer_class = ProductoSerializer

    def perform_create(self, serializer):
        producto = serializer.save()
        try:
            client = OdooClient()
            odoo_id = client.crear_producto(producto)
            if odoo_id:
                producto.odoo_id = odoo_id
                producto.save()
                print(f"✅ Sincronizado con Odoo (ID: {odoo_id})")
        except Exception as e:
            print(f"❌ Error Odoo: {e}")

# =================================================
# 2. REGISTRAR VENTA (¡LA CLASE QUE FALTABA!)
# =================================================
class RegistrarVentaView(APIView):
    def post(self, request):
        # Data esperada: { "items": [ {"id": 1, "cantidad": 2} ], "total": 50.00 }
        data = request.data
        try:
            with transaction.atomic():
                # 1. Crear Cabecera
                venta = Venta.objects.create(
                    total_venta=data.get('total', 0),
                    ganancia_total=0
                )
                
                ganancia_acumulada = 0
                
                # 2. Procesar Items
                for item in data.get('items', []):
                    prod = Producto.objects.get(id=item['id'])
                    cantidad = item['cantidad']
                    
                    # Validar Stock
                    if prod.stock_actual < cantidad:
                        raise Exception(f"Stock insuficiente para {prod.nombre}")
                    
                    # Descontar Stock
                    prod.stock_actual -= cantidad
                    prod.save()
                    
                    # Cálculos Financieros
                    subtotal = prod.precio_venta * cantidad
                    costo = prod.costo_unitario * cantidad
                    ganancia_acumulada += (subtotal - costo)
                    
                    # Guardar Detalle
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=prod,
                        cantidad=cantidad,
                        precio_unitario=prod.precio_venta,
                        subtotal=subtotal
                    )
                
                # 3. Guardar Ganancia Real
                venta.ganancia_total = ganancia_acumulada
                venta.save()
                
                return Response({"mensaje": "Venta registrada", "id": venta.id}, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# =================================================
# 3. DASHBOARD DE VENTAS Y FINANZAS
# =================================================
class DashboardView(APIView):
    def get(self, request):
        hoy = timezone.now().date()
        
        ventas_hoy_qs = Venta.objects.filter(fecha__date=hoy)
        total_ventas = ventas_hoy_qs.aggregate(Sum('total_venta'))['total_venta__sum'] or 0
        ganancia_dia = ventas_hoy_qs.aggregate(Sum('ganancia_total'))['ganancia_total__sum'] or 0
        
        stock_bajo = Producto.objects.filter(stock_actual__lte=F('stock_minimo')).count()
        
        return Response({
            "kpis": {
                "ventas_hoy": f"S/ {total_ventas:.2f}",
                "ganancia_hoy": f"S/ {ganancia_dia:.2f}",
                "pedidos_hoy": ventas_hoy_qs.count(),
                "productos_stock_bajo": stock_bajo
            },
            "sunat": {
                "estado": "🟢 En Rango (RUS 1)" if total_ventas < 200 else "🟡 Cuidado (Límite RUS)",
                "mensaje": "Proyección fiscal controlada."
            }
        })

# =================================================
# 4. CHATBOT SUNAT
# =================================================
class ChatbotView(APIView):
    def post(self, request):
        mensaje = request.data.get('mensaje', '').lower()
        empresa = Empresa.objects.first()
        
        respuesta = "🤖 Soy AliadoMype. Pregúntame: 'deuda', 'ventas' o 'stock'."
        
        if not empresa:
            return Response({"bot_response": "⚠️ Error: Configura tu Empresa en el Admin."})

        if 'deuda' in mensaje or 'sunat' in mensaje:
            if empresa.deuda_historica_sunat > 0:
                respuesta = f"🚨 Tienes deuda de **S/ {empresa.deuda_historica_sunat}**. RUC: {empresa.ruc}."
            else:
                respuesta = f"✅ La empresa **{empresa.razon_social}** está limpia con SUNAT."

        elif 'ventas' in mensaje:
             hoy = timezone.now().date()
             total = Venta.objects.filter(fecha__date=hoy).aggregate(Sum('total_venta'))['total_venta__sum'] or 0
             respuesta = f"💰 Ventas de hoy: **S/ {total:.2f}**."
             
        elif 'stock' in mensaje:
            bajos = Producto.objects.filter(stock_actual__lte=F('stock_minimo'))
            if bajos.exists():
                respuesta = f"⚠️ {bajos.count()} productos con stock crítico."
            else:
                respuesta = "📦 Inventario OK."

        return Response({"bot_response": respuesta})