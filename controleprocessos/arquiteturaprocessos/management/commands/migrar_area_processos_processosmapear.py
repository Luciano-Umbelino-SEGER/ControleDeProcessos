from django.core.management.base import BaseCommand
from arquiteturaprocessos.models import ProcessoMapear, Processo, ContatoAreaSeger


class Command(BaseCommand):
    help = "Migra area_responsavel (string) para area_responsavel_fk com correspondência exata"

    def handle(self, *args, **kwargs):

        self.stdout.write("🚀 Iniciando migração...\n")

        # 🔥 Carrega todas as áreas em memória
        areas = {
            area.nome_area.strip(): area
            for area in ContatoAreaSeger.objects.all()
        }

        total_mapear = 0
        total_processo = 0
        nao_encontrados = []

        # --------------------------------------------------
        # ProcessoMapear
        # --------------------------------------------------
        for obj in ProcessoMapear.objects.all():

            nome = (obj.area_responsavel or "").strip()

            if not nome:
                continue

            contato = areas.get(nome)

            if contato:
                obj.area_responsavel_fk = contato
                obj.save()
                total_mapear += 1

                self.stdout.write(
                    f"✔ ProcessoMapear {obj.id} -> {nome}"
                )

            else:
                nao_encontrados.append(nome)
                self.stdout.write(
                    f"❌ Não encontrado (ProcessoMapear): {nome}"
                )

        # --------------------------------------------------
        # Processo
        # --------------------------------------------------
        for obj in Processo.objects.all():

            nome = (obj.area_responsavel or "").strip()

            if not nome:
                continue

            contato = areas.get(nome)

            if contato:
                obj.area_responsavel_fk = contato
                obj.save()
                total_processo += 1

                self.stdout.write(
                    f"✔ Processo {obj.id} -> {nome}"
                )

            else:
                nao_encontrados.append(nome)
                self.stdout.write(
                    f"❌ Não encontrado (Processo): {nome}"
                )

        # --------------------------------------------------
        # RESUMO FINAL
        # --------------------------------------------------
        self.stdout.write("\n📊 RESUMO:")
        self.stdout.write(f"✔ ProcessoMapear migrados: {total_mapear}")
        self.stdout.write(f"✔ Processo migrados: {total_processo}")
        self.stdout.write(f"❌ Não encontrados: {len(set(nao_encontrados))}")

        if nao_encontrados:
            self.stdout.write("\n⚠ Lista de não encontrados:")
            for nome in sorted(set(nao_encontrados)):
                self.stdout.write(f"- {nome}")

        self.stdout.write("\n✅ Migração concluída!")