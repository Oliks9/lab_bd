import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk
from uuid import uuid4

from .config import connection_label, settings_path
from .installer import install_database


def confirm_installation(parent, dsn, schema_user):
    warning = (
        f"Подключение: {connection_label(dsn)}\nСхема: {schema_user}\n\n"
        "Будет выполнен install.sql. Он УДАЛИТ существующие данные проекта: "
        "пользователей приложения, тесты, ответы и результаты, затем создаст начальные данные.\n\n"
        "Это установка с нуля, НЕ обновление. Сначала сделайте резервную копию. "
        "Закройте остальные подключения приложения к этой схеме. "
        "Создание и удаление объектов Oracle нельзя полностью откатить.\n\nПродолжить?"
    )
    if not messagebox.askyesno("Установка с удалением данных", warning, parent=parent, default="no", icon="warning"):
        return False
    typed = simpledialog.askstring("Подтверждение схемы", f"Для подтверждения удаления данных проекта введите имя схемы:\n{schema_user}", parent=parent)
    return typed is not None and typed.strip().upper() == schema_user.upper()


def open_installation(parent, dsn, schema_user, password):
    if getattr(parent, "installation_busy", False) or not confirm_installation(parent, dsn, schema_user):
        return
    dialog = tk.Toplevel(parent)
    dialog.title("Установка базы приложения")
    dialog.geometry("850x540")
    dialog.minsize(600, 360)
    dialog.transient(parent)
    dialog.grab_set()
    parent.installation_busy = True
    content = ttk.Frame(dialog, padding=16)
    content.pack(fill="both", expand=True)
    status = ttk.Label(content, text="Подготовка установки. Не закрывайте приложение.", wraplength=720)
    status.pack(fill="x")
    content.bind("<Configure>", lambda event: status.configure(wraplength=max(200, event.width - 32)))
    progress = ttk.Progressbar(content, maximum=1)
    progress.pack(fill="x", pady=12)
    footer = ttk.Frame(content)
    footer.pack(side="bottom", fill="x", pady=(10, 0))
    output_frame = ttk.Frame(content)
    output_frame.pack(fill="both", expand=True)
    output = tk.Text(output_frame, wrap="word", state="disabled", height=12)
    scrollbar = ttk.Scrollbar(output_frame, command=output.yview)
    scrollbar.pack(side="right", fill="y")
    output.configure(yscrollcommand=scrollbar.set)
    output.pack(fill="both", expand=True)

    def close():
        if not parent.installation_busy:
            dialog.grab_release()
            dialog.destroy()

    close_button = ttk.Button(footer, text="Закрыть", command=close, state="disabled")
    close_button.pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", close)
    dialog.bind("<Return>", lambda _event: "break")
    dialog.bind("<Escape>", lambda _event: close())
    messages = queue.Queue()

    def worker():
        log_path = None
        try:
            directory = settings_path().parent / "install_logs"
            directory.mkdir(parents=True, exist_ok=True)
            log_path = directory / f"install_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}.log"
            with log_path.open("w", encoding="utf-8") as log:
                def report(text, done, total):
                    safe_text = str(text).replace(password, "[скрыто]")
                    log.write(safe_text + "\n")
                    log.flush()
                    messages.put(("progress", safe_text, done, total))

                try:
                    install_database(dsn, schema_user, password, report)
                except Exception as exc:
                    report(str(exc), 0, 1)
                    raise
            messages.put(("done", True, str(log_path)))
        except Exception as exc:
            messages.put(("error", str(exc).replace(password, "[скрыто]"), str(log_path or "")))

    def poll():
        finished = False
        while True:
            try:
                item = messages.get_nowait()
            except queue.Empty:
                break
            if item[0] == "progress":
                output.configure(state="normal")
                output.insert("end", item[1] + "\n")
                output.see("end")
                output.configure(state="disabled")
                progress.configure(maximum=item[3], value=item[2])
            else:
                finished = True
                parent.installation_busy = False
                close_button.configure(state="normal")
                if item[0] == "done":
                    status.configure(text="Установка завершена. Закройте это окно и нажмите «Подключиться». Вход: admin / Admin123!\nЖурнал: " + item[2])
                else:
                    status.configure(text="Установка не завершена. Подробности ошибки в журнале ниже.\nЖурнал: " + item[2])
                    output.configure(state="normal")
                    output.insert("end", "\nОШИБКА: " + item[1])
                    output.see("end")
                    output.configure(state="disabled")
        if not finished:
            parent.after(100, poll)

    threading.Thread(target=worker, name="oracle-installation", daemon=False).start()
    parent.after(100, poll)
