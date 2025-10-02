export $(grep -v '^#' .env | xargs)
curl -X POST https://api.telegram.org/bot${TELEGRAM_TOKEN}/logout
