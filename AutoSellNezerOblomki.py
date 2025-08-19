# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pyautogui
import pydirectinput
import keyboard
import time
import threading
import os
import json
import queue

class ProcessStoppedException(Exception):
    pass

class MinecraftSellerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.coordinates = {}
        self.is_calibrated = False
        self.is_running = False
        self.settings_file = "config.json"
        self.hotkey_listener = None
        self.sale_queue = queue.Queue()
        self.log_watcher_thread = None
        self.anti_afk_thread = None
        self.action_lock = threading.Lock()
        self.anti_afk_forward = True
        
       
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("AhSellerFunTime (DISCORD 4596036)")
        self.geometry("900x650")
        self.resizable(False, False)

       
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)
        
      
        self.settings_frame = ctk.CTkFrame(self, width=350, corner_radius=10)
        self.settings_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.settings_frame.grid_propagate(False)
        self.settings_frame.grid_columnconfigure(0, weight=1)

        header_label = ctk.CTkLabel(self.settings_frame, text="Панель Управления", font=ctk.CTkFont(size=20, weight="bold"))
        header_label.grid(row=0, column=0, padx=20, pady=20)
        
        log_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        log_frame.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="ew")
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text="Файл логов Minecraft:").grid(row=0, column=0, columnspan=2, sticky="w")
        self.log_path_var = ctk.StringVar()
        log_entry = ctk.CTkEntry(log_frame, textvariable=self.log_path_var, height=35)
        log_entry.grid(row=1, column=0, sticky="ew")
        browse_button = ctk.CTkButton(log_frame, text="Обзор...", command=self.browse_log_file, width=80, height=35)
        browse_button.grid(row=1, column=1, padx=(10, 0))

        sale_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        sale_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        sale_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(sale_frame, text="Цена продажи:").grid(row=0, column=0, sticky="w")
        self.price_var = ctk.StringVar(value="1000")
        ctk.CTkEntry(sale_frame, textvariable=self.price_var, height=35).grid(row=0, column=1, sticky="ew", padx=10)
        ctk.CTkLabel(sale_frame, text="Текст успеха в логах:").grid(row=1, column=0, sticky="w", pady=(10,0))
        self.success_msg_var = ctk.StringVar(value="[CHAT] [☃] У Вас купили")
        ctk.CTkEntry(sale_frame, textvariable=self.success_msg_var, height=35).grid(row=1, column=1, sticky="ew", padx=10, pady=(10,0))

        ctk.CTkLabel(self.settings_frame, text="Калибровка координат", font=ctk.CTkFont(size=14, weight="bold")).grid(row=3, column=0, padx=20, pady=(20, 5), sticky="w")
        self.calibrate_button = ctk.CTkButton(self.settings_frame, text="Начать калибровку (12 точек)", command=self.start_calibration, height=40)
        self.calibrate_button.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        self.calibration_status_label = ctk.CTkLabel(self.settings_frame, text="Статус: Не откалибровано", text_color="gray")
        self.calibration_status_label.grid(row=5, column=0, padx=20, pady=5)
        
        hotkey_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        hotkey_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=(20, 5))
        hotkey_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hotkey_frame, text="Горячая клавиша:").grid(row=0, column=0)
        self.hotkey_var = ctk.StringVar(value="f6")
        hotkey_entry = ctk.CTkEntry(hotkey_frame, textvariable=self.hotkey_var, width=80, justify="center", height=35)
        hotkey_entry.grid(row=0, column=1, padx=10)
        self.save_button = ctk.CTkButton(self.settings_frame, text="Сохранить все настройки", command=self.save_settings, height=35)
        self.save_button.grid(row=7, column=0, padx=20, pady=10, sticky="ew")

        
        self.run_frame = ctk.CTkFrame(self, corner_radius=10)
        self.run_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.run_frame.grid_columnconfigure(0, weight=1)
        self.run_frame.grid_rowconfigure(1, weight=1)

        self.start_button = ctk.CTkButton(self.run_frame, text="ЗАПУСТИТЬ ПРОДАЖУ", state="disabled", command=self.toggle_process, font=ctk.CTkFont(size=16, weight="bold"), height=50)
        self.start_button.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        self.status_log = ctk.CTkTextbox(self.run_frame, state="disabled", corner_radius=10, font=("Consolas", 12))
        self.status_log.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.status_log.tag_config('info', foreground="#abb2bf")
        self.status_log.tag_config('error', foreground="#e06c75")
        self.status_log.tag_config('success', foreground="#98c379")
        self.status_log.tag_config('warning', foreground="#e5c07b")
        self.status_log.tag_config('action', foreground="#61afef")

     
        self.load_settings()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

   
    def _check_if_running(self):
        if not self.is_running:
            raise ProcessStoppedException()

    def log_message(self, message, level='info'):
        if not hasattr(self, 'status_log') or not self.status_log.winfo_exists(): return
        self.status_log.configure(state="normal")
        self.status_log.insert(ctk.END, message + "\n", level)
        self.status_log.see(ctk.END)
        self.status_log.configure(state="disabled")

    def browse_log_file(self):
        initial_dir = os.path.join(os.getenv('APPDATA', ''), '.minecraft', 'logs')
        filepath = filedialog.askopenfilename(title="Выберите файл latest.log", filetypes=(("Log files", "*.log"), ("All files", "*.*")), initialdir=initial_dir)
        if filepath:
            self.log_path_var.set(filepath)
            self.log_message(f"Выбран новый лог-файл: {filepath}", 'success')

    def setup_hotkey(self):
        try:
            if self.hotkey_listener: keyboard.remove_hotkey(self.hotkey_listener)
            hotkey_str = self.hotkey_var.get()
            if hotkey_str:
               
                self.hotkey_listener = keyboard.add_hotkey(hotkey_str, lambda: self.after(0, self.toggle_process))
                self.log_message(f"Горячая клавиша '{hotkey_str}' установлена.", 'success')
        except Exception as e:
            self.log_message(f"Ошибка установки хоткея '{self.hotkey_var.get()}': {e}", "error")

    def save_settings(self):
        settings = {"log_path": self.log_path_var.get(), "price": self.price_var.get(), "success_message": self.success_msg_var.get(), "hotkey": self.hotkey_var.get(), "coordinates": {key: (p.x, p.y) for key, p in self.coordinates.items()} if self.is_calibrated else {}}
        try:
            with open(self.settings_file, 'w') as f: json.dump(settings, f, indent=4)
            self.log_message(f"Настройки сохранены в {self.settings_file}", 'success')
            self.setup_hotkey()
        except Exception as e: self.log_message(f"Ошибка сохранения настроек: {e}", "error")

    def load_settings(self):
        try:
            if not os.path.exists(self.settings_file):
                self.log_message("Файл настроек не найден. Используются значения по умолчанию.", 'warning')
                self.calibration_status_label.configure(text="Статус: Требуется калибровка", text_color="gray")
                self.log_path_var.set(os.path.join(os.getenv('APPDATA', ''), '.minecraft', 'logs', 'latest.log'))
                self.setup_hotkey(); return
            with open(self.settings_file, 'r') as f: settings = json.load(f)
            self.log_path_var.set(settings.get("log_path", ""))
            self.price_var.set(settings.get("price", "1000"))
            self.success_msg_var.set(settings.get("success_message", "[CHAT] [☃] У Вас купили"))
            self.hotkey_var.set(settings.get("hotkey", "f6"))
            coords = settings.get("coordinates", {})
            if len(coords) == 12:
                self.coordinates = {int(k): pyautogui.Point(v[0], v[1]) for k, v in coords.items()}
                self.is_calibrated = True
                self.log_message("Настройки и 12 координат загружены.", 'success')
                self.calibration_status_label.configure(text="Статус: Координаты загружены", text_color="#98c379")
                self.start_button.configure(state="normal")
            else:
                self.log_message("Настройки загружены, но нужна калибровка.", 'warning')
                self.calibration_status_label.configure(text="Статус: Требуется калибровка", text_color="gray")
            self.setup_hotkey()
        except Exception as e: self.log_message(f"Ошибка загрузки настроек: {e}", "error")

    def start_calibration(self):
        self.calibrate_button.configure(state="disabled")
        self.start_button.configure(state="disabled")
        threading.Thread(target=self._calibration_thread, daemon=True).start()

    def _calibration_thread(self):
      
        self.is_calibrated = False
        try:
            self.log_message("\n--- НАЧАЛО КАЛИБРОВКИ ---", 'action')
            time.sleep(3)
            slots_to_calibrate = [10] + list(range(1, 10)) + [11, 12]
            prompts = {10: "Наведите на СЛОТ 10", 11: "Наведите на ПЕРВУЮ кнопку в /ah", 12: "Наведите на ВТОРУЮ кнопку в /ah"}
            for slot in slots_to_calibrate:
                prompt_text = prompts.get(slot, f"Наведите на слот инвентаря [{slot}]")
                self.calibration_status_label.configure(text=f"{prompt_text}\nи НАЖМИТЕ ПРАВЫЙ CTRL", text_color="#e5c07b")
                keyboard.wait('right ctrl')
                pos = pyautogui.position(); self.coordinates[slot] = pos
                self.log_message(f"Координата [{slot}] откалибрована: {pos}")
                time.sleep(0.5)
            self.calibration_status_label.configure(text="Статус: Калибровка завершена!", text_color="#98c379")
            self.is_calibrated = True; self.log_message("--- КАЛИБРОВКА УСПЕШНО ЗАВЕРШЕНА ---", 'success')
            self.save_settings()
        except Exception as e:
            self.log_message(f"Ошибка калибровки: {e}", "error"); self.calibration_status_label.configure(text="Статус: Ошибка!", text_color="#e06c75")
        finally:
            self.calibrate_button.configure(state="normal")
            if self.is_calibrated: self.start_button.configure(state="normal")

    def _type_command_via_clipboard(self, command):
       
        original_clipboard_content = "";
        try: original_clipboard_content = self.clipboard_get()
        except Exception: pass
        self.clipboard_clear(); self.clipboard_append(command); self.update()
        time.sleep(0.1); pydirectinput.press('t'); time.sleep(0.3)
        pydirectinput.keyDown('ctrl'); time.sleep(0.1); pydirectinput.press('v'); time.sleep(0.1); pydirectinput.keyUp('ctrl')
        time.sleep(0.2); pydirectinput.press('enter'); self.clipboard_clear()
        if original_clipboard_content: self.clipboard_append(original_clipboard_content)
        self.update()

    def toggle_process(self):
        if self.is_running: self.stop_process()
        else: self.start_process()
            
    def start_process(self):
        if not self.is_calibrated: messagebox.showerror("Ошибка", "Сначала откалибруйте все 12 координат!"); return
        if not os.path.exists(self.log_path_var.get()): messagebox.showerror("Ошибка", f"Файл логов не найден по пути:\n{self.log_path_var.get()}\n\nПроверьте путь в настройках."); return
        
        self.is_running = True
        with self.sale_queue.mutex: self.sale_queue.queue.clear()
        self.log_message("Очистка очереди...", 'warning')
        
        self.start_button.configure(text="ОСТАНОВИТЬ", fg_color="#e06c75", hover_color="#c45d65")
        self.calibrate_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        
        if self.log_watcher_thread is None or not self.log_watcher_thread.is_alive():
            self.log_watcher_thread = threading.Thread(target=self._persistent_log_watcher, daemon=True); self.log_watcher_thread.start()
        if self.anti_afk_thread is None or not self.anti_afk_thread.is_alive():
            self.anti_afk_thread = threading.Thread(target=self._anti_afk_thread, daemon=True); self.anti_afk_thread.start()
        main_logic = threading.Thread(target=self._main_logic_thread, daemon=True); main_logic.start()

    def stop_process(self):
        
        if not self.is_running: return 
        self.is_running = False
        self.log_message("--- СИГНАЛ ОСТАНОВКИ ПОЛУЧЕН ---", 'warning')
      
        self.start_button.configure(text="ЗАПУСТИТЬ ПРОДАЖУ", fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#36719F", "#144870"))
        self.calibrate_button.configure(state="normal")
        self.save_button.configure(state="normal")

    def _persistent_log_watcher(self):
        log_file = self.log_path_var.get()
        success_msg_lower = self.success_msg_var.get().lower()
        self.log_message(f"--- [Наблюдатель]: Запущен ---", 'action')
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore', buffering=1) as f:
                f.seek(0, 2)
                while self.is_running: 
                    line = f.readline()
                    if not line: time.sleep(0.05); continue
                    if success_msg_lower in line.strip().lower():
                        self.log_message(f"[Наблюдатель]: Обнаружена продажа!", 'success')
                        self.sale_queue.put(line)
        except Exception as e: self.log_message(f"[Наблюдатель]: Ошибка: {e}", "error")
        self.log_message(f"--- [Наблюдатель]: Остановлен ---", 'action')
   
    def _anti_afk_thread(self):
        self.log_message("--- [Анти-АФК]: Запущен ---", 'action')
        while self.is_running:
           
            for _ in range(300):
                if not self.is_running: break
                time.sleep(0.1)
            if not self.is_running: break

            with self.action_lock:
                self._check_if_running()
                self.log_message("[Анти-АФК]: Выполнение действий...", 'warning')
                key = 'w' if self.anti_afk_forward else 's'
                pydirectinput.keyDown(key); time.sleep(0.1); pydirectinput.keyUp(key)
                self.anti_afk_forward = not self.anti_afk_forward
                time.sleep(0.3)
                pydirectinput.move(60, 0, relative=True); time.sleep(0.3)
                pydirectinput.move(-120, 0, relative=True); time.sleep(0.3)
                pydirectinput.move(60, 0, relative=True)
        self.log_message("--- [Анти-АФК]: Остановлен ---", 'action')

    def _main_logic_thread(self):
        
        try:
            self.log_message("\n[Логика]: Начало работы. Пауза 5 секунд...", 'warning')
            time.sleep(5)
            
            while True: 
                self._check_if_running()
                self.log_message("\n--- [Логика]: НАЧАЛО НОВОГО ЦИКЛА ---", 'action')
                with self.action_lock:
                    self.log_message("[Логика]: Расставляю 9 предметов...", 'info')
                    pydirectinput.press('e'); time.sleep(1); self._check_if_running()
                    pydirectinput.moveTo(self.coordinates[10].x, self.coordinates[10].y); time.sleep(0.2); pydirectinput.click(); time.sleep(0.3)
                    for i in range(1, 10):
                        self._check_if_running()
                        pydirectinput.moveTo(self.coordinates[i].x, self.coordinates[i].y); time.sleep(0.2); pydirectinput.click(button='right'); time.sleep(0.2)
                    pydirectinput.moveTo(self.coordinates[10].x, self.coordinates[10].y); time.sleep(0.2); pydirectinput.click(); time.sleep(0.3)
                    pydirectinput.press('e'); time.sleep(1)

                for i in range(0, 9, 3):
                    self._check_if_running()
                    start_slot, end_slot = i + 1, i + 3
                    with self.action_lock:
                        self.log_message(f"[Логика]: Выставляю слоты {start_slot}-{end_slot}...", 'info')
                        price = self.price_var.get()
                        for slot in range(start_slot, end_slot + 1):
                            self._check_if_running()
                            pydirectinput.press(str(slot)); time.sleep(0.5)
                            self._type_command_via_clipboard(f"/ah sell {price}"); time.sleep(2)
                    
                    self.log_message(f"[Логика]: Ожидаю 3 продажи...", 'info')
                    sales_needed, start_time = 3, time.time()
                    while sales_needed > 0:
                        self._check_if_running()
                        try:
                            self.sale_queue.get(timeout=0.2) 
                            self.log_message(f"[Логика]: Продажа! ({3 - sales_needed + 1}/3)", 'success')
                            sales_needed -= 1; start_time = time.time()
                        except queue.Empty:
                            if time.time() - start_time > 60:
                                with self.action_lock:
                                    self._check_if_running()
                                    self.log_message("[Логика]: Тайм-аут! Обновляю лоты...", 'warning')
                                    self._type_command_via_clipboard("/ah"); time.sleep(2)
                                    pydirectinput.click(self.coordinates[11].x, self.coordinates[11].y); time.sleep(2)
                                    pydirectinput.click(self.coordinates[12].x, self.coordinates[12].y); time.sleep(1)
                                    pydirectinput.press('esc'); start_time = time.time()
                    self.log_message(f"[Логика]: Партия {start_slot}-{end_slot} продана!", 'success')
                
                self.log_message("--- [Логика]: Полный цикл завершен. Пауза 2с. ---", 'success')
                time.sleep(2)

        except ProcessStoppedException:
            self.log_message("[Логика]: Процесс был прерван пользователем.", 'warning')
        except Exception as e:
            self.log_message(f"[Логика]: Критическая ошибка: {e}", 'error')
        finally:
            self.log_message("--- [Логика]: Основной поток завершил работу. ---", 'action')
    
    def on_closing(self):
        self.stop_process()
        if self.hotkey_listener: keyboard.remove_hotkey(self.hotkey_listener)
        self.destroy()

if __name__ == "__main__":
    app = MinecraftSellerApp()
    app.mainloop()