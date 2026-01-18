"""
Alerts Module

Email and SMS notification system for trading events.

Features:
- Email alerts via SMTP
- SMS alerts via Twilio
- Configurable alert rules
- Rate limiting
- Alert history
- Template-based messages

Usage:
    from src.web.alerts import AlertManager

    manager = AlertManager(config)
    manager.send_trade_alert(trade_data)
    manager.send_error_alert(error_message)
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage email and SMS alerts."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize alert manager.

        Args:
            config: Alert configuration
        """
        self.config = config or {}

        # Email config
        self.email_enabled = self.config.get('email_enabled', False)
        self.smtp_host = self.config.get('smtp_host', 'smtp.gmail.com')
        self.smtp_port = self.config.get('smtp_port', 587)
        self.smtp_user = self.config.get('smtp_user', '')
        self.smtp_password = self.config.get('smtp_password', '')
        self.from_email = self.config.get('from_email', self.smtp_user)
        self.to_emails = self.config.get('to_emails', [])

        # SMS config
        self.sms_enabled = self.config.get('sms_enabled', False)
        self.twilio_account_sid = self.config.get('twilio_account_sid', '')
        self.twilio_auth_token = self.config.get('twilio_auth_token', '')
        self.twilio_from_number = self.config.get('twilio_from_number', '')
        self.to_phone_numbers = self.config.get('to_phone_numbers', [])

        # Alert rules
        self.alert_on_trade = self.config.get('alert_on_trade', False)
        self.alert_on_error = self.config.get('alert_on_error', True)
        self.alert_on_profit_threshold = self.config.get('alert_on_profit_threshold', 100.0)
        self.alert_on_loss_threshold = self.config.get('alert_on_loss_threshold', -50.0)

        # Rate limiting
        self.max_alerts_per_hour = self.config.get('max_alerts_per_hour', 10)
        self.alert_history: deque = deque(maxlen=1000)

        # Twilio client
        self.twilio_client = None
        if self.sms_enabled:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
                logger.info("Twilio SMS alerts enabled")
            except ImportError:
                logger.warning("Twilio library not installed, SMS alerts disabled")
                self.sms_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Twilio: {e}")
                self.sms_enabled = False

        logger.info(f"Alert manager initialized (email: {self.email_enabled}, sms: {self.sms_enabled})")

    def send_trade_alert(self, trade: Dict[str, Any]) -> bool:
        """
        Send alert for trade execution.

        Args:
            trade: Trade data

        Returns:
            True if alert sent successfully
        """
        if not self.alert_on_trade:
            return False

        # Check profit/loss thresholds
        profit = trade.get('profit', 0)
        if profit < self.alert_on_profit_threshold and profit > self.alert_on_loss_threshold:
            return False

        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("Alert rate limit exceeded")
            return False

        # Prepare message
        subject = f"{'🎉 Profit' if profit > 0 else '⚠️ Loss'} Alert: ${abs(profit):.2f}"
        message = self._format_trade_message(trade)

        # Send alerts
        success = True
        if self.email_enabled:
            success &= self._send_email(subject, message)
        if self.sms_enabled:
            success &= self._send_sms(message[:160])  # SMS character limit

        # Record alert
        if success:
            self.alert_history.append({
                'timestamp': datetime.now(),
                'type': 'trade',
                'data': trade
            })

        return success

    def send_error_alert(self, error: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send alert for errors.

        Args:
            error: Error message
            context: Additional context

        Returns:
            True if alert sent successfully
        """
        if not self.alert_on_error:
            return False

        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("Alert rate limit exceeded")
            return False

        # Prepare message
        subject = f"🚨 Error Alert: {error[:50]}"
        message = f"Error occurred:\n\n{error}"
        if context:
            message += f"\n\nContext:\n{context}"

        # Send alerts
        success = True
        if self.email_enabled:
            success &= self._send_email(subject, message)
        if self.sms_enabled:
            success &= self._send_sms(f"Error: {error[:140]}")

        # Record alert
        if success:
            self.alert_history.append({
                'timestamp': datetime.now(),
                'type': 'error',
                'error': error
            })

        return success

    def send_custom_alert(self, subject: str, message: str, level: str = 'info') -> bool:
        """
        Send custom alert.

        Args:
            subject: Alert subject
            message: Alert message
            level: Alert level (info, warning, error)

        Returns:
            True if alert sent successfully
        """
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("Alert rate limit exceeded")
            return False

        # Add emoji based on level
        emoji = {'info': 'ℹ️', 'warning': '⚠️', 'error': '🚨'}.get(level, 'ℹ️')
        subject_with_emoji = f"{emoji} {subject}"

        # Send alerts
        success = True
        if self.email_enabled:
            success &= self._send_email(subject_with_emoji, message)
        if self.sms_enabled:
            success &= self._send_sms(message[:160])

        # Record alert
        if success:
            self.alert_history.append({
                'timestamp': datetime.now(),
                'type': 'custom',
                'subject': subject,
                'level': level
            })

        return success

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get alert history.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts
        """
        alerts = list(self.alert_history)
        return alerts[-limit:]

    def _send_email(self, subject: str, body: str) -> bool:
        """Send email alert."""
        if not self.to_emails:
            logger.warning("No email recipients configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email alert sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _send_sms(self, message: str) -> bool:
        """Send SMS alert."""
        if not self.twilio_client or not self.to_phone_numbers:
            return False

        try:
            for phone_number in self.to_phone_numbers:
                self.twilio_client.messages.create(
                    body=message,
                    from_=self.twilio_from_number,
                    to=phone_number
                )

            logger.info(f"SMS alert sent to {len(self.to_phone_numbers)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows sending alert."""
        # Count alerts in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_alerts = [
            alert for alert in self.alert_history
            if alert['timestamp'] > one_hour_ago
        ]

        return len(recent_alerts) < self.max_alerts_per_hour

    def _format_trade_message(self, trade: Dict[str, Any]) -> str:
        """Format trade data as message."""
        profit = trade.get('profit', 0)
        return f"""
Trade Executed:

Strategy: {trade.get('strategy', 'N/A')}
Pair: {trade.get('pair', 'N/A')}
Side: {trade.get('side', 'N/A')}
Size: {trade.get('size', 0):.4f}
Price: ${trade.get('price', 0):.2f}
Profit/Loss: ${profit:.2f}

Time: {trade.get('timestamp', datetime.now())}
""".strip()


def create_alert_manager(config: Optional[Dict[str, Any]] = None) -> AlertManager:
    """
    Create and return alert manager instance.

    Args:
        config: Alert configuration

    Returns:
        AlertManager instance
    """
    return AlertManager(config)
