# José Naim Tool

Python app wrapped around Akamai PowerShell module, for easily search your Akamai accounts, retrieve production hostnames, and export the results to a CSV file.


## Prerequisites

1. **PowerShell Core (`pwsh`)**: Must be installed and accessible via your system's PATH.
2. **Akamai PowerShell Module**: Installed in your PowerShell environment (`Install-Module -Name Akamai`).
3. **Akamai Credentials**: A valid `.edgerc` file configured in your user directory with the necessary API credentials to access Property Manager (PAPI) and Identity & Access Management.

## Python Dependencies

This script is built entirely using Python's standard library. There are no external `pip` packages required to run the source code.

**Standard Libraries Used:**
* `tkinter` (GUI framework)
* `subprocess` (PowerShell execution)
* `json` (Data parsing)
* `csv` (Export functionality)
* `threading` (Asynchronous UI loading)


## How to Run Locally

1. Clone or download this repository.
2. Open your terminal and navigate to the folder containing `josenaim.py`.
3. Run the script:
   ```bash
   python akamai_app.py