import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import json
import csv
import threading

class AkamaiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Akamai Hostname Tool")
        self.root.geometry("850x650")
        
        # UI Styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main Frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Authentication Overrides (Optional) ---
        auth_frame = ttk.LabelFrame(main_frame, text="Authentication Overrides (Optional)", padding="10")
        auth_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(auth_frame, text=".edgerc Path:").grid(row=0, column=0, sticky=tk.W, pady=2, padx=(0, 5))
        self.edgerc_var = tk.StringVar()
        ttk.Entry(auth_frame, textvariable=self.edgerc_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=2, padx=(0, 5))
        ttk.Button(auth_frame, text="Browse", command=self.browse_edgerc).grid(row=0, column=2, sticky=tk.W, pady=2)
        
        ttk.Label(auth_frame, text="Section:").grid(row=1, column=0, sticky=tk.W, pady=2, padx=(0, 5))
        self.section_var = tk.StringVar()
        ttk.Entry(auth_frame, textvariable=self.section_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=2, padx=(0, 5))
        
        # --- Step 1: Search ---
        ttk.Label(main_frame, text="Step 1: Search Account", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_btn = ttk.Button(search_frame, text="Search", command=self.start_search_thread)
        self.search_btn.pack(side=tk.LEFT)
        
        self.account_status = ttk.Label(search_frame, text="")
        self.account_status.pack(side=tk.LEFT, padx=(10, 0))
        
        # --- Step 2: Select ---
        ttk.Label(main_frame, text="Step 2: Select Account", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        select_frame = ttk.Frame(main_frame)
        select_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.account_var = tk.StringVar()
        self.account_dropdown = ttk.Combobox(select_frame, textvariable=self.account_var, state="readonly", width=50)
        self.account_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        
        self.fetch_btn = ttk.Button(select_frame, text="Get Hostnames", command=self.start_fetch_thread, state=tk.DISABLED)
        self.fetch_btn.pack(side=tk.LEFT)
        
        self.hostname_status = ttk.Label(select_frame, text="")
        self.hostname_status.pack(side=tk.LEFT, padx=(10, 0))
        
        # Store raw account mappings (Name -> SwitchKey)
        self.account_map = {}
        
        # --- Step 3: Results Table ---
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Treeview (Table)
        columns = ("Hostname", "CertType", "EdgeHostname", "PropertyName")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, minwidth=100, width=180)
            
        # Scrollbar for Table
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Export Button
        self.export_btn = ttk.Button(main_frame, text="Export to CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_btn.pack(pady=(15, 0), anchor=tk.E)

    # --- UI Helpers ---
    def browse_edgerc(self):
        file_path = filedialog.askopenfilename(title="Select .edgerc File")
        if file_path:
            self.edgerc_var.set(file_path)

    def get_auth_flags(self):
        """Constructs the PowerShell arguments for edgerc and section overrides if provided."""
        flags = ""
        edgerc = self.edgerc_var.get().strip()
        section = self.section_var.get().strip()
        
        if edgerc:
            flags += f" -Edgerc '{edgerc}'"
        if section:
            flags += f" -Section '{section}'"
            
        return flags

    # --- PowerShell Execution Helper ---
    def run_powershell(self, command):
        print(f"\n[DEBUG] Executing: {command}")
        
        # $ErrorActionPreference = 'Stop' forces PowerShell to throw an actual error 
        # instead of silently failing in the pipeline.
        strict_command = f"$ErrorActionPreference = 'Stop'; {command}"
        
        process = subprocess.Popen(
            ['pwsh', '-Command', strict_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        print(f"[DEBUG] Return Code: {process.returncode}")
        
        if stderr.strip():
            print(f"[DEBUG] STDERR: {stderr.strip()}")
            
        if stdout.strip():
            print(f"[DEBUG] STDOUT: {stdout.strip()[:300]}") 
            
        if process.returncode != 0:
            raise Exception(f"{stderr.strip() or stdout.strip()}")
            
        if not stdout.strip():
            print("[DEBUG] PowerShell returned completely empty output.")
            return []
            
        try:
            data = json.loads(stdout)
            if not isinstance(data, list):
                data = [data]
            return data
        except json.JSONDecodeError:
            print(f"[DEBUG] JSON Parse Failed. Raw Output:\n{stdout}")
            raise Exception("Failed to parse PowerShell JSON output.")

    # --- Search Logic ---
    def start_search_thread(self):
        self.search_btn.config(state=tk.DISABLED)
        self.account_status.config(text="Searching... please wait.", foreground="blue")
        self.account_dropdown.set('')
        self.account_dropdown['values'] = []
        self.fetch_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.search_accounts, daemon=True).start()

    def search_accounts(self):
        search_query = self.search_var.get().strip()
        ps_arg = f"'{search_query}'" if search_query else ""
        auth_flags = self.get_auth_flags()
        
        # Dynamically append auth flags if they exist
        command = f"Get-AccountSwitchKey {ps_arg}{auth_flags} | Select-Object accountName, accountSwitchKey | ConvertTo-Json"
        
        try:
            data = self.run_powershell(command)
            
            self.account_map.clear()
            options = []
            
            for acc in data:
                name = acc.get("accountName", acc.get("AccountName", "Unknown Account"))
                key = acc.get("accountSwitchKey", acc.get("AccountSwitchKey", "*"))
                
                if key != '*':
                    display_text = f"{name} ({key})"
                    self.account_map[display_text] = key
                    options.append(display_text)
            
            self.root.after(0, self.update_search_ui, options)
            
        except Exception as e:
            self.root.after(0, self.show_error, "account_status", str(e), self.search_btn)

    def update_search_ui(self, options):
        self.search_btn.config(state=tk.NORMAL)
        if not options:
            self.account_status.config(text="No matching accounts found.", foreground="red")
        else:
            self.account_status.config(text=f"Found {len(options)} accounts.", foreground="green")
            self.account_dropdown['values'] = options
            self.account_dropdown.current(0)
            self.fetch_btn.config(state=tk.NORMAL)

    # --- Fetch Logic ---
    def start_fetch_thread(self):
        selected = self.account_var.get()
        if not selected:
            return
            
        self.fetch_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        self.hostname_status.config(text="Fetching domains... please wait.", foreground="blue")
        
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        switch_key = self.account_map[selected]
        threading.Thread(target=self.fetch_hostnames, args=(switch_key,), daemon=True).start()

    def fetch_hostnames(self, switch_key):
        auth_flags = self.get_auth_flags()
        
        # Dynamically append auth flags if they exist
        command = f"Get-PropertyHostname -AccountSwitchKey {switch_key} -Network PRODUCTION{auth_flags} | Select-Object cnameFrom, productionCertType, productionCnameTo, propertyName | ConvertTo-Json"
        
        try:
            data = self.run_powershell(command)
            self.root.after(0, self.update_table_ui, data)
        except Exception as e:
            self.root.after(0, self.show_error, "hostname_status", str(e), self.fetch_btn)

    def update_table_ui(self, data):
        self.fetch_btn.config(state=tk.NORMAL)
        
        if not data:
            self.hostname_status.config(text="No hostnames found.", foreground="red")
            return
            
        self.hostname_status.config(text=f"Loaded {len(data)} hostnames.", foreground="green")
        
        for item in data:
            self.tree.insert("", tk.END, values=(
                item.get("cnameFrom", "-"),
                item.get("productionCertType", "-"),
                item.get("productionCnameTo", "-"),
                item.get("propertyName", "-")
            ))
            
        self.export_btn.config(state=tk.NORMAL)

    # --- Export Logic ---
    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Hostnames as CSV"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Hostname", "CertType", "EdgeHostname", "PropertyName"])
                
                for row_id in self.tree.get_children():
                    row_data = self.tree.item(row_id)['values']
                    writer.writerow(row_data)
                    
            messagebox.showinfo("Success", f"Data successfully exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def show_error(self, status_label, error_msg, button_to_enable):
        label = getattr(self, status_label)
        label.config(text="Error occurred (see popup)", foreground="red")
        button_to_enable.config(state=tk.NORMAL)
        messagebox.showerror("Execution Error", error_msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = AkamaiApp(root)
    root.mainloop()