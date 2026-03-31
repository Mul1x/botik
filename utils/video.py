import os
from telegram import Bot, InputFile
from config import VIDEO_PATH


async def send_menu_with_video(update, text: str, reply_markup, video_path: str = VIDEO_PATH):
    """Отправляет видео с клавиатурой. Если видео есть - отправляет его и удаляет предыдущее."""
    chat_id = update.effective_chat.id
    
    # Получаем текущее сообщение для удаления (если есть)
    context = update.callback_query if hasattr(update, 'callback_query') else update
    
    try:
        # Пытаемся удалить предыдущее сообщение
        if hasattr(update, 'callback_query') and update.callback_query.message:
            await update.callback_query.message.delete()
        elif hasattr(update, 'message') and update.message:
            # Если это новое сообщение
            pass
    except Exception:
        pass
    
    # Отправляем видео
    if os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.effective_chat.send_video(
                video=InputFile(video),
                caption=text,
                reply_markup=reply_markup
            )
    else:
        await update.effective_chat.send_message(
            text=text,
            reply_markup=reply_markup
        )


async def edit_menu_with_video(query, text: str, reply_markup):
    """Редактирует существующее сообщение с видео"""
    try:
        if query.message.video:
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup
            )
    except Exception:
        # Если не удалось отредактировать, отправляем новое
        await send_menu_with_video(query, text, reply_markup)
