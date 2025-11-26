from django.db import models
from django.utils import timezone

# ==========================================
# 1. MÓDULO DE CONFIGURACIÓN Y SUNAT
# ==========================================
class Empresa(models.Model):
    """
    Datos del negocio local. El Chatbot usa esto para saber quién eres.
    """
    REGIMENES = [
        ('RUS', 'Nuevo RUS (Cuota fija)'),
        ('MYPE', 'MYPE Tributario'),
        ('RER', 'Régimen Especial'),
    ]
    
    ruc = models.CharField(max_length=11, unique=True, default="20601234567")
    razon_social = models.CharField(max_length=200, default="Mi Bodega SAC")
    regimen = models.CharField(max_length=10, choices=REGIMENES, default='RUS')
    
    # Campo para el "Bot": Deuda antigua que no está en el sistema actual
    deuda_historica_sunat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Credenciales Odoo (Simuladas para la demo)
    odoo_url = models.CharField(max_length=200, blank=True, help_text="Endpoint de AWS")
    
    def __str__(self):
        return f"{self.razon_social} ({self.ruc})"

# ==========================================
# 2. MÓDULO DE INVENTARIO (Con espejo Odoo)
# ==========================================
class Producto(models.Model):
    # --- Datos Locales ---
    nombre = models.CharField(max_length=200)
    #codigo_barras = models.CharField(max_length=50, unique=True, blank=True)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=5, help_text="Para alertas de IA")
    
    # --- Datos Financieros (Clave para tu Dashboard) ---
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2) # P.V.P
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2) # Costo real (Odoo)
    
    # --- Conexión AWS Odoo ---
    odoo_id = models.IntegerField(null=True, blank=True, help_text="ID externo en la BD de Odoo")
    ultima_sincronizacion = models.DateTimeField(auto_now=True)

    def ganancia_estimada(self):
        """Calcula cuánto ganas por unidad (Rentabilidad)"""
        return self.precio_venta - self.costo_unitario

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_actual})"

# ==========================================
# 3. MÓDULO DE VENTAS (Transacciones)
# ==========================================
class Venta(models.Model):
    SYNC_STATES = [
        ('PENDING', '🟡 Pendiente (Local)'),
        ('SYNCED', '🟢 Sincronizado (AWS)'),
        ('ERROR', '🔴 Error de Conexión'),
    ]

    fecha = models.DateTimeField(default=timezone.now)
    
    # Totales calculados automáticamente
    total_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ganancia_total = models.DecimalField(max_digits=10, decimal_places=2, default=0) # KPI Financiero
    
    # Datos para SUNAT
    es_factura = models.BooleanField(default=False)
    cliente_dni_ruc = models.CharField(max_length=11, blank=True, null=True)

    # --- Conexión AWS Odoo ---
    sync_status = models.CharField(max_length=20, choices=SYNC_STATES, default='PENDING')
    odoo_order_id = models.CharField(max_length=50, blank=True, null=True) # ID de la venta en Odoo
    log_respuesta = models.TextField(blank=True, help_text="Respuesta del servidor Odoo")

    def __str__(self):
        return f"Venta #{self.id} - {self.sync_status}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) # Precio al momento de venta
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        # Auto-calcular subtotal
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"