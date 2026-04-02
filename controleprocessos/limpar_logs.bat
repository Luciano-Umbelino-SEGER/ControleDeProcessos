@echo off

REM 🔥 Define ambiente
set DJANGO_ENV=dev

REM 🔥 Caminho do projeto
cd /d C:\projects\ArquiteturaDeProcessos\ControleDeProcessos\controleprocessos

REM 🔥 Executa command usando venv
C:\projects\ArquiteturaDeProcessos\ControleDeProcessos\controleprocessos\venv\Scripts\python.exe manage.py limpar_logs

REM 🔥 (Opcional) log de execução
echo Execucao finalizada em %date% %time%