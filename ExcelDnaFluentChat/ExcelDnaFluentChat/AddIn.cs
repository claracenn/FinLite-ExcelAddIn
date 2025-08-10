using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using ExcelDna.Integration;
using ExcelDna.Integration.CustomUI;
using Excel = Microsoft.Office.Interop.Excel;

namespace ExcelDnaFluentChat
{
    public class AddIn : IExcelAddIn
    {
        private CustomTaskPane? _pane;
        private WebViewPane? _view;
        private Excel.Application _app => (Excel.Application)ExcelDnaUtil.Application;
        private readonly HttpClient _http = new HttpClient { BaseAddress = new Uri("http://127.0.0.1:8000") };

        public void AutoOpen()
        {
            _view = new WebViewPane();
            _view.OnMessageFromJs += HandleJsMessage;
            _pane = CustomTaskPaneFactory.CreateCustomTaskPane(_view, "AI Assistant");
            _pane.Width = 520; _pane.Visible = true;

            // Wire Excel selection change -> push to UI
            _app.SheetSelectionChange += OnSheetSelectionChange;
            // Send initial selection once UI is loaded
            _view.Ready += (_, __) => PushSelectionAsync().ConfigureAwait(false);
        }

        public void AutoClose()
        {
            try { _app.SheetSelectionChange -= OnSheetSelectionChange; } catch { }
            _view?.Dispose();
        }

        private void OnSheetSelectionChange(object sh, Excel.Range target)
        {
            _ = PushSelectionAsync();
        }

        private async Task PushSelectionAsync()
        {
            try
            {
                var sel = (Excel.Range)_app.Selection;
                if (sel == null) return;

                object[,]? values = sel.Value2 as object[,];
                string text;
                if (values == null)
                {
                    text = sel.Value2?.ToString() ?? string.Empty;
                }
                else
                {
                    // Convert to TSV preview (cap length)
                    int r1 = values.GetLowerBound(0), r2 = values.GetUpperBound(0);
                    int c1 = values.GetLowerBound(1), c2 = values.GetUpperBound(1);
                    var lines = Enumerable.Range(r1, r2 - r1 + 1).Select(r =>
                        string.Join("\t", Enumerable.Range(c1, c2 - c1 + 1).Select(c => values[r, c]?.ToString() ?? string.Empty)));
                    text = string.Join("\n", lines);
                    if (text.Length > 4000) text = text.Substring(0, 4000) + "\n…";
                }
                await _view!.PostToJsAsync(new { type = "selection", text });
            }
            catch (Exception ex)
            {
                await _view!.PostToJsAsync(new { type = "error", message = ex.Message });
            }
        }

        private async void HandleJsMessage(object? sender, JsMessage e)
        {
            if (e.Type == "ask")
            {
                await AskBackendAndReplyAsync(e.Payload);
            }
            else if (e.Type == "help")
            {
                await _view!.PostToJsAsync(new { type = "answer", text = "Open the ? menu for tips. Backend: POST /chat on 127.0.0.1:8000." });
            }
        }

        private async Task AskBackendAndReplyAsync(JsonElement payload)
        {
            try
            {
                string prompt = payload.GetProperty("prompt").GetString() ?? string.Empty;
                string verbosity = payload.TryGetProperty("verbosity", out var v) ? v.GetString() ?? "Concise" : "Concise";

                var body = JsonSerializer.Serialize(new { prompt, snippets = (string[]?)null, verbosity });
                var resp = await _http.PostAsync("/chat", new StringContent(body, Encoding.UTF8, "application/json"));
                resp.EnsureSuccessStatusCode();
                using var s = await resp.Content.ReadAsStreamAsync();
                var doc = await JsonDocument.ParseAsync(s);
                string answer = doc.RootElement.GetProperty("response").GetString() ?? "";
                // Optionally tailor by verbosity on client if backend ignores it
                if (verbosity.Equals("Concise", StringComparison.OrdinalIgnoreCase) && answer.Length > 1200)
                    answer = answer.Substring(0, 1200) + "\n\n(Truncated for concise mode.)";

                await _view!.PostToJsAsync(new { type = "answer", text = answer });
            }
            catch (Exception ex)
            {
                await _view!.PostToJsAsync(new { type = "error", message = ex.Message });
            }
        }
    }
}
