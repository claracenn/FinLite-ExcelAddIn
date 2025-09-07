using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using Office = Microsoft.Office.Core;
using Microsoft.Office.Tools;
using System.Windows.Forms;
using Excel = Microsoft.Office.Interop.Excel;
using Microsoft.Win32;

namespace ExcelAddIn
{
    public partial class ThisAddIn
    {
        private const int InitialPaneWidth = 750;
        private CustomTaskPane _pane;
        private WebView2Pane _control;

        // Public properties for Ribbon access
        public CustomTaskPane TaskPane => _pane;
        public WebView2Pane WebView2Control => _control;

        private async void ThisAddIn_Startup(object sender, System.EventArgs e)
        {
            try
            {
                Trace.WriteLine("[FinLite] Add-in startup begin");
                _control = new WebView2Pane();
                _pane = this.CustomTaskPanes.Add(_control, "FinLite");
                _pane.Visible = true;

                Trace.WriteLine("[FinLite] Starting backend service");
                await BackendService.EnsureStartedAsync();

                _pane.DockPosition = Office.MsoCTPDockPosition.msoCTPDockPositionRight;
                if (_pane.Width < InitialPaneWidth)
                    _pane.Width = InitialPaneWidth;

                await System.Threading.Tasks.Task.Delay(200);
                try { if (_pane.Width < InitialPaneWidth) _pane.Width = InitialPaneWidth; } catch { }

                Application.SheetSelectionChange += OnSelectionChange;
                Application.WorkbookActivate += OnWorkbookActivate;

                try
                {
                    var sel = Application.Selection as Excel.Range;
                    SendSelectionToPane(sel);
                }
                catch (Exception ex)
                {
                    Trace.WriteLine($"[FinLite][Error] Failed sending initial selection: {ex}");
                }

                var wb = Application.ActiveWorkbook;
                if (wb != null && !string.IsNullOrWhiteSpace(wb.FullName))
                {
                    try
                    {
                        var path = wb.FullName;
                        var ok = !string.IsNullOrWhiteSpace(path) && File.Exists(path);
                        var ext = ok ? Path.GetExtension(path)?.ToLowerInvariant() : string.Empty;
                        var extOk = ext == ".xlsx" || ext == ".xlsm";
                        if (ok && extOk)
                        {
                            Trace.WriteLine($"[FinLite] Initializing workbook: {path}");
                            await _control.InitializeWorkbookAsync(path);
                        }
                        else
                        {
                            Trace.WriteLine($"[FinLite] Skip auto-initialize. PathExists={ok}, Ext={ext}");
                        }
                    }
                    catch (Exception ex2)
                    {
                        Trace.WriteLine($"[FinLite][Error] Init workbook guard failed: {ex2}");
                    }
                }
                Trace.WriteLine("[FinLite] Add-in startup complete");
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"[FinLite][Error] Add-in startup error: {ex}");
                MessageBox.Show("FinLite add-in failed to load:\n" + ex.Message, "FinLite", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
        private void ThisAddIn_Shutdown(object sender, System.EventArgs e)
        {
            try
            {
                Application.SheetSelectionChange -= OnSelectionChange;
                Application.WorkbookActivate -= OnWorkbookActivate;
                BackendService.Stop();
                
                if (ShouldCleanupLocalData())
                {
                    Trace.WriteLine("[FinLite] Cleaning up local data during shutdown");
                    BackendService.CleanupLocalData();
                }
                
                Trace.WriteLine("[FinLite] Add-in shutdown complete");
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"[FinLite][Error] Add-in shutdown error: {ex}");
            }
        }

        private bool ShouldCleanupLocalData()
        {
            try
            {
                var flagPath = Path.Combine(Path.GetTempPath(), "FinLite_Cleanup.flag");
                if (File.Exists(flagPath))
                {
                    Trace.WriteLine("[FinLite] Cleanup flag found, proceeding with data cleanup");
                    try { File.Delete(flagPath); } catch { }
                    return true;
                }

                var currentDir = AppDomain.CurrentDomain.BaseDirectory;
                var tempPaths = new[] { 
                    Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData) + "\\Temp",
                    Path.GetTempPath(),
                    Environment.GetEnvironmentVariable("TEMP"),
                    Environment.GetEnvironmentVariable("TMP")
                };
                
                bool isInTempDir = tempPaths.Any(temp => !string.IsNullOrEmpty(temp) && 
                    currentDir.StartsWith(temp, StringComparison.OrdinalIgnoreCase));
                
                if (isInTempDir)
                {
                    var msiProcesses = Process.GetProcessesByName("msiexec");
                    var setupProcesses = Process.GetProcessesByName("setup");
                    
                    if (msiProcesses.Length > 0 || setupProcesses.Length > 0)
                    {
                        Trace.WriteLine("[FinLite] Running from temp directory during installer process, proceeding with cleanup");
                        return true;
                    }
                }

                return false;
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"[FinLite] Error checking cleanup conditions: {ex.Message}");
                return false;
            }
        }

        private async void OnWorkbookActivate(Excel.Workbook wb)
        {
            if (wb != null && !string.IsNullOrWhiteSpace(wb.FullName))
            {
                await _control.InitializeWorkbookAsync(wb.FullName);
            }
        }

        private void OnSelectionChange(object sh, Excel.Range target)
        {
            SendSelectionToPane(target);
        }

        private void SendSelectionToPane(Excel.Range target)
        {
            if (_control == null || target == null) return;

            var sb = new StringBuilder();
            bool any = false;

            int rows = Math.Min(target.Rows.Count, 1000);
            int cols = Math.Min(target.Columns.Count, 50);

            for (int i = 1; i <= rows; i++)
            {
                var row = new string[cols];
                for (int j = 1; j <= cols; j++)
                {
                    var txt = ((Excel.Range)target.Cells[i, j])?.Text?.ToString() ?? "";
                    if (!string.IsNullOrWhiteSpace(txt)) any = true;
                    row[j - 1] = txt;
                }
                sb.AppendLine(string.Join("\t", row));
            }

            _control.SendSelection(any ? sb.ToString().TrimEnd() : "");
        }

        private void InternalStartup()
        {
            this.Startup += new System.EventHandler(ThisAddIn_Startup);
            this.Shutdown += new System.EventHandler(ThisAddIn_Shutdown);
        }
    }
}