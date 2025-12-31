import os

from django import forms
from django.contrib import admin, messages
from django.forms.widgets import FileInput
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    AnexoDemanda,
    Contato,
    Demanda,
    Pendencia,
    Situacao,
    Tema,
    TipoAtividade,
)


class MultipleFileInput(FileInput):
    """
    Widget que contorna a trava do Django para permitir múltiplos arquivos.
    """

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs["multiple"] = "multiple"
        return super().render(name, value, attrs, renderer)


class AnexoForm(forms.ModelForm):
    arquivo = forms.FileField(
        widget=MultipleFileInput(), required=False, label="Adicionar arquivo(s)"
    )

    class Meta:
        model = AnexoDemanda
        fields = ["arquivo"]


class AnexoDemandaInline(admin.TabularInline):
    model = AnexoDemanda
    form = AnexoForm
    extra = 1
    fields = ["arquivo", "link_download"]
    readonly_fields = ["link_download"]

    def link_download(self, obj):
        if obj.id and obj.arquivo:
            import os

            nome = os.path.basename(obj.arquivo.name)
            nome_exibicao = (nome[:17] + "..") if len(nome) > 20 else nome
            return format_html(
                '<a href="{}" target="_blank" title="{}" style="'
                "background-color: #17a2b8; color: white; padding: 4px 10px; "
                "border-radius: 4px; text-decoration: none; font-size: 10px; "
                'font-weight: bold; display: inline-block; min-width: 80px; text-align: center;">'
                "📄 {}</a>",
                obj.arquivo.url,
                nome,
                nome_exibicao,
            )
        return "-"


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


class SubitemInline(admin.TabularInline):
    model = Demanda
    extra = 0
    fields = ["tema", "titulo", "situacao", "responsavel", "data_prazo"]
    show_change_link = True


class PendenciaInline(admin.TabularInline):
    model = Pendencia
    extra = 0
    # Campos conforme seu original: histórico somente leitura
    fields = ("descricao", "criado_em", "resolvida", "dias_pendente")
    readonly_fields = ("descricao", "criado_em", "dias_pendente")
    can_delete = False

    def dias_pendente(self, obj):
        if not obj.criado_em:
            return "-"
        fim = (
            obj.resolvido_em.date()
            if (obj.resolvida and obj.resolvido_em)
            else timezone.now().date()
        )
        delta = fim - obj.criado_em.date()
        return f"{delta.days} dias"


@admin.register(AnexoDemanda)
class AnexoDemandaAdmin(admin.ModelAdmin):
    list_display = ("id", "demanda_link", "nome_arquivo", "data_upload", "baixar")

    def baixar(self, obj):
        return format_html(
            '<a class="button" href="{}" target="_blank" style="'
            "background-color: #28a745; color: white; padding: 5px 15px; "
            "border-radius: 20px; text-decoration: none; font-weight: bold; "
            'box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: none;">'
            "📥 DOWNLOAD</a>",
            obj.arquivo.url,
        )

    def demanda_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:core_demanda_change", args=[obj.demanda.id]),
            obj.demanda.titulo,
        )

    def nome_arquivo(self, obj):
        return os.path.basename(obj.arquivo.name)


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    search_fields = ["nome", "email"]
    list_display = ("nome", "email")


@admin.register(Demanda)
class DemandaAdmin(SimpleHistoryAdmin):
    form = DemandaForm
    inlines = [SubitemInline, PendenciaInline, AnexoDemandaInline]
    list_display = (
        "titulo",
        "tema",
        "status_tag",
        "status_prazo_tag",
        "responsavel",
        "acoes_rapidas",
    )
    list_filter = ("tema", "situacao", "responsavel", "tema")
    search_fields = ("titulo", "descricao")
    autocomplete_fields = ["parent", "responsavel", "solicitantes"]
    readonly_fields = ["data_fechamento"]
    save_on_top = True

    fieldsets = (
        (
            "Principal",
            {"fields": ("titulo", "parent", "tema", "tipo", "situacao")},
        ),
        ("Pessoas", {"fields": ("responsavel", "solicitantes")}),
        ("Detalhes", {"fields": ("descricao", "observacao")}),
        ("Datas", {"fields": ("data_inicio", "data_prazo", "data_fechamento")}),
    )

    def status_tag(self, obj):
        if not obj.situacao:
            return "-"
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            obj.situacao.cor_hex,
            obj.situacao.nome,
        )

    status_tag.admin_order_field = "situacao__nome"
    status_tag.short_description = "Bucket"

    def status_prazo_tag(self, obj):
        if not obj.data_prazo:
            return "-"
        atrasado = (
            obj.data_prazo < timezone.now().date()
            if obj.data_fechamento is None
            else obj.data_prazo < obj.data_fechamento.date()
        )
        cor = (
            "#e74c3c"
            if atrasado
            else "#27ae60" if obj.data_fechamento is None else "#2980b9"
        )
        txt = (
            "Fora do Prazo"
            if atrasado and obj.data_fechamento is None
            else (
                "No Prazo"
                if obj.data_fechamento is None
                else (
                    "Finalizado no Prazo"
                    if not atrasado
                    else "Finalizado Fora do Prazo"
                )
            )
        )
        return format_html('<strong style="color: {};">{}</strong>', cor, txt)

    status_prazo_tag.admin_order_field = "data_prazo"
    status_prazo_tag.short_description = "Status do Prazo"

    def changelist_view(self, request, extra_context=None):
        # Guardamos o request atual para usar no método acoes_rapidas
        self._current_request = request
        return super().changelist_view(request, extra_context)

    def acoes_rapidas(self, obj):
        # Recuperamos o ID do usuário diretamente do request que salvamos
        usuario_logado = self._current_request.user if self._current_request else None
        id_do_usuario = usuario_logado.id if usuario_logado else None

        html = []

        # Botão + Sub
        html.append(
            format_html(
                '<a class="btn" href="{}" style="background:#17a2b8; color:white; padding:2px 5px; font-size:10px; margin-right:3px; border-radius:3px; text-decoration:none;">+ Sub</a>',
                reverse("criar_subatividade", args=[obj.pk]),
            )
        )

        # Botão Assumir (Aparece apenas se o logado NÃO for o responsável)
        if obj.responsavel_id != id_do_usuario:
            assumir_url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_assumir",
                args=[obj.pk],
            )
            html.append(
                format_html(
                    '<a class="btn" href="{}" style="background:#28a745; color:white; padding:2px 5px; font-size:10px; margin-right:3px; border-radius:3px; text-decoration:none;">Assumir</a>',
                    assumir_url,
                )
            )

        # Status seguintes
        if obj.situacao:
            for proxima in obj.situacao.proximas_situacoes.all():
                url = reverse("alterar_status", args=[obj.pk, proxima.id])

                if "pend" in proxima.nome.lower():
                    html.append(
                        format_html(
                            '<a href="{}" '
                            "onclick=\"window.open(this.href, 'popup', 'width=600,height=500,scrollbars=yes,resizable=yes'); return false;\" "
                            'style="font-size:10px; padding:1px 4px; border:1px solid #ffc107; color:#856404; background:#fff3cd; text-decoration:none; margin-right:2px;">'
                            "{}</a>",
                            url,
                            proxima.nome,
                        )
                    )
                else:
                    html.append(
                        format_html(
                            '<a href="{}" style="font-size:10px; padding:1px 4px; border:1px solid #ccc; color:#666; text-decoration:none; margin-right:2px;">'
                            "{}</a>",
                            url,
                            proxima.nome,
                        )
                    )
        return mark_safe("".join(html))

    acoes_rapidas.short_description = "Ações"

    def get_urls(self):
        return [
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
        ] + super().get_urls()

    def assumir_demanda(self, request, pk):
        obj = self.get_object(request, pk)
        if obj:
            obj.responsavel = request.user
            obj.save()
            self.message_user(
                request, f"Você assumiu a demanda: {obj.titulo}", messages.SUCCESS
            )
        return redirect(reverse("admin:core_demanda_changelist"))

    def admin_dashboard(self, request):
        return render(request, "admin/core/demanda_dashboard.html")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        desc = form.cleaned_data.get("pendencia_descricao")
        if desc:
            Pendencia.objects.create(
                demanda=obj, descricao=desc, criado_por=request.user
            )

    def save_formset(self, request, form, formset, change):
        if formset.model == AnexoDemanda:
            instances = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for i, inline_form in enumerate(formset.forms):
                if inline_form in formset.deleted_forms:
                    continue

                files = request.FILES.getlist(f"{formset.prefix}-{i}-arquivo")

                if files:
                    instance = inline_form.instance
                    if not instance.demanda_id:
                        instance.demanda = form.instance

                    instance.arquivo = files[0]
                    instance.save()
                    if instance not in formset.new_objects:
                        formset.new_objects.append(instance)

                    for f in files[1:]:
                        novo_anexo = AnexoDemanda.objects.create(
                            demanda=form.instance, arquivo=f
                        )
                        formset.new_objects.append(novo_anexo)
                else:
                    if inline_form.instance.pk and inline_form.has_changed():
                        inline_form.save()
        else:
            super().save_formset(request, form, formset, change)

    class Media:
        css = {"all": ("css/custom_admin.css",)}


@admin.register(Tema, TipoAtividade)
class AuxiliarAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


class SituacaoForm(forms.ModelForm):
    class Meta:
        model = Situacao
        fields = "__all__"
        widgets = {"cor_hex": forms.TextInput(attrs={"type": "color"})}


@admin.register(Situacao)
class SituacaoAdmin(admin.ModelAdmin):
    form = SituacaoForm
    list_display = ("nome", "padrao", "pendente")
    search_fields = ["nome"]
