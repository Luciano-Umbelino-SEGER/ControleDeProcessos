from django.core.exceptions import ValidationError
from arquiteturaprocessos.models import NormaProcedimento
from django.utils.safestring import mark_safe

# =========================================
# UTIL – Validação de Normas do Processo
# =========================================
def validar_normas_processo(post_data):

    normas_ids = []

    norma_principal = post_data.get(
        "norma_procedimento"
    )

    if norma_principal:
        normas_ids.append(norma_principal)

    normas_ids.extend(
        post_data.getlist(
            "norma_procedimento_extra[]"
        )
    )

    normas_ids = list(filter(None, normas_ids))

    duplicadas = {
        x for x in normas_ids
        if normas_ids.count(x) > 1
    }

    if duplicadas:
        norma = NormaProcedimento.objects.get(
            pk=duplicadas.pop()
        )
        raise ValidationError(
            mark_safe(
                'Não é permitido associar a Norma de Procedimento '
                f'<strong>"{norma.nome_norma}"</strong>, '
                'mais de uma vez ao Processo.'
            )
        )

    return normas_ids