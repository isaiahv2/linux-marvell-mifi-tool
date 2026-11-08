#!/usr/bin/env python3
"""Small Tk GUI for the Linux Marvell MiFi tool."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from mifi_tool import READ_COMMANDS, UsbAt, clean_response


class MiFiApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Marvell MiFi Tool")
        self.geometry("700x470")
        self.minsize(600, 380)
        self.jobs: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self.busy = False
        self._build()
        self.after(100, self._poll_jobs)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Marvell MiFi Tool", font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        ttk.Label(root, text="USB AT interface • 115200 8N1").pack(anchor="w", pady=(2, 12))

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=(0, 10))
        self.info_button = ttk.Button(actions, text="Read Info", command=self.read_info)
        self.info_button.pack(side="left")
        self.status_button = ttk.Button(actions, text="Check Lock", command=self.check_lock)
        self.status_button.pack(side="left", padx=8)
        self.unlock_button = ttk.Button(actions, text="Unlock", command=self.unlock)
        self.unlock_button.pack(side="left")
        ttk.Label(actions, text="Code:").pack(side="left", padx=(22, 5))
        self.code = ttk.Entry(actions, width=14)
        self.code.insert(0, "123456")
        self.code.pack(side="left")

        self.status = ttk.Label(root, text="Ready. Connect the MiFi and choose an action.", foreground="#555")
        self.status.pack(anchor="w", pady=(0, 8))

        frame = ttk.Frame(root)
        frame.pack(fill="both", expand=True)
        self.output = tk.Text(frame, wrap="word", height=18, state="disabled", background="#111827", foreground="#e5e7eb", insertbackground="white")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", text)
        self.output.configure(state="disabled")

    def _run(self, title: str, commands: dict[str, str]) -> None:
        if self.busy:
            return
        self.busy = True
        for button in (self.info_button, self.status_button, self.unlock_button):
            button.configure(state="disabled")
        self.status.configure(text=f"Working: {title}…")

        def worker() -> None:
            device = None
            try:
                device = UsbAt()
                chunks = []
                for label, command in commands.items():
                    response = device.query(command, 3.0)
                    chunks.append(f"[{label}] {command}\n{clean_response(response)}")
                self.jobs.put(("ok", title, "\n\n".join(chunks)))
            except Exception as exc:
                self.jobs.put(("error", title, str(exc)))
            finally:
                if device:
                    device.close()

        threading.Thread(target=worker, daemon=True).start()

    def read_info(self) -> None:
        self._run("reading device information", READ_COMMANDS)

    def check_lock(self) -> None:
        self._run("checking lock status", {"lock status": "+CLCK=PN,2", "SIM state": "+CPIN?"})

    def unlock(self) -> None:
        code = self.code.get().strip()
        if not code:
            messagebox.showwarning("Unlock", "Enter the unlock code first.")
            return
        self._run("unlocking MiFi", {"unlock": f"+CLCK=PN,0,{code}", "SIM state": "+CPIN?"})

    def _poll_jobs(self) -> None:
        try:
            kind, title, result = self.jobs.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_jobs)
            return
        self.busy = False
        for button in (self.info_button, self.status_button, self.unlock_button):
            button.configure(state="normal")
        self._set_output(result)
        self.status.configure(text=(f"Completed: {title}" if kind == "ok" else f"Error: {result}"))
        self.after(100, self._poll_jobs)


if __name__ == "__main__":
    MiFiApp().mainloop()
