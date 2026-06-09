"""
Generador idempotente del dataset de prueba para Inmobiliaria RAG.

Genera y carga en MongoDB:
  - 13 usuarios, 3 agencias
  - 20 propiedades con coordenadas GeoJSON reales de Manizales
  - 20 publicaciones (listings)
  - 15 contratos con cláusulas
  - 52 media_assets
  - 20 reseñas
  - 10 solicitudes de mantenimiento
  - 15 sesiones de chat
  - 100 documentos en documents_repository (base para el RAG)

Ejecutar:
    cd python
    python generate_dataset.py
"""

import sys
from datetime import datetime, timezone

from pymongo import UpdateOne

sys.path.insert(0, ".")
from config import settings
from database import get_db, close


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert(collection, doc: dict):
    collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)


# ---------------------------------------------------------------------------
# Datos maestros
# ---------------------------------------------------------------------------

USERS = [
    {"_id": "u_001", "nombre": "Carlos Ríos",        "email": "carlos.rios@gmail.com",    "roles": ["propietario"]},
    {"_id": "u_002", "nombre": "María Ospina",        "email": "maria.ospina@gmail.com",   "roles": ["propietario"]},
    {"_id": "u_003", "nombre": "Jorge Salazar",       "email": "jorge.salazar@gmail.com",  "roles": ["propietario"]},
    {"_id": "u_004", "nombre": "Lucía Montoya",       "email": "lucia.montoya@gmail.com",  "roles": ["propietario"]},
    {"_id": "u_005", "nombre": "Pedro Gutiérrez",     "email": "pedro.gutierrez@gmail.com","roles": ["propietario"]},
    {"_id": "u_006", "nombre": "Ana Ríos",            "email": "ana.rios@realty.co",       "roles": ["agente"],       "agency_id": "ag_001"},
    {"_id": "u_007", "nombre": "Felipe Castaño",      "email": "felipe.castano@realty.co", "roles": ["agente"],       "agency_id": "ag_001"},
    {"_id": "u_008", "nombre": "Sandra Mejía",        "email": "sandra.mejia@casas.co",    "roles": ["agente"],       "agency_id": "ag_002"},
    {"_id": "u_009", "nombre": "Tomás Vélez",         "email": "tomas.velez@casas.co",     "roles": ["agente"],       "agency_id": "ag_002"},
    {"_id": "u_010", "nombre": "Catalina Arango",     "email": "catalina.arango@home.co",  "roles": ["agente"],       "agency_id": "ag_003"},
    {"_id": "u_011", "nombre": "Andrés Torres",       "email": "andres.torres@hotmail.com","roles": ["arrendatario"]},
    {"_id": "u_012", "nombre": "Valentina López",     "email": "valentina.lopez@gmail.com","roles": ["arrendatario"]},
    {"_id": "u_013", "nombre": "Sebastián Cano",      "email": "sebastian.cano@outlook.com","roles": ["arrendatario"]},
]

AGENCIES = [
    {"_id": "ag_001", "nombre": "Realty Manizales",       "agents_ids": ["u_006", "u_007"]},
    {"_id": "ag_002", "nombre": "Casas y Fincas Caldas",  "agents_ids": ["u_008", "u_009"]},
    {"_id": "ag_003", "nombre": "HomeMatch Colombia",     "agents_ids": ["u_010"]},
]

# (barrio, lat, lng, estrato_base)
NEIGHBORHOODS = {
    "El Cable":   (5.0647, -75.5011, 5),
    "Milán":      (5.0678, -75.4948, 4),
    "Chipre":     (5.0751, -75.5089, 4),
    "Palermo":    (5.0612, -75.5097, 3),
    "La Enea":    (5.0891, -75.4677, 3),
    "Centro":     (5.0689, -75.5144, 3),
    "Versalles":  (5.0721, -75.5034, 4),
    "Palogrande": (5.0598, -75.5061, 5),
    "Belén":      (5.0802, -75.4823, 4),
    "La Sultana": (5.0566, -75.5152, 3),
}

PROPERTY_CONFIGS = [
    {"_id": "prop_001", "owner": "u_001", "tipo": "apartamento", "barrio": "El Cable",   "area": 75,  "hab": 2, "ban": 2, "piso": 5,  "admin": 180000, "park": True,  "masc": False, "agent": "u_006"},
    {"_id": "prop_002", "owner": "u_001", "tipo": "apartamento", "barrio": "El Cable",   "area": 90,  "hab": 3, "ban": 2, "piso": 8,  "admin": 210000, "park": True,  "masc": True,  "agent": "u_006"},
    {"_id": "prop_003", "owner": "u_002", "tipo": "apartamento", "barrio": "Milán",      "area": 60,  "hab": 2, "ban": 1, "piso": 3,  "admin": 150000, "park": False, "masc": True,  "agent": "u_007"},
    {"_id": "prop_004", "owner": "u_002", "tipo": "apartamento", "barrio": "Milán",      "area": 48,  "hab": 1, "ban": 1, "piso": 2,  "admin": 120000, "park": False, "masc": False, "agent": "u_007"},
    {"_id": "prop_005", "owner": "u_003", "tipo": "casa",        "barrio": "Chipre",     "area": 140, "hab": 4, "ban": 3, "piso": 1,  "admin": 0,      "park": True,  "masc": True,  "agent": "u_008"},
    {"_id": "prop_006", "owner": "u_003", "tipo": "apartamento", "barrio": "Chipre",     "area": 80,  "hab": 2, "ban": 2, "piso": 6,  "admin": 200000, "park": True,  "masc": False, "agent": "u_008"},
    {"_id": "prop_007", "owner": "u_004", "tipo": "apartamento", "barrio": "Palermo",    "area": 65,  "hab": 2, "ban": 1, "piso": 4,  "admin": 160000, "park": False, "masc": True,  "agent": "u_009"},
    {"_id": "prop_008", "owner": "u_004", "tipo": "apartamento", "barrio": "Palermo",    "area": 55,  "hab": 1, "ban": 1, "piso": 1,  "admin": 130000, "park": False, "masc": False, "agent": "u_009"},
    {"_id": "prop_009", "owner": "u_005", "tipo": "casa",        "barrio": "La Enea",    "area": 180, "hab": 5, "ban": 3, "piso": 1,  "admin": 0,      "park": True,  "masc": True,  "agent": "u_010"},
    {"_id": "prop_010", "owner": "u_005", "tipo": "apartamento", "barrio": "La Enea",    "area": 70,  "hab": 2, "ban": 2, "piso": 7,  "admin": 170000, "park": True,  "masc": False, "agent": "u_010"},
    {"_id": "prop_011", "owner": "u_001", "tipo": "local",       "barrio": "Centro",     "area": 50,  "hab": 0, "ban": 1, "piso": 1,  "admin": 90000,  "park": False, "masc": False, "agent": "u_006"},
    {"_id": "prop_012", "owner": "u_002", "tipo": "apartamento", "barrio": "Versalles",  "area": 85,  "hab": 3, "ban": 2, "piso": 9,  "admin": 190000, "park": True,  "masc": True,  "agent": "u_007"},
    {"_id": "prop_013", "owner": "u_003", "tipo": "apartamento", "barrio": "Palogrande", "area": 100, "hab": 3, "ban": 2, "piso": 11, "admin": 220000, "park": True,  "masc": False, "agent": "u_008"},
    {"_id": "prop_014", "owner": "u_004", "tipo": "casa",        "barrio": "Belén",      "area": 120, "hab": 3, "ban": 2, "piso": 1,  "admin": 0,      "park": True,  "masc": True,  "agent": "u_009"},
    {"_id": "prop_015", "owner": "u_005", "tipo": "apartamento", "barrio": "La Sultana", "area": 58,  "hab": 2, "ban": 1, "piso": 3,  "admin": 140000, "park": False, "masc": True,  "agent": "u_010"},
    {"_id": "prop_016", "owner": "u_001", "tipo": "apartamento", "barrio": "El Cable",   "area": 110, "hab": 3, "ban": 3, "piso": 12, "admin": 240000, "park": True,  "masc": False, "agent": "u_006"},
    {"_id": "prop_017", "owner": "u_002", "tipo": "local",       "barrio": "Milán",      "area": 80,  "hab": 0, "ban": 2, "piso": 1,  "admin": 110000, "park": True,  "masc": False, "agent": "u_007"},
    {"_id": "prop_018", "owner": "u_003", "tipo": "apartamento", "barrio": "Chipre",     "area": 72,  "hab": 2, "ban": 2, "piso": 4,  "admin": 175000, "park": True,  "masc": True,  "agent": "u_008"},
    {"_id": "prop_019", "owner": "u_004", "tipo": "apartamento", "barrio": "Versalles",  "area": 88,  "hab": 3, "ban": 2, "piso": 6,  "admin": 195000, "park": True,  "masc": False, "agent": "u_009"},
    {"_id": "prop_020", "owner": "u_005", "tipo": "casa",        "barrio": "Palogrande", "area": 200, "hab": 5, "ban": 4, "piso": 1,  "admin": 0,      "park": True,  "masc": True,  "agent": "u_010"},
]

# Canon de arriendo por tipo/tamaño (COP)
def canon_arriendo(tipo: str, area: int, hab: int) -> int:
    if tipo == "local":
        return 100000 * (area // 10 + 5)
    if tipo == "casa":
        return 800000 + 50000 * hab + 5000 * area
    # apartamento
    if hab == 1:
        return 850000 + 3000 * area
    if hab == 2:
        return 1200000 + 4000 * area
    return 1800000 + 5000 * area


def precio_venta(tipo: str, area: int, estrato: int) -> int:
    base = {"local": 3_500_000, "casa": 4_200_000, "apartamento": 3_800_000}.get(tipo, 3_500_000)
    return base * area * (1 + (estrato - 3) * 0.1)


# ---------------------------------------------------------------------------
# Generadores de texto de documentos (realistas, en español colombiano)
# ---------------------------------------------------------------------------

def descripcion_propiedad(cfg: dict) -> str:
    nb = cfg["barrio"]
    lat, lng, estrato = NEIGHBORHOODS[nb]
    area, hab, ban = cfg["area"], cfg["hab"], cfg["ban"]
    tipo = cfg["tipo"]
    park_txt = "parqueadero privado techado" if cfg["park"] else "sin parqueadero (disponible comunal)"
    masc_txt = ("Sí, se aceptan hasta 2 mascotas pequeñas (máximo 8 kg), previa firma de cláusula adicional."
                if cfg["masc"] else "No se permiten mascotas por reglamento del conjunto.")
    canon = canon_arriendo(tipo, area, hab)
    admin = cfg["admin"]

    tipo_str = {"apartamento": "apartamento", "casa": "casa independiente", "local": "local comercial"}[tipo]
    vista_str = "las montañas del Eje Cafetero" if cfg.get("piso", 1) > 4 else "el jardín y la zona comunal"

    amenidades = ""
    if admin > 0:
        amenidades = "gimnasio equipado, piscina temperada, salón social para eventos, cancha múltiple, portería 24 horas con circuito cerrado de televisión"
    else:
        amenidades = "jardín privado, zona de parqueo para visitantes, acceso controlado"

    servicios_cercanos = {
        "El Cable": "el centro comercial Cable Plaza, la Universidad de Caldas y el Parque del Cable",
        "Milán":    "el sector gastronómico de Milán, el Hospital de Caldas y múltiples rutas de transporte urbano",
        "Chipre":   "el mirador del Chipre, el Estadio Palogrande y el sector financiero de la ciudad",
        "Palermo":  "la Avenida del Centro, colegios de alta calidad y centros de salud",
        "La Enea":  "el aeropuerto La Nubia, zonas industriales y grandes superficies comerciales",
        "Centro":   "la Gobernación de Caldas, juzgados, notarías y todo el centro histórico",
        "Versalles": "el sector universitario, restaurantes y cafeterías del barrio",
        "Palogrande": "la Universidad Nacional sede Manizales, el Estadio y centros comerciales",
        "Belén":    "parques recreativos, iglesias, colegios de cobertura y centros de salud",
        "La Sultana": "el sector de Maltería, grandes superficies y vías de acceso rápido",
    }.get(nb, "múltiples servicios de la ciudad")

    cocina_str = {
        "apartamento": "está integrada a la sala-comedor, con mesón en granito negro, gabinetes en madera laminada, espacio para nevera y lavaplatos doble poceta",
        "casa": "independiente y amplia, con estufa a gas, horno empotrado, área de ropas con zona de lavado y tendedero cubierto",
        "local": "cuenta con zona de preparación y cuarto de servicios adaptable a múltiples usos comerciales",
    }.get(tipo, "funcional y bien iluminada")

    return f"""
{tipo_str.capitalize()} en {nb}, Manizales — Inmobiliaria RAG

DESCRIPCIÓN GENERAL
Excelente {tipo_str} ubicado en el sector de {nb}, uno de los sectores más {
    'exclusivos' if estrato >= 4 else 'reconocidos'} de Manizales, Caldas.
Con {area} metros cuadrados de área construida, este inmueble ofrece {
    f'{hab} habitaciones y {ban} baños completos' if tipo != "local" else f'{ban} baño(s) y amplio espacio comercial'
}, ideal para {'familias o profesionales que buscan calidad y confort' if tipo != 'local' else 'emprendimientos, consultorios u oficinas'}.

El inmueble se encuentra en excelente estado de conservación, {'en el piso ' + str(cfg['piso']) + ' del edificio, ' if tipo == 'apartamento' else ''}con acabados de primera calidad: pisos en cerámica de alto tráfico, pintura en vinilo lavable y closets empotrados en todas las habitaciones.

ILUMINACIÓN Y VENTILACIÓN
Gracias a su orientación estratégica, el inmueble recibe abundante luz natural durante la mayor parte del día. Los amplios ventanales permiten disfrutar de una vista privilegiada hacia {vista_str}. La ventilación cruzada garantiza un ambiente fresco sin necesidad de aire acondicionado.

COCINA Y ZONA DE SERVICIOS
La cocina {cocina_str}. La zona de ropas está dotada con punto de lavadora, secadero cubierto y espacio para electrodomésticos.

CARACTERÍSTICAS PRINCIPALES
- Área total: {area} m²
- {'Habitaciones: ' + str(hab) if tipo != 'local' else 'Área abierta de uso comercial'}
- Baños completos: {ban}
- Piso: {cfg.get('piso', 1)}{'° de un edificio de ' + str(cfg.get('piso', 1) + 3) + ' pisos' if tipo == 'apartamento' else ''}
- Parqueadero: {park_txt}
- Estrato socioeconómico: {estrato}
- Mascotas: {masc_txt}

CONJUNTO RESIDENCIAL Y ZONAS COMUNES
{f'El conjunto cuenta con {amenidades}.' if admin > 0 else f'La propiedad es {tipo_str} independiente con {amenidades}.'}
{'La cuota de administración mensual es de $' + f'{admin:,}'.replace(',', '.') + ' COP, que cubre el mantenimiento de todas las zonas comunes, servicios públicos de áreas comunes y vigilancia.' if admin > 0 else 'Al ser propiedad independiente, no aplica cuota de administración.'}

UBICACIÓN Y ACCESIBILIDAD
Localizado a menos de 10 minutos del centro de Manizales, con fácil acceso en transporte público. Cerca de {servicios_cercanos}.

INFORMACIÓN COMERCIAL
- Canon de arrendamiento: ${canon:,} COP mensuales (servicios públicos no incluidos)
- Depósito de garantía: 2 meses de arrendamiento
- Pago de administración: {'a cargo del arrendatario' if admin > 0 else 'N/A'}
- Disponibilidad: inmediata
- Para visitas o mayor información, comunicarse con el agente asignado.

El inmueble cuenta con todos los servicios públicos instalados (acueducto, alcantarillado, energía, gas natural y recolección de basuras). Internet y cable no incluidos.
""".strip()


def texto_contrato(cont: dict, prop: dict) -> str:
    nb = prop["barrio"]
    canon = canon_arriendo(prop["tipo"], prop["area"], prop["hab"])
    deposito = canon * 2
    return f"""
CONTRATO DE ARRENDAMIENTO DE INMUEBLE URBANO

En la ciudad de Manizales, Caldas, República de Colombia, a los {cont.get('dia', 1)} días del mes de {cont.get('mes', 'enero')} de {cont.get('year', 2025)}, entre las partes que a continuación se identifican, se celebra el presente contrato de arrendamiento, regido por la Ley 820 de 2003 y las normas concordantes del Código Civil colombiano.

PRIMERA – PARTES CONTRATANTES
ARRENDADOR: Persona natural identificada con la cédula de ciudadanía consignada en el sistema, propietaria del inmueble objeto de este contrato, en adelante denominada EL ARRENDADOR.
ARRENDATARIO: Persona natural identificada con la cédula de ciudadanía consignada en el sistema, en adelante denominada EL ARRENDATARIO.

SEGUNDA – OBJETO DEL CONTRATO
EL ARRENDADOR entrega al ARRENDATARIO, a título de arrendamiento, el inmueble ubicado en el barrio {nb}, municipio de Manizales, Caldas, con un área de {prop['area']} metros cuadrados de construcción, {f"{prop['hab']} habitaciones y {prop['ban']} baños" if prop['tipo'] != 'local' else 'destinado a uso comercial'}. El inmueble se entrega en buen estado de conservación y con todos los servicios públicos instalados y al día.

TERCERA – CANON DE ARRENDAMIENTO
El canon mensual de arrendamiento se fija en la suma de ${canon:,} (pesos colombianos), pagaderos por mensualidades anticipadas dentro de los primeros cinco (5) días de cada mes. El pago deberá realizarse mediante transferencia bancaria a la cuenta designada por EL ARRENDADOR. El incumplimiento en el pago generará intereses moratorios a la tasa máxima legal permitida.

CUARTA – DEPÓSITO DE GARANTÍA
EL ARRENDATARIO entrega a EL ARRENDADOR un depósito de garantía equivalente a ${deposito:,} COP (dos cánones de arrendamiento), destinado a garantizar el cumplimiento de las obligaciones contractuales y el estado de entrega del inmueble. Este depósito será devuelto dentro de los treinta (30) días siguientes a la terminación del contrato, previo inventario de salida.

QUINTA – DURACIÓN
El presente contrato tendrá una duración inicial de doce (12) meses, contados a partir de la fecha de entrega del inmueble. Al vencimiento, se prorrogará automáticamente por períodos iguales, salvo notificación escrita de cualquiera de las partes con un mínimo de tres (3) meses de anticipación.

SEXTA – INCREMENTO DEL CANON
El canon de arrendamiento se incrementará anualmente de conformidad con el Índice de Precios al Consumidor (IPC) certificado por el DANE para el año inmediatamente anterior, según lo establece el artículo 20 de la Ley 820 de 2003.

SÉPTIMA – MASCOTAS
{"El reglamento del conjunto residencial NO permite la tenencia de mascotas. El ARRENDATARIO declara conocer y aceptar esta restricción." if not prop['masc'] else "Se permite la tenencia de hasta dos (2) mascotas de razas no peligrosas y con peso inferior a ocho (8) kilogramos. EL ARRENDATARIO asume toda responsabilidad civil y económica por daños ocasionados por sus mascotas a terceros, al inmueble o a las zonas comunes."}

OCTAVA – SUBARRIENDO Y CESIÓN
Queda expresamente prohibido subarrendar total o parcialmente el inmueble, así como ceder los derechos derivados de este contrato, sin el previo consentimiento escrito de EL ARRENDADOR. El incumplimiento de esta cláusula dará lugar a la terminación inmediata del contrato.

NOVENA – MANTENIMIENTO Y REPARACIONES
EL ARRENDATARIO se obliga a conservar el inmueble en el estado en que lo recibe, realizando las reparaciones locativas a su cargo según lo establece el artículo 2029 del Código Civil. Las reparaciones de mayor cuantía que no provengan del uso normal del inmueble estarán a cargo de EL ARRENDADOR, previa notificación y verificación técnica.

DÉCIMA – SERVICIOS PÚBLICOS
EL ARRENDATARIO asume el pago oportuno de los servicios públicos domiciliarios a su cargo (energía eléctrica, gas natural, acueducto y alcantarillado, internet y televisión por cable). {'El pago de la cuota de administración del conjunto es también responsabilidad del ARRENDATARIO.' if prop['admin'] > 0 else ''}

DÉCIMA PRIMERA – RESTITUCIÓN DEL INMUEBLE
Al finalizar el contrato, EL ARRENDATARIO deberá restituir el inmueble en las mismas condiciones en que fue recibido, descontando el deterioro natural por el uso. Se realizará un inventario de entrega y uno de salida, los cuales harán parte integral de este contrato.

DÉCIMA SEGUNDA – CAUSALES DE TERMINACIÓN
El presente contrato podrá ser terminado unilateralmente por cualquiera de las partes, previa notificación escrita con antelación mínima de tres (3) meses. Son causales de terminación inmediata el no pago del canon por más de dos (2) períodos consecutivos, el subarriendo no autorizado, el uso del inmueble para actividades ilícitas o el incumplimiento grave de cualquiera de las cláusulas aquí pactadas.

DÉCIMA TERCERA – CLÁUSULA COMPROMISORIA
Las controversias derivadas del presente contrato se resolverán preferiblemente mediante conciliación ante un Centro de Conciliación autorizado. De no llegarse a un acuerdo, las partes se someten a los jueces competentes del municipio de Manizales.

Para constancia se firma en dos (2) ejemplares del mismo tenor y valor, en la ciudad y fecha indicadas al inicio.

_____________________________          _____________________________
EL ARRENDADOR                          EL ARRENDATARIO
""".strip()


def reglamento_copropiedad(edificio: str, barrio: str, num_pisos: int) -> str:
    return f"""
REGLAMENTO DE PROPIEDAD HORIZONTAL
{edificio.upper()} — BARRIO {barrio.upper()}, MANIZALES, CALDAS

CAPÍTULO I — DISPOSICIONES GENERALES

Artículo 1. El presente reglamento tiene por objeto regular la convivencia, el uso de las zonas comunes y las obligaciones de los residentes del conjunto residencial {edificio}, ubicado en el barrio {barrio}, municipio de Manizales, departamento de Caldas. Es de obligatorio cumplimiento para propietarios, arrendatarios, visitantes y cualquier persona que se encuentre dentro de las instalaciones.

Artículo 2. La administración del conjunto estará a cargo de un administrador designado por la Asamblea de Copropietarios, quien tendrá las funciones y atribuciones establecidas en la Ley 675 de 2001 y sus decretos reglamentarios.

CAPÍTULO II — USO DE ZONAS COMUNES

Artículo 3. Las zonas comunes del conjunto son: hall de ingreso, zonas verdes, {f"piscina, gimnasio, salón social, " if num_pisos > 6 else ""}parqueadero de visitantes, cuarto de basuras y pasillos de acceso a los apartamentos. Estas zonas son de uso exclusivo de los residentes y sus visitantes autorizados.

Artículo 4. El gimnasio estará disponible de lunes a domingo de 5:00 a.m. a 10:00 p.m. Su uso es exclusivo para mayores de 16 años. Los menores de edad deberán estar acompañados por un adulto responsable. Se prohíbe el ingreso con calzado de calle.

Artículo 5. El salón social podrá ser reservado por los residentes con un mínimo de 72 horas de anticipación ante la administración, mediante solicitud escrita o a través de la plataforma digital habilitada. El horario de uso para eventos con música es hasta las 11:00 p.m. de domingo a jueves, y hasta la 1:00 a.m. los viernes y sábados. El residente que realice el evento será responsable por daños causados y por garantizar el orden y el respeto a los demás residentes.

Artículo 6. La piscina estará disponible de martes a domingo de 8:00 a.m. a 7:00 p.m. Es obligatorio ducharse antes de ingresar. Queda prohibido el consumo de alimentos dentro del área de la piscina. Los niños menores de 10 años deben estar acompañados permanentemente por un adulto.

CAPÍTULO III — RUIDO Y CONVIVENCIA

Artículo 7. En respeto al descanso de los residentes, el uso de electrodomésticos que generen ruido elevado (lavadoras, taladros, instrumentos musicales, equipos de sonido) queda restringido en el horario de 9:00 p.m. a 7:00 a.m. de lunes a sábado, y de 9:00 p.m. a 9:00 a.m. los domingos y festivos.

Artículo 8. Queda prohibido arrojar objetos, agua o cualquier sustancia desde las ventanas, balcones o terrazas, así como tender ropa en las barandas visibles desde el exterior.

Artículo 9. Las reuniones sociales dentro de las unidades privadas deberán mantener el ruido dentro de los niveles permisibles establecidos por la norma ambiental colombiana. Ante reiteradas quejas por ruido, la administración podrá imponer las sanciones pecuniarias previstas en el reglamento.

CAPÍTULO IV — MASCOTAS

Artículo 10. Se permite la tenencia de mascotas (perros y gatos) dentro de las unidades privadas, con las siguientes condiciones:
a) Máximo dos (2) mascotas por unidad privada.
b) Las mascotas deberán circular siempre con correa por las zonas comunes y estar vacunadas.
c) El propietario deberá recoger inmediatamente los excrementos de su mascota en zonas comunes.
d) Se prohíben razas consideradas potencialmente peligrosas según la Ley 746 de 2002, a menos que se acredite entrenamiento especial y se cuente con póliza de responsabilidad civil.
e) Los propietarios de mascotas son responsables por daños causados a personas o bienes.

CAPÍTULO V — PARQUEADEROS

Artículo 11. El uso del parqueadero es exclusivo para los vehículos del residente asignado. Está prohibido utilizar el parqueadero propio o ajeno para almacenar objetos, realizar labores de mecánica o lavar vehículos.

Artículo 12. Las visitas deberán usar los parqueaderos de visitantes, previa autorización de portería. Estos parqueaderos tienen un tiempo máximo de uso de 6 horas continuas.

Artículo 13. La administración no se hace responsable por daños, hurtos o pérdidas de vehículos o pertenencias dentro del parqueadero.

CAPÍTULO VI — SEGURIDAD Y ACCESO

Artículo 14. Todo visitante deberá registrarse en portería, dejando número de identificación y anunciando el apartamento al que se dirige. Ningún visitante podrá ingresar sin autorización expresa del residente.

Artículo 15. El personal de domicilios y mensajería solo podrá ingresar hasta el hall de entrada. En ningún caso podrán acceder a los pisos sin supervisión del residente.

Artículo 16. El conjunto cuenta con circuito cerrado de televisión (CCTV) con grabación continua de 30 días. Las grabaciones son de uso exclusivo de la administración y autoridades competentes.

CAPÍTULO VII — CUOTA DE ADMINISTRACIÓN

Artículo 17. Todos los propietarios y arrendatarios (según lo estipulado en el contrato de arrendamiento) están obligados al pago de la cuota de administración dentro de los primeros cinco (5) días de cada mes. El incumplimiento generará intereses moratorios a la tasa máxima legal y podrá restringirse el acceso a las zonas comunes al residente moroso.

Artículo 18. El presente reglamento fue aprobado en Asamblea General de Copropietarios y tiene plena vigencia a partir de su publicación. Modificaciones al mismo deberán aprobarse en asamblea con el quórum establecido en la Ley 675 de 2001.

CONJUNTO RESIDENCIAL {edificio.upper()} — {num_pisos} PISOS — MANIZALES, CALDAS
""".strip()


def chat_session_text(listing_id: str, barrio: str, canon: int, hab: int, masc: bool) -> str:
    masc_str = "máximo 2 mascotas pequeñas (hasta 8 kg)" if masc else "No acepta mascotas"
    return f"""
TRANSCRIPCIÓN DE SESIÓN DE CHAT — Listing {listing_id}

[10:02] Interesado: Buenos días, vi la publicación del apartamento en {barrio}. ¿Sigue disponible?
[10:04] Agente: ¡Buenos días! Sí, el apartamento sigue disponible. ¿Le gustaría más información?
[10:05] Interesado: Perfecto. Primero que todo, ¿cuánto es el arriendo mensual?
[10:06] Agente: El canon de arrendamiento es de ${canon:,} COP mensuales. Este valor no incluye servicios públicos ni administración.
[10:07] Interesado: ¿Y cuánto es la administración?
[10:08] Agente: La administración está alrededor de $150.000 a $240.000 COP dependiendo del mes. Queda a cargo del arrendatario según el contrato estándar.
[10:09] Interesado: Entendido. ¿Cuántas habitaciones tiene?
[10:10] Agente: El apartamento tiene {hab} {'habitación' if hab == 1 else 'habitaciones'}, baño(s) completo(s) y zona de ropas independiente.
[10:11] Interesado: Muy bien. Tengo un perro pequeño, ¿aceptan mascotas?
[10:12] Agente: En este inmueble la política de mascotas es: {masc_str}. {'Necesitaríamos que firme una cláusula adicional de responsabilidad y pague un mes adicional de depósito.' if masc else 'Le pido disculpas, el reglamento del conjunto no lo permite.'}
[10:14] Interesado: Comprendo. ¿El apartamento tiene parqueadero?
[10:15] Agente: Sí, incluye parqueadero cubierto para un vehículo.
[10:16] Interesado: ¿Y qué piden para arrendar? ¿Codeudor?
[10:17] Agente: Los requisitos son: dos últimas colillas de pago, certificado laboral o extractos bancarios de los últimos 3 meses, fotocopia de cédula y referencias personales. En caso de trabajadores independientes, se solicita codeudor solidario o póliza de arrendamiento.
[10:19] Interesado: ¿El canon incluye algún servicio público?
[10:20] Agente: No, ninguno. Los servicios públicos (agua, luz, gas, internet) van aparte y quedan a nombre del arrendatario.
[10:21] Interesado: ¿Cuánto piden de depósito?
[10:22] Agente: El depósito estándar es de 2 cánones de arrendamiento: ${canon*2:,} COP. Este valor se devuelve al finalizar el contrato, previa revisión del estado del inmueble.
[10:24] Interesado: Perfecto. ¿Podríamos agendar una visita para esta semana?
[10:25] Agente: Claro que sí. Tengo disponibilidad el miércoles a las 3:00 p.m. o el viernes a las 10:00 a.m. ¿Cuál le queda mejor?
[10:26] Interesado: El miércoles a las 3 está bien.
[10:27] Agente: Perfecto. Le confirmo la visita para el miércoles en el apartamento del barrio {barrio}. Le comparto la dirección exacta y le recuerdo traer documento de identificación.
[10:28] Interesado: Muchísimas gracias. Hasta el miércoles.
[10:29] Agente: ¡Con mucho gusto! Cualquier duda adicional no dude en escribirme. Hasta pronto.
""".strip()


def reporte_mercado(barrio: str, estrato: int) -> str:
    canon_min = 800000 + estrato * 100000
    canon_max = 1500000 + estrato * 200000
    return f"""
REPORTE DE MERCADO INMOBILIARIO — BARRIO {barrio.upper()}, MANIZALES

Elaborado por el equipo de análisis de Inmobiliaria RAG. Fecha: junio 2025.

RESUMEN EJECUTIVO
El barrio {barrio} de Manizales presenta un mercado inmobiliario dinámico, con una demanda sostenida de inmuebles para arrendamiento, especialmente por parte de profesionales, estudiantes universitarios y familias de estrato {estrato}. La oferta disponible ha crecido moderadamente en el último año, impulsada por el desarrollo de nuevos proyectos de construcción en la zona.

TENDENCIAS DE PRECIOS
Los cánones de arrendamiento en {barrio} oscilan entre ${canon_min:,} y ${canon_max:,} COP mensuales para apartamentos de 1 a 3 habitaciones. Los inmuebles más solicitados son los apartamentos de 2 habitaciones con parqueadero, que representan el 45% de la demanda total en el sector. Las casas independientes de 3 o más habitaciones registran cánones entre $2.000.000 y $3.500.000 COP mensuales.

En el mercado de venta, el precio por metro cuadrado en {barrio} se ubica entre $3.200.000 y $4.800.000 COP, dependiendo del piso, los acabados y las amenidades del conjunto. Los inmuebles de estratos {estrato} y {estrato+1} presentan la mayor valorización anual, con incrementos del 8% al 12% en el último periodo.

TIEMPO PROMEDIO EN MERCADO
Los inmuebles en {barrio} tienen un tiempo promedio de colocación de 23 días en arrendamiento y 65 días en venta, por debajo del promedio de la ciudad (31 días y 82 días respectivamente). La cercanía a centros educativos, comerciales y de salud es el principal factor que acelera la colocación.

PERFIL DEL DEMANDANTE
El 60% de los interesados en {barrio} son profesionales entre 25 y 40 años, solteros o en pareja, sin hijos o con hijos pequeños. El 30% corresponde a familias con hijos en edad escolar que priorizan la calidad de vida y la seguridad del sector. El 10% restante son empresas o profesionales independientes que buscan locales o oficinas en la zona.

FACTORES DE VALORIZACIÓN
- Mejoramiento de la malla vial y ampliación de ciclovías en el sector
- Nuevos proyectos gastronómicos y comerciales que dinamizan la economía local
- Acceso a transporte masivo (Transporte Cable) en zonas cercanas
- Alta cobertura de servicios educativos de calidad en un radio de 2 km
- Baja tasa de criminalidad respecto al promedio metropolitano de Manizales

PROYECCIONES 2025-2026
Se espera un incremento del 9% en los cánones de arrendamiento de {barrio} para el próximo año, consistente con el IPC proyectado y la mayor demanda de inmuebles de estrato {estrato}. La oferta permanecerá estable, con algunos proyectos nuevos en construcción que ingresarán al mercado en el segundo semestre de 2025.

RECOMENDACIÓN PARA PROPIETARIOS
Es un buen momento para poner en arriendo inmuebles en {barrio}. Se recomienda invertir en mejoras estéticas (pintura, pisos, griferías) para posicionarse en el rango superior de precios del sector. La inclusión de parqueadero y lavandería aumenta significativamente la velocidad de colocación del inmueble.
""".strip()


def faq_inmobiliario(tema: str) -> str:
    faqs = {
        "mascotas": """
PREGUNTAS FRECUENTES — MASCOTAS EN INMUEBLES DE ARRIENDO

¿Se permiten mascotas en los apartamentos en arriendo?
Depende de cada propietario y del reglamento del conjunto residencial. En Inmobiliaria RAG, cada publicación especifica claramente si acepta mascotas o no. Cuando se aceptan mascotas, generalmente se establecen condiciones específicas en el contrato de arrendamiento.

¿Qué condiciones aplican cuando se aceptan mascotas?
Las condiciones más comunes son: máximo 2 mascotas, peso inferior a 8-10 kilogramos para perros, restricción de razas peligrosas según la Ley 746 de 2002, obligación de mantener vacunas al día, depósito adicional equivalente a 1 mes de arriendo y firma de cláusula especial de responsabilidad por daños.

¿Qué pasa si tengo una mascota y el contrato no lo permite?
Cualquier incumplimiento de cláusulas contractuales puede ser causal de terminación del contrato. Si llegas a un inmueble con mascota no autorizada, el arrendador puede iniciar un proceso de restitución del inmueble.

¿Los reglamentos de copropiedad pueden prohibir mascotas aunque el propietario las acepte?
Sí. El reglamento de propiedad horizontal tiene primacía sobre la voluntad individual del propietario. Si el conjunto residencial prohíbe mascotas, esta restricción aplica aunque el arrendador esté de acuerdo. Siempre verifica tanto la posición del arrendador como el reglamento del conjunto.

¿Hay razas de mascotas completamente prohibidas?
Según la Ley 746 de 2002, las razas consideradas potencialmente peligrosas (Pit Bull Terrier, Rottweiler, Dogo Argentino, Bull Mastiff y otras) requieren cumplir requisitos especiales: bozal en zonas comunes, correa resistente y póliza de responsabilidad civil. Muchos conjuntos residenciales de Manizales optan por prohibirlas directamente.
""",
        "canon_pago": """
PREGUNTAS FRECUENTES — CANON DE ARRENDAMIENTO Y FORMAS DE PAGO

¿Cuándo debo pagar el arriendo?
El canon de arrendamiento generalmente se paga dentro de los primeros cinco (5) días de cada mes calendario. La fecha exacta queda establecida en el contrato de arrendamiento firmado entre las partes.

¿Qué pasa si no pago a tiempo?
El incumplimiento en el pago del canon genera intereses moratorios a la tasa máxima legal establecida por la Superintendencia Financiera de Colombia. Si el atraso supera 2 meses consecutivos, el arrendador puede iniciar proceso judicial de restitución del inmueble.

¿Cómo se realiza el pago del arrendamiento?
Lo más común en Manizales es mediante transferencia bancaria o consignación en la cuenta designada por el arrendador. También puede pactarse el pago en efectivo con recibo de caja. Se recomienda siempre conservar los comprobantes de pago.

¿En cuánto puede incrementarse el arriendo cada año?
Según el artículo 20 de la Ley 820 de 2003, el incremento anual del canon no puede superar el IPC del año inmediatamente anterior, certificado por el DANE. Por ejemplo, si el IPC fue del 7%, el incremento máximo es del 7%.

¿Qué incluye el canon de arrendamiento?
Por lo general, el canon NO incluye: servicios públicos domiciliarios (agua, luz, gas, teléfono, internet), cuota de administración del conjunto ni ningún otro servicio adicional. Estos valores son responsabilidad del arrendatario y se pagan directamente a las empresas prestadoras.

¿Qué es el depósito de garantía y cuándo se devuelve?
Es un valor que el arrendatario paga al inicio del contrato (generalmente 1 a 3 meses de canon) para garantizar el cumplimiento de sus obligaciones. Se devuelve al finalizar el contrato, descontando posibles daños o deudas pendientes, dentro de los 30 días siguientes a la restitución del inmueble.
""",
        "contratos": """
PREGUNTAS FRECUENTES — CONTRATOS DE ARRENDAMIENTO EN COLOMBIA

¿Es obligatorio hacer contrato escrito?
Sí. Si bien los contratos verbales tienen validez legal, la Ley 820 de 2003 recomienda formalizar el arrendamiento por escrito para proteger a ambas partes. Un contrato escrito detalla claramente las obligaciones de arrendador y arrendatario, evitando disputas futuras.

¿Qué documentos se necesitan para arrendar?
Los requisitos habituales son: fotocopia de cédula de ciudadanía, dos últimas colillas de pago o constancia laboral, extractos bancarios de los últimos 3 meses, referencias personales y comerciales. Los trabajadores independientes generalmente deben presentar codeudor solidario o adquirir póliza de arrendamiento.

¿Cuánto dura un contrato de arrendamiento?
El plazo mínimo legal es de 1 año. Al vencimiento, si ninguna de las partes notifica su intención de terminar el contrato con al menos 3 meses de anticipación, este se renueva automáticamente por el mismo período.

¿Puedo terminar el contrato antes del plazo?
Sí, pero deben cumplirse los términos pactados. Si el arrendatario termina anticipadamente sin causa justa, puede quedar obligado al pago de una indemnización. Si el arrendador quiere terminar anticipadamente sin las causales legales, también debe indemnizar al arrendatario.

¿Qué es un codeudor y cuándo se requiere?
Es una persona que se compromete solidariamente a responder por las obligaciones del arrendatario en caso de incumplimiento. Se suele exigir cuando el arrendatario no puede demostrar ingresos suficientes (mínimo 3 veces el valor del canon), cuando trabaja de manera independiente o cuando tiene historial crediticio negativo.

¿Quién paga las reparaciones del inmueble?
Las reparaciones locativas (daños menores por el uso normal: cambio de bombillos, pintura de uso, arreglo de llaves, etc.) son responsabilidad del arrendatario. Las reparaciones mayores y de mantenimiento estructural corresponden al propietario.
""",
        "subarriendo": """
PREGUNTAS FRECUENTES — SUBARRIENDO EN COLOMBIA

¿Puedo subarrendar el inmueble que tengo en arriendo?
En Colombia, el subarriendo está expresamente prohibido sin autorización escrita del arrendador, según la Ley 820 de 2003. Si el contrato no lo permite expresamente, se entiende que está prohibido, y su incumplimiento puede ocasionar la terminación inmediata del contrato.

¿Qué es exactamente el subarriendo?
El subarriendo ocurre cuando el arrendatario arrienda a su vez el inmueble (total o parcialmente) a un tercero, convirtiéndose en arrendador de ese tercero. Es diferente al hospedaje esporádico de familiares o amigos.

¿Qué consecuencias tiene subarrendar sin autorización?
Las consecuencias pueden ser: terminación inmediata del contrato de arrendamiento, pérdida del depósito de garantía, obligación de pagar los perjuicios causados al propietario y, en casos graves, acciones penales si se acredita fraude.

¿Plataformas como Airbnb son consideradas subarriendo?
Sí. El arrendamiento temporal o por noches a través de plataformas digitales es considerado subarriendo y está sujeto a las mismas restricciones. Además, muchos reglamentos de copropiedad en Manizales prohíben expresamente el uso de plataformas de hospedaje temporal en los apartamentos.

¿Cómo se puede subarrendar legalmente?
El arrendatario debe obtener autorización escrita del arrendador, la cual debe especificar las condiciones del subarriendo. El arrendatario original sigue siendo responsable ante el propietario por el cumplimiento de todas las obligaciones contractuales.
""",
        "servicios": """
PREGUNTAS FRECUENTES — SERVICIOS PÚBLICOS EN ARRENDAMIENTO

¿Los servicios públicos están incluidos en el arriendo?
Generalmente no. El canon de arrendamiento en Colombia raramente incluye servicios públicos. Agua, luz, gas natural, internet y televisión por cable son responsabilidad del arrendatario y se pagan directamente a las empresas prestadoras.

¿A quién le llegan las facturas de servicios en un apartamento arrendado?
En muchos casos las facturas siguen llegando a nombre del propietario, pero el pago es responsabilidad del arrendatario. Lo ideal es que el arrendatario solicite el traslado de los contratos de servicio a su nombre para mayor claridad y control.

¿Qué pasa si dejo de pagar los servicios públicos?
El impago puede llevar a la suspensión del servicio y la acumulación de deudas que afectan tanto al arrendatario como al propietario. La deuda de servicios públicos puede considerarse un incumplimiento contractual que habilita al arrendador para iniciar proceso de restitución.

¿La administración del conjunto es un servicio público?
No es un servicio público domiciliario, pero sí es un gasto recurrente que frecuentemente queda a cargo del arrendatario según el contrato. Corresponde al mantenimiento de zonas comunes, vigilancia y administración del conjunto residencial.

¿Qué pasa con los servicios al finalizar el contrato?
Al terminar el contrato, el arrendatario debe dejar los servicios al día y, si los trasladó a su nombre, realizar el cambio de titular nuevamente. Los saldos pendientes serán descontados del depósito de garantía.
""",
    }
    return faqs.get(tema, "Información no disponible").strip()


def guia_mantenimiento(tipo: str) -> str:
    guias = {
        "plomeria": """
GUÍA DE MANTENIMIENTO — PLOMERÍA EN APARTAMENTOS DE ARRIENDO, MANIZALES

Esta guía está dirigida a arrendatarios de inmuebles administrados por Inmobiliaria RAG en Manizales, Caldas, con el fin de orientar sobre la correcta detección, reporte y manejo de problemas de plomería.

TIPOS DE PROBLEMAS Y RESPONSABILIDADES

1. FUGAS DE AGUA
Las fugas en tuberías internas son responsabilidad del propietario si se deben al deterioro natural de la instalación. Si la fuga es causada por mal uso o descuido del arrendatario (golpes, sobrecalentamiento, sobrecarga), el costo de reparación recae en el arrendatario.

Cómo detectar una fuga: aumento inexplicable en la factura de agua, humedad en paredes o pisos, manchas de agua en el techo del piso inferior, sonido de agua corriendo cuando todos los grifos están cerrados.

2. TAPONAMIENTO DE SIFONES Y DESAGÜES
Los taponamientos por acumulación de cabello, grasa o residuos son reparaciones locativas a cargo del arrendatario. Se recomienda usar mallas protectoras en todos los sifones y evitar arrojar aceites o toallas húmedas por el inodoro.

3. PRESIÓN BAJA DE AGUA
Si la presión es baja en todo el inmueble, generalmente corresponde a un problema de la red pública o del sistema de bombeo del conjunto, responsabilidad del conjunto residencial. Si la baja presión es solo en un grifo, puede tratarse de sedimento en el aireador, que el arrendatario puede limpiar fácilmente.

PROCEDIMIENTO DE REPORTE
Ante cualquier problema de plomería que supere las reparaciones locativas: notificar inmediatamente al propietario o al agente de Inmobiliaria RAG, describir el problema con detalle (ubicación, síntomas, desde cuándo), esperar autorización antes de contratar servicios de reparación, conservar todas las facturas y fotografías como evidencia.

EMERGENCIAS HIDRÁULICAS
En caso de fuga masiva que represente riesgo para el inmueble: cerrar la llave de paso general (ubicada generalmente en el cuarto de contadores del piso o en la cocina), notificar inmediatamente a portería y al propietario, llamar a una empresa de plomería de emergencia si el propietario no responde en 30 minutos.
""",
        "electrico": """
GUÍA DE MANTENIMIENTO — INSTALACIONES ELÉCTRICAS EN ARRIENDO

INTRODUCCIÓN
El mantenimiento eléctrico preventivo es fundamental para la seguridad y el bienestar de los residentes. Esta guía orienta a los arrendatarios de Inmobiliaria RAG sobre qué hacer ante problemas eléctricos comunes en Manizales.

PROBLEMAS ELÉCTRICOS COMUNES

1. CORTOCIRCUITOS Y DISYUNTORES
Si se dispara un disyuntor (interruptor del tablero eléctrico), primero desconecte el electrodoméstico o aparato que causó la sobrecarga. Luego restablezca el disyuntor (llévelo completamente a la posición OFF y luego a ON). Si el problema persiste o se repite frecuentemente, reporte al propietario, pues puede indicar un problema en la instalación.

2. TOMAS DAÑADAS O SIN CORRIENTE
Si una toma específica no funciona, verifique primero si se disparó un disyuntor relacionado. Si la toma está físicamente dañada (quemada, suelta o con marcas de arco eléctrico), NO la use y reporte de inmediato. Este tipo de daño puede ser de responsabilidad compartida según las circunstancias.

3. ILUMINACIÓN
El cambio de bombillos es responsabilidad del arrendatario (reparación locativa). Sin embargo, si el problema está en el cableado interno o en el interruptor, es responsabilidad del propietario.

SEGURIDAD ELÉCTRICA
No sobrecargue las tomas eléctricas con extensiones o regletas. Evite el uso de equipos de alta potencia (calentadores, hornos eléctricos) en redes no diseñadas para ello. Ante olor a quemado, chispas o calor excesivo en enchufes, desconecte inmediatamente y llame a un electricista certificado. En Manizales, puede comunicarse con la CHEC (Central Hidroeléctrica de Caldas) para reportar emergencias eléctricas al 115.

NOTA LEGAL: Las reparaciones eléctricas deben realizarlas técnicos certificados. Intervenir instalaciones eléctricas sin las competencias técnicas es peligroso y puede anular garantías o seguros del inmueble.
""",
    }
    return guias.get(tipo, "Guía no disponible").strip()


# ---------------------------------------------------------------------------
# Cargar datos en MongoDB
# ---------------------------------------------------------------------------

def load_users(db):
    col = db["users"]
    for u in USERS:
        upsert(col, u)
    print(f"  [OK] {len(USERS)} usuarios")


def load_agencies(db):
    col = db["agencies"]
    for a in AGENCIES:
        upsert(col, a)
    print(f"  [OK] {len(AGENCIES)} agencias")


def load_properties(db):
    props_col = db["properties"]
    media_col = db["media_assets"]
    media_count = 0

    for cfg in PROPERTY_CONFIGS:
        nb = cfg["barrio"]
        lat, lng, estrato = NEIGHBORHOODS[nb]
        prop_doc = {
            "_id": cfg["_id"],
            "owner_id": cfg["owner"],
            "titulo": f"{'Moderno' if estrato >= 4 else 'Amplio'} {cfg['tipo']} en {nb}",
            "ubicacion": {
                "ciudad": "Manizales",
                "geo": {"type": "Point", "coordinates": [lng, lat]},
            },
            "caracteristicas": {
                "area": cfg["area"],
                "habitaciones": cfg["hab"],
                "banos": cfg["ban"],
            },
            "media_ids": [f"med_{cfg['_id']}_{i:02d}" for i in range(1, 4)],
        }
        upsert(props_col, prop_doc)

        # Media assets (3 por propiedad → 60 total)
        tipos = ["imagen_sala", "imagen_habitacion", "imagen_fachada"]
        for i, t in enumerate(tipos, 1):
            med_id = f"med_{cfg['_id']}_{i:02d}"
            upsert(media_col, {
                "_id": med_id,
                "property_id": cfg["_id"],
                "url": f"https://cdn.inmobiliaria-rag.co/media/{cfg['_id']}/{t}.jpg",
                "tipo": "imagen",
                "embedding_id": f"img_emb_{med_id}",
            })
            media_count += 1

    print(f"  [OK] {len(PROPERTY_CONFIGS)} propiedades, {media_count} media_assets")


def load_listings(db):
    col = db["listings"]
    for i, cfg in enumerate(PROPERTY_CONFIGS, 1):
        lat, lng, estrato = NEIGHBORHOODS[cfg["barrio"]]
        tipo_op = "venta" if i % 5 == 0 else "arriendo"
        canon = canon_arriendo(cfg["tipo"], cfg["area"], cfg["hab"])
        precio = precio_venta(cfg["tipo"], cfg["area"], estrato) if tipo_op == "venta" else canon

        upsert(col, {
            "_id": f"list_{cfg['_id']}",
            "codigo_listing": f"LST-{i:04d}",
            "property_id": cfg["_id"],
            "agent_id": cfg["agent"],
            "tipo": tipo_op,
            "precio": float(precio),
            "estado": "activo",
        })
    print(f"  [OK] {len(PROPERTY_CONFIGS)} listings")


def load_contracts(db):
    col = db["contracts"]
    contract_data = [
        ("cont_001", "list_prop_001", "u_001", "u_011", "activo",   "2024-03-01", "2025-03-01", 1, "marzo",    2024),
        ("cont_002", "list_prop_003", "u_002", "u_012", "activo",   "2024-06-15", "2025-06-15", 15,"junio",    2024),
        ("cont_003", "list_prop_005", "u_003", "u_013", "activo",   "2024-09-01", "2025-09-01", 1, "septiembre",2024),
        ("cont_004", "list_prop_007", "u_004", "u_011", "activo",   "2025-01-10", "2026-01-10", 10,"enero",    2025),
        ("cont_005", "list_prop_009", "u_005", "u_012", "activo",   "2025-03-01", "2026-03-01", 1, "marzo",    2025),
        ("cont_006", "list_prop_002", "u_001", "u_013", "finalizado","2023-04-01", "2024-04-01", 1, "abril",    2023),
        ("cont_007", "list_prop_004", "u_002", "u_011", "finalizado","2023-07-15", "2024-07-15", 15,"julio",    2023),
        ("cont_008", "list_prop_006", "u_003", "u_012", "activo",   "2024-11-01", "2025-11-01", 1, "noviembre",2024),
        ("cont_009", "list_prop_010", "u_005", "u_013", "activo",   "2024-08-20", "2025-08-20", 20,"agosto",   2024),
        ("cont_010", "list_prop_012", "u_002", "u_011", "cancelado","2024-02-01", "2025-02-01", 1, "febrero",  2024),
        ("cont_011", "list_prop_013", "u_003", "u_012", "activo",   "2025-02-01", "2026-02-01", 1, "febrero",  2025),
        ("cont_012", "list_prop_015", "u_005", "u_013", "activo",   "2024-10-01", "2025-10-01", 1, "octubre",  2024),
        ("cont_013", "list_prop_018", "u_003", "u_011", "activo",   "2025-04-01", "2026-04-01", 1, "abril",    2025),
        ("cont_014", "list_prop_019", "u_004", "u_012", "activo",   "2025-05-15", "2026-05-15", 15,"mayo",     2025),
        ("cont_015", "list_prop_020", "u_005", "u_013", "activo",   "2025-01-01", "2026-01-01", 1, "enero",    2025),
    ]
    for row in contract_data:
        cid, lid, arr_or, arr_ee, estado, f_ini, f_ven, dia, mes, year = row
        upsert(col, {
            "_id": cid,
            "listing_id": lid,
            "arrendador_id": arr_or,
            "arrendatario_id": arr_ee,
            "estado": estado,
            "fecha_inicio": f_ini,
            "fecha_vencimiento": f_ven,
            "clausulas": [
                {"titulo": "Mascotas",     "descripcion": "Según política del inmueble indicada en el contrato."},
                {"titulo": "Subarriendo",  "descripcion": "Prohibido sin autorización escrita del arrendador."},
                {"titulo": "Canon",        "descripcion": "Pagadero dentro de los primeros 5 días de cada mes."},
                {"titulo": "Mantenimiento","descripcion": "Reparaciones locativas a cargo del arrendatario."},
            ],
            "document_id": f"doc_cont_{cid}",
            "_meta": {"dia": dia, "mes": mes, "year": year},
        })
    print(f"  [OK] {len(contract_data)} contratos")
    return contract_data


def load_reviews(db):
    col = db["reviews"]
    reviews = [
        ("rev_001", "u_011", "prop_001", 5, "Excelente apartamento, muy bien ubicado en El Cable. La iluminación natural es perfecta y el vecindario es muy tranquilo. Lo recomiendo ampliamente."),
        ("rev_002", "u_012", "prop_003", 4, "Buen apartamento en Milán, práctico y cómodo. El acceso al transporte público es muy conveniente. La única observación es que el parqueadero comunal es pequeño."),
        ("rev_003", "u_013", "prop_005", 5, "Casa hermosa en Chipre con vista espectacular a la ciudad. El espacio es amplio, la zona es segura y los vecinos son muy amables. Definitivamente el mejor lugar donde he vivido en Manizales."),
        ("rev_004", "u_011", "prop_007", 3, "Apartamento decente en Palermo, bien ubicado pero con algo de ruido en la calle. El precio es justo para la zona. La administración del conjunto responde bien a los reclamos."),
        ("rev_005", "u_012", "prop_009", 5, "La casa en La Enea superó todas mis expectativas. Amplia, con jardín privado y en una zona muy tranquila. El propietario es muy atento y resuelve cualquier inconveniente rápidamente."),
        ("rev_006", "u_013", "prop_002", 4, "Apartamento moderno con excelentes amenidades. El gimnasio y la piscina son un plus increíble. La vista desde el piso 8 es simplemente espectacular en las noches."),
        ("rev_007", "u_011", "prop_012", 4, "Muy buena ubicación en Versalles, cerca de universidades y restaurantes. El apartamento está bien distribuido y tiene buena iluminación. Recomendado para profesionales."),
        ("rev_008", "u_012", "prop_015", 3, "Apartamento funcional en La Sultana. El precio es accesible para la zona. Los acabados son sencillos pero en buen estado. El transporte desde el sector es un poco escaso en horas pico."),
        ("rev_009", "u_013", "prop_013", 5, "Impresionante apartamento en Palogrande, excelentes acabados y vista panorámica desde el piso 11. La zona es de lo mejor de Manizales. El conjunto tiene todo lo que se necesita."),
        ("rev_010", "u_011", "prop_018", 4, "Buen apartamento en Chipre con parqueadero incluido, lo cual es difícil de encontrar en la zona. El conjunto es bien administrado y la seguridad es buena."),
        ("rev_011", "u_012", "prop_006", 4, "Cómodo y bien ubicado en Chipre. El piso 6 ofrece una vista agradable sin ser demasiado alto. Buena relación calidad-precio para el sector."),
        ("rev_012", "u_013", "prop_010", 3, "Apartamento aceptable en La Enea. La zona tiene acceso rápido al aeropuerto, lo cual es conveniente. El barrio está en proceso de mejora y se nota el desarrollo en la zona."),
        ("rev_013", "u_011", "prop_019", 5, "Hermoso apartamento en Versalles con todas las comodidades. El equipo de la inmobiliaria fue muy profesional durante todo el proceso. Sin duda volvería a arrendar con ellos."),
        ("rev_014", "u_012", "prop_020", 5, "La casa en Palogrande es simplemente espectacular. 200 m² de espacio bien distribuido, jardín hermoso y en la mejor zona de Manizales. Vale cada peso del arriendo."),
        ("rev_015", "u_013", "prop_014", 4, "Casa confortable en Belén con buen espacio para familia. El barrio es familiar y seguro. La única observación es que en horas pico el tráfico en la zona puede ser complicado."),
    ]
    for row in reviews:
        rid, autor, prop, cal, com = row
        upsert(col, {
            "_id": rid,
            "autor_id": autor,
            "target_property_id": prop,
            "calificacion": cal,
            "comentario": com,
        })
    print(f"  [OK] {len(reviews)} reseñas")


def load_maintenance(db):
    col = db["maintenance_requests"]
    requests = [
        ("mnt_001", "cont_001", "Fuga de agua en la tubería de la cocina", "resuelto"),
        ("mnt_002", "cont_002", "Daño en la cerradura de la puerta principal", "resuelto"),
        ("mnt_003", "cont_003", "Problema eléctrico: cortocircuito en toma de la sala", "en_progreso"),
        ("mnt_004", "cont_004", "Filtración de agua en el techo del baño principal", "pendiente"),
        ("mnt_005", "cont_005", "Puerta de closet principal no cierra correctamente", "pendiente"),
        ("mnt_006", "cont_008", "Taponamiento del sifón de la cocina", "resuelto"),
        ("mnt_007", "cont_009", "Calentador de agua no funciona", "en_progreso"),
        ("mnt_008", "cont_011", "Humedad en pared de la habitación secundaria", "pendiente"),
        ("mnt_009", "cont_013", "Grifo de la ducha con goteo constante", "en_progreso"),
        ("mnt_010", "cont_014", "Ventana de la sala no cierra herméticamente", "resuelto"),
    ]
    for row in requests:
        mid, cid, desc, estado = row
        upsert(col, {
            "_id": mid,
            "contract_id": cid,
            "descripcion": desc,
            "estado": estado,
        })
    print(f"  [OK] {len(requests)} solicitudes de mantenimiento")


def load_documents(db, contract_data):
    col = db["documents_repository"]
    docs = []

    # ── 1. Descripciones de propiedades (20 docs) ──────────────────────────
    for cfg in PROPERTY_CONFIGS:
        docs.append({
            "_id": f"doc_desc_{cfg['_id']}",
            "tipo": "descripcion_propiedad",
            "contenido": descripcion_propiedad(cfg),
            "origen_id": cfg["_id"],
            "origen_tipo": "property",
            "chunking_aplicado": [],
        })

    # ── 2. Contratos completos (15 docs) ───────────────────────────────────
    for i, row in enumerate(contract_data):
        cid, lid, arr_or, arr_ee, estado, f_ini, f_ven, dia, mes, year = row
        prop_id = lid.replace("list_", "")
        cfg = next((c for c in PROPERTY_CONFIGS if c["_id"] == prop_id), PROPERTY_CONFIGS[0])
        cont_meta = {"dia": dia, "mes": mes, "year": year}
        docs.append({
            "_id": f"doc_cont_{cid}",
            "tipo": "contrato",
            "contenido": texto_contrato(cont_meta, cfg),
            "origen_id": cid,
            "origen_tipo": "contract",
            "chunking_aplicado": [],
        })

    # ── 3. Reglamentos de copropiedad (15 docs) ────────────────────────────
    edificios = [
        ("Torre El Cable I",    "El Cable",   14),
        ("Torre El Cable II",   "El Cable",   10),
        ("Edificio Milán Park", "Milán",       8),
        ("Residencias Milán",   "Milán",       6),
        ("Chipre Heights",      "Chipre",     12),
        ("Edificio Chipre Sur", "Chipre",      9),
        ("Palermo Suites",      "Palermo",     7),
        ("Conjunto Palermo",    "Palermo",     5),
        ("La Enea Park",        "La Enea",     8),
        ("Versalles Tower",     "Versalles",  15),
        ("Versalles Plaza",     "Versalles",  11),
        ("Palogrande Elite",    "Palogrande", 13),
        ("Conjunto Belén",      "Belén",       6),
        ("Sultana Residencias", "La Sultana",  8),
        ("Centro Business",     "Centro",      4),
    ]
    for edificio, barrio, pisos in edificios:
        docs.append({
            "_id": f"doc_reg_{edificio.lower().replace(' ', '_')}",
            "tipo": "reglamento_copropiedad",
            "contenido": reglamento_copropiedad(edificio, barrio, pisos),
            "origen_id": "general",
            "origen_tipo": "general",
            "chunking_aplicado": [],
        })

    # ── 4. Transcripciones de chat (15 docs) ───────────────────────────────
    chat_params = [
        ("list_prop_001", "El Cable",   1500000, 2, False),
        ("list_prop_002", "El Cable",   1900000, 3, True),
        ("list_prop_003", "Milán",      1340000, 2, True),
        ("list_prop_004", "Milán",       994000, 1, False),
        ("list_prop_005", "Chipre",     2300000, 4, True),
        ("list_prop_006", "Chipre",     1570000, 2, False),
        ("list_prop_007", "Palermo",    1410000, 2, True),
        ("list_prop_008", "Palermo",    1015000, 1, False),
        ("list_prop_009", "La Enea",    3150000, 5, True),
        ("list_prop_010", "La Enea",    1490000, 2, False),
        ("list_prop_012", "Versalles",  1730000, 3, True),
        ("list_prop_013", "Palogrande", 2030000, 3, False),
        ("list_prop_015", "La Sultana", 1222000, 2, True),
        ("list_prop_018", "Chipre",     1480000, 2, True),
        ("list_prop_019", "Versalles",  1780000, 3, False),
    ]
    for lid, barrio, canon, hab, masc in chat_params:
        docs.append({
            "_id": f"doc_chat_{lid}",
            "tipo": "chat",
            "contenido": chat_session_text(lid, barrio, canon, hab, masc),
            "origen_id": lid,
            "origen_tipo": "chat_session",
            "chunking_aplicado": [],
        })

    # ── 5. Reportes de mercado por barrio (10 docs) ────────────────────────
    for barrio, (lat, lng, estrato) in NEIGHBORHOODS.items():
        if barrio in ["El Cable", "Milán", "Chipre", "Palermo", "La Enea",
                      "Versalles", "Palogrande", "Belén", "La Sultana", "Centro"]:
            docs.append({
                "_id": f"doc_reporte_{barrio.lower().replace(' ', '_')}",
                "tipo": "reporte_mercado",
                "contenido": reporte_mercado(barrio, estrato),
                "origen_id": "general",
                "origen_tipo": "general",
                "chunking_aplicado": [],
            })

    # ── 6. FAQs y políticas (5 docs) ───────────────────────────────────────
    for tema in ["mascotas", "canon_pago", "contratos", "subarriendo", "servicios"]:
        docs.append({
            "_id": f"doc_faq_{tema}",
            "tipo": "faq",
            "contenido": faq_inmobiliario(tema),
            "origen_id": "general",
            "origen_tipo": "general",
            "chunking_aplicado": [],
        })

    # ── 7. Guías de mantenimiento (2 docs) ─────────────────────────────────
    for tipo in ["plomeria", "electrico"]:
        docs.append({
            "_id": f"doc_guia_{tipo}",
            "tipo": "guia_mantenimiento",
            "contenido": guia_mantenimiento(tipo),
            "origen_id": "general",
            "origen_tipo": "general",
            "chunking_aplicado": [],
        })

    # ── 8. Documentos adicionales para llegar a 100+ ───────────────────────
    docs_extra = [
        ("doc_guia_cocina", "guia_mantenimiento", """
GUÍA DE MANTENIMIENTO — COCINA Y ELECTRODOMÉSTICOS EN ARRIENDO, MANIZALES

COCINA INTEGRAL Y GABINETES
Los gabinetes de cocina en madera o MDF requieren limpieza con paño húmedo y productos neutros. Evite el uso de productos abrasivos que dañen el laminado. Las bisagras y rieles de cajones se pueden lubricar con aceite de silicona si presentan fricción, lo cual es una reparación locativa a cargo del arrendatario.

MESÓN Y SUPERFICIE DE TRABAJO
Los mesones en granito o mármol deben limpiarse con jabón neutro. Evite la exposición prolongada a ácidos (limón, vinagre) sin limpiar inmediatamente, ya que pueden manchar o erosionar la superficie. Las manchas difíciles se pueden tratar con bicarbonato de sodio.

ESTUFA Y CAMPANA EXTRACTORA
La limpieza regular de los quemadores de la estufa a gas es responsabilidad del arrendatario. Los filtros de la campana extractora deben limpiarse cada 2-3 meses con agua caliente y detergente. Si la campana tiene filtro de carbón activado, debe reemplazarse cada 6-12 meses.

LAVAPLATOS Y GRIFERÍA
El taponamiento del sifón del lavaplatos por acumulación de grasa y residuos es una reparación locativa del arrendatario. Use periódicamente agua hirviendo con bicarbonato para prevenir taponamientos. Si la fuga proviene de la tubería interna, es responsabilidad del propietario.

NEVERA Y LAVADORA
Si el inmueble incluye nevera y lavadora, su mantenimiento rutinario (limpieza, descongelado, limpieza de filtros de lavadora) es responsabilidad del arrendatario. Daños por mal uso o sobrecarga eléctrica también corren por cuenta del arrendatario.

NOTA: Ante cualquier daño que no sea claramente una reparación locativa, consulte con el propietario o el agente de Inmobiliaria RAG antes de contratar servicios de reparación. Conserve siempre las facturas de mantenimiento realizados.
"""),
        ("doc_guia_pintura", "guia_mantenimiento", """
GUÍA DE MANTENIMIENTO — PINTURA Y ACABADOS EN INMUEBLES DE ARRIENDO

RESPONSABILIDADES DE PINTURA
La pintura de las paredes interiores es un tema frecuente de disputa entre arrendadores y arrendatarios en Colombia. La Ley 820 de 2003 establece que el desgaste natural de la pintura por el uso normal del inmueble durante la vigencia del contrato es responsabilidad del propietario. Sin embargo, manchas, rayaduras, agujeros o daños causados por el arrendatario son de su responsabilidad.

DAÑOS LOCATIVOS VS. ESTRUCTURALES
Ejemplos de daños locativos (arrendatario): agujeros en paredes para colgar cuadros, manchas de alimentos o humedad por descuido, rayaduras causadas por muebles o juegos. Ejemplos de daños estructurales (propietario): humedad por filtraciones externas, hongos por problemas de impermeabilización, descascaramiento por problemas de la estructura.

RECOMENDACIONES AL MOMENTO DE INGRESAR
Al recibir el inmueble, realice un inventario fotográfico detallado del estado de cada pared, techo y superficie. Este registro será fundamental para determinar responsabilidades al momento de la entrega del inmueble.

ACABADOS EN PISOS Y CERÁMICA
Los pisos en cerámica o porcelanato son durables pero pueden romperse por impactos fuertes. Una baldosa rota por descuido del arrendatario es su responsabilidad de reparación. El grout (material entre baldosas) puede oscurecerse con el tiempo; su limpieza con productos especiales es una reparación locativa del arrendatario.

CLOSETS Y CARPINTERÍA
Los golpes, rayones profundos o daños en puertas de closets son responsabilidad del arrendatario. El ajuste de puertas que no cierran bien debido al uso normal puede ser reparación locativa si el daño es menor. Si el daño proviene de humedad estructural o pandeo de la madera, corresponde al propietario.
"""),
        ("doc_guia_seguridad", "guia_mantenimiento", """
GUÍA DE SEGURIDAD — CONSEJOS PARA RESIDENTES EN CONJUNTOS DE MANIZALES

SEGURIDAD EN EL APARTAMENTO
Siempre asegúrese de cerrar con llave la puerta principal al salir, incluso para salidas cortas. No comparta las claves de acceso del conjunto residencial con personas no autorizadas. Ante pérdida o robo de llaves, notifique inmediatamente a la administración del conjunto.

CIRCUITO CERRADO DE TELEVISIÓN (CCTV)
La mayoría de conjuntos residenciales en Manizales cuentan con cámaras de seguridad en accesos, parqueaderos, zonas comunes y pasillos. Las grabaciones se conservan por un período mínimo de 30 días. En caso de incidente, solicite la grabación a la administración dentro de ese período.

VISITANTES Y DOMICILIOS
Nunca autorice el ingreso de visitantes desconocidos sin verificar su identidad. Los domiciliarios deben entregarse en portería o en el hall de entrada, no en el apartamento. Ante llamadas sospechosas que soliciten información sobre su unidad o rutinas, notifique a la administración.

EMERGENCIAS
Tenga siempre a mano los teléfonos de emergencia de Manizales: Policía (123), Bomberos (119), Cruz Roja (132). Conozca las rutas de evacuación del conjunto y las salidas de emergencia. Familiarícese con la ubicación de extintores y llaves de paso de agua y gas.

PREVENCIÓN DE HURTOS
Evite dejar objetos de valor a la vista en vehículos estacionados en el conjunto. No comente públicamente sobre viajes o ausencias prolongadas. Informe a un vecino de confianza sobre ausencias largas para que esté pendiente de su unidad.

SEGURIDAD DE NIÑOS Y MASCOTAS
Asegúrese de que las ventanas y balcones de pisos altos tengan protecciones adecuadas para menores de edad. Las mascotas deben estar siempre controladas en zonas comunes. Informe a portería sobre visitas de niños pequeños para que tengan atención especial en el acceso.
"""),
        ("doc_norma_conv_1", "reglamento_copropiedad", """
NORMAS DE CONVIVENCIA — SECTOR RESIDENCIAL EL CABLE Y MILÁN, MANIZALES

INTRODUCCIÓN
Las siguientes normas de convivencia aplican a los residentes de los sectores El Cable y Milán de Manizales, complementando los reglamentos individuales de cada conjunto residencial. Han sido establecidas por acuerdo comunitario y buscan garantizar la calidad de vida de todos los habitantes del sector.

RESPETO AL ESPACIO PÚBLICO
El andén (acera) y la calzada son de uso público. No está permitido obstaculizarlos con vehículos, objetos personales, mesas de trabajo ni ningún elemento que dificulte el tránsito peatonal o vehicular. Las zonas de parqueo en vía pública son de uso rotativo; está prohibido reservar espacios con conos, muebles u objetos.

MANEJO DE RESIDUOS
Los residuos sólidos deben depositarse en las canecas habilitadas por la Alcaldía de Manizales en los puntos de recolección designados. La recolección de basuras en El Cable y Milán se realiza los días lunes, miércoles y viernes. Los residuos reciclables deben separarse en la fuente.

ANIMALES EN ESPACIO PÚBLICO
Los propietarios de mascotas deben recoger inmediatamente los excrementos de sus animales en zonas públicas. Las mascotas deben ir siempre con correa en espacios públicos. Los perros de razas potencialmente peligrosas deben usar bozal según la Ley 746 de 2002.

RUIDO EN ESPACIOS COMUNES Y VÍAS
El uso de cornetas en vías residenciales de El Cable y Milán está restringido. Las obras de construcción en viviendas particulares deben realizarse entre las 7:00 a.m. y las 6:00 p.m. de lunes a sábado. Queda prohibido el uso de equipos de sonido en vehículos estacionados a volumen que perturbe la tranquilidad del sector.

CONVIVENCIA VECINAL
Los conflictos entre vecinos deben intentar resolverse primero de manera directa y respetuosa. En caso de no lograr acuerdo, el Comité de Convivencia del conjunto o la Inspección de Policía de Manizales son las instancias competentes. Actos de agresión física o verbal entre vecinos son sancionables conforme al Código Nacional de Policía y Convivencia (Ley 1801 de 2016).
"""),
        ("doc_proceso_arriendo", "faq", """
GUÍA DEL PROCESO DE ARRENDAMIENTO — INMOBILIARIA RAG MANIZALES

PASO 1 — BÚSQUEDA DEL INMUEBLE
Navegue por nuestra plataforma y filtre por barrio, tipo de inmueble, precio y características. Cada publicación incluye descripción detallada, fotografías, mapa de ubicación y política de mascotas. Guarde sus favoritos y compare opciones antes de agendar visitas.

PASO 2 — VISITA AL INMUEBLE
Agenda una visita a través del chat de la plataforma o contactando directamente al agente asignado. Durante la visita, revise detalladamente el estado de las instalaciones, iluminación, presión del agua, funcionamiento de llaves, enchufes y electrodomésticos incluidos. Solicite el inventario de entrega para verificar el estado de cada elemento.

PASO 3 — SOLICITUD DE ARRENDAMIENTO
Si el inmueble le interesa, envíe su solicitud con los documentos requeridos: cédula de ciudadanía, dos últimas colillas de pago o constancia laboral, extractos bancarios de los últimos 3 meses, referencias personales y comerciales. Los ingresos deben ser al menos 3 veces el valor del canon mensual.

PASO 4 — ESTUDIO SOCIOECONÓMICO
El propietario o la inmobiliaria realizarán un estudio de crédito y verificación de referencias. Este proceso tarda entre 2 y 5 días hábiles. En caso de aprobación, se procede a la firma del contrato. En caso de rechazo, la inmobiliaria orientará al solicitante sobre opciones alternativas como póliza de arrendamiento o codeudor.

PASO 5 — FIRMA DEL CONTRATO Y ENTREGA
Una vez aprobada la solicitud, se firma el contrato de arrendamiento en presencia de todas las partes. Se realiza el inventario de entrega del inmueble, se registra el estado de cada área y se toman fotografías. El arrendatario entrega el depósito de garantía y el primer mes de arriendo.

PASO 6 — DURANTE EL ARRENDAMIENTO
Mantenga el pago del canon al día dentro de los primeros 5 días de cada mes. Reporte cualquier daño o necesidad de mantenimiento mayor a la inmobiliaria o propietario. Conserve los comprobantes de pago de arriendo, servicios y administración durante todo el período del contrato.

PASO 7 — TERMINACIÓN Y ENTREGA
Notifique con 3 meses de anticipación si no va a renovar el contrato. Realice las reparaciones locativas necesarias antes de la entrega. El propietario tiene 30 días para devolver el depósito de garantía, descontando daños verificados en el inventario de salida.
"""),
        ("doc_amenidades_manizales", "reporte_mercado", """
GUÍA DE AMENIDADES Y SERVICIOS — BARRIOS DE MANIZALES, CALDAS

SERVICIOS EDUCATIVOS
Manizales cuenta con una amplia oferta educativa en todos sus barrios. En el sector universitario (Palogrande, El Cable, Centro), se encuentran la Universidad de Caldas, la Universidad Nacional sede Manizales, la Universidad de Manizales y la Universidad Autónoma de Manizales. Para educación básica y media, los barrios de mayor cobertura son Milán, Chipre, Palermo y La Enea, donde se concentran los colegios de mejor desempeño académico según pruebas Saber.

SERVICIOS DE SALUD
El sistema de salud en Manizales se estructura alrededor del Hospital de Caldas (barrio Milán), el Hospital Santa Sofía y la Clínica Versalles. Para atención de urgencias, los sectores de El Cable, Chipre y Centro tienen los tiempos de respuesta más rápidos de la ciudad. En La Enea y la zona oriental, la Clínica Sanitas tiene cobertura para varias EPS.

TRANSPORTE PÚBLICO
El sistema Cable Aéreo (TransCable) conecta los barrios en ladera con el centro de la ciudad. Las rutas de bus urbano tienen cobertura en todos los barrios principales. Los sectores de El Cable, Milán y Chipre tienen la mayor frecuencia de rutas y mayor conectividad con el resto de la ciudad.

CENTROS COMERCIALES Y COMERCIO
El Cable Plaza es el centro comercial de referencia del sector norte. Chipre y el Centro histórico concentran comercio tradicional y gastronómico. Pereira está a 50 minutos y Bogotá a 3 horas por carretera, lo que posiciona a Manizales como hub regional.

PARQUES Y ESPARCIMIENTO
Manizales cuenta con el Parque Los Yarumos (ecológico), el Parque de la Mujer (recreativo), el Estadio Palogrande (deporte) y múltiples parques de barrio. Los sectores de Chipre y Palogrande tienen la mayor densidad de espacios verdes por habitante de la ciudad.

GASTRONOMÍA
La cultura cafetera de Manizales se refleja en una vibrante escena gastronómica. El barrio Milán concentra restaurantes de cocina internacional y colombiana. Chipre y El Cable son reconocidos por sus cafeterías especializadas y bares con vista a la ciudad. Los precios son considerablemente inferiores a los de Bogotá o Medellín para calidades similares.
"""),
        ("doc_inversion_inmobiliaria", "reporte_mercado", """
GUÍA DE INVERSIÓN INMOBILIARIA — MANIZALES, CALDAS

¿POR QUÉ INVERTIR EN FINCA RAÍZ EN MANIZALES?
Manizales es considerada una de las ciudades con mejor calidad de vida en Colombia y con uno de los mercados inmobiliarios más estables del Eje Cafetero. Su economía, basada en la agroindustria cafetera, el turismo y los servicios universitarios, genera una demanda sostenida de inmuebles para arrendamiento.

RENTABILIDAD ESPERADA
La rentabilidad bruta anual por arrendamiento en Manizales oscila entre el 6% y el 9% del valor comercial del inmueble, dependiendo del sector y el tipo de propiedad. Los apartamentos en sectores universitarios (Palogrande, El Cable) tienden a tener las mayores tasas de ocupación (superiores al 95%) y menor tiempo de vacancia.

VALORIZACIÓN HISTÓRICA
En los últimos 10 años, el valor del metro cuadrado en Manizales ha tenido una valorización promedio del 8% al 12% anual en sectores como El Cable, Palogrande y Chipre. Esta valorización supera consistentemente la inflación, convirtiendo la finca raíz manizaleña en una inversión en activo real.

ZONAS DE MAYOR POTENCIAL
El Cable: alta demanda, buena valorización, perfil socioeconómico alto (estrato 4-5). Ideal para inversión en arriendo a profesionales.
Palogrande: proximidad a universidades, alta demanda estudiantil, buena liquidez al momento de venta.
Chipre: sector en desarrollo, precios aún asequibles, potencial de valorización en los próximos 5 años.
La Enea: cercano al aeropuerto, en proceso de consolidación como sector residencial de calidad.

CONSIDERACIONES FISCALES
La renta por arrendamiento de inmuebles es un ingreso gravable para personas naturales en Colombia. Si los ingresos anuales por arrendamiento superan ciertos topes, deben declararse en la declaración de renta. Consulte a un contador o asesor fiscal para optimizar su estructura de inversión.

RIESGOS A CONSIDERAR
El mercado inmobiliario de Manizales, como cualquier mercado de finca raíz, no es completamente líquido. Los períodos de vacancia entre arrendatarios pueden afectar la rentabilidad. La correcta selección del arrendatario y el uso de pólizas de arrendamiento son medidas fundamentales para mitigar el riesgo de impago.
"""),
        ("doc_tips_arrendatario", "faq", """
TIPS PARA ARRENDATARIOS PRIMERIZOS EN MANIZALES

1. NEGOCIE ANTES DE FIRMAR
Todo en el contrato de arrendamiento es negociable antes de la firma. El canon, el tiempo del contrato, las condiciones de mascotas, el período de gracia para mudarse y los elementos incluidos (nevera, lavadora, accesorios de cocina) pueden ser objeto de negociación. Una vez firmado el contrato, los cambios requieren acuerdo escrito de ambas partes.

2. HAGA UN INVENTARIO FOTOGRÁFICO COMPLETO
El día que reciba el inmueble, tome fotografías de cada habitación, incluyendo paredes, pisos, techos, ventanas, electrodomésticos y zonas de servicio. Envíe este inventario al arrendador por correo electrónico para que quede registro de la fecha. Esto lo protegerá de cobros injustos al momento de entregar el inmueble.

3. ENTIENDA QUÉ CUBRE EL CANON
El canon de arrendamiento en Manizales generalmente NO incluye: servicios públicos (agua, luz, gas), internet y cable, cuota de administración del conjunto, parqueadero adicional (si no está incluido), ni nada que no esté expresamente mencionado en el contrato.

4. PRESUPUESTE CORRECTAMENTE
Además del canon mensual, calcule los costos adicionales: servicios públicos (estimado $150.000-$300.000/mes para un apartamento de 2 habitaciones en Manizales), administración (si aplica), internet ($60.000-$100.000/mes). El costo total mensual puede ser un 30-40% superior al canon.

5. CONOZCA SUS DERECHOS
Como arrendatario en Colombia tiene derecho a: habitar el inmueble en paz y tranquilidad, solicitar reparaciones estructurales al propietario, recibir el depósito de garantía dentro de los 30 días de entrega del inmueble, recibir aviso con mínimo 3 meses de anticipación si el propietario quiere dar por terminado el contrato.

6. COMUNÍQUESE POR ESCRITO
Mantenga toda comunicación importante con el propietario o agente por correo electrónico o mensajes de texto. Esto crea un registro que puede ser útil en caso de disputas. Evite acuerdos verbales sin respaldo escrito, especialmente para temas de reparaciones, prórrogas o cambios en el canon.

7. SEGURO DE ARRENDATARIO
Considere adquirir un seguro de contenidos que proteja sus bienes personales (muebles, electrodomésticos, ropa) ante robos, incendios u otros siniestros. El propietario tiene seguro sobre la estructura del inmueble, pero sus pertenencias personales no están cubiertas por ese seguro.
"""),
        ("doc_zonas_comunes_guia", "reglamento_copropiedad", """
GUÍA DE USO DE ZONAS COMUNES — CONJUNTOS RESIDENCIALES DE MANIZALES

PRINCIPIOS GENERALES
Las zonas comunes de los conjuntos residenciales de Manizales son bienes de copropiedad que pertenecen proporcionalmente a todos los propietarios. Su uso es un derecho y una responsabilidad compartida. El cuidado de estos espacios impacta directamente en la valorización del inmueble y la calidad de vida de todos los residentes.

ÁREAS VERDES Y JARDINES
Las zonas verdes son de disfrute para todos los residentes. No se permite depositar basuras, escombros ni objetos personales en las zonas verdes. El personal de mantenimiento realiza el corte de pasto y el cuidado de las plantas según cronograma de la administración. Los residentes pueden plantar flores o plantas decorativas previa autorización de la administración.

SALÓN SOCIAL
El salón social es el espacio comunitario de mayor demanda en los conjuntos de Manizales. Para su uso exclusivo, los residentes deben: Reservarlo con mínimo 72 horas de anticipación por escrito. Pagar la cuota de aseo establecida por la administración. Responsabilizarse por daños causados durante el evento. Retirar todos los elementos del salón y entregarlo limpio al finalizar. El incumplimiento de estas normas puede generar restricción del derecho de uso.

GIMNASIO
El gimnasio es para uso exclusivo de residentes mayores de 16 años. Esté acompañado por un adulto si lleva menores. Use ropa y calzado deportivo apropiado. Limpie los equipos después de usarlos con los productos disponibles. No ocupe equipos si hay otros usuarios esperando (máximo 30 minutos por máquina).

PARQUEADERO
Cada parqueadero tiene asignado un número de unidad. Está estrictamente prohibido usar el parqueadero de otro residente, incluso temporalmente. El parqueadero es solo para vehículos; no se permite el almacenamiento de objetos, chatarra ni la realización de trabajos mecánicos. La velocidad máxima dentro del conjunto es de 10 km/h.

CUARTO DE BASURAS
El cuarto de basuras debe usarse correctamente para garantizar el servicio de recolección. Deposite las bolsas bien cerradas en los días de recolección indicados. Realice la separación de residuos (orgánicos, reciclables) según lo exige la normativa ambiental de Manizales. No deje basuras en pasillos, escaleras o áreas comunes bajo ninguna circunstancia.
"""),
        ("doc_ley_820", "faq", """
LEY 820 DE 2003 — GUÍA PRÁCTICA PARA ARRENDATARIOS Y ARRENDADORES EN COLOMBIA

¿QUÉ ES LA LEY 820 DE 2003?
La Ley 820 de 2003 es el estatuto que regula el arrendamiento de vivienda urbana en Colombia. Establece los derechos y obligaciones de arrendadores y arrendatarios, los requisitos del contrato, las causales de terminación y el régimen sancionatorio.

OBLIGACIONES DEL ARRENDADOR (Artículo 8)
El arrendador está obligado a: Entregar el inmueble en buen estado de servicio, seguridad y sanidad. Mantener en buen estado el inmueble durante el contrato. Realizar las reparaciones necesarias que no sean locativas. Suministrar al arrendatario comprobante de pago cuando lo solicite. No aumentar el canon en cuantía superior al IPC anual.

OBLIGACIONES DEL ARRENDATARIO (Artículo 9)
El arrendatario está obligado a: Pagar el precio del arrendamiento dentro del plazo pactado. Cuidar el inmueble y las cosas recibidas en arrendamiento. Pagar las reparaciones locativas a que haya lugar. Usar el inmueble para el uso convenido y en la forma debida. Restituir el inmueble en buen estado al vencimiento del plazo.

PRECIO DEL ARRENDAMIENTO (Artículo 18)
El precio mensual de arrendamiento fijado por las partes no puede exceder el 1% del valor comercial del inmueble. El incremento anual está limitado al IPC del año inmediatamente anterior. Los contratos deben estipular el canon inicial y la fecha de actualización.

TERMINACIÓN DEL CONTRATO (Artículos 22-25)
Por parte del arrendador: No pago del canon por 2 períodos consecutivos, subarriendo no autorizado, deterioro del inmueble, necesidad del propietario de habitar el inmueble (con preaviso de 3 meses). Por parte del arrendatario: Incumplimiento de obligaciones del arrendador, suspensión de servicios públicos imputable al propietario, deterioro grave del inmueble imputable al arrendador.

DEPÓSITO Y FIANZA (Artículo 16)
El depósito no puede ser superior a 2 meses de canon. Debe devolverse dentro de los 30 días siguientes a la restitución del inmueble, con los intereses causados. El arrendador no puede cobrar cuotas de administración ni ningún otro concepto adicional al canon y el depósito al inicio del contrato.
"""),
    ]

    # 8 documentos adicionales de variaciones de propiedades (props 1-8 con enfoque diferente)
    enfoques = [
        ("ubicacion", "Ubicación privilegiada, acceso a transporte, servicios cercanos, conectividad vial del sector."),
        ("habitaciones", "Distribución interior detallada, habitaciones, closets, ventilación, pisos y acabados."),
    ]
    for i, cfg in enumerate(PROPERTY_CONFIGS[:4]):
        for j, (enfoque, desc) in enumerate(enfoques):
            lat, lng, estrato = NEIGHBORHOODS[cfg["barrio"]]
            canon = canon_arriendo(cfg["tipo"], cfg["area"], cfg["hab"])
            contenido_extra = f"""
FICHA TÉCNICA — {cfg['tipo'].upper()} EN {cfg['barrio'].upper()} — ENFOQUE: {enfoque.upper()}

Propiedad: {cfg['_id']} | Barrio: {cfg['barrio']}, Manizales | Estrato: {estrato}
Área: {cfg['area']} m² | Habitaciones: {cfg['hab']} | Baños: {cfg['ban']}
Canon arriendo: ${canon:,} COP | Parqueadero: {'Sí' if cfg['park'] else 'No'} | Mascotas: {'Sí' if cfg['masc'] else 'No'}

ANÁLISIS DETALLADO — {desc}

El inmueble en {cfg['barrio']} presenta características destacadas en cuanto a {enfoque}.
La distribución espacial de {cfg['area']} metros cuadrados permite una organización funcional
que maximiza el aprovechamiento de cada ambiente. Con {cfg['hab']} habitaciones y {cfg['ban']} baños,
el inmueble resulta ideal para familias o profesionales que valoran la calidad de vida en
uno de los sectores más dinámicos de Manizales, Caldas.

Las coordenadas exactas del inmueble son: latitud {lat:.4f}, longitud {lng:.4f},
ubicándose en el corazón del barrio {cfg['barrio']}. La cercanía a vías principales y
al sistema de transporte público garantiza movilidad eficiente en toda la ciudad.

Canon de arrendamiento: ${canon:,} COP mensuales. Depósito: 2 cánones.
Administración mensual: {'$' + f'{cfg["admin"]:,} COP' if cfg['admin'] > 0 else 'N/A (inmueble independiente)'}.
""".strip()
            docs.append({
                "_id": f"doc_ficha_{cfg['_id']}_{enfoque}",
                "tipo": "descripcion_propiedad",
                "contenido": contenido_extra,
                "origen_id": cfg["_id"],
                "origen_tipo": "property",
                "chunking_aplicado": [],
            })

    for doc_id, tipo, contenido in docs_extra:
        docs.append({
            "_id": doc_id,
            "tipo": tipo,
            "contenido": contenido.strip(),
            "origen_id": "general",
            "origen_tipo": "general",
            "chunking_aplicado": [],
        })

    for doc in docs:
        upsert(col, doc)
    print(f"  [OK] {len(docs)} documentos en documents_repository")
    return docs


def load_image_embeddings(db):
    """Embeddings de imagen simulados (dimensión 512, CLIP)."""
    import random
    import math
    col = db["image_embeddings"]
    media_col = db["media_assets"]
    count = 0
    for media in media_col.find({}, {"_id": 1}):
        mid = media["_id"]
        emb_id = f"img_emb_{mid}"
        random.seed(hash(mid) % (2**32))
        vec = [random.uniform(-1, 1) for _ in range(512)]
        norm = math.sqrt(sum(x**2 for x in vec))
        vec = [x / norm for x in vec]
        upsert(col, {
            "_id": emb_id,
            "media_id": mid,
            "embedding": vec,
            "modelo": "clip-vit-base-patch32",
        })
        count += 1
    print(f"  [OK] {count} image_embeddings (simulados con CLIP 512-dim)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Generando dataset de prueba ===")
    db = get_db()

    load_users(db)
    load_agencies(db)
    load_properties(db)
    load_listings(db)
    contract_data = load_contracts(db)
    load_reviews(db)
    load_maintenance(db)
    docs = load_documents(db, contract_data)
    load_image_embeddings(db)

    print("\n=== Dataset cargado exitosamente ===")
    print(f"  Base de datos: {settings.db_name}")
    print(f"  Documentos para RAG: {len(docs)}")
    print("\nPróximo paso: ejecutar python chunking_pipeline.py")

    close()


if __name__ == "__main__":
    main()
