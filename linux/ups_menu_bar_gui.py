#!/usr/bin/env python3
"""Linux desktop prototype. Uses the read-only CLI as a background worker."""
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk


class MonitorWindow:
    FIELDS = [('input_V', 'Input voltage', ' V'), ('output_V', 'Output voltage', ' V'),
              ('load_percent', 'Load', ' %'), ('estimated_W', 'Estimated power', ' W'),
              ('battery_V', 'Battery voltage', ' V'), ('battery_charge_percent', 'Battery charge', ' %'),
              ('battery_runtime_s', 'Battery runtime', ' s'), ('temperature_C', 'Temperature', ' °C'),
              ('frequency_Hz', 'Frequency', ' Hz')]

    def __init__(self, root):
        self.root = root
        self.process = None
        self.generation = 0
        self.events = queue.Queue()
        self.closed = False
        self.timer = None
        root.title('UPS Menu Bar · Linux preview')
        root.minsize(730, 720)
        root.geometry('760x740')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#f4f7fa')
        style.configure('TLabel', background='#f4f7fa', foreground='#172c40', font=('DejaVu Sans', 10))
        style.configure('Title.TLabel', font=('DejaVu Sans', 22, 'bold'))
        style.configure('Value.TLabel', font=('DejaVu Sans', 13, 'bold'))
        style.configure('TButton', padding=(12, 8))
        style.configure('TLabelframe', background='#f4f7fa')
        style.configure('TLabelframe.Label', background='#f4f7fa', foreground='#172c40')
        body = ttk.Frame(root, padding=24)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='UPS Menu Bar', style='Title.TLabel').pack(anchor='w')
        ttk.Label(body, text='Linux preview · Read-only NUT monitoring').pack(anchor='w', pady=(2, 16))
        self.status = tk.StringVar(value='Not connected')
        ttk.Label(body, textvariable=self.status, style='Value.TLabel').pack(anchor='w', pady=(0, 12))
        form = ttk.LabelFrame(body, text='Connection', padding=12)
        form.pack(fill='x')
        self.settings = {}
        for row, (key, label, default) in enumerate([
            ('host', 'NUT server', '127.0.0.1'), ('port', 'Port', '3493'),
            ('ups', 'UPS name', ''), ('rated', 'Rated output power (W, optional)', '')]):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky='w', padx=(0, 16), pady=3)
            value = tk.StringVar(value=default)
            self.settings[key] = value
            ttk.Entry(form, textvariable=value).grid(row=row, column=1, sticky='ew', pady=3)
        form.columnconfigure(1, weight=1)
        self.csv_path = tk.StringVar()
        files = ttk.Frame(body)
        files.pack(fill='x', pady=10)
        ttk.Button(files, text='Choose CSV…', command=self.choose_csv).pack(side='left')
        ttk.Button(files, text='No CSV', command=lambda: self.csv_path.set('')).pack(side='left', padx=6)
        ttk.Label(files, textvariable=self.csv_path, wraplength=390).pack(side='left', padx=6)
        actions = ttk.Frame(body)
        actions.pack(fill='x', pady=(0, 12))
        ttk.Button(actions, text='Connect / Apply', command=self.connect).pack(side='left')
        ttk.Button(actions, text='Disconnect', command=self.disconnect).pack(side='left', padx=8)
        table = ttk.Frame(body)
        table.pack(fill='x')
        table.columnconfigure(1, weight=1)
        self.values = {}
        for row, (key, label, _) in enumerate(self.FIELDS):
            ttk.Label(table, text=label).grid(row=row, column=0, sticky='w', pady=1)
            value = tk.StringVar(value='—')
            self.values[key] = value
            ttk.Label(table, textvariable=value, style='Value.TLabel').grid(row=row, column=1, sticky='e', pady=1)
        self.detail = tk.StringVar(value='Enter your NUT server and UPS name to begin.')
        ttk.Label(body, textvariable=self.detail, wraplength=670).pack(anchor='w', pady=(12, 0))
        ttk.Label(body, text='Power and energy are estimates. Missing values are shown as —.').pack(anchor='w', pady=(8, 0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.timer = root.after(100, self.drain)

    def choose_csv(self):
        path = filedialog.asksaveasfilename(title='Choose a separate Linux CSV file',
                                          defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if path:
            self.csv_path.set(path)

    def clear(self):
        for value in self.values.values():
            value.set('—')

    def stop_worker(self):
        self.generation += 1
        process, self.process = self.process, None
        if process and process.poll() is None:
            process.terminate()
            def reap():
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            threading.Thread(target=reap, daemon=True).start()
        return process

    def connect(self):
        previous = self.stop_worker()
        self.clear()
        self.status.set('Connecting…')
        self.detail.set('Waiting for current telemetry…')
        command = [sys.executable, str(Path(__file__).with_name('ups_menu_bar.py')),
                   '--host', self.settings['host'].get().strip(),
                   '--port', self.settings['port'].get().strip(),
                   '--ups', self.settings['ups'].get().strip()]
        if self.settings['rated'].get().strip():
            command += ['--rated-watts', self.settings['rated'].get().strip()]
        if self.csv_path.get():
            command += ['--csv', self.csv_path.get()]
        generation = self.generation
        self.launch(command, generation, previous)

    def launch(self, command, generation, previous):
        if self.closed or generation != self.generation:
            return
        if previous and previous.poll() is None:
            self.root.after(100, lambda: self.launch(command, generation, previous))
            return
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except OSError as error:
            self.status.set('Cannot start monitoring')
            self.detail.set(str(error))
            return
        self.process = process
        def receive():
            try:
                for line in process.stdout:
                    self.events.put((generation, json.loads(line)))
                error = process.stderr.read().strip()
                code = process.wait()
                self.events.put((generation, {'connected': False, 'error': error or f'Monitor stopped ({code})'}))
            except (ValueError, OSError) as error:
                self.events.put((generation, {'connected': False, 'error': str(error)}))
            finally:
                process.stdout.close()
                process.stderr.close()
        threading.Thread(target=receive, daemon=True).start()

    def render(self, event):
        if not event.get('connected'):
            self.clear()
            self.status.set('No current data')
            self.detail.set(event.get('error', 'Connection unavailable'))
            return
        flags = event['status'].split()
        state = 'Low battery' if 'LB' in flags else 'On battery' if 'OB' in flags else 'Online' if 'OL' in flags else event['status']
        self.status.set(state)
        for key, _, unit in self.FIELDS:
            value = event.get(key)
            self.values[key].set('—' if value is None else f'{value:g}{unit}')
        self.detail.set(f"{event['target']} · Updated {event['timestamp']} (UTC)")

    def drain(self):
        if self.closed:
            return
        try:
            while True:
                generation, event = self.events.get_nowait()
                if generation == self.generation:
                    self.render(event)
        except queue.Empty:
            pass
        self.timer = self.root.after(100, self.drain)

    def disconnect(self):
        self.stop_worker()
        self.clear()
        self.status.set('Disconnected')
        self.detail.set('Monitoring stopped. No UPS commands were sent.')

    def close(self):
        self.closed = True
        self.stop_worker()
        if self.timer:
            self.root.after_cancel(self.timer)
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    MonitorWindow(root)
    root.mainloop()
