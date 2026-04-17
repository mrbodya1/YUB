# yookassa_client.py
import yookassa
from yookassa import Payment, Configuration
import config
import uuid

# Настройка клиента ЮKassa
Configuration.account_id = config.config.YOOKASSA_SHOP_ID
Configuration.secret_key = config.config.YOOKASSA_SECRET_KEY

def create_payment(user_id=None, amount=990, description="Взнос", return_url=None, payment_ref=None):
    try:
        if payment_ref is None:
            payment_ref = str(uuid.uuid4())[:8]

        if return_url is None:
            return_url = config.config.YOOKASSA_RETURN_URL_BOT

        # Добавляем payment_ref к return_url
        if '?' in return_url:
            return_url_with_ref = f"{return_url}&payment_ref={payment_ref}"
        else:
            return_url_with_ref = f"{return_url}?payment_ref={payment_ref}"

        payment = Payment.create({
            "amount": {"value": str(amount), "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url_with_ref},
            "capture": True,
            "description": description,
            "metadata": {"user_id": str(user_id) if user_id else None, "payment_ref": payment_ref}
        })

        return {
            "success": True,
            "payment_id": payment.id,
            "payment_url": payment.confirmation.confirmation_url,
            "payment_ref": payment_ref,
            "status": payment.status
        }
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"success": False, "error": str(e)}


def create_redirect_payment(user_id=None, amount=990, description="Взнос в челлендж", return_url=None, payment_ref=None):
    """Алиас для create_payment — создает платеж с редиректом"""
    return create_payment(user_id, amount, description, return_url, payment_ref)


def create_embedded_payment(user_id=None, amount=990, description="Взнос в челлендж", payment_ref=None):
    """Создает платеж для виджета (embedded)"""
    try:
        if payment_ref is None:
            payment_ref = str(uuid.uuid4())[:8]

        payment = Payment.create({
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "embedded"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id) if user_id else None,
                "payment_ref": payment_ref
            }
        })

        return {
            "success": True,
            "payment_id": payment.id,
            "confirmation_token": payment.confirmation.confirmation_token,
            "payment_ref": payment_ref,
            "status": payment.status
        }
    except Exception as e:
        print(f"❌ Ошибка создания embedded-платежа: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_payment_status(payment_id):
    """Проверяет статус платежа"""
    try:
        payment = Payment.find_one(payment_id)
        return {
            "success": True,
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "metadata": payment.metadata
        }
    except Exception as e:
        print(f"❌ Ошибка проверки статуса: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def is_payment_successful(payment_id):
    """Проверяет, успешно ли завершен платеж"""
    try:
        payment = Payment.find_one(payment_id)
        return payment.status == 'succeeded' and payment.paid is True
    except:
        return False


def create_landing_payment(amount=990):
    """Создает платеж для лендинга (устаревший)"""
    landing_return_url = config.config.YOOKASSA_RETURN_URL_LANDING
    return create_payment(
        user_id=None,
        amount=amount,
        description="Взнос в челлендж «Королевская Битва»",
        return_url=landing_return_url
    )