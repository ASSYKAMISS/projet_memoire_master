import hashlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Departement
from signatures.models import Signature
from .models import AccesDocument, Document, HistoriqueOperation


RESPONSABLE_ROLES = ['RESPONSABLE', 'RESPONSABLE_DEPARTEMENT']


def home(request):
    return render(request, 'pages/home.html')


def is_responsable(user):
    return hasattr(user, 'profil') and user.profil.role in RESPONSABLE_ROLES


def is_admin_organisation(user):
    return hasattr(user, 'profil') and user.profil.role == 'ADMIN_ORGANISATION'


def user_departement(user):
    if hasattr(user, 'profil'):
        return user.profil.departement
    return None


def prochaine_signature(document):
    return document.signatures.filter(
        statut='EN_ATTENTE'
    ).order_by('ordre').first()


def documents_for_user(user):
    if user.is_superuser:
        return Document.objects.all()

    if is_admin_organisation(user):
        return Document.objects.filter(
            utilisateur__profil__organisation=user.profil.organisation
        )

    if is_responsable(user):
        return Document.objects.filter(
            Q(utilisateur=user) | Q(signatures__utilisateur=user)
        ).distinct()

    return Document.objects.filter(
        signatures__utilisateur=user
    ).distinct()


def can_manage_document(user, document):
    if user.is_superuser:
        return True

    if document.utilisateur == user:
        return True

    if is_admin_organisation(user):
        owner_profile = getattr(document.utilisateur, 'profil', None)
        return owner_profile and owner_profile.organisation_id == user.profil.organisation_id

    return False

def can_view_document(user, document):
    if can_manage_document(user, document):
        return True

    if Signature.objects.filter(document=document, utilisateur=user).exists():
        return True

    if is_responsable(user):
        departement = user.profil.departement
        return Signature.objects.filter(
            document=document,
            utilisateur__profil__departement=departement,
            utilisateur__profil__role='AGENT'
        ).exists()

    return False

def calculer_sha256(fichier):
    sha256 = hashlib.sha256()

    fichier.open('rb')
    for chunk in fichier.chunks():
        sha256.update(chunk)
    fichier.close()

    return sha256.hexdigest()


@login_required
def dashboard(request):
    documents = documents_for_user(request.user).order_by('-date_upload')

    context = {
        'documents': documents,
        'total_documents': documents.count(),
        'total_signes': documents.filter(statut='SIGNE').count(),
        'total_invalides': documents.filter(statut='INVALIDE').count(),
        'active_page': 'dashboard',
    }

    return render(request, 'pages/dashboard.html', context)


@login_required
def document_list(request):
    documents = documents_for_user(request.user).order_by('-date_upload')

    return render(request, 'documents/list.html', {
        'documents': documents,
        'page_heading': 'Mes documents',
        'page_description': 'Consultez les documents auxquels vous avez accès.',
        'empty_title': 'Aucun document enregistré',
        'empty_description': 'Aucun document disponible pour le moment.',
        'active_page': 'documents',
    })


@login_required
def documents_envoyes(request):
    if request.user.is_superuser:
        documents = Document.objects.all()
    elif is_admin_organisation(request.user):
        documents = Document.objects.filter(
            utilisateur__profil__organisation=request.user.profil.organisation
        )
    else:
        documents = Document.objects.filter(utilisateur=request.user)

    return render(request, 'documents/list.html', {
        'documents': documents.order_by('-date_upload'),
        'page_heading': 'Documents envoyés',
        'page_description': 'Liste des documents téléversés par votre compte.',
        'empty_title': 'Aucun document envoyé',
        'empty_description': 'Vous n’avez encore envoyé aucun document.',
        'active_page': 'documents_sent',
    })


@login_required
def documents_signes(request):
    user = request.user

    if user.is_superuser:
        documents = Document.objects.filter(statut='SIGNE')
    elif is_admin_organisation(user):
        documents = Document.objects.filter(
            statut='SIGNE',
            utilisateur__profil__organisation=user.profil.organisation
        )
    elif is_responsable(user):
        departement = user.profil.departement
        documents = Document.objects.filter(
            statut='SIGNE'
        ).filter(
            Q(utilisateur=user)
            | Q(signatures__utilisateur=user, signatures__statut='SIGNE')
            | Q(signatures__utilisateur__profil__departement=departement, signatures__utilisateur__profil__role='AGENT', signatures__statut='SIGNE')
        ).distinct()
    else:
        documents = Document.objects.filter(
            statut='SIGNE'
        ).filter(
            Q(utilisateur=user)
            | Q(signatures__utilisateur=user, signatures__statut='SIGNE')
        ).distinct()

    return render(request, 'documents/list.html', {
        'documents': documents.order_by('-date_upload'),
        'page_heading': 'Documents signés',
        'page_description': 'Liste des documents signés que vous êtes autorisé à consulter.',
        'empty_title': 'Aucun document signé',
        'empty_description': 'Aucun document signé disponible pour le moment.',
        'active_page': 'signed_documents',
    })


@login_required
def upload_document(request):
    if not request.user.is_superuser and not hasattr(request.user, 'profil'):
        messages.error(request, "Votre compte n'est pas autorisé à téléverser un document.")
        return redirect('dashboard')

    if request.method == 'POST':
        titre = request.POST.get('titre')
        fichier = request.FILES.get('fichier_original')

        if not titre or not fichier:
            messages.error(request, "Veuillez renseigner le titre et selectionner un fichier PDF.")
            return redirect('upload_document')

        document = Document.objects.create(
            utilisateur=request.user,
            titre=titre,
            fichier_original=fichier,
        )

        document.hash_original = calculer_sha256(document.fichier_original)
        document.statut = 'BROUILLON'
        document.save()

        messages.success(request, "Document téléverser avec succès. Veuillez définir le circuit de signature.")
        return redirect('document_access', document_id=document.id)

    return render(request, 'documents/upload.html', {
        'active_page': 'upload',
    })


@login_required
def document_access(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    if not can_manage_document(request.user, document):
        messages.error(request, "Accès réservé au propriétaire du document ou à un gestionnaire autorisé.")
        return redirect('dashboard')

    agents = User.objects.filter(
        is_superuser=False,
        is_active=True,
    ).select_related('profil', 'profil__departement', 'profil__organisation')

    if request.user.is_superuser:
        agents = agents.filter(profil__role__in=['AGENT', 'RESPONSABLE_DEPARTEMENT', 'RESPONSABLE'])
    elif is_admin_organisation(request.user):
        agents = agents.filter(
            profil__organisation=request.user.profil.organisation,
            profil__role__in=['AGENT', 'RESPONSABLE_DEPARTEMENT', 'RESPONSABLE']
        ).exclude(id=request.user.id)
    elif is_responsable(request.user):
        agents = agents.filter(
            profil__departement=request.user.profil.departement,
            profil__role='AGENT'
        ).exclude(id=request.user.id)
    else:
        departement = request.user.profil.departement
        responsable = departement.responsable if departement else None
        agents = agents.filter(
            Q(profil__departement=departement, profil__role='AGENT')
            | Q(id=responsable.id if responsable else None)
        ).exclude(id=request.user.id)

    agents = agents.order_by('first_name', 'last_name', 'email')

    if request.method == 'POST':
        agent_ids = request.POST.getlist('agents')

        if not agent_ids:
            messages.error(request, "Veuillez choisir au moins un agent signataire.")
            return redirect('document_access', document_id=document.id)

        selected_signataires = []
        selected_ids = set()
        used_orders = set()

        for agent_id in agent_ids:
            if agent_id in selected_ids:
                continue

            agent = get_object_or_404(agents, id=agent_id)
            ordre_value = request.POST.get(f'ordre_{agent_id}', '').strip()

            if not ordre_value:
                messages.error(request, "Veuillez renseigner un ordre pour chaque agent sÃƒÂ©lectionnÃƒÂ©.")
                return redirect('document_access', document_id=document.id)

            try:
                ordre = int(ordre_value)
            except ValueError:
                messages.error(request, "L'ordre de signature doit etre un nombre entier.")
                return redirect('document_access', document_id=document.id)

            if ordre < 1:
                messages.error(request, "L'ordre de signature doit commencer par  1.")
                return redirect('document_access', document_id=document.id)

            if ordre in used_orders:
                messages.error(request, "Chaque signataire doit avoir un ordre différent.")
                return redirect('document_access', document_id=document.id)

            selected_signataires.append((ordre, agent))
            selected_ids.add(agent_id)
            used_orders.add(ordre)

        expected_orders = set(range(1, len(selected_signataires) + 1))
        if used_orders != expected_orders:
            messages.error(request, "L'ordre doit etre continu : 1, 2, 3, sans saut ni doublon.")
            return redirect('document_access', document_id=document.id)

        selected_signataires.sort(key=lambda item: item[0])

        AccesDocument.objects.filter(document=document).delete()
        Signature.objects.filter(document=document).delete()

        for index, (_, agent) in enumerate(selected_signataires, start=1):
            AccesDocument.objects.create(
                document=document,
                agent=agent,
                peut_signer=True
            )

            Signature.objects.create(
                document=document,
                utilisateur=agent,
                statut='EN_ATTENTE',
                ordre=index,
            )

        document.statut = 'EN_ATTENTE_SIGNATURE'
        document.save(update_fields=['statut'])

        messages.success(
            request,
            f"Circuit de signature créé avec succès. {len(selected_signataires)} signature(s) attendue(s) dans l'ordre defini."
        )
        return redirect('document_detail', document_id=document.id)

    search = request.GET.get('q', '').strip()
    if search:
        agents = agents.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(profil__poste__icontains=search)
            | Q(profil__matricule__icontains=search)
            | Q(profil__departement__nom__icontains=search)
        )

    paginator = Paginator(agents, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'documents/access.html', {
        'document': document,
        'agents': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'active_page': 'upload',
    })


@login_required
def documents_to_sign(request):
    signatures = Signature.objects.filter(
        utilisateur=request.user,
        statut='EN_ATTENTE',
        document__statut='EN_ATTENTE_SIGNATURE'
    ).select_related('document').order_by('document__date_upload')

    documents_ids = []

    for signature in signatures:
        next_signature = prochaine_signature(signature.document)
        if next_signature and next_signature.id == signature.id:
            documents_ids.append(signature.document_id)

    documents = Document.objects.filter(
        id__in=documents_ids
    ).order_by('-date_upload')

    return render(request, 'documents/to_sign.html', {
        'documents': documents,
        'active_page': 'to_sign',
    })


@login_required
def document_detail(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    if not can_view_document(request.user, document):
        messages.error(request, "Vous n'avez pas accès à ce document.")
        return redirect('dashboard')

    signatures_attendues = document.signatures.select_related('utilisateur').all().order_by('ordre')
    signatures_signees = signatures_attendues.filter(statut='SIGNE').count()
    signatures_restantes = signatures_attendues.filter(statut='EN_ATTENTE').count()
    next_signature = prochaine_signature(document)
    current_signature = signatures_attendues.filter(utilisateur=request.user).first()
    can_sign_now = next_signature and current_signature and next_signature.id == current_signature.id

    return render(request, 'documents/detail.html', {
        'document': document,
        'signatures_attendues': signatures_attendues,
        'signatures_signees': signatures_signees,
        'signatures_restantes': signatures_restantes,
        'current_signature': current_signature,
        'next_signature': next_signature,
        'can_sign_now': can_sign_now,
        'active_page': 'documents',
    })


@login_required
def verify_document(request):
    return render(request, 'documents/verify.html', {
        'active_page': 'verification',
    })


@login_required
def operation_history(request):
    if request.user.is_superuser:
        historiques = HistoriqueOperation.objects.all()
    else:
        historiques = HistoriqueOperation.objects.filter(utilisateur=request.user)

    return render(request, 'documents/history.html', {
        'historiques': historiques.order_by('-date_action'),
        'active_page': 'history',
    })
