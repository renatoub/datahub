import os

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Tema(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class TipoAtividade(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Situacao(models.Model):
    nome = models.CharField(max_length=100)
    cor_hex = models.CharField(
        max_length=7,
        default="#6c757d",
        help_text="Insira a cor em Hexadecimal (ex: #d9534f)",
    )
    padrao = models.BooleanField(
        default=False,
        help_text="Marcar como situação padrão para novas demandas",
    )
    pendente = models.BooleanField(
        default=False,
        help_text="Marcar como situação que representa 'pendente'",
    )
    proximas_situacoes = models.ManyToManyField("self", symmetrical=False, blank=True)

    class Meta:
        verbose_name_plural = "Situações"

    def __str__(self):
        return self.nome


class Contato(models.Model):
    nome = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nome


class Demanda(models.Model):
    NIVEL_CHOICES = [
        ("Projeto", "Projeto"),
        ("Atividade", "Atividade"),
        ("Sub-item", "Sub-item"),
    ]
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default="Atividade")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subitens",
        verbose_name="Demanda Pai",
    )
    titulo = models.CharField(max_length=255, verbose_name="Título")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    observacao = models.TextField(blank=True, verbose_name="Observação Interna")
    tema = models.ForeignKey(Tema, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.ForeignKey(
        TipoAtividade, on_delete=models.SET_NULL, null=True, blank=True
    )
    situacao = models.ForeignKey(
        Situacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Situação",
    )
    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="demandas_responsaveis",
        verbose_name="Responsável",
    )
    solicitantes = models.ManyToManyField(
        Contato, blank=True, related_name="demandas_solicitadas"
    )
    data_inicio = models.DateField(default=timezone.now)
    data_prazo = models.DateField(null=True, blank=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(
        auto_now=timezone.now
    )  # Corrigido para evitar erro de migração
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.nivel}: {self.titulo}"


def upload_anexo_path(instance, filename):
    return os.path.join("anexos", f"demanda_{instance.demanda.id}", filename)


class AnexoDemanda(models.Model):
    demanda = models.ForeignKey(
        Demanda, on_delete=models.CASCADE, related_name="anexos_set"
    )
    arquivo = models.FileField(upload_to=upload_anexo_path)
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Todos os Anexos"

    def __str__(self):
        return os.path.basename(self.arquivo.name)


class Pendencia(models.Model):
    demanda = models.ForeignKey(
        Demanda, on_delete=models.CASCADE, related_name="pendencias"
    )
    descricao = models.TextField()
    resolvida = models.BooleanField(default=False)
    criado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    resolvido_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pendência em {self.demanda.titulo}"


@receiver(pre_save, sender=Pendencia)
def pendencia_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Pendencia.objects.get(pk=instance.pk)
            instance._was_resolvida = bool(old.resolvida)
        except Pendencia.DoesNotExist:
            instance._was_resolvida = False
    else:
        instance._was_resolvida = False


@receiver(post_save, sender=Pendencia)
def pendencia_post_save(sender, instance, created, **kwargs):
    was = getattr(instance, "_was_resolvida", False)
    now = bool(instance.resolvida)
    if not was and now:
        if not instance.resolvido_em:
            Pendencia.objects.filter(pk=instance.pk).update(resolvido_em=timezone.now())
        exec_sit = Situacao.objects.filter(nome__icontains="exec").first()
        if exec_sit:
            Demanda.objects.filter(pk=instance.demanda_id).update(
                situacao_id=exec_sit.pk, data_fechamento=None
            )
    if was and not now:
        Pendencia.objects.filter(pk=instance.pk).update(resolvido_em=None)
        pend_sit = Situacao.objects.filter(nome__icontains="pend").first()
        if pend_sit:
            Demanda.objects.filter(pk=instance.demanda_id).update(
                situacao_id=pend_sit.pk
            )
