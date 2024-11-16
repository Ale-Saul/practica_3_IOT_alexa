import json
import logging
import boto3
import time
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import get_request_type, get_intent_name
from ask_sdk_model import Response

# Configuración de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configura el cliente IoT Data
iot_client = boto3.client('iot-data', endpoint_url='https://aleas6fbrinez-ats.iot.us-east-1.amazonaws.com')
thing_name = "proyecto_03"  # Reemplaza con tu dispositivo en IoT Core

# Manejador de inicio de la skill
class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return get_request_type(handler_input) == "LaunchRequest"

    def handle(self, handler_input):
        speak_output = 'Bienvenido al sistema de riego. Puedes decir "activar el regador", "desactivar el regador", o "consultar humedad".'
        return handler_input.response_builder.speak(speak_output).reprompt(speak_output).response

# Manejador para activar el regador
class ActivarRegadorIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return get_intent_name(handler_input) == "ActivarRegadorIntent"

    def handle(self, handler_input):
        payload = {"state": {"desired": {"bomba": "ON"}}}
        try:
            iot_client.update_thing_shadow(thingName=thing_name, payload=json.dumps(payload))
            speak_output = 'El regador ha sido activado.'
        except Exception as e:
            logger.error(f"Error al activar el regador: {e}")
            speak_output = 'Hubo un problema al activar el regador, por favor intenta nuevamente.'
        return handler_input.response_builder.speak(speak_output).response

# Manejador para desactivar el regador
class DesactivarRegadorIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return get_intent_name(handler_input) == "DesactivarRegadorIntent"

    def handle(self, handler_input):
        payload = {"state": {"desired": {"bomba": "OFF"}}}
        try:
            iot_client.update_thing_shadow(thingName=thing_name, payload=json.dumps(payload))
            speak_output = 'El regador ha sido desactivado.'
        except Exception as e:
            logger.error(f"Error al desactivar el regador: {e}")
            speak_output = 'Hubo un problema al desactivar el regador, por favor intenta nuevamente.'
        return handler_input.response_builder.speak(speak_output).response

# Manejador para consultar la humedad
class ConsultarHumedadIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return get_intent_name(handler_input) == "ConsultarHumedadIntent"

    def handle(self, handler_input):
        try:
            iot_client.publish(
                topic="sistema_riego/solicitud_humedad",
                qos=1,
                payload=json.dumps({"message": "SOLICITAR_HUMEDAD"})
            )
            time.sleep(2)  # Espera unos segundos para que el ESP32 procese y actualice el shadow
            response = iot_client.get_thing_shadow(thingName=thing_name)
            json_state = json.loads(response["payload"].read())
            humedad = json_state["state"]["reported"].get("humedad", None)
            
            if humedad is None:
                speak_output = "No puedo obtener la humedad en este momento."
            else:
                estado = "húmedo" if humedad < 1300 else "seco"
                speak_output = f"El nivel de humedad es {humedad}. El suelo está {estado}."

        except Exception as e:
            logger.error(f"Error al obtener la humedad: {e}")
            speak_output = "Hubo un problema al obtener la humedad. Por favor, intenta nuevamente."

        return handler_input.response_builder.speak(speak_output).response

# Manejador de errores
class ErrorHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(f"Error handled: {exception}")
        speak_output = 'Lo siento, hubo un problema. Por favor intenta nuevamente.'
        return handler_input.response_builder.speak(speak_output).response

# Construcción de la skill
sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(ActivarRegadorIntentHandler())
sb.add_request_handler(DesactivarRegadorIntentHandler())
sb.add_request_handler(ConsultarHumedadIntentHandler())
sb.add_exception_handler(ErrorHandler())

lambda_handler = sb.lambda_handler()


