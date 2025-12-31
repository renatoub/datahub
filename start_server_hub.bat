@echo off
cd C:\EQTONE\DataHub\
call git pull
call .venv\Scripts\python.exe manage.py runserver 0.0.0.0:12345