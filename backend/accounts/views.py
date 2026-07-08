from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from .models import Departement, Organisation, ProfilUtilisateur


ROLE_ADMIN_ORG = 'ADMIN_ORGANISATION'
ROLE_RESPONSABLE_DEPT = 'RESPONSABLE_DEPARTEMENT'
ROLE_RESPONSABLE_LEGACY = 'RESPONSABLE'
ROLE_AGENT = 'AGENT'
RESPONSABLE_ROLES = [ROLE_RESPONSABLE_DEPT, ROLE_RESPONSABLE_LEGACY]
MANAGER_ROLES = [ROLE_ADMIN_ORG, ROLE_RESPONSABLE_DEPT, ROLE_RESPONSABLE_LEGACY]


def is_superadmin(user):
    return user.is_authenticated and user.is_superuser


def is_admin_organisation(user):
    return hasattr(user, 'profil') and user.profil.role == ROLE_ADMIN_ORG


def is_responsable(user):
    return hasattr(user, 'profil') and user.profil.role in RESPONSABLE_ROLES


def can_manage_users(user):
    return is_superadmin(user) or is_admin_organisation(user) or is_responsable(user)


def role_label(role):
    labels = {
        ROLE_ADMIN_ORG: 'Admin organisation',
        ROLE_RESPONSABLE_DEPT: 'Responsable département',
        ROLE_RESPONSABLE_LEGACY: 'Responsable',
        ROLE_AGENT: 'Agent',
    }
    return labels.get(role, role)


def ensure_profile(
    user,
    role=ROLE_AGENT,
    organisation=None,
    departement=None,
    cree_par=None,
    poste='',
    matricule='',
    telephone='',
    adresse='',
    date_naissance=None,
):
    profil, created = ProfilUtilisateur.objects.get_or_create(
        utilisateur=user,
        defaults={
            'role': role,
            'organisation': organisation,
            'departement': departement,
            'cree_par': cree_par,
            'poste': poste,
            'matricule': matricule,
            'telephone': telephone,
            'adresse': adresse,
            'date_naissance': date_naissance,
            'doit_changer_mot_de_passe': True,
        }
    )

    if not created:
        profil.role = role
        profil.organisation = organisation
        profil.departement = departement
        profil.cree_par = cree_par
        profil.poste = poste
        profil.matricule = matricule
        profil.telephone = telephone
        profil.adresse = adresse
        profil.date_naissance = date_naissance
        profil.save()

    return profil


def get_user_scope(request_user):
    if request_user.is_superuser:
        return {
            'roles': [ROLE_ADMIN_ORG, ROLE_RESPONSABLE_DEPT, ROLE_AGENT],
            'organisations': Organisation.objects.all().order_by('nom'),
            'departements': Departement.objects.select_related('organisation').all().order_by('organisation__nom', 'nom'),
            'forced_organisation': None,
            'forced_departement': None,
            'can_choose_role': True,
        }

    profil = getattr(request_user, 'profil', None)

    if profil and profil.role == ROLE_ADMIN_ORG:
        return {
            'roles': [ROLE_RESPONSABLE_DEPT, ROLE_AGENT],
            'organisations': Organisation.objects.filter(id=profil.organisation_id),
            'departements': Departement.objects.filter(organisation=profil.organisation).order_by('nom'),
            'forced_organisation': profil.organisation,
            'forced_departement': None,
            'can_choose_role': True,
        }

    if profil and profil.role in RESPONSABLE_ROLES:
        return {
            'roles': [ROLE_AGENT],
            'organisations': Organisation.objects.filter(id=profil.organisation_id),
            'departements': Departement.objects.filter(id=profil.departement_id),
            'forced_organisation': profil.organisation,
            'forced_departement': profil.departement,
            'can_choose_role': False,
        }

    return None


def manageable_users_queryset(request_user):
    queryset = User.objects.select_related(
        'profil', 'profil__organisation', 'profil__departement', 'profil__cree_par'
    )

    if request_user.is_superuser:
        return queryset.exclude(id=request_user.id)

    profil = getattr(request_user, 'profil', None)
    if profil and profil.role == ROLE_ADMIN_ORG:
        return queryset.filter(profil__organisation=profil.organisation).exclude(id=request_user.id)

    if profil and profil.role in RESPONSABLE_ROLES:
        return queryset.filter(
            profil__departement=profil.departement,
            profil__role=ROLE_AGENT,
        ).exclude(id=request_user.id)

    return queryset.none()


def get_manageable_user_or_404(request_user, user_id):
    return get_object_or_404(manageable_users_queryset(request_user), id=user_id)


@login_required
def create_user_by_responsable(request):
    scope = get_user_scope(request.user)
    if scope is None:
        messages.error(request, "Accès réservé aux administrateurs et responsables.")
        return redirect('dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        role = request.POST.get('role', ROLE_AGENT)
        organisation_id = request.POST.get('organisation')
        departement_id = request.POST.get('departement')
        poste = request.POST.get('poste', '').strip()
        matricule = request.POST.get('matricule', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        adresse = request.POST.get('adresse', '').strip()
        date_naissance = parse_date(request.POST.get('date_naissance', '').strip()) if request.POST.get('date_naissance') else None

        if role not in scope['roles']:
            messages.error(request, "Rôle invalide pour votre niveau d'accès.")
            return redirect('create_user')

        if not first_name or not last_name or not email:
            messages.error(request, "Le nom, le prénom et l'email sont obligatoires.")
            return redirect('create_user')

        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect('create_user')

        organisation = scope['forced_organisation']
        if organisation is None:
            if not organisation_id:
                messages.error(request, "Veuillez sélectionner une organisation.")
                return redirect('create_user')
            organisation = get_object_or_404(Organisation, id=organisation_id)

        departement = scope['forced_departement']
        if role in [ROLE_RESPONSABLE_DEPT, ROLE_AGENT]:
            if departement is None:
                if not departement_id:
                    messages.error(request, "Veuillez sélectionner un département.")
                    return redirect('create_user')
                departement = get_object_or_404(Departement, id=departement_id, organisation=organisation)
        else:
            departement = None

        password = "Agent@2026"
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_staff = True
        user.is_superuser = False
        user.save()

        ensure_profile(
            user,
            role=role,
            organisation=organisation,
            departement=departement,
            cree_par=request.user,
            poste=poste,
            matricule=matricule,
            telephone=telephone,
            adresse=adresse,
            date_naissance=date_naissance,
        )

        if role == ROLE_RESPONSABLE_DEPT and departement:
            departement.responsable = user
            departement.save(update_fields=['responsable'])

        messages.success(request, "Compte créé avec succès. Mot de passe temporaire : Agent@2026")
        return redirect('user_management')

    return render(request, 'accounts/create_user.html', {
        'roles': scope['roles'],
        'role_labels': {role: role_label(role) for role in scope['roles']},
        'organisations': scope['organisations'],
        'departements': scope['departements'],
        'forced_organisation': scope['forced_organisation'],
        'forced_departement': scope['forced_departement'],
        'can_choose_role': scope['can_choose_role'],
        'active_page': 'create_user',
    })


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Connexion réussie.")
            if hasattr(user, 'profil') and user.profil.doit_changer_mot_de_passe:
                return redirect('change_password')
            return redirect('dashboard')

        messages.error(request, "Email ou mot de passe incorrect.")

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "Déconnexion réussie.")
    return redirect('home')


@login_required
def user_management(request):
    if not can_manage_users(request.user):
        messages.error(request, "Accès réservé aux administrateurs et responsables.")
        return redirect('dashboard')

    users = manageable_users_queryset(request.user).order_by('-date_joined')
    search = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    departement_id = request.GET.get('departement', '').strip()

    if search:
        users = users.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(username__icontains=search)
            | Q(profil__poste__icontains=search)
            | Q(profil__matricule__icontains=search)
            | Q(profil__telephone__icontains=search)
        )

    if role:
        users = users.filter(profil__role=role)

    if departement_id:
        users = users.filter(profil__departement_id=departement_id)

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    scope = get_user_scope(request.user)
    departements = scope['departements'] if scope else Departement.objects.none()
    available_roles = scope['roles'] if scope else []

    if request.user.is_superuser:
        titre_page = "Gestion globale des utilisateurs"
    elif is_admin_organisation(request.user):
        titre_page = "Utilisateurs de mon organisation"
    else:
        titre_page = "Agents de mon département"

    return render(request, 'accounts/users.html', {
        'users': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'titre_page': titre_page,
        'departements': departements,
        'available_roles': available_roles,
        'search': search,
        'selected_role': role,
        'selected_departement': departement_id,
        'active_page': 'users',
    })


@login_required
def user_detail(request, user_id):
    if not can_manage_users(request.user):
        messages.error(request, "Accès refusé.")
        return redirect('dashboard')

    user_item = get_manageable_user_or_404(request.user, user_id)
    return render(request, 'accounts/user_detail.html', {
        'user_item': user_item,
        'active_page': 'users',
    })


@login_required
def edit_user(request, user_id):
    if not can_manage_users(request.user):
        messages.error(request, "Accès refusé.")
        return redirect('dashboard')

    user_item = get_manageable_user_or_404(request.user, user_id)
    profil = user_item.profil
    scope = get_user_scope(request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        role = request.POST.get('role', profil.role)
        organisation_id = request.POST.get('organisation')
        departement_id = request.POST.get('departement')
        is_active = request.POST.get('is_active') == 'on'

        if role not in scope['roles']:
            messages.error(request, "Rôle invalide pour votre niveau d'accès.")
            return redirect('edit_user', user_id=user_item.id)

        if not first_name or not last_name or not email:
            messages.error(request, "Le nom, le prénom et l'email sont obligatoires.")
            return redirect('edit_user', user_id=user_item.id)

        email_exists = User.objects.filter(Q(username=email) | Q(email=email)).exclude(id=user_item.id).exists()
        if email_exists:
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect('edit_user', user_id=user_item.id)

        organisation = scope['forced_organisation']
        if organisation is None:
            if not organisation_id:
                messages.error(request, "Veuillez sélectionner une organisation.")
                return redirect('edit_user', user_id=user_item.id)
            organisation = get_object_or_404(Organisation, id=organisation_id)

        departement = scope['forced_departement']
        if role in [ROLE_RESPONSABLE_DEPT, ROLE_AGENT]:
            if departement is None:
                if not departement_id:
                    messages.error(request, "Veuillez sélectionner un département.")
                    return redirect('edit_user', user_id=user_item.id)
                departement = get_object_or_404(Departement, id=departement_id, organisation=organisation)
        else:
            departement = None

        user_item.first_name = first_name
        user_item.last_name = last_name
        user_item.email = email
        user_item.username = email
        user_item.is_active = is_active
        user_item.save()

        old_responsable_departments = Departement.objects.filter(responsable=user_item)
        if role != ROLE_RESPONSABLE_DEPT:
            old_responsable_departments.update(responsable=None)

        profil.role = role
        profil.organisation = organisation
        profil.departement = departement
        profil.poste = request.POST.get('poste', '').strip()
        profil.matricule = request.POST.get('matricule', '').strip()
        profil.telephone = request.POST.get('telephone', '').strip()
        profil.adresse = request.POST.get('adresse', '').strip()
        profil.date_naissance = parse_date(request.POST.get('date_naissance', '').strip()) if request.POST.get('date_naissance') else None
        profil.save()

        if role == ROLE_RESPONSABLE_DEPT and departement:
            departement.responsable = user_item
            departement.save(update_fields=['responsable'])

        messages.success(request, "Utilisateur modifié avec succès.")
        return redirect('user_detail', user_id=user_item.id)

    return render(request, 'accounts/edit_user.html', {
        'user_item': user_item,
        'roles': scope['roles'],
        'organisations': scope['organisations'],
        'departements': scope['departements'],
        'forced_organisation': scope['forced_organisation'],
        'forced_departement': scope['forced_departement'],
        'active_page': 'users',
    })


@login_required
def toggle_user_status(request, user_id):
    if not can_manage_users(request.user):
        messages.error(request, "Accès refusé.")
        return redirect('dashboard')

    user_item = get_manageable_user_or_404(request.user, user_id)
    user_item.is_active = not user_item.is_active
    user_item.save(update_fields=['is_active'])
    messages.success(request, "Statut utilisateur mis à jour.")
    return redirect('user_management')


@login_required
def change_user_role(request, user_id):
    messages.warning(request, "Le changement de rôle se fait depuis la page de modification utilisateur.")
    return redirect('edit_user', user_id=user_id)


@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {
        'active_page': 'profile',
    })


@login_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        if hasattr(user, 'profil'):
            user.profil.doit_changer_mot_de_passe = False
            user.profil.save(update_fields=['doit_changer_mot_de_passe'])
        update_session_auth_hash(request, user)
        messages.success(request, "Mot de passe modifié avec succès.")
        return redirect('dashboard')

    return render(request, 'accounts/change_password.html', {
        'form': form,
        'must_change': hasattr(request.user, 'profil') and request.user.profil.doit_changer_mot_de_passe,
        'active_page': 'profile',
    })


@login_required
def departments(request):
    is_super = request.user.is_superuser
    is_org_admin = is_admin_organisation(request.user)
    is_dept_responsable = is_responsable(request.user)

    if not is_super and not is_org_admin and not is_dept_responsable:
        messages.error(request, "Accès réservé aux administrateurs et responsables.")
        return redirect('dashboard')

    user_profile = getattr(request.user, 'profil', None)
    can_create_department = is_super or is_org_admin

    if is_super:
        organisations = Organisation.objects.all().order_by('nom')
        responsables = User.objects.filter(
            profil__role__in=RESPONSABLE_ROLES
        ).select_related('profil', 'profil__organisation').order_by('first_name', 'last_name', 'username')
        departements = Departement.objects.select_related(
            'organisation', 'responsable'
        ).all().order_by('-date_creation')
    elif is_org_admin:
        organisations = Organisation.objects.filter(id=user_profile.organisation_id)
        responsables = User.objects.filter(
            profil__organisation=user_profile.organisation,
            profil__role__in=RESPONSABLE_ROLES
        ).select_related('profil', 'profil__organisation').order_by('first_name', 'last_name', 'username')
        departements = Departement.objects.select_related(
            'organisation', 'responsable'
        ).filter(organisation=user_profile.organisation).order_by('-date_creation')
    else:
        organisations = Organisation.objects.none()
        responsables = User.objects.none()
        departements = Departement.objects.select_related(
            'organisation', 'responsable'
        ).filter(responsable=request.user).order_by('-date_creation')

    if request.method == 'POST':
        if not can_create_department:
            messages.error(request, "Vous n'êtes pas autorisé à créer un département.")
            return redirect('departments')

        nom = request.POST.get('nom', '').strip()
        description = request.POST.get('description', '').strip()
        organisation_id = request.POST.get('organisation')
        responsable_id = request.POST.get('responsable')

        if not nom:
            messages.error(request, "Le nom du département est obligatoire.")
            return redirect('departments')

        if is_super:
            if not organisation_id:
                messages.error(request, "Veuillez sélectionner une organisation.")
                return redirect('departments')
            organisation = get_object_or_404(Organisation, id=organisation_id)
        else:
            organisation = user_profile.organisation
            if organisation is None:
                messages.error(request, "Votre compte n'est rattaché à aucune organisation.")
                return redirect('departments')

        if Departement.objects.filter(organisation=organisation, nom__iexact=nom).exists():
            messages.error(request, "Ce département existe déjà dans cette organisation.")
            return redirect('departments')

        responsable = None
        if responsable_id:
            responsable = get_object_or_404(
                responsables,
                id=responsable_id,
                profil__organisation=organisation,
            )

        Departement.objects.create(
            organisation=organisation,
            nom=nom,
            description=description,
            responsable=responsable,
        )

        messages.success(request, "Département créé avec succès.")
        return redirect('departments')

    return render(request, 'accounts/departments.html', {
        'departements': departements,
        'organisations': organisations,
        'responsables': responsables,
        'can_create_department': can_create_department,
        'is_superadmin': is_super,
        'active_page': 'departements',
    })


@login_required
def organisations(request):
    if not is_superadmin(request.user):
        messages.error(request, "Accès réservé au superadmin.")
        return redirect('dashboard')

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        description = request.POST.get('description', '').strip()
        adresse = request.POST.get('adresse', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        email = request.POST.get('email', '').strip()

        if not nom:
            messages.error(request, "Le nom de l'organisation est obligatoire.")
            return redirect('organisations')

        if Organisation.objects.filter(nom__iexact=nom).exists():
            messages.error(request, "Cette organisation existe déjà.")
            return redirect('organisations')

        Organisation.objects.create(
            nom=nom,
            description=description,
            adresse=adresse,
            telephone=telephone,
            email=email,
        )

        messages.success(request, "Organisation créée avec succès.")
        return redirect('organisations')

    organisations_list = Organisation.objects.all().order_by('nom')

    return render(request, 'accounts/organisations.html', {
        'organisations': organisations_list,
        'active_page': 'organisations',
    })