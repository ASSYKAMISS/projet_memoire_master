from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .models import Departement, ProfilUtilisateur


def is_responsable(user):
    return hasattr(user, 'profil') and user.profil.role == 'RESPONSABLE'


def ensure_profile(user, role='AGENT', departement=None, cree_par=None):
    profil, created = ProfilUtilisateur.objects.get_or_create(
        utilisateur=user,
        defaults={
            'role': role,
            'departement': departement,
            'cree_par': cree_par,
        }
    )

    if not created:
        profil.role = role
        profil.departement = departement
        profil.cree_par = cree_par
        profil.save()

    return profil


@login_required
def create_user_by_responsable(request):
    if not request.user.is_superuser and not is_responsable(request.user):
        messages.error(request, "Accès réservé au superadmin ou au responsable.")
        return redirect('dashboard')

    if request.user.is_superuser:
        departements = Departement.objects.all().order_by('nom')
        can_choose_role = True
    else:
        departements = Departement.objects.filter(
            responsable=request.user
        ).order_by('nom')
        can_choose_role = False

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        departement_id = request.POST.get('departement')
        role = request.POST.get('role', 'AGENT')

        if not request.user.is_superuser:
            role = 'AGENT'

        if role not in ['RESPONSABLE', 'AGENT']:
            messages.error(request, "Rôle invalide.")
            return redirect('create_user')

        if not first_name or not last_name or not email:
            messages.error(request, "Tous les champs sont obligatoires.")
            return redirect('create_user')

        if role == 'AGENT' and not departement_id:
            messages.error(request, "Veuillez sélectionner un département pour l'agent.")
            return redirect('create_user')

        if User.objects.filter(username=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect('create_user')

        departement = None
        if role == 'AGENT':
            departement = get_object_or_404(departements, id=departement_id)

        password = "Agent@2026"
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        user.is_staff = True
        user.is_superuser = False
        user.save()

        ensure_profile(
            user,
            role=role,
            departement=departement,
            cree_par=request.user
        )

        label = "Responsable" if role == 'RESPONSABLE' else "Agent"
        messages.success(request, f"{label} créé avec succès. Mot de passe par défaut : Agent@2026")
        return redirect('user_management')

    return render(request, 'accounts/create_user.html', {
        'departements': departements,
        'active_page': 'create_user',
        'can_choose_role': can_choose_role,
    })


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Connexion réussie.")
            return redirect('dashboard')

        messages.error(request, "Email ou mot de passe incorrect.")

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "Déconnexion réussie.")
    return redirect('home')


@login_required
def user_management(request):
    if not request.user.is_superuser and not is_responsable(request.user):
        messages.error(request, "Accès réservé au superadmin ou au responsable.")
        return redirect('dashboard')

    if request.user.is_superuser:
        users = User.objects.exclude(id=request.user.id).order_by('-date_joined')
        titre_page = "Gestion globale des utilisateurs"
    else:
        users = User.objects.filter(
            profil__cree_par=request.user,
            profil__role='AGENT'
        ).order_by('-date_joined')
        titre_page = "Mes agents"

    return render(request, 'accounts/users.html', {
        'users': users,
        'titre_page': titre_page,
        'active_page': 'users',
    })


@login_required
def toggle_user_status(request, user_id):
    if not request.user.is_superuser and not is_responsable(request.user):
        messages.error(request, "Accès refusé.")
        return redirect('dashboard')

    if request.user.is_superuser:
        user_item = get_object_or_404(User, id=user_id)
    else:
        user_item = get_object_or_404(
            User,
            id=user_id,
            profil__cree_par=request.user,
            profil__role='AGENT'
        )

    if user_item == request.user:
        messages.warning(request, "Vous ne pouvez pas désactiver votre propre compte.")
        return redirect('user_management')

    user_item.is_active = not user_item.is_active
    user_item.save()
    messages.success(request, "Statut utilisateur mis à jour.")
    return redirect('user_management')


@login_required
def change_user_role(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect('dashboard')

    user_item = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        role = request.POST.get('role')

        if role == 'RESPONSABLE':
            user_item.is_staff = True
            user_item.is_superuser = False
            ensure_profile(user_item, role='RESPONSABLE', departement=None)
        elif role == 'AGENT':
            user_item.is_staff = True
            user_item.is_superuser = False
            ensure_profile(user_item, role='AGENT')
        else:
            messages.error(request, "Rôle invalide.")
            return redirect('user_management')

        user_item.save()
        messages.success(request, "Rôle utilisateur mis à jour.")

    return redirect('user_management')


@login_required
def departments(request):
    if not request.user.is_superuser and not is_responsable(request.user):
        messages.error(request, "Accès réservé au superadmin ou au responsable.")
        return redirect('dashboard')

    if request.method == 'POST':
        nom = request.POST.get('nom')
        description = request.POST.get('description')

        if not nom:
            messages.error(request, "Le nom du département est obligatoire.")
            return redirect('departments')

        if Departement.objects.filter(nom=nom).exists():
            messages.error(request, "Ce département existe déjà.")
            return redirect('departments')

        Departement.objects.create(
            nom=nom,
            description=description,
            responsable=None if request.user.is_superuser else request.user
        )

        messages.success(request, "Département créé avec succès.")
        return redirect('departments')

    if request.user.is_superuser:
        departements = Departement.objects.all().order_by('-date_creation')
    else:
        departements = Departement.objects.filter(
            responsable=request.user
        ).order_by('-date_creation')

    return render(request, 'accounts/departments.html', {
        'departements': departements,
        'active_page': 'departements',
    })
