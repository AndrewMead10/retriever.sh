from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from ..config import settings

router = APIRouter()

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

class ContactResponse(BaseModel):
    success: bool
    message: str

@router.get("/onload", response_model=dict)
async def connect_onload():
    """
    Load connect page data
    """
    return {
        "discord_link": "https://discord.gg/YOUR_DISCORD_INVITE",
        "support_email": "support@retriever.sh",
        "contact_info": {
            "email": "support@retriever.sh",
            "response_time": "24-48 hours"
        }
    }

@router.post("/submit", response_model=ContactResponse)
async def submit_contact_form(form_data: ContactForm):
    """
    Handle contact form submission
    """
    try:
        # Here you would typically:
        # 1. Save the contact form to database
        # 2. Send email notification
        # 3. Send confirmation email to user

        # For now, we'll just log and return success
        print(f"Contact form submission from {form_data.email}:")
        print(f"Subject: {form_data.subject}")
        print(f"Message: {form_data.message}")

        # TODO: Implement actual email sending functionality
        # You could use services like SendGrid, AWS SES, or SMTP

        return ContactResponse(
            success=True,
            message="Thank you for your message! We'll get back to you within 24-48 hours."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to submit contact form. Please try again."
        )