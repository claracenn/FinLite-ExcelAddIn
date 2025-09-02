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
        private readonly HttpClient _http = new HttpClient 
        { 
            BaseAddress = new Uri("http://127.0.0.1:8000"),
            Timeout = TimeSpan.FromMinutes(5)
        };
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
                        var sessionId = (string)msg["session_id"] ?? "";
                        await HandleAskAsync(prompt, verbosity, sessionId);
                        break;
                    }
                case "help":
                    {
                        var help = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ui", "help.html");
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
                            var resp = await _http.GetAsync("/history/unified?limit=10");
                            if (!resp.IsSuccessStatusCode)
                            {
                                resp = await _http.GetAsync("/history/grouped?limit=10");
                                if (!resp.IsSuccessStatusCode)
                                {
                                    var last = await _http.GetAsync("/history?limit=50");
                                    last.EnsureSuccessStatusCode();
                                    var jsonFlat = await last.Content.ReadAsStringAsync();
                                    var flat = JArray.Parse(jsonFlat);
                                    var bySession = new System.Collections.Generic.Dictionary<string, JObject>(StringComparer.OrdinalIgnoreCase);
                                    foreach (var it in flat)
                                    {
                                        var o = it as JObject; if (o == null) continue;
                                        var sid = o.Value<string>("session_id") ?? string.Empty;
                                        if (!bySession.TryGetValue(sid, out var agg))
                                        {
                                            agg = new JObject
                                            {
                                                ["session_id"] = sid,
                                                ["first_prompt"] = o.Value<string>("prompt") ?? "New Chat",
                                                ["last_timestamp"] = o.Value<string>("timestamp") ?? string.Empty,
                                                ["turns"] = 1
                                            };
                                            bySession[sid] = agg;
                                        }
                                        else
                                        {
                                            agg["turns"] = agg.Value<int>("turns") + 1;
                                            var ts = o.Value<string>("timestamp") ?? string.Empty;
                                            if (!string.IsNullOrEmpty(ts)) agg["last_timestamp"] = ts;
                                        }
                                    }
                                    var normFromFlat = new JArray();
                                    foreach (var kv in bySession.Values)
                                    {
                                        normFromFlat.Add(new JObject
                                        {
                                            ["session_id"] = kv.Value<string>("session_id") ?? string.Empty,
                                            ["title"] = kv.Value<string>("first_prompt") ?? "New Chat",
                                            ["timestamp"] = kv.Value<string>("last_timestamp") ?? string.Empty,
                                            ["turns"] = kv.Value<int?>("turns") ?? 1
                                        });
                                    }
                                    PostToWeb(new JObject { ["type"] = "history-data", ["items"] = normFromFlat });
                                    break;
                                }

                                var jsonGrouped = await resp.Content.ReadAsStringAsync();
                                var grouped = JArray.Parse(jsonGrouped);
                                var normFromGrouped = new JArray();
                                foreach (var item in grouped)
                                {
                                    var o = item as JObject; if (o == null) continue;
                                    normFromGrouped.Add(new JObject
                                    {
                                        ["session_id"] = o.Value<string>("session_id") ?? string.Empty,
                                        ["title"] = o.Value<string>("first_prompt") ?? "New Chat",
                                        ["timestamp"] = o.Value<string>("last_timestamp") ?? string.Empty,
                                        ["turns"] = o.Value<int?>("turns") ?? 1
                                    });
                                }
                                PostToWeb(new JObject { ["type"] = "history-data", ["items"] = normFromGrouped });
                                break;
                            }

                            resp.EnsureSuccessStatusCode();
                            var json = await resp.Content.ReadAsStringAsync();
                var arr = JArray.Parse(json);
                            var norm = new JArray();
                            foreach (var item in arr)
                            {
                                var o = item as JObject;
                                if (o == null) continue;
                                norm.Add(new JObject
                                {
                                    ["session_id"] = o.Value<string>("session_id") ?? string.Empty,
                    ["first_prompt"] = o.Value<string>("first_prompt") ?? "New Chat",
                    ["title"] = o.Value<string>("first_prompt") ?? "New Chat",
                                    ["timestamp"] = o.Value<string>("last_timestamp") ?? string.Empty,
                                    ["turns"] = o.Value<int?>("turns") ?? 1
                                });
                            }
                            PostToWeb(new JObject { ["type"] = "history-data", ["items"] = norm });
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
                            var sid = (string)msg["session_id"] ?? string.Empty;
                            HttpResponseMessage resp;
                            if (!string.IsNullOrWhiteSpace(sid))
                            {
                                var content = new StringContent(new JObject { ["session_id"] = sid }.ToString(), Encoding.UTF8, "application/json");
                                try
                                {
                                    resp = await _http.PostAsync("/history/open", content);
                                }
                                catch
                                {
                                    resp = new HttpResponseMessage(System.Net.HttpStatusCode.NotFound);
                                }
                                if (!resp.IsSuccessStatusCode)
                                {
                                    var getResp = await _http.GetAsync($"/history/session/{sid}");
                                    getResp.EnsureSuccessStatusCode();
                                    var js = await getResp.Content.ReadAsStringAsync();
                                    JToken parsed;
                                    try { parsed = JObject.Parse(js); }
                                    catch { parsed = new JObject { ["items"] = JArray.Parse(js) }; }
                                    PostToWeb(new JObject { ["type"] = "history-item-data", ["item"] = parsed });
                                    break;
                                }
                            }
                            else
                            {
                                var id = (int?)msg["id"] ?? -1;
                                if (id < 0) throw new Exception("invalid id");
                                var content = new StringContent(new JObject { ["id"] = id }.ToString(), Encoding.UTF8, "application/json");
                                try
                                {
                                    resp = await _http.PostAsync("/history/open", content);
                                }
                                catch
                                {
                                    resp = new HttpResponseMessage(System.Net.HttpStatusCode.NotFound);
                                }
                                if (!resp.IsSuccessStatusCode)
                                {
                                    var getResp = await _http.GetAsync($"/history/{id}");
                                    getResp.EnsureSuccessStatusCode();
                                    var js = await getResp.Content.ReadAsStringAsync();
                                    JToken parsed;
                                    try { parsed = JObject.Parse(js); }
                                    catch { parsed = new JObject { ["item"] = JToken.Parse(js) }; }
                                    PostToWeb(new JObject { ["type"] = "history-item-data", ["item"] = parsed });
                                    break;
                                }
                            }
                            resp.EnsureSuccessStatusCode();
                            var json2 = await resp.Content.ReadAsStringAsync();
                            PostToWeb(new JObject {
                                ["type"] = "history-item-data",
                                ["item"] = JObject.Parse(json2)
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

        private async Task HandleAskAsync(string prompt, string verbosity, string sessionId)
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
                ["detailed"] = verbosity != "Concise",
                ["session_id"] = sessionId ?? string.Empty
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
                    PostToWeb(new JObject { ["type"] = "toast", ["message"] = $"Initialize failed ({(int)resp.StatusCode}): {detail}" });
                    return;
                }

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
