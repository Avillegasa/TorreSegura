from django.utils.deprecation import MiddlewareMixin

class DetectarDispositivoMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        es_movil = any(mobile in user_agent for mobile in ['iphone', 'android', 'blackberry', 'mobile'])

        request.es_movil = es_movil  # Esto estará disponible en views y templates
