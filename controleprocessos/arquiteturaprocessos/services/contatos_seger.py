from arquiteturaprocessos.models import ContatoAreaSeger, ProcessoMapear, Processo
from auditoria.models import LogAcaoSistema

from django.utils import timezone

import requests
from bs4 import BeautifulSoup
import re


def atualizar_contatos_seger(usuario=None):

    url = "https://seger.es.gov.br/contatos-seger"

    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        raise Exception("Erro ao acessar o site da SEGER")

    soup = BeautifulSoup(response.text, "html.parser")

    blocos = soup.find_all("li", class_="panel")

    total_processados = 0
    total_criados = 0
    total_atualizados = 0
    total_excluidos = 0

    areas_site = set()

    for bloco in blocos:
        try:
            titulo = bloco.find("h4", class_="panel-title")
            if not titulo:
                continue

            nome_area = titulo.get_text(strip=True)
            areas_site.add(nome_area)

            body = bloco.find("div", class_="panel-body")
            if not body:
                continue

            titular = ""
            telefone = ""
            email = ""

            infos = body.find_all("div", class_="info-contato")

            for info in infos:
                titulo_info = info.find("strong", class_="info-title")
                valor_info = info.find("div", class_="info-value")

                if not titulo_info or not valor_info:
                    continue

                titulo_texto = titulo_info.get_text(strip=True)
                valor = valor_info.get_text(strip=True)

                if "Titular" in titulo_texto:
                    titular = valor

                elif "Telefone" in titulo_texto:
                    telefone_raw = valor

                    ddd_match = re.search(r"\(\d{2}\)", telefone_raw)
                    ddd = ddd_match.group() if ddd_match else ""

                    telefones = []
                    for t in telefone_raw.split("/"):
                        t = t.strip()
                        if not t.startswith("(") and ddd:
                            t = f"{ddd} {t}"
                        telefones.append(t)

                    telefone = " | ".join(telefones)

                elif "E-mail" in titulo_texto:
                    email = valor

            obj, created = ContatoAreaSeger.objects.get_or_create(
                nome_area=nome_area
            )

            if created:
                obj.usuario_cadastro = usuario
                total_criados += 1
            else:
                total_atualizados += 1

            # Atualiza sempre
            obj.titular = titular
            obj.telefone = telefone
            obj.email = email
            obj.ativo = True
            obj.origem = "SEGER_SITE"
            obj.usuario_atualizacao = usuario
            obj.atualizado_em = timezone.now()

            obj.save()

            # 🔥 Atualiza processos relacionados
            ProcessoMapear.objects.filter(area_responsavel=obj).update(
                gestor=titular,
                telefone=telefone,
                email=email
            )

            Processo.objects.filter(area_responsavel=obj).update(
                gestor=titular,
                telefone=telefone,
                email=email
            )

            total_processados += 1

        except Exception:
            continue

    # 🔥 DELETE FÍSICO (somente origem SEGER_SITE)
    areas_para_excluir = ContatoAreaSeger.objects.filter(
        origem="SEGER_SITE"
    ).exclude(nome_area__in=areas_site)

    total_excluidos = areas_para_excluir.count()
    areas_para_excluir.delete()

    # 🔥 LOG ÚNICO
    try:
        LogAcaoSistema.objects.create(
            usuario=usuario,
            acao=LogAcaoSistema.TipoAcao.UPDATE,
            modelo_afetado="ContatoAreaSeger",
            descricao=(
                f"Atualização de contatos SEGER | "
                f"Criados: {total_criados}, "
                f"Atualizados: {total_atualizados}, "
                f"Excluídos: {total_excluidos}"
            ),
            dados_depois={
                "criados": total_criados,
                "atualizados": total_atualizados,
                "excluidos": total_excluidos
            },
            sucesso=True
        )
    except Exception as e:
        print("Erro ao registrar log:", e)

    return total_processados