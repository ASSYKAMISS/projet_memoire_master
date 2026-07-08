from django.shortcuts import redirect
from django.urls import reverse


class PasswordChangeRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'profil'):
            allowed_paths = {
                reverse('change_password'),
                reverse('logout'),
            }
            if request.user.profil.doit_changer_mot_de_passe and request.path not in allowed_paths:
                return redirect('change_password')

        return self.get_response(request)