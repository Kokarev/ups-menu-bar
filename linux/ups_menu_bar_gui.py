#!/usr/bin/env python3
"""Linux desktop prototype. Uses the read-only CLI as a background worker."""
import json
from datetime import datetime
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
        root.minsize(460, 600)
        root.geometry('500x960')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#f4f7fa')
        style.configure('TLabel', background='#f4f7fa', foreground='#172c40', font=('DejaVu Sans', 10))
        style.configure('Title.TLabel', font=('DejaVu Sans', 22, 'bold'))
        style.configure('Value.TLabel', font=('DejaVu Sans', 13, 'bold'))
        style.configure('TButton', padding=(12, 8))
        style.configure('TLabelframe', background='#f4f7fa')
        style.configure('TLabelframe.Label', background='#f4f7fa', foreground='#172c40')
        style.configure('Section.TLabel', font=('DejaVu Sans', 10, 'bold'), foreground='#72808c')
        outer = ttk.Frame(root)
        outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, background='#f4f7fa', highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        body = ttk.Frame(canvas, padding=18)
        content = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(content, width=e.width))
        root.bind('<Button-4>', lambda e: canvas.yview_scroll(-1, 'units'))
        root.bind('<Button-5>', lambda e: canvas.yview_scroll(1, 'units'))
        self.summary = tk.StringVar(value='— V  ·  — W  ·  — %')
        ttk.Label(body, textvariable=self.summary, style='Value.TLabel').pack(anchor='w', pady=(0, 10))
        self.status = tk.StringVar(value='Not connected')
        ttk.Label(body, textvariable=self.status, style='Value.TLabel').pack(anchor='w', pady=(0, 4))
        self.settings = {key: tk.StringVar(value=value) for key, value in
                         [('host', '127.0.0.1'), ('port', '3493'), ('ups', ''), ('rated', '')]}
        self.csv_path = tk.StringVar()
        self.settings_window = None
        self.active_csv = ''
        self.values = {}
        self.info = {}
        def section(title, rows):
            ttk.Separator(body).pack(fill='x', pady=(9, 7))
            ttk.Label(body, text=title, style='Section.TLabel').pack(anchor='w', pady=(0, 4))
            frame = ttk.Frame(body)
            frame.pack(fill='x')
            frame.columnconfigure(1, weight=1)
            for row, (key, label, default) in enumerate(rows):
                ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=2)
                var = tk.StringVar(value=default)
                (self.values if key in {f[0] for f in self.FIELDS} else self.info)[key] = var
                ttk.Label(frame, textvariable=var).grid(row=row, column=1, sticky='e', pady=2)
        section('Mains', [('input_V', 'Input', '—'), ('output_V', 'Output', '—'), ('frequency_Hz', 'Frequency', '—')])
        section('Load', [('load_percent', 'Load', '—'), ('estimated_W', 'Estimated power', '—')])
        section('Battery', [('battery_V', 'Voltage', '—'), ('mode', 'Mode', 'No data'),
                            ('battery_charge_percent', 'Charge', '—'), ('battery_runtime_s', 'Runtime (NUT)', '—')])
        section('Power outages', [('last_outage', 'Last outage', 'Not recorded'),
                                 ('duration', 'Duration', '—'), ('min_voltage', 'Min. battery voltage', '—'),
                                 ('drop', 'Voltage drop', '—')])
        ttk.Label(body, text='Event history is not available in this Linux preview.', wraplength=420, style='Section.TLabel').pack(anchor='w')
        section('Temperature', [('temperature_C', 'UPS', '—')])
        section('Energy statistics', [('today', 'Today', 'Not calculated'), ('month', 'This month', 'Not calculated')])
        section('Diagnostics', [('connection', 'NUT', 'Disconnected'), ('raw_status', 'UPS status', '—'),
                                ('driver', 'Driver', '—'), ('updated', 'Last update', '—')])
        self.detail = tk.StringVar(value='Enter your NUT server and UPS name to begin.')
        ttk.Label(body, textvariable=self.detail, wraplength=420).pack(anchor='w', pady=(8, 0))
        ttk.Separator(body).pack(fill='x', pady=10)
        for label, action in [('Settings…', self.show_settings), ('Open CSV log', self.open_csv_log),
                              ('Disconnect', self.disconnect), ('Quit', self.close)]:
            ttk.Button(body, text=label, command=action).pack(fill='x', pady=2)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.timer = root.after(100, self.drain)

    def show_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title('UPS Menu Bar Settings')
        window.geometry('650x360')
        frame = ttk.Frame(window, padding=20)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        for row, (key, label) in enumerate([('host', 'NUT server'), ('port', 'Port'),
                                          ('ups', 'UPS name'), ('rated', 'Rated output power (W, optional)')]):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', padx=(0, 12), pady=5)
            ttk.Entry(frame, textvariable=self.settings[key]).grid(row=row, column=1, sticky='ew', pady=5)
        ttk.Button(frame, text='Choose CSV…', command=self.choose_csv).grid(row=4, column=0, sticky='w', pady=8)
        ttk.Label(frame, textvariable=self.csv_path, wraplength=340).grid(row=4, column=1, sticky='w')
        ttk.Button(frame, text='No CSV', command=lambda: self.csv_path.set('')).grid(row=5, column=0, sticky='w')
        ttk.Button(frame, text='Connect / Apply', command=self.connect).grid(row=6, column=0, sticky='w', pady=16)
        ttk.Button(frame, text='Close', command=window.destroy).grid(row=6, column=1, sticky='e')

    def open_csv_log(self):
        if self.active_csv and Path(self.active_csv).is_file():
            try:
                subprocess.Popen(['xdg-open', str(Path(self.active_csv).resolve())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                self.detail.set('No desktop file opener is installed. CSV: ' + self.active_csv)
        else:
            self.detail.set('No CSV log selected. Choose a file in Settings and apply the connection.')

    def choose_csv(self):
        path = filedialog.asksaveasfilename(title='Choose a separate Linux CSV file',
                                          defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if path:
            self.csv_path.set(path)

    def clear(self):
        for value in self.values.values():
            value.set('—')
        self.summary.set('— V  ·  — W  ·  — %')
        for key in ['mode', 'raw_status', 'driver', 'updated']:
            self.info[key].set('—')
        self.info['connection'].set('Disconnected')

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
        self.active_csv = self.csv_path.get()
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
        self.info['mode'].set(state)
        self.info['connection'].set('Connected')
        self.info['raw_status'].set(event['status'])
        self.info['driver'].set(event.get('driver_state') or 'No data')
        self.info['updated'].set(datetime.fromisoformat(event['timestamp']).astimezone().strftime('%H:%M:%S'))
        for key, _, unit in self.FIELDS:
            value = event.get(key)
            self.values[key].set('—' if value is None else f'{value:g}{unit}')
        self.summary.set('  ·  '.join(self.values[k].get() for k in ['input_V', 'estimated_W', 'load_percent']))
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
