"""
Django settings for telegram_bot project.

Generated by 'django-admin startproject' using Django 5.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
from decouple import config
# from django.templatetags.static import static
# from django.urls import reverse_lazy
# from django.utils.translation import gettext_lazy as _




# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-r9ul9+#!rm*@lb!iiohc1rwawgacml%j0sg(y1bz*2e208c--a'
BOT_TOKEN = '8156115400:AAESiwQMq4jgDc_ou4UAijD2kNNVmlvjIFA'
# BOT_TOKEN = '7277573243:AAHJBQhgXcW5akG3UB84r7uNh7mctWEiUv8'
BOT_API_BASE_URL = "http://127.0.0.1:8000"


# Koushik Test
# BYBIT_API_KEY = "uQE5hJdsTkCqddn2gn"
# BYBIT_API_SECRET = "eE7fUQkyJHyZKrV02F9x4HJyYbtzUMHsL2Nkv"

# Ajay
# BYBIT_API_SECRET = "l3JCFrcWiwxBfzCnGTOse0H7oNXifXSJYzq5"
# BYBIT_API_KEY = "0fw2QcEpDOKm3n7wX9"

# Test Ajay
# BYBIT_API_SECRET = "zynFHJjrEzI8sdeIaVAST4u4Yb9yeRVoH78b"
# BYBIT_API_KEY = "BerLfmUSBRR4y3iC5H"

BYBIT_API_SECRET = "xGaErbycDwdOxpMv2lHCPdHZKKsHrgTIyVHc"
BYBIT_API_KEY = "gVAhSlNc1yCe2A0UlT"

TELEGRAM_BOT_TOKEN = "8156115400:AAESiwQMq4jgDc_ou4UAijD2kNNVmlvjIFA"

# BOT_TOKEN = config('BOT_TOKEN')
# BYBIT_API_SECRET = config('BYBIT_API_SECRET')
# BYBIT_API_KEY = config('BYBIT_API_KEY')
# BINANCE_API_KEY= config('BINANCE_API_KEY')
# BINANCE_SECRET = config('BINANCE_SECRET')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'channels',
    'core',
    'api',
    'bot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'telegram_bot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'telegram_bot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



# UNFOLD = {
#     "SIDEBAR": {
#         "show_search": False,  # Search in applications and models names
#         "show_all_applications": False,  # Dropdown with all applications and models
#         "navigation": [
#             {
#                 "title": _("Navigation"),
#                 "separator": True,  # Top border
#                 "collapsible": True,  # Collapsible group of links
#                 "items": [
#                     {
#                         "title": _("Dashboard"),
#                         "icon": "dashboard",  # Supported icon set: https://fonts.google.com/icons
#                         "link": reverse_lazy("admin:index"),
#                         "badge": "sample_app.badge_callback",
#                         "permission": lambda request: request.user.is_superuser,
#                     },
#                     {
#                         "title": _("Users"),
#                         "icon": "people",
#                         "link": reverse_lazy("admin:auth_user_changelist"),
#                     },
#                 ],
#             },
#         ],
#     },
# }

# UNFOLD = {
#     "SIDEBAR": {
#         "items": [
#             {
#                 "title": _("Upload Voucher Codes"),
#                 "icon": "upload",  # or any icon from Material Icons
#                 "link": reverse_lazy("admin:upload_voucher_codes"),
#             },
#         ]
#     }
# }




# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
