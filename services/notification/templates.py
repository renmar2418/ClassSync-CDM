"""HTML email templates for ClassSync notifications.
Brand theme: CdM Midnight (#34141f), Rouge (#872e49), Rose (#f8ebf0).
"""

def render_otp_email(full_name: str, otp_code: str, expiry_minutes: int = 5) -> str:
    """Render empathetic, responsive HTML template for 2FA OTP login verification."""
    display_name = full_name if full_name else "ClassSync User"
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ClassSync Verification Code</title>
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8ebf0; color: #1e293b;">
  <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(52, 20, 31, 0.08);">
    <div style="background: linear-gradient(135deg, #34141f 0%, #872e49 100%); padding: 32px 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">ClassSync</h1>
      <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.85;">Pamantasan ng Montalban • Security Verification</p>
    </div>
    
    <div style="padding: 32px 24px;">
      <p style="font-size: 15px; margin: 0 0 16px;">Hello <strong>{display_name}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; margin: 0 0 24px; color: #475569;">
        Please use the following 6-digit verification code to complete your sign-in to the ClassSync portal.
      </p>
      
      <div style="background: #fdf2f4; border: 2px dashed #872e49; border-radius: 12px; padding: 20px; text-align: center; margin: 0 0 24px;">
        <span style="font-family: 'Courier New', monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #872e49;">
          {otp_code}
        </span>
      </div>
      
      <p style="font-size: 13px; color: #64748b; line-height: 1.5; margin: 0 0 16px;">
        ⏱️ This code will expire in <strong>{expiry_minutes} minutes</strong>. For your account security, never share this code with anyone.
      </p>
      
      <p style="font-size: 12px; color: #94a3b8; line-height: 1.5; margin: 0; border-top: 1px solid #f1f5f9; padding-top: 16px;">
        If you did not attempt to sign in to ClassSync, you can safely ignore this email.
      </p>
    </div>
  </div>
</body>
</html>
"""


def render_schedule_change_email(full_name: str, details: str) -> str:
    """Render notification for schedule or classroom reassignment alerts."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; padding: 20px; background: #f8ebf0;">
  <div style="max-width: 520px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 12px;">
    <h2 style="color: #872e49; margin-top: 0;">ClassSync Schedule Notice</h2>
    <p>Dear {full_name},</p>
    <p>There has been an update to your academic timetable:</p>
    <div style="background: #f1f5f9; padding: 12px; border-radius: 8px; font-size: 14px;">
      {details}
    </div>
    <p style="font-size: 12px; color: #64748b; margin-top: 20px;">
      Pamantasan ng Montalban • Automated Timetable Notification
    </p>
  </div>
</body>
</html>
"""
