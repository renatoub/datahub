import os

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
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


class AnexoDemandaInline(admin.TabularInline):
    model = AnexoDemanda
    extra = 1
    fields = ["arquivo", "link_download"]
    readonly_fields = ["link_download"]

    def link_download(self, obj):
        if obj.id and obj.arquivo:
            return format_html(
                '<a href="{}" target="_blank">📄 Baixar</a>', obj.arquivo.url
            )
        return "-"


class SubitemInline(admin.TabularInline):
    model = Demanda
    extra = 0
    fields = ["nivel", "titulo", "situacao", "responsavel", "data_prazo"]
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
    search_fields = ("demanda__titulo", "arquivo")

    def demanda_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:core_demanda_change", args=[obj.demanda.id]),
            obj.demanda.titulo,
        )

    def nome_arquivo(self, obj):
        return os.path.basename(obj.arquivo.name)

    def baixar(self, obj):
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background:#17a2b8; color:white;">Download</a>',
            obj.arquivo.url,
        )


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
        "nivel",
        "status_tag",
        "status_prazo_tag",
        "responsavel",
        "acoes_rapidas",
    )
    list_filter = ("nivel", "situacao", "responsavel", "tema")
    search_fields = ("titulo", "descricao")
    autocomplete_fields = ["parent", "responsavel", "solicitantes"]
    readonly_fields = ["data_fechamento"]
    save_on_top = True

    fieldsets = (
        (
            "Principal",
            {"fields": ("titulo", "nivel", "parent", "tema", "tipo", "situacao")},
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

    def status_prazo_tag(self, obj):
        if not obj.data_prazo:
            return "-"
        atrasado = obj.data_prazo < timezone.now().date()
        cor = "#e74c3c" if atrasado else "#27ae60"
        txt = "Fora do Prazo" if atrasado else "No Prazo"
        return format_html('<strong style="color: {};">{}</strong>', cor, txt)

    def acoes_rapidas(self, obj):
        sub_url = reverse("criar_subatividade", args=[obj.pk])
        assumir_url = reverse("admin:core_demanda_assumir", args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:#17a2b8; color:white; padding:2px 5px; border-radius:3px; font-size:10px; text-decoration:none;">+ Sub</a> '
            '<a href="{}" style="background:#28a745; color:white; padding:2px 5px; border-radius:3px; font-size:10px; text-decoration:none;">Assumir</a>',
            sub_url,
            assumir_url,
        )

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
