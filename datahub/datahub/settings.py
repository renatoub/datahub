import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-+8!lj9_fo5v!r)7o88hp-w4ia6hwr(u9cy_c-^zm-2&2mla_f^"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "localhost",
    "10.6.6.95",
]


# Application definition

INSTALLED_APPS = [
    "jazzmin",
    "core",
    "simple_history",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "datahub.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "datahub.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

JAZZMIN_SETTINGS = {
    "site_title": "DataHub Management",
    "site_header": "DataHub",
    "site_brand": "DataHub",
    "welcome_sign": "Bem-vindo ao DataHub de Demandas",
    "copyright": "DataHub Ltda",
    "search_model": ["core.Demanda"],
    "user_avatar": None,
    # Links no menu superior
    "topmenu_links": [
        {"name": "Início", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "core.Demanda"},
    ],
    # Menu Lateral
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    # Ícones para os modelos (usando Font Awesome)
    "icons": {
        "auth.Group": "fas fa-users",
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "core.Demanda": "fas fa-tasks",
        "core.Tema": "fas fa-tags",
        "core.Situacao": "fas fa-check-circle",
        "core.TipoAtividade": "fas fa-list",
        "core.Contato": "fas fa-address-book",
    },
    # Configuração de Interface
    "show_ui_builder": True,  # Isso permite que você ajuste o tema em tempo real no painel
    "changeform_format": "horizontal_tabs",  # Organiza os campos em abas se quiser
}

JAZZMIN_UI_TWEAKS = {
    # Tema Base Claro e Harmonioso
    "theme": "simplex",
    # Ativa o seletor de Dark Mode no menu do usuário
    # "dark_mode_theme": "darkly",
    # Ajustes finos de cores
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": True,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme_cls": "flatly",
}
