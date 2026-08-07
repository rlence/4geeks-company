import httpx

import config


def _reset_email_html(reset_url: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #1f2937;">Restablece tu contraseña</h2>
      <p style="color: #374151; font-size: 15px; line-height: 1.5;">
        Recibimos una solicitud para restablecer la contraseña de tu cuenta en Brasaland.
        Este enlace expira en {config.RESET_TOKEN_TTL_MINUTES} minutos.
      </p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}"
           style="background-color: #b45309; color: #ffffff; padding: 12px 24px;
                  border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">
          Restablecer contraseña
        </a>
      </p>
      <p style="color: #6b7280; font-size: 13px;">
        Si no solicitaste este cambio, puedes ignorar este correo.
      </p>
    </div>
    """


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        json={
            "from": config.EMAIL_FROM,
            "to": [to_email],
            "subject": "Restablece tu contraseña — Brasaland",
            "html": _reset_email_html(reset_url),
        },
        timeout=10.0,
    )
    response.raise_for_status()
