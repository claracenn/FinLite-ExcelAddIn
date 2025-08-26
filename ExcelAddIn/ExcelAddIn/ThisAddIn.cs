using System;
using System.Text;
using Office = Microsoft.Office.Core;
using Microsoft.Office.Tools;
using System.Windows.Forms;
using Excel = Microsoft.Office.Interop.Excel;

namespace ExcelAddIn
{
    public partial class ThisAddIn
    {
        private const int InitialPaneWidth = 750;
        private CustomTaskPane _pane;
        private WebView2Pane _control;

        private async void ThisAddIn_Startup(object sender, System.EventArgs e)
        {
            _control = new WebView2Pane();
            _pane = this.CustomTaskPanes.Add(_control, "FinLite");
            _pane.Visible = true;

            // Ensure backend is running (spawns run_server.exe if needed)
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
            catch { /* ignore */ }

            var wb = Application.ActiveWorkbook;
            if (wb != null && !string.IsNullOrWhiteSpace(wb.FullName))
                await _control.InitializeWorkbookAsync(wb.FullName);
        }
        private void ThisAddIn_Shutdown(object sender, System.EventArgs e)
        {
            Application.SheetSelectionChange -= OnSelectionChange;
            Application.WorkbookActivate -= OnWorkbookActivate;
            BackendService.Stop();
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