"""Conservative rules shared by input, output, external sources and memory."""
import re
import unicodedata

REDIRECT = ("Estoy aquí para ayudarte con operaciones de localización de Brasaland: "
            "incidentes, inventario y procedimientos de turno. ¿Qué necesitas para tu localización?")
SAFE_RESPONSE = "No puedo proporcionar ese contenido. " + REDIRECT

def normalize(text):
    text = unicodedata.normalize("NFKD", text).casefold()
    return " ".join("".join(c for c in text if not unicodedata.combining(c)
                             and unicodedata.category(c) != "Cf").split())

def matches(pattern, text):
    return bool(re.search(pattern, normalize(text)))

INJECTION = (r"(?:ignor\w*|olvid\w*|disregard|forget|override|bypass).{0,90}"
             r"(?:instruccion|regla|brasaland|instruction|rule|system|previous)|"
             r"(?:sin|without|no)\s+(?:reglas|restricciones|rules|restrictions)|"
             r"(?:no tuvieras|no tengas|dont have|do not have).{0,20}(?:reglas|restricciones|rules)|"
             r"(?:ahora eres|you are now).{0,60}(?:asistente|assistant|unrestricted)|"
             r"(?:system|developer)\s*(?:prompt|message|:)|"
             r"(?:prompt|instrucciones?)\s+(?:intern[oa]s?|del sistema)|"
             r"\[/?(?:system|inst)\]|<\|(?:im_start|system)|"
             r"(?:revela|muestra|repite|print|reveal).{0,45}(?:prompt|instructions)|"
             r"(?:ejecuta|execute|invoke).{0,40}(?:tool|shell|comando)")
SENSITIVE = (r"receta\s+(?:madre|completa|de la salsa)|formula\s+(?:propietaria|completa)|"
             r"(?:house|mother|secret)\s+(?:sauce\s+)?recipe|"
             r"(?:salsa.{0,55}(?:ingrediente|proporcion|cantidades|gramos)|"
             r"(?:ingrediente|proporcion|cantidades).{0,55}salsa)|"
             r"(?:contrato|contract).{0,50}(?:proveedor|supplier)|"
             r"(?:precio|price|costo|cost|tarifa).{0,65}(?:negociad|proveedor|supplier|porcion)|"
             r"\b(?:nomina|payroll|salario|salary|sueldo|wage)\b|"
             r"(?:api[_ -]?key|bearer)\s*[:= ]\s*[a-z0-9_./+-]{12,}|"
             r"(?:evaluacion|evaluation|review).{0,30}(?:desempeno|performance|empleado|employee)|"
             r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\+?\d{9,15}\b|"
             r"(?:telefono|email|correo|direccion|pii|datos personales).{0,40}(?:cliente|customer)|"
             r"(?:cliente|customer).{0,40}(?:telefono|email|correo|direccion|pii)")
PERSONAL = (r"\b(?:poema|poem|ensayo|essay|terapeuta|therapist|homework)\b|"
            r"tarea.{0,30}(?:universidad|escolar)|(?:codigo|code).{0,40}(?:otro proyecto|other project)|"
            r"(?:consejo|advice).{0,30}(?:personal|pareja|relationship)")
FOLLOWUP = r"\b(?:ingrediente|ingredient|primero|primer|segundo|siguiente|next|cantidad|cuanto|proporcion)\b"
DOMAIN = (r"\b(?:ticket|incidente|incidencia|incident|inventario|inventory|stock|turno|shift|"
          r"apertura|cierre|opening|closing|procedimiento|procedimientos|procedure|protocolo|playbook|"
          r"alergeno|alergenos|allergen|cocina|sala|local|sede|location|proveedor|supplier|"
          r"politica|politicas|policy|puntos|oro|points|conservacion|reporte|report|resumen|resumenes)\b")

def unsafe_reason(text):
    if matches(INJECTION, text):
        return "instruction_override"
    if matches(SENSITIVE, text):
        return "sensitive_data"
    return None

def require_safe_memory(text):
    reason = unsafe_reason(text)
    if reason:
        from .events import record
        record("memory", "security" if reason == "instruction_override" else "content", "block", reason)
        raise ValueError("Contenido no memorizable")
