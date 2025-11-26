import xmlrpc.client

class OdooClient:
    def __init__(self):
        # ====================================================
        # 🟢 TUS CREDENCIALES (Extraídas de tu imagen)
        # ====================================================
        
        self.url = 'http://18.216.109.149:8069/' 
        
        # 2. EL NOMBRE DE LA BASE DE DATOS
        self.db = 'erpcrm_db'
        
        # 3. EL USUARIO (Es el Email que pusiste)
        self.username = '2019110453@udh.edu.pe'
        
        # 4. LA CONTRASEÑA (No el Master Password, sino la del usuario)
        self.password = 'admin123'
        
        # ====================================================
        
        # Conexión a los endpoints de Odoo
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        self.uid = None

    def conectar(self):
        """Intenta hacer login en Odoo y obtener el UID"""
        try:
            # Autenticación XML-RPC estándar
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            
            if self.uid:
                print(f"✅ CONECTADO A ODOO AWS (UID: {self.uid})")
                return True
            else:
                print("❌ ERROR: Credenciales de Odoo incorrectas.")
                return False
        except Exception as e:
            print(f"❌ ERROR DE CONEXIÓN: {e}")
            print("💡 TIP: Revisa si el puerto 8069 está abierto en el Security Group de AWS.")
            return False

    def crear_producto(self, producto_django):
        """Envía el producto local a Odoo AWS"""
        if not self.uid:
            if not self.conectar(): return None

        try:
            # Mapeo de campos: Django -> Odoo
            datos_odoo = {
                'name': producto_django.nombre,
                'list_price': float(producto_django.precio_venta),     
                'standard_price': float(producto_django.costo_unitario),
                'type': 'consu', # Tipo consumible
            }

            # Llamada XML-RPC para crear
            odoo_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'product.product', 'create', 
                [datos_odoo]
            )
            print(f"📦 PRODUCTO CREADO EN AWS ODOO con ID: {odoo_id}")
            return odoo_id
            
        except Exception as e:
            print(f"❌ Error creando producto en Odoo: {e}")
            return None