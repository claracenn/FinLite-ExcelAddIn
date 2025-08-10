using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace YourAddInNamespace.Services
{
    public class ChatService
    {
        private readonly HttpClient _http;

        public ChatService(string baseUrl = "http://127.0.0.1:8000")
        {
            _http = new HttpClient { BaseAddress = new Uri(baseUrl) };
        }

        public HttpClient HttpClient => _http;

        public async Task InitializeWorkbookAsync(string workbookFullPath)
        {
            var payload = new JObject { ["path"] = workbookFullPath };
            var content = new StringContent(payload.ToString(), Encoding.UTF8, "application/json");
            var resp = await _http.PostAsync("/initialize", content);
            resp.EnsureSuccessStatusCode();
        }

        public async Task<string> AskAsync(string prompt, IEnumerable<string> snippets = null)
        {
            // 确保 BaseAddress 正确
            _http.BaseAddress = new Uri(_http.BaseAddress?.ToString() ?? "http://127.0.0.1:8000");

            // 等待后端启动并可用
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(60);
            while (DateTime.UtcNow < deadline)
            {
                try
                {
                    var ping = await _http.GetAsync("/health");
                    if (ping.IsSuccessStatusCode)
                        break;
                }
                catch
                {
                }
                await Task.Delay(200);
            }

            // 构造请求 JSON
            var payload = new JObject { ["prompt"] = prompt };
            if (snippets != null && snippets.Any())
            {
                payload["snippets"] = new JArray(snippets);
            }

            var content = new StringContent(
                payload.ToString(),
                Encoding.UTF8,
                "application/json"
            );

            // 调用后端 /chat
            var resp = await _http.PostAsync("/chat", content);
            resp.EnsureSuccessStatusCode();
            var json = await resp.Content.ReadAsStringAsync();
            var raw = JObject.Parse(json)["response"]?.ToString() ?? "";

            // 如果后端返回中包含 “Answer:”，截取其后的内容
            const string marker = "Answer:";
            var idx = raw.LastIndexOf(marker, StringComparison.OrdinalIgnoreCase);
            if (idx >= 0)
            {
                return raw.Substring(idx + marker.Length).Trim();
            }
            return raw.Trim();
        }
    }
}
