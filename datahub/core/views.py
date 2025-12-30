from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import UploadForm
from .models import AnexoDemanda, Demanda, Pendencia, Situacao


def upload_arquivos(request, demanda_id=None):
    demanda = None
    if demanda_id:
        demanda = get_object_or_404(Demanda, id=demanda_id)

    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            arquivos = request.FILES.getlist("arquivos")
            for f in arquivos:
                if demanda:
                    AnexoDemanda.objects.create(demanda=demanda, arquivo=f)
            return render(request, "sucesso.html")
    else:
        form = UploadForm()
    return render(request, "upload.html", {"form": form, "demanda": demanda})


def dashboard_view(request):
    SENHA_MESTRE = "hub123"
    if "logout" in request.GET:
        request.session["auth_dashboard"] = False
        return redirect("dashboard")
    if request.method == "POST":
        if request.POST.get("password") == SENHA_MESTRE:
            request.session["auth_dashboard"] = True
        else:
            return render(
                request, "core/login_dashboard.html", {"error": "Senha incorreta!"}
            )

    if not request.session.get("auth_dashboard"):
        return render(request, "core/login_dashboard.html")

    hoje = timezone.now().date()
    todas_demandas = (
        Demanda.objects.all()
        .select_related("situacao", "responsavel")
        .order_by("-criado_em")
    )

    for d in todas_demandas:
        if not d.data_prazo:
            d.status_prazo, d.cor_prazo = "Sem Prazo", "secondary"
        elif d.data_prazo < hoje:
            d.status_prazo, d.cor_prazo = "Atrasado", "danger"
        else:
            d.status_prazo, d.cor_prazo = "No Prazo", "success"

    desired_order = ["Backlog", "Priorizada", "Em execução", "No Farol", "Finalizado"]
    all_situacoes = list(Situacao.objects.all())
    situacoes = [
        s
        for name in desired_order
        for s in all_situacoes
        if s.nome.lower() == name.lower()
    ]
    situacoes += [s for s in all_situacoes if s not in situacoes]

    kanban_data = {
        sit: [d for d in todas_demandas if d.situacao_id == sit.id] for sit in situacoes
    }
    sit_data = Demanda.objects.values("situacao__nome", "situacao__cor_hex").annotate(
        total=Count("id")
    )
    nivel_data = Demanda.objects.values("nivel").annotate(total=Count("id"))

    context = {
        "kanban_data": kanban_data,
        "demandas": todas_demandas,
        "hoje": hoje,
        "labels_situacao": [
            item["situacao__nome"] or "Sem Situação" for item in sit_data
        ],
        "counts_situacao": [item["total"] for item in sit_data],
        "cores_situacao": [item["situacao__cor_hex"] or "#bdc3c7" for item in sit_data],
        "labels_nivel": [item["nivel"] for item in nivel_data],
        "counts_nivel": [item["total"] for item in nivel_data],
    }
    return render(request, "core/dashboard.html", context)


def alterar_status_view(request, pk, situacao_id):
    d = get_object_or_404(Demanda, pk=pk)
    target = get_object_or_404(Situacao, pk=situacao_id)
    nome = (target.nome or "").lower()

    if request.method == "GET" and "pend" in nome:
        return render(
            request,
            "core/pendencia_form.html",
            {"demanda": d, "target": target, "action_url": request.path},
        )

    if request.method == "POST":
        desc = request.POST.get("pendencia_descricao", "").strip()
        d.situacao = target
        d.save()
        if desc:
            Pendencia.objects.create(demanda=d, descricao=desc, criado_por=request.user)
    return redirect(request.META.get("HTTP_REFERER", "dashboard"))


def criar_subatividade_view(request, pk):
    pai = get_object_or_404(Demanda, pk=pk)
    url = reverse("admin:core_demanda_add")
    params = f"?parent={pai.id}&tema={pai.tema.id if pai.tema else ''}"
    return redirect(url + params)
