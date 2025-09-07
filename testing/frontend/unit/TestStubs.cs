// Test-only stubs to allow unit tests to compile without requiring full Office / WebView2 runtime.
// These are intentionally minimal and live in the FinLiteTests.Unit.Stubs namespace to avoid conflicts.

#if NET8_0_OR_GREATER
namespace Microsoft.Office.Core
{
    // Minimal copy of enum needed by tests
    public enum MsoCTPDockPosition
    {
        msoCTPDockPositionLeft = 0,
        msoCTPDockPositionTop = 1,
        msoCTPDockPositionRight = 2,
        msoCTPDockPositionBottom = 3,
        msoCTPDockPositionFloating = 4
    }
}
#endif

namespace FinLiteTests.Unit.Stubs
{
    using System;
    using System.Threading.Tasks;

    public interface IBackendService
    {
        Task EnsureStartedAsync();
        void Stop();
        Task<bool> IsHealthyAsync(TimeSpan timeout);
        Task<bool> InitializeWorkbookAsync(string path);
    }

    public interface IExcelRange
    {
        string Address { get; }
        object[,] GetValues();
    }

    public interface IExcelWorkbook
    {
        string FullName { get; }
    }

    public interface IExcelApplication
    {
        IExcelRange Selection { get; }
        event EventHandler SelectionChange;
        event EventHandler WorkbookOpen;
    }

    public interface IWebView2Pane : IDisposable
    {
        void SendSelection(string address, object[,] values);
        void NotifyWorkbookInitialized(string path);
        void ShowError(string message);
    }

    public interface IHttpClientWrapper : IDisposable
    {
        Task<System.Net.Http.HttpResponseMessage> GetAsync(string endpoint);
        Task<System.Net.Http.HttpResponseMessage> PostAsync(string endpoint, string content);
    }

    public interface IWebView2Core
    {
        void PostWebMessageAsJson(string message);
        void Navigate(string uri);
        void NavigateToString(string htmlContent);
        string Source { get; set; }
        bool IsEnabled { get; set; }
    }
}
