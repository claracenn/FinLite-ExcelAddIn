using System;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using Newtonsoft.Json.Linq;

namespace ExcelAddIn
{
    public class WebView2Pane : UserControl
    {
        private readonly WebView2 _web = new WebView2();
        private readonly HttpClient _http = new HttpClient { BaseAddress = new Uri("http://127.0.0.1:8000") };
        private string _lastSelection = "";

        public WebView2Pane()
        {
            Dock = DockStyle.Fill;
            Controls.Add(_web);
            _web.Dock = DockStyle.Fill;
            _ = InitAsync();
        }

        private async Task InitAsync()
        {
            try
            {
                var dataRoot = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "FinLite", "WebView2UserData");
                Directory.CreateDirectory(dataRoot);

                var env = await CoreWebView2Environment.CreateAsync(null, dataRoot, null);
                await _web.EnsureCoreWebView2Async(env);

                var baseDir = AppDomain.CurrentDomain.BaseDirectory;
                var uiFolder = Path.Combine(baseDir, "ui");
                var index = Path.Combine(uiFolder, "index.html");
                if (!File.Exists(index))
                {
                    _web.CoreWebView2.NavigateToString("<h3>ui/index.html missing.</h3>");
                    return;
                }
                _web.CoreWebView2.SetVirtualHostNameToFolderMapping(
                    "app", uiFolder, CoreWebView2HostResourceAccessKind.Allow);

                _web.CoreWebView2.WebMessageReceived += OnWebMessage;
                _web.CoreWebView2.Navigate("https://app/index.html");
            }
            catch (Exception ex)
            {
                MessageBox.Show("WebView2 init failed:\n" + ex.Message,
                    "FinLite", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // JS -> .NET
        private async void OnWebMessage(object sender, CoreWebView2WebMessageReceivedEventArgs e)
        {
            JObject msg;
            try { msg = JObject.Parse(e.TryGetWebMessageAsString() ?? "{}"); }
            catch { return; }

            var type = (string)msg["type"];
            switch (type)
            {
                case "ask":
                    {
                        var prompt = (string)msg["prompt"] ?? "";
                        var verbosity = (string)msg["verbosity"] ?? "Concise";
                        await HandleAskAsync(prompt, verbosity);
                        break;
                    }
                case "help":
                    {
                        var help = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "help.html");
                        if (File.Exists(help))
                            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(help) { UseShellExecute = true });
                        else
                            PostToWeb(new JObject { ["type"] = "toast", ["message"] = "help.html not found" });
                        break;
                    }
                case "history":
                    {
                        try
                        {
                            var resp = await _http.GetAsync("/history?limit=5");
                            resp.EnsureSuccessStatusCode();
                            var json = await resp.Content.ReadAsStringAsync();
                            PostToWeb(new JObject {
                                ["type"] = "history-data",
                                ["items"] = JArray.Parse(json)
                            });
                        }
                        catch (Exception ex)
                        {
                            PostToWeb(new JObject { ["type"] = "history-error", ["message"] = ex.Message });
                        }
                        break;
                    }
                    case "history-item":
                    {
                        try
                        {
                            var id = (int?)msg["id"] ?? -1;
                            if (id < 0) throw new Exception("invalid id");
                            var resp = await _http.GetAsync($"/history/{id}");
                            resp.EnsureSuccessStatusCode();
                            var json = await resp.Content.ReadAsStringAsync();
                            PostToWeb(new JObject {
                                ["type"] = "history-item-data",
                                ["item"] = JObject.Parse(json)
                            });
                        }
                        catch (Exception ex)
                        {
                            PostToWeb(new JObject { ["type"] = "history-error", ["message"] = ex.Message });
                        }
                        break;
                    }
            }
        }

        private async Task HandleAskAsync(string prompt, string verbosity)
        {
            if (string.IsNullOrWhiteSpace(prompt))
            {
                PostToWeb(new JObject { ["type"] = "toast", ["message"] = "Prompt is empty." });
                return;
            }

            PostToWeb(new JObject { ["type"] = "thinking" });

            if (!await WaitBackendAsync(TimeSpan.FromSeconds(5)))
            {
                PostToWeb(new JObject { ["type"] = "error", ["message"] = "Backend not reachable." });
                return;
            }

            var effective = verbosity == "Concise"
                ? $"Please answer concisely: {prompt}"
                : $"Please answer detailedly: {prompt}";

            var payload = new JObject { 
                ["prompt"] = effective,
                ["detailed"] = verbosity != "Concise"
            };
            if (!string.IsNullOrWhiteSpace(_lastSelection))
                payload["snippets"] = new JArray(_lastSelection.Split('\n'));

            try
            {
                var content = new StringContent(payload.ToString(), Encoding.UTF8, "application/json");
                var resp = await _http.PostAsync("/chat", content);
                if (!resp.IsSuccessStatusCode)
                {
                    var body = await resp.Content.ReadAsStringAsync();
                    string detail = body;
                    try
                    {
                        var jo = JObject.Parse(body);
                        detail = jo["detail"]?.ToString() ?? body;
                    }
                    catch { }
                    throw new Exception($"Backend error {(int)resp.StatusCode}: {detail}");
                }
                var json = await resp.Content.ReadAsStringAsync();
                var answer = JObject.Parse(json)["response"]?.ToString() ?? "";
                int qidx = answer.IndexOf("Question:", StringComparison.OrdinalIgnoreCase);
                if (qidx >= 0) answer = answer.Substring(0, qidx).TrimEnd();

                PostToWeb(new JObject { ["type"] = "answer", ["text"] = answer });
            }
            catch (Exception ex)
            {
                PostToWeb(new JObject { ["type"] = "error", ["message"] = ex.Message });
            }
        }

        private async Task<bool> WaitBackendAsync(TimeSpan timeout)
        {
            var deadline = DateTime.UtcNow + timeout;
            while (DateTime.UtcNow < deadline)
            {
                try
                {
                    var ping = await _http.GetAsync("/health");
                    if (ping.IsSuccessStatusCode) return true;
                }
                catch { }
                await Task.Delay(300);
            }
            return false;
        }

        public async Task InitializeWorkbookAsync(string fullPath)
        {
            try
            {
                if (!await WaitBackendAsync(TimeSpan.FromSeconds(5)))
                {
                    PostToWeb(new JObject { ["type"] = "toast", ["message"] = "Backend not ready yet." });
                    return;
                }

                PostToWeb(new JObject { ["type"] = "toast", ["message"] = $"Loading workbook: {Path.GetFileName(fullPath)}" });

                var payload = new JObject { ["path"] = fullPath };
                var content = new StringContent(payload.ToString(), Encoding.UTF8, "application/json");
                var resp = await _http.PostAsync("/initialize", content);
                resp.EnsureSuccessStatusCode();

                var responseText = await resp.Content.ReadAsStringAsync();
                var responseJson = JObject.Parse(responseText);
                var snippetCount = responseJson["snippets"]?.Value<int>() ?? 0;

                PostToWeb(new JObject { ["type"] = "reset" });
            }
            catch (Exception ex)
            {
                PostToWeb(new JObject { ["type"] = "toast", ["message"] = $"Failed to load workbook: {ex.Message}" });
            }
        }

        public void SendSelection(string tsv)
        {
            _lastSelection = tsv ?? "";

            void send()
            {
                if (_web.CoreWebView2 == null)
                {
                    _ = Task.Delay(200).ContinueWith(_ => SendSelection(_lastSelection));
                    return;
                }
                PostToWeb(new JObject { ["type"] = "selection", ["text"] = _lastSelection });
            }

            if (_web.InvokeRequired) _web.BeginInvoke(new Action(send));
            else send();
        }

        private void PostToWeb(JObject obj)
        {
            var payload = obj.ToString();
            void doSend()
            {
                try { _web.CoreWebView2?.PostWebMessageAsString(payload); }
                catch { /* log if needed */ }
            }
            if (_web.InvokeRequired) _web.BeginInvoke(new Action(doSend));
            else doSend();
        }
    }
}
