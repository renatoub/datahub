from datetime import timedelta

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
    # Valor padrão como cinza (#6c757d)
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

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Situações"


class Contato(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.nome


class Pendencia(models.Model):
    demanda = models.ForeignKey(
        "Demanda", on_delete=models.CASCADE, related_name="pendencias"
    )
    descricao = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()
    criado_por = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    resolvida = models.BooleanField(default=False)
    resolvido_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pendência #{self.pk} - {self.demanda}"


class Demanda(models.Model):
    NIVEIS = (
        ("INICIATIVA", "Iniciativa"),
        ("EPICO", "Épico"),
        ("HISTORIA", "História"),
        ("ATIVIDADE", "Atividade"),
    )

    nivel = models.CharField(max_length=20, choices=NIVEIS, default="ATIVIDADE")
    titulo = models.CharField("Atividade / Título", max_length=255)

    # Hierarquia: Uma atividade pode ter uma História "pai", que tem um Épico "pai"...
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subitens",
        verbose_name="Item Pai (Iniciativa/Épico/História)",
    )

    tema = models.ForeignKey(Tema, on_delete=models.PROTECT)
    tipo = models.ForeignKey(TipoAtividade, on_delete=models.PROTECT)
    # (campo `parent` definido acima)
    responsavel = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    situacao = models.ForeignKey(
        "Situacao", on_delete=models.PROTECT, null=True, blank=True
    )
    data_inicio = models.DateField(null=True, blank=True)
    data_prazo = models.DateField(null=True, blank=True)
    descricao = models.TextField(blank=True)
    observacao = models.TextField(blank=True)
    solicitantes = models.ManyToManyField(Contato, blank=True, related_name="demandas")
    data_fechamento = models.DateField(null=True, blank=True)
    history = HistoricalRecords()
    descricao = models.TextField(blank=True)
    observacao = models.TextField(blank=True)
    solicitantes = models.ManyToManyField(Contato, blank=True, related_name="demandas")
    criado_em = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Se não houver situação definida, usar a situação marcada como padrão
        if not self.situacao:
            try:
                default_sit = Situacao.objects.filter(padrao=True).first()
            except Exception:
                default_sit = None
            if default_sit:
                self.situacao = default_sit
        # Regra: Se tem início mas não tem prazo, soma 7 dias
        if self.data_inicio and not self.data_prazo:
            self.data_prazo = self.data_inicio + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo

    def is_final(self):
        return bool(
            self.situacao
            and self.situacao.nome
            and self.situacao.nome.lower().startswith("final")
        )


@receiver(post_save, sender=Demanda)
def demanda_post_save(sender, instance, **kwargs):
    """Ao salvar uma demanda, se ela estiver em situação final, garante `data_fechamento`.
    Depois verifica o pai (e recursivamente os pais) para finalizar automaticamente
    quando todos os subitens estiverem finalizados, atribuindo a data de fechamento
    como a mais recente entre os filhos.
    """
    today = timezone.now().date()

    # Se o item atual estiver final e não tiver data_fechamento, seta para hoje
    if instance.is_final() and not instance.data_fechamento:
        Demanda.objects.filter(pk=instance.pk).update(data_fechamento=today)

    # Propagar para pais enquanto todos os subitens estiverem finalizados
    parent = instance.parent
    while parent:
        subs = list(parent.subitens.all())
        if not subs:
            break
        all_final = all((s.is_final() for s in subs))
        if all_final:
            # determina a data de fechamento mais recente entre os filhos
            dates = [s.data_fechamento or today for s in subs]
            latest = max([d for d in dates if d is not None])
            # tenta encontrar uma situação com nome contendo 'final'
            final_sit = Situacao.objects.filter(nome__icontains="final").first()
            updates = {"data_fechamento": latest}
            if final_sit:
                updates["situacao_id"] = final_sit.pk
            Demanda.objects.filter(pk=parent.pk).update(**updates)
            # subir um nível
            parent = Demanda.objects.filter(pk=parent.pk).first().parent
        else:
            break


@receiver(post_save, sender=Situacao)
def situacao_post_save(sender, instance, created, **kwargs):
    """Garante que apenas uma situação esteja marcada como padrão.

    Quando uma `Situacao` é salva com `padrao=True`, as demais têm `padrao=False`.
    """
    # Se marcou como padrão, remove flag das outras
    if instance.padrao:
        Situacao.objects.exclude(pk=instance.pk).filter(padrao=True).update(
            padrao=False
        )

    # Se marcou como pendente, remove flag de pendente das outras
    if instance.pendente:
        Situacao.objects.exclude(pk=instance.pk).filter(pendente=True).update(
            pendente=False
        )


@receiver(pre_save, sender=Pendencia)
def pendencia_pre_save(sender, instance, **kwargs):
    """Grava o estado anterior de `resolvida` para comparação no post_save."""
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
    """Ao mudar o estado de resolvida, atualiza timestamps e a situacao da Demanda.

    - se passou de False->True: define `resolvido_em` (se ausente) e coloca demanda em 'exec'
    - se passou de True->False: limpa `resolvido_em` e coloca demanda em 'pend'
    """
    was = getattr(instance, "_was_resolvida", False)
    now = bool(instance.resolvida)

    # transição False -> True (resolvida agora)
    if not was and now:
        if not instance.resolvido_em:
            Pendencia.objects.filter(pk=instance.pk).update(resolvido_em=timezone.now())
        exec_sit = Situacao.objects.filter(nome__icontains="exec").first()
        if exec_sit:
            Demanda.objects.filter(pk=instance.demanda_id).update(
                situacao_id=exec_sit.pk, data_fechamento=None
            )

    # transição True -> False (foi desmarcada)
    if was and not now:
        if instance.resolvido_em:
            Pendencia.objects.filter(pk=instance.pk).update(resolvido_em=None)
        pend_sit = Situacao.objects.filter(nome__icontains="pend").first()
        if pend_sit:
            Demanda.objects.filter(pk=instance.demanda_id).update(
                situacao_id=pend_sit.pk, data_fechamento=None
            )
