from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Demanda, Pendencia, Situacao


def dashboard_view(request):
    SENHA_MESTRE = "hub123"

    # Lógica de Logout
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

    # Ação de assumir demanda (Take)
    if request.GET.get("action") == "take" and request.GET.get("id"):
        demanda = get_object_or_404(Demanda, id=request.GET.get("id"))
        demanda.responsavel = request.user
        demanda.save()
        return redirect("dashboard")

    # 1. Definir o hoje
    hoje = timezone.now().date()

    # 2. Buscar todas as demandas UMA VEZ SÓ
    # Usamos prefetch_related/select_related para performance
    todas_demandas = (
        Demanda.objects.all()
        .select_related("situacao", "responsavel")
        .order_by("-criado_em")
    )

    # 3. Processar status de prazo no Python (para usar na tabela e no Kanban)
    for d in todas_demandas:
        if not d.data_prazo:
            d.status_prazo = "Sem Prazo"
            d.cor_prazo = "secondary"
        elif d.data_prazo < hoje:
            d.status_prazo = "Atrasado"
            d.cor_prazo = "danger"
        else:
            d.status_prazo = "No Prazo"
            d.cor_prazo = "success"

    # 4. Dados para o Kanban (Filtrando da lista que já temos em memória para não ir ao banco várias vezes)
    # Ordenar colunas do Kanban em ordem desejada (backlog -> priorizada -> execução -> farol -> finalizado)
    desired_order = ["Backlog", "Priorizada", "Em execução", "No Farol", "Finalizado"]
    all_situacoes = list(Situacao.objects.all())
    situacoes = []
    # Adiciona na ordem desejada, se existir
    for name in desired_order:
        for s in all_situacoes:
            if s.nome and s.nome.lower() == name.lower():
                situacoes.append(s)
                break
    # Complementa com as demais situações não listadas explicitamente
    for s in all_situacoes:
        if s not in situacoes:
            situacoes.append(s)

    kanban_data = {}
    for sit in situacoes:
        kanban_data[sit] = [d for d in todas_demandas if d.situacao_id == sit.id]

    # 5. Dados para gráficos
    sit_data = Demanda.objects.values("situacao__nome", "situacao__cor_hex").annotate(
        total=Count("id")
    )
    nivel_data = Demanda.objects.values("nivel").annotate(total=Count("id"))

    context = {
        "kanban_data": kanban_data,
        "demandas": todas_demandas,  # Agora contém os objetos processados com status_prazo
        "hoje": hoje,  # ESSENCIAL para o template comparar datas
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

    # Se a situação alvo indicar pendência, pedir descrição antes de aplicar
    nome = (target.nome or "").lower()
    if request.method == "GET" and "pend" in nome:
        # renderiza um formulário simples solicitando a descrição
        return render(
            request,
            "core/pendencia_form.html",
            {"demanda": d, "target": target, "action_url": request.path},
        )

    # POST: aplicar a alteração e, se houver descrição, criar Pendencia
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
