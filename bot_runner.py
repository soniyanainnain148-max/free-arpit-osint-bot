import threading
import bot


def run_bot():
    bot.main()


bot_thread = threading.Thread(
    target=run_bot,
    daemon=True
)

bot_thread.start()
