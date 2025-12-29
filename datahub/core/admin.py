from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import Contato, Demanda, Pendencia, Situacao, Tema, TipoAtividade


class DemandaForm(forms.ModelForm):
    pendencia_descricao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Preencha quando marcar a demanda como pendência.",
    )

    class Meta:
        model = Demanda
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        situacao = cleaned.get("situacao")
        desc = cleaned.get("pendencia_descricao")
        if situacao and situacao.nome and "pend" in situacao.nome.lower():
            old = getattr(self.instance, "situacao", None)
            old_id = old.pk if old else None
            new_id = situacao.pk
            if old_id != new_id and not desc:
                raise forms.ValidationError(
                    {
                        "pendencia_descricao": "Descrição da pendência é obrigatória ao marcar como pendente."
                    }
                )
        return cleaned


# Permite editar subitens dentro do item pai
class SubitemInline(admin.TabularInline):
    model = Demanda
    extra = 0
    fields = ["nivel", "titulo", "situacao", "responsavel", "data_prazo"]
    show_change_link = True
    verbose_name = "Subitem vinculado"
    verbose_name_plural = (
        "Subitens vinculados (Iniciativas > Épicos > Histórias > Atividades)"
    )


class PendenciaInline(admin.TabularInline):
    model = Pendencia
    extra = 0
    fields = ("descricao", "criado_em", "resolvida", "dias_pendente")
    readonly_fields = ("descricao", "criado_em", "dias_pendente")
    can_delete = False
    verbose_name = "Pendência"
    verbose_name_plural = "Pendências"

    def dias_pendente(self, obj):
        if not obj.criado_em:
            return "-"
        if obj.resolvida and obj.resolvido_em:
            delta = obj.resolvido_em.date() - obj.criado_em.date()
        else:
            delta = timezone.now().date() - obj.criado_em.date()
        return f"{delta.days} dias"

    dias_pendente.short_description = "Dias pendente"


@admin.register(Demanda)
class DemandaAdmin(SimpleHistoryAdmin):
    # Adicionado 'status_prazo_tag' e 'acoes_rapidas' na listagem
    list_display = (
        "titulo",
        "nivel",
        "status_tag",
        "status_prazo_tag",
        "responsavel",
        "acoes_rapidas",
    )
    list_filter = ("nivel", "situacao", "responsavel", "tema")
    search_fields = ("titulo", "descricao")
    autocomplete_fields = ["parent", "responsavel", "solicitantes"]
    readonly_fields = ["situacao", "data_fechamento"]
    inlines = [SubitemInline, PendenciaInline]
    form = DemandaForm
    save_on_top = True

    fieldsets = (
        (
            "Principal",
            {
                "fields": ("titulo", "nivel", "parent", "tema", "tipo", "situacao"),
            },
        ),
        (
            "Pessoas",
            {
                "fields": ("responsavel", "solicitantes"),
            },
        ),
        (
            "Detalhes",
            {
                "fields": ("descricao", "observacao"),
            },
        ),
        (
            "Datas",
            {
                "fields": ("data_inicio", "data_prazo", "data_fechamento"),
            },
        ),
    )

    # --- 1. COLUNA DE STATUS DO PRAZO ---
    def status_prazo_tag(self, obj):
        if not obj.data_prazo:
            return format_html('<span style="color: #999;">{}</span>', "-")

        hoje = timezone.now().date()
        if obj.data_prazo < hoje:
            cor = "#e74c3c"  # Vermelho
            texto = "Fora do Prazo"
        else:
            cor = "#27ae60"  # Verde
            texto = "No Prazo"

        return format_html(
            '<strong style="color: {}; font-size: 10px; text-transform: uppercase;">{}</strong>',
            cor,
            texto,
        )

    status_prazo_tag.short_description = "Status Prazo"

    # --- 2. COLUNA DE SITUAÇÃO (TAG COLORIDA) ---
    def status_tag(self, obj):
        if not obj.situacao:
            return "-"
        cor = obj.situacao.cor_hex
        # se houver pendências, mostra tooltip com a última pendência e dias pendente
        last = None
        try:
            last = obj.pendencias.order_by("-criado_em").first()
        except Exception:
            last = None

        if last:
            if last.resolvida and last.resolvido_em:
                delta = last.resolvido_em.date() - last.criado_em.date()
            else:
                delta = timezone.now().date() - last.criado_em.date()
            title = f"Última pendência: {last.descricao} — {delta.days} dias"
        else:
            title = obj.situacao.nome

        return format_html(
            '<span title="{}" style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            title,
            cor,
            obj.situacao.nome,
        )

    status_tag.short_description = "Situação"

    # --- 3. AÇÕES RÁPIDAS (SUB-ITEM, STATUS E ASSUMIR) ---
    def acoes_rapidas(self, obj):
        html = []

        # Botão Sub-item
        sub_url = reverse("criar_subatividade", args=[obj.pk])
        html.append(
            format_html(
                '<a class="btn btn-xs btn-info" href="{}" title="Sub-item" style="margin-right:5px; color:white; padding: 2px 5px; font-size: 10px; text-decoration: none; background: #17a2b8; border-radius: 3px;"><i class="fas fa-plus"></i> Sub</a>',
                sub_url,
            )
        )

        # Botão DELEGAR PARA MIM (Assumir)
        # Só exibe se o responsável não for o usuário atual
        assumir_url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_assumir", args=[obj.pk]
        )
        html.append(
            format_html(
                '<a class="btn btn-xs" href="{}" title="Assumir" style="margin-right:5px; color:white; padding: 2px 5px; font-size: 10px; text-decoration: none; background: #28a745; border-radius: 3px;"><i class="fas fa-user-check"></i> Assumir</a>',
                assumir_url,
            )
        )

        # Botões de Alteração de Status
        if obj.situacao:
            proximas = obj.situacao.proximas_situacoes.all()
            for proxima in proximas:
                url = reverse("alterar_status", args=[obj.pk, proxima.id])
                html.append(
                    format_html(
                        '<a class="btn btn-xs btn-outline-secondary" href="{}" style="margin-right:2px; font-size:10px; padding: 1px 4px; border: 1px solid #ccc; text-decoration: none; color: #666; border-radius: 3px;">{}</a>',
                        url,
                        proxima.nome,
                    )
                )

        return format_html("".join(["{}" for _ in range(len(html))]), *html)

    acoes_rapidas.short_description = "Ações Rápidas"

    # --- 4. LÓGICA PARA O BOTÃO ASSUMIR ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/assumir/",
                self.admin_site.admin_view(self.assumir_demanda),
                name="core_demanda_assumir",
            ),
            path(
                "dashboard/",
                self.admin_site.admin_view(self.admin_dashboard),
                name="core_demanda_dashboard",
            ),
        ]
        return custom_urls + urls

    def assumir_demanda(self, request, pk):
        obj = self.get_object(request, pk)
        if obj:
            obj.responsavel = request.user
            obj.save()
            self.message_user(
                request, f"Você assumiu a demanda: {obj.titulo}", messages.SUCCESS
            )
        return redirect(
            reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist")
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)

        # Se foi fornecida descrição de pendência, registrar histórico
        try:
            pend_desc = form.cleaned_data.get("pendencia_descricao")
        except Exception:
            pend_desc = None

        if pend_desc:
            Pendencia.objects.create(
                demanda=obj, descricao=pend_desc, criado_por=request.user
            )
            # sinaliza para redirecionar ao changelist após salvar
            try:
                request._pendencia_created = True
            except Exception:
                pass

    def response_change(self, request, obj):
        # se criamos uma pendência durante o save, redireciona para o changelist
        if getattr(request, "_pendencia_created", False):
            return redirect(
                reverse(
                    f"admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist"
                )
            )
        return super().response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        if getattr(request, "_pendencia_created", False):
            return redirect(
                reverse(
                    f"admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist"
                )
            )
        return super().response_add(request, obj, post_url_continue=post_url_continue)

    def admin_dashboard(self, request):
        """Admin view that shows Kanban and a table of demandas similar to the front dashboard."""
        from django.db.models import Count

        hoje = timezone.now().date()

        todas_demandas = (
            Demanda.objects.all()
            .select_related("situacao", "responsavel")
            .order_by("-criado_em")
        )

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

        desired_order = [
            "Backlog",
            "Priorizada",
            "Em execução",
            "No Farol",
            "Finalizado",
        ]
        all_situacoes = list(Situacao.objects.all())
        situacoes = []
        for name in desired_order:
            for s in all_situacoes:
                if s.nome and s.nome.lower() == name.lower():
                    situacoes.append(s)
                    break
        for s in all_situacoes:
            if s not in situacoes:
                situacoes.append(s)

        kanban_data = {}
        for sit in situacoes:
            kanban_data[sit] = [d for d in todas_demandas if d.situacao_id == sit.id]

        sit_data = Demanda.objects.values(
            "situacao__nome", "situacao__cor_hex"
        ).annotate(total=Count("id"))
        nivel_data = Demanda.objects.values("nivel").annotate(total=Count("id"))

        context = {
            "kanban_data": kanban_data,
            "demandas": todas_demandas,
            "hoje": hoje,
            "labels_situacao": [
                item["situacao__nome"] or "Sem Situação" for item in sit_data
            ],
            "counts_situacao": [item["total"] for item in sit_data],
            "cores_situacao": [
                item["situacao__cor_hex"] or "#bdc3c7" for item in sit_data
            ],
            "labels_nivel": [item["nivel"] for item in nivel_data],
            "counts_nivel": [item["total"] for item in nivel_data],
            # URLs
            "add_url": reverse("admin:core_demanda_add"),
        }
        return render(request, "admin/core/demanda_dashboard.html", context)

    def save_formset(self, request, form, formset, change):
        """Ensure inline Demanda (subitens) inherit `tema` from the parent when not provided.
        Use commit=False to set the field before saving to avoid NOT NULL constraint errors.
        """
        # Get instances without saving to DB yet
        instances = formset.save(commit=False)
        for inst in instances:
            # If the inline doesn't have thema set, inherit from parent
            if not getattr(inst, "tema_id", None):
                try:
                    inst.tema = form.instance.tema
                except Exception:
                    pass
            # Herdar tipo do pai se não fornecido no inline
            if not getattr(inst, "tipo_id", None):
                try:
                    inst.tipo = form.instance.tipo
                except Exception:
                    pass
            # Ensure parent is set when saving from inline (usually set by admin)
            if not getattr(inst, "parent_id", None):
                inst.parent = form.instance
            inst.save()

        # Handle m2m and deletions as usual
        formset.save_m2m()
        for obj in formset.deleted_objects:
            obj.delete()


@admin.register(Tema, TipoAtividade)
class AuxiliarAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    search_fields = ["nome", "email"]
    list_display = ("nome", "email")


class SituacaoForm(forms.ModelForm):
    class Meta:
        model = Situacao
        fields = "__all__"
        widgets = {
            "cor_hex": forms.TextInput(
                attrs={"type": "color", "style": "width: 100px; height: 40px;"}
            ),
        }


@admin.register(Situacao)
class SituacaoAdmin(admin.ModelAdmin):
    form = SituacaoForm
    list_display = ("nome", "cor_exemplo", "padrao", "pendente")
    search_fields = ["nome"]

    def cor_exemplo(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border-radius: 4px;"></div>',
            obj.cor_hex,
        )

    cor_exemplo.short_description = "Cor"
