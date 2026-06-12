import os
import logging

from fastapi import APIRouter
from fastapi.responses import FileResponse

logger = logging.getLogger("matchiq")

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

logger.info("FRONTEND_DIR: %s", FRONTEND_DIR)
logger.info("FRONTEND EXISTS: %s", os.path.exists(FRONTEND_DIR))


def frontend_file(filename: str):
    return FileResponse(os.path.join(FRONTEND_DIR, filename))


@router.get("/")
def serve_home():
    return frontend_file("index.html")


@router.get("/index.html")
def serve_index_html():
    return frontend_file("index.html")


@router.get("/admin-beta.html")
def serve_admin_beta():
    return frontend_file("admin-beta.html")


@router.get("/admin")
def serve_admin_alias():
    return frontend_file("admin-beta.html")


@router.get("/admin-analytics.html")
def serve_admin_analytics():
    return frontend_file("admin-analytics.html")


@router.get("/scout.html")
def serve_scout():
    return frontend_file("scout.html")


@router.get("/match.html")
def serve_match():
    return frontend_file("match.html")


@router.get("/coach.html")
def serve_coach():
    return frontend_file("coach.html")


@router.get("/video.html")
def serve_video():
    return frontend_file("video.html")


@router.get("/account.html")
def serve_account():
    return frontend_file("account.html")


@router.get("/login.html")
def serve_login():
    return frontend_file("login.html")


@router.get("/register.html")
def serve_register():
    return frontend_file("register.html")


@router.get("/admin-users.html")
def serve_admin_users():
    return frontend_file("admin-users.html")


@router.get("/verify-email.html")
def serve_verify_email():
    return frontend_file("verify-email.html")


@router.get("/reset-password.html")
def serve_reset_password():
    return frontend_file("reset-password.html")
