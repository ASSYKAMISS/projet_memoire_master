import hashlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Departement
from signatures.models import Signature
from .models import AccesDocument, Document, HistoriqueOperation


def home(request):
    return render(request, 'pages/home.html')


def is_responsable(user):
    return hasattr(user, 'profil') and user.profil.role == 'RESPONSABLE'


def user_departement(user):
    if hasattr(user, 'profil'):
        return user.profil.departement
    return None


def documents_for_user(user):
    if user.is_superuser:
        return Document.objects.all()

    if is_responsable(user):
        return Document.objects.filter(utilisateur=user)

    return Document.objects.filter(
        signatures__utilisateur=user
    ).distinct()


def can_manage_document(user, document):
    return user.is_superuser or (is_responsable(user) and document.utilisateur == user)


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
        'active_page': 'documents',
    })


@login_required
def upload_document(request):
    if not request.user.is_superuser and not is_responsable(request.user):
        messages.error(request, "Seul le superadmin ou le responsable peut téléverser un document.")
        return redirect('dashboard')

    if request.method == 'POST':
        titre = request.POST.get('titre')
        fichier = request.FILES.get('fichier_original')

        if not titre or not fichier:
            messages.error(request, "Veuillez renseigner le titre et sélectionner un fichier PDF.")
            return redirect('upload_document')

        document = Document.objects.create(
            utilisateur=request.user,
            titre=titre,
            fichier_original=fichier,
        )

        document.hash_original = calculer_sha256(document.fichier_original)
        document.statut = 'BROUILLON'
        document.save()

        messages.success(request, "Document téléversé avec succès. Veuillez attribuer les accès.")
        return redirect('document_access', document_id=document.id)

    return render(request, 'documents/upload.html', {
        'active_page': 'upload',
    })


@login_required
def document_access(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    if not can_manage_document(request.user, document):
        messages.error(request, "Accès réservé au propriétaire du document ou au superadmin.")
        return redirect('dashboard')

    if request.user.is_superuser:
        departements = Departement.objects.all().order_by('nom')
        agents = User.objects.filter(
            is_superuser=False,
            is_active=True,
            profil__role='AGENT'
        ).order_by('first_name', 'last_name')
    else:
        departements = Departement.objects.filter(
            responsable=request.user
        ).order_by('nom')
        agents = User.objects.filter(
            is_active=True,
            profil__cree_par=request.user,
            profil__role='AGENT'
        ).order_by('first_name', 'last_name')

    if request.method == 'POST':
        departement_ids = request.POST.getlist('departements')
        agent_ids = request.POST.getlist('agents')

        if not departement_ids and not agent_ids:
            messages.error(request, "Veuillez choisir au moins un département ou un agent.")
            return redirect('document_access', document_id=document.id)

        AccesDocument.objects.filter(document=document).delete()
        Signature.objects.filter(document=document).delete()

        signataires = set()

        for dep_id in departement_ids:
            departement = get_object_or_404(departements, id=dep_id)
            AccesDocument.objects.get_or_create(
                document=document,
                departement=departement,
                peut_signer=True
            )

            agents_departement = agents.filter(profil__departement=departement)
            for agent in agents_departement:
                signataires.add(agent)

        for agent_id in agent_ids:
            agent = get_object_or_404(agents, id=agent_id)
            AccesDocument.objects.get_or_create(
                document=document,
                agent=agent,
                peut_signer=True
            )
            signataires.add(agent)

        if not signataires:
            messages.error(request, "Aucun agent signataire trouvé pour cette attribution.")
            return redirect('document_access', document_id=document.id)

        for agent in signataires:
            Signature.objects.get_or_create(
                document=document,
                utilisateur=agent,
                defaults={'statut': 'EN_ATTENTE'}
            )

        document.statut = 'EN_ATTENTE_SIGNATURE'
        document.save()

        messages.success(request, f"Accès attribués avec succès. {len(signataires)} signature(s) attendue(s).")
        return redirect('document_detail', document_id=document.id)

    return render(request, 'documents/access.html', {
        'document': document,
        'departements': departements,
        'agents': agents,
        'active_page': 'upload',
    })


@login_required
def documents_to_sign(request):
    documents = Document.objects.filter(
        statut='EN_ATTENTE_SIGNATURE',
        signatures__utilisateur=request.user,
        signatures__statut='EN_ATTENTE'
    ).distinct().order_by('-date_upload')

    return render(request, 'documents/to_sign.html', {
        'documents': documents,
        'active_page': 'to_sign',
    })


@login_required
def document_detail(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    if not can_manage_document(request.user, document):
        autorise = Signature.objects.filter(
            document=document,
            utilisateur=request.user
        ).exists()

        if not autorise:
            messages.error(request, "Vous n'avez pas accès à ce document.")
            return redirect('dashboard')

    signatures_attendues = document.signatures.all().order_by('utilisateur__first_name', 'utilisateur__last_name')
    signatures_signees = signatures_attendues.filter(statut='SIGNE').count()
    signatures_restantes = signatures_attendues.filter(statut='EN_ATTENTE').count()
    current_signature = signatures_attendues.filter(utilisateur=request.user).first()

    return render(request, 'documents/detail.html', {
        'document': document,
        'signatures_attendues': signatures_attendues,
        'signatures_signees': signatures_signees,
        'signatures_restantes': signatures_restantes,
        'current_signature': current_signature,
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

