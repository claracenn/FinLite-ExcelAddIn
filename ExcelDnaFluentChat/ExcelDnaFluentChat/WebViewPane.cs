using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace ExcelDnaFluentChat
{
    public record JsMessage(string Type, JsonElement Payload);

    public class WebViewPane : UserControl
    {
        private readonly WebView2 _wv = new WebView2();
        private TaskCompletionSource<bool>? _readyTcs;

        public event EventHandler? Ready;
        public event EventHandler<JsMessage>? OnMessageFromJs;

        public WebViewPane()
        {
            Dock = DockStyle.Fill;
            _wv.Dock = DockStyle.Fill;
            Controls.Add(_wv);

            // ��Ҫ�ڹ������첽��ʼ��
            Load += OnLoadAsync;
        }

        private async void OnLoadAsync(object? sender, EventArgs e)
        {
            try
            {
                _readyTcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

                // ָ����д���û�����Ŀ¼���������/Ȩ������
                var userData = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "ExcelDnaFluentChat", "WebView2");

                var env = await CoreWebView2Environment.CreateAsync(
                    browserExecutableFolder: null,
                    userDataFolder: userData,
                    options: null);

                await _wv.EnsureCoreWebView2Async(env);

                _wv.CoreWebView2.Settings.AreDevToolsEnabled = true;
                _wv.CoreWebView2.WebMessageReceived += CoreWebView2_WebMessageReceived;

                var exeDir = AppDomain.CurrentDomain.BaseDirectory;
                var uiPath = Path.Combine(exeDir, "ui", "index.html");
                _wv.Source = new Uri(Path.GetFullPath(uiPath));

                _wv.NavigationCompleted += (_, __) =>
                {
                    _readyTcs?.TrySetResult(true);
                    Ready?.Invoke(this, EventArgs.Empty);
                };
            }
            catch (Exception ex)
            {
                // ������Ҳ���Խ������׸��ϲ㣬�򵯳� MessageBox
                MessageBox.Show("WebView2 ��ʼ��ʧ��: " + ex.Message, "Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                _readyTcs?.TrySetException(ex);
            }
        }

        private void CoreWebView2_WebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                using var doc = JsonDocument.Parse(e.WebMessageAsJson);
                var root = doc.RootElement;
                var type = root.TryGetProperty("type", out var t) ? (t.GetString() ?? "") : "";
                var payload = root.TryGetProperty("payload", out var p) ? p : default;
                OnMessageFromJs?.Invoke(this, new JsMessage(type, payload));
            }
            catch
            {
                // ���Խ����쳣������Ӱ������
            }
        }

        public async Task PostToJsAsync(object obj)
        {
            // ȷ������ɳ�ʼ��/����
            if (_readyTcs != null) await _readyTcs.Task;

            var json = JsonSerializer.Serialize(obj);
            _wv.CoreWebView2.PostWebMessageAsJson(json);
        }
    }
}
