# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pyautogui
import pydirectinput
import keyboard
import time
import threading
import os
import json
import queue

class MinecraftSellerApp:
    def __init__(self):
      
        self.coordinates = {}
        self.is_calibrated = False
        self.is_running = False
        self.settings_file = "config.json"
        self.hotkey_listener = None
        self.sale_queue = queue.Queue()
        self.log_watcher_thread = None

        self.root = tk.Tk()
        self.root.title("Minecraft AH Seller v2.5")
        self.root.geometry("500x630")
        self.root.resizable(False, False)
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
   
        log_frame = ttk.LabelFrame(main_frame, text="1. Настройки лог-файла")
        log_frame.pack(fill="x", padx=5, pady=5)
        self.log_path_var = tk.StringVar()
        log_entry = ttk.Entry(log_frame, textvariable=self.log_path_var, width=50)
        log_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        browse_button = ttk.Button(log_frame, text="Обзор...", command=self.browse_log_file)
        browse_button.pack(side="left", padx=5, pady=5)
        settings_frame = ttk.LabelFrame(main_frame, text="2. Настройки продажи")
        settings_frame.pack(fill="x", padx=5, pady=5, ipady=5)
        ttk.Label(settings_frame, text="Цена продажи:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.price_var = tk.StringVar(value="1000")
        ttk.Entry(settings_frame, textvariable=self.price_var).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(settings_frame, text="Текст успеха в логах:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.success_msg_var = tk.StringVar(value="[CHAT] [☃] У Вас купили")
        ttk.Entry(settings_frame, textvariable=self.success_msg_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        settings_frame.columnconfigure(1, weight=1)
        calib_frame = ttk.LabelFrame(main_frame, text="3. Калибровка 12 координат")
        calib_frame.pack(fill="x", padx=5, pady=5, ipady=5)
        self.calibrate_button = ttk.Button(calib_frame, text="Начать калибровку", command=self.start_calibration)
        self.calibrate_button.pack(pady=5)
        self.calibration_status_label = ttk.Label(calib_frame, text="Статус: ...")
        self.calibration_status_label.pack(pady=5)
        control_frame = ttk.LabelFrame(main_frame, text="4. Управление и Настройки")
        control_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(control_frame, text="Горячая клавиша Старт/Стоп:").pack(side="left", padx=5)
        self.hotkey_var = tk.StringVar(value="f6")
        hotkey_entry = ttk.Entry(control_frame, textvariable=self.hotkey_var, width=10)
        hotkey_entry.pack(side="left", padx=5)
        self.save_button = ttk.Button(control_frame, text="Сохранить все настройки", command=self.save_settings)
        self.save_button.pack(side="right", padx=10, pady=5)
        run_frame = ttk.LabelFrame(main_frame, text="5. Запуск и Информация")
        run_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.start_button = ttk.Button(run_frame, text="ЗАПУСТИТЬ ПРОДАЖУ (или использовать хоткей)", state="disabled", command=self.toggle_process)
        self.start_button.pack(pady=10)
        self.status_log = scrolledtext.ScrolledText(run_frame, height=10, state="disabled")
        self.status_log.pack(fill="both", expand=True, padx=5, pady=5)
        self.load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    
    def log_message(self, message, level='info'):
        if not hasattr(self, 'status_log') or not self.status_log.winfo_exists(): return
        self.status_log.config(state="normal")
        self.status_log.insert(tk.END, message + "\n")
        self.status_log.see(tk.END)
        self.status_log.config(state="disabled")
        if level == 'error': print(f"ERROR: {message}")
        
    def browse_log_file(self):
        filepath = filedialog.askopenfilename(title="Выберите файл latest.log", filetypes=(("Log files", "*.log"), ("All files", "*.*")), initialdir=os.path.join(os.getenv('APPDATA', ''), '.minecraft', 'logs'))
        if filepath: self.log_path_var.set(filepath); self.log_message(f"Выбран новый лог-файл: {filepath}")

    def setup_hotkey(self):
        try:
            if self.hotkey_listener: keyboard.remove_hotkey(self.hotkey_listener)
            hotkey_str = self.hotkey_var.get()
            if hotkey_str: self.hotkey_listener = keyboard.add_hotkey(hotkey_str, self.toggle_process); self.log_message(f"Горячая клавиша '{hotkey_str}' установлена.")
        except Exception as e: self.log_message(f"Ошибка установки хоткея '{self.hotkey_var.get()}': {e}", "error")

    def save_settings(self):
        settings = { "log_path": self.log_path_var.get(), "price": self.price_var.get(), "success_message": self.success_msg_var.get(), "hotkey": self.hotkey_var.get(), "coordinates": {key: (p.x, p.y) for key, p in self.coordinates.items()} if self.is_calibrated else {} }
        try:
            with open(self.settings_file, 'w') as f: json.dump(settings, f, indent=4)
            self.log_message(f"Настройки сохранены в файл: {self.settings_file}"); self.setup_hotkey()
        except Exception as e: self.log_message(f"Ошибка сохранения настроек: {e}", "error")

    def load_settings(self):
        try:
            if not os.path.exists(self.settings_file):
                self.log_message("Файл настроек не найден. Используются значения по умолчанию."); self.calibration_status_label.config(text="Статус: Требуется калибровка")
                self.log_path_var.set(os.path.join(os.getenv('APPDATA', ''), '.minecraft', 'logs', 'latest.log')); self.setup_hotkey(); return
            with open(self.settings_file, 'r') as f: settings = json.load(f)
            self.log_path_var.set(settings.get("log_path", "")); self.price_var.set(settings.get("price", "1000")); self.success_msg_var.set(settings.get("success_message", "[CHAT] [☃] У Вас купили")); self.hotkey_var.set(settings.get("hotkey", "f6"))
            coords_from_file = settings.get("coordinates", {})
          
            if len(coords_from_file) == 12:
                self.coordinates = {int(k): pyautogui.Point(v[0], v[1]) for k, v in coords_from_file.items()}; self.is_calibrated = True
                self.log_message(f"Настройки и 12 координат загружены из {self.settings_file}."); self.calibration_status_label.config(text="Статус: Координаты загружены"); self.start_button.config(state="normal")
            else: self.log_message(f"Настройки загружены, но координаты неполные (нужно 12). Нужна калибровка."); self.calibration_status_label.config(text="Статус: Требуется калибровка")
            self.setup_hotkey()
        except Exception as e: self.log_message(f"Ошибка загрузки настроек: {e}", "error")
        
    def start_calibration(self):
        self.calibrate_button.config(state="disabled"); self.start_button.config(state="disabled")
        threading.Thread(target=self._calibration_thread, daemon=True).start()

    def _calibration_thread(self):
        self.is_calibrated = False
        try:
            self.log_message("\n--- НАЧАЛО КАЛИБРОВКИ ---"); time.sleep(3)
         
            slots_to_calibrate = [10] + list(range(1, 10)) + [11, 12]
            prompts = {
                11: "Наведите на ПЕРВУЮ кнопку в /ah (Мои лоты)",
                12: "Наведите на ВТОРУЮ кнопку в /ah (Обновить)"
            }
            
            for slot_num in slots_to_calibrate:
                prompt_text = prompts.get(slot_num, f"Наведите на слот инвентаря [{slot_num}]")
                self.calibration_status_label.config(text=f"{prompt_text} и НАЖМИТЕ ПРАВЫЙ CTRL")
                keyboard.wait('right ctrl'); pos = pyautogui.position()
                self.coordinates[slot_num] = pos; self.log_message(f"Координата [{slot_num}] откалибрована: {pos}"); time.sleep(0.5)
            
            self.calibration_status_label.config(text="Статус: Калибровка завершена!"); self.is_calibrated = True; self.save_settings()
        except Exception as e: self.log_message(f"Ошибка калибровки: {e}", "error"); self.calibration_status_label.config(text="Статус: Ошибка!")
        finally:
            self.calibrate_button.config(state="normal")
            if self.is_calibrated: self.start_button.config(state="normal")

    
    def toggle_process(self):
        if self.is_running:
            self.stop_process()
        else:
            self.start_process()
            
    def start_process(self):
        if not self.is_calibrated: messagebox.showerror("Ошибка", "Сначала нужно откалибровать все 12 координат!"); return
        self.is_running = True
        
        self.log_message("Очистка очереди от старых событий...")
        with self.sale_queue.mutex:
            self.sale_queue.queue.clear()
            
        self.start_button.config(text="ОСТАНОВИТЬ (или использовать хоткей)")
        self.calibrate_button.config(state="disabled"); self.save_button.config(state="disabled")

        if self.log_watcher_thread is None or not self.log_watcher_thread.is_alive():
            self.log_watcher_thread = threading.Thread(target=self._persistent_log_watcher, daemon=True)
            self.log_watcher_thread.start()
        
        main_logic = threading.Thread(target=self._main_logic_thread, daemon=True)
        main_logic.start()

    def stop_process(self):
        self.is_running = False
        self.log_message("--- ПОЛУЧЕН СИГНАЛ ОСТАНОВКИ ---")
        time.sleep(1)
        self.start_button.config(text="ЗАПУСТИТЬ ПРОДАЖУ (или использовать хоткей)")
        self.calibrate_button.config(state="normal"); self.save_button.config(state="normal")

    def _persistent_log_watcher(self):
        log_file = self.log_path_var.get()
        success_msg_lower = self.success_msg_var.get().lower()
        self.log_message(f"--- [Наблюдатель]: Запущен. ---")

        if not os.path.exists(log_file):
            self.log_message(f"[Наблюдатель]: ОШИБКА: Лог-файл не найден!", "error"); return
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore', buffering=1) as f:
                f.seek(0, 2)
                while self.is_running:
                    line = f.readline()
                    if not line:
                        time.sleep(0.05)
                        continue
                    
                    cleaned_line = line.strip()
                    if cleaned_line and success_msg_lower in cleaned_line.lower():
                        self.log_message(f"[Наблюдатель]: Обнаружена продажа -> {cleaned_line}")
                        self.sale_queue.put(cleaned_line)
        except Exception as e:
            self.log_message(f"[Наблюдатель]: Ошибка: {e}", "error")
        
        self.log_message(f"--- [Наблюдатель]: Остановлен. ---")

 
    def _main_logic_thread(self):
        try:
            self.log_message("\n[Логика]: Начало работы. Пауза 5 секунд..."); time.sleep(5)
            
            while self.is_running:
                self.log_message("\n--- [Логика]: НАЧАЛО НОВОГО ЦИКЛА ПРОДАЖ ---")
                
          
                self.log_message("[Логика]: Расставляю 9 предметов из слота 10...")
                pydirectinput.press('e'); time.sleep(1)
                pydirectinput.moveTo(self.coordinates[10].x, self.coordinates[10].y); time.sleep(0.2); pydirectinput.click(button='left'); time.sleep(0.3)
                for i in range(1, 10):
                    if not self.is_running: raise Exception("Процесс остановлен во время расстановки.")
                    pydirectinput.moveTo(self.coordinates[i].x, self.coordinates[i].y); time.sleep(0.2); pydirectinput.click(button='right'); time.sleep(0.2)
                pydirectinput.moveTo(self.coordinates[10].x, self.coordinates[10].y); time.sleep(0.2); pydirectinput.click(button='left'); time.sleep(0.3)
                pydirectinput.press('e'); time.sleep(1)

               
                for i in range(0, 9, 3):
                    start_slot, end_slot = i + 1, i + 3
                    if not self.is_running: raise Exception("Процесс остановлен.")
                    
                    self.log_message(f"[Логика]: Выставляю предметы из слотов с {start_slot} по {end_slot}...")
                    price = self.price_var.get()
                    for slot in range(start_slot, end_slot + 1):
                        pydirectinput.press(str(slot)); time.sleep(0.5)
                        pydirectinput.press('/'); time.sleep(0.2)
                        pyautogui.typewrite(f"ah sell {price}", interval=0.05); pydirectinput.press('enter'); time.sleep(2)
                    
                    self.log_message(f"[Логика]: Ожидаю 3 продажи...")
                    sales_needed = 3
                    start_time = time.time() 
                    
                    while sales_needed > 0 and self.is_running:
                        try:
                            sale_info = self.sale_queue.get(timeout=0.5)
                            self.log_message(f"[Логика]: Получено подтверждение ({3 - sales_needed + 1}/3): {sale_info}")
                            sales_needed -= 1
                            start_time = time.time() 
                        except queue.Empty:
                            
                            if time.time() - start_time > 60:
                                self.log_message("[Логика]: Тайм-аут 1 минута! Выполняю процедуру обновления лотов...")
                                pydirectinput.press('/'); time.sleep(0.2)
                                pyautogui.typewrite("ah", interval=0.05); pydirectinput.press('enter'); time.sleep(2)
                                
                                pydirectinput.click(self.coordinates[11].x, self.coordinates[11].y)
                                self.log_message("[Логика]: Нажатие на ПЕРВУЮ кнопку (коорд. 11)."); time.sleep(2)
                                
                                pydirectinput.click(self.coordinates[12].x, self.coordinates[12].y)
                                self.log_message("[Логика]: Нажатие на ВТОРУЮ кнопку (коорд. 12)."); time.sleep(1)

                                pydirectinput.press('esc')
                                self.log_message("[Логика]: Нажат ESC. Возобновляю ожидание продаж.")
                                start_time = time.time() 
                    
                    if not self.is_running: raise Exception("Процесс остановлен в ожидании продаж.")
                    self.log_message(f"[Логика]: Партия из слотов {start_slot}-{end_slot} продана!")
                
                self.log_message("--- [Логика]: Все 9 предметов проданы. Начинаю цикл заново. ---"); time.sleep(2)

        except Exception as e:
            self.log_message(f"[Логика]: Процесс прерван: {e}")
        finally:
            self.log_message("--- [Логика]: Основной поток завершил свою работу. ---")
            if not self.is_running:
                 self.start_button.config(text="ЗАПУСТИТЬ ПРОДАЖУ (или использовать хоткей)")
                 self.calibrate_button.config(state="normal"); self.save_button.config(state="normal")
    
    def on_closing(self):
        self.stop_process()
        if self.hotkey_listener: keyboard.remove_hotkey(self.hotkey_listener)
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MinecraftSellerApp()

    app.run()
