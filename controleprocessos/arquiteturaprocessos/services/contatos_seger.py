from arquiteturaprocessos.models import ContatoAreaSeger

import requests
from bs4 import BeautifulSoup
import re


def atualizar_contatos_seger():

    url = "https://seger.es.gov.br/contatos-seger"

    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        raise Exception("Erro ao acessar o site da SEGER")

    soup = BeautifulSoup(response.text, "html.parser")

    blocos = soup.find_all("li", class_="panel")

    total = 0
    areas_encontradas = set()

    for bloco in blocos:

        try:
            titulo = bloco.find("h4", class_="panel-title")
            if not titulo:
                continue

            nome_area = titulo.get_text(strip=True)
            areas_encontradas.add(nome_area)

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

            ContatoAreaSeger.objects.update_or_create(
                nome_area=nome_area,
                defaults={
                    "titular": titular,
                    "telefone": telefone,
                    "email": email,
                    "ativo": True,
                    "origem": "SEGER_SITE",
                }
            )

            total += 1

        except Exception:
            continue

    # 🔥 Desativa áreas que sumiram do site
    ContatoAreaSeger.objects.exclude(
        nome_area__in=areas_encontradas
    ).update(ativo=False)

    return total