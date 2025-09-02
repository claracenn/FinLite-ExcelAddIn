using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace ExcelAddIn
{
    internal static class BackendService
    {
        private static readonly object _gate = new object();
        private static Process _proc;
        private static readonly Uri _baseUri = new Uri("http://127.0.0.1:8000");

    public static async Task EnsureStartedAsync()
        {
            try
            {
        // Probe for an already-running backend before spawning
        if (await IsHealthyAsync(TimeSpan.FromSeconds(2))) return;

                lock (_gate)
                {
                    if (_proc != null && !_proc.HasExited) return;

                    var baseDir = AppDomain.CurrentDomain.BaseDirectory;
                    var backendDir = Path.Combine(baseDir, "backend");
                    Trace.WriteLine($"[FinLite] EnsureStarted: baseDir={baseDir}, backendDir={backendDir}");

                    string exePath = null;
                    var candidates = new[]
                    {
                        Path.Combine(backendDir, "run_server.exe"),
                        Path.Combine(backendDir, "build", "run_server", "run_server.dist", "run_server.exe"),
                        Path.Combine(backendDir, "run_server", "run_server.exe"),
                    };
                    foreach (var c in candidates)
                    {
                        if (File.Exists(c)) { exePath = c; Trace.WriteLine($"[FinLite] Found backend exe: {exePath}"); break; }
                    }

                    if (exePath == null)
                    {
                        // Fallback: try python runner if present
                        var pyExe = Path.Combine(backendDir, "pyembed", "python.exe");
                        var runPy = Path.Combine(backendDir, "app", "run_server.py");
                        Trace.WriteLine($"[FinLite] Backend exe not found. Trying python fallback: py={pyExe}, script={runPy}");
                        if (File.Exists(pyExe) && File.Exists(runPy))
                        {
                            var psiPy = new ProcessStartInfo
                            {
                                FileName = pyExe,
                                Arguments = Quote(runPy),
                                WorkingDirectory = backendDir,
                                UseShellExecute = false,
                                CreateNoWindow = true,
                                RedirectStandardOutput = true,
                                RedirectStandardError = true,
                            };
                            _proc = Process.Start(psiPy);
                            HookLogs(_proc);
                            Trace.WriteLine("[FinLite] Started backend via embedded python");
                        }
                        else
                        {
                            Trace.WriteLine("[FinLite][Error] No backend executable or python fallback found. Ensure backend is copied to ExcelAddIn/backend.");
                        }
                    }
                    else
                    {
                        var psi = new ProcessStartInfo
                        {
                            FileName = exePath,
                            WorkingDirectory = Path.GetDirectoryName(exePath) ?? backendDir,
                            UseShellExecute = false,
                            CreateNoWindow = true,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true,
                        };
                        _proc = Process.Start(psi);
                        HookLogs(_proc);
            Trace.WriteLine($"[FinLite] Started backend exe: {exePath}");
                    }
                }

                // Wait for health
                var healthy = await IsHealthyAsync(TimeSpan.FromSeconds(15));
        Trace.WriteLine($"[FinLite] Backend health: {healthy}");
            }
            catch (Exception ex)
            {
        Trace.WriteLine($"[FinLite][Error] EnsureStartedAsync error: {ex}");
                throw;
            }
        }

    public static void Stop()
        {
            try
            {
                lock (_gate)
                {
                    if (_proc == null) return;
                    if (!_proc.HasExited)
                    {
                        try { _proc.CloseMainWindow(); } catch { }
                        try { if (!_proc.WaitForExit(1500)) _proc.Kill(); } catch { }
                    }
                    _proc.Dispose();
                    _proc = null;
                }

                // Kill by pid file as a safety net (if process handle was lost)
                try
                {
                    var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "FinLite", "logs");
                    var pidPath = Path.Combine(dir, "backend.pid");
                    if (File.Exists(pidPath))
                    {
                        var text = File.ReadAllText(pidPath).Trim();
                        if (int.TryParse(text, out var pid))
                        {
                            try
                            {
                                var p = Process.GetProcessById(pid);
                                if (!p.HasExited)
                                {
                                    try { p.CloseMainWindow(); } catch { }
                                    try { if (!p.WaitForExit(1000)) p.Kill(); } catch { }
                                }
                            }
                            catch { }
                        }
                        try { File.Delete(pidPath); } catch { }
                    }
                }
                catch { }
            }
            catch { }
        }

        private static async Task<bool> IsHealthyAsync(TimeSpan timeout)
        {
            try
            {
                using (var cts = new CancellationTokenSource(timeout))
                using (var http = new HttpClient() { BaseAddress = _baseUri })
                {
                    var deadline = DateTime.UtcNow + timeout;
                    while (DateTime.UtcNow < deadline)
                    {
                        try
                        {
                            var resp = await http.GetAsync("/health", cts.Token);
                            if (resp.IsSuccessStatusCode) return true;
                        }
                        catch { }
                        await Task.Delay(300, cts.Token);
                    }
                }
            }
            catch { }
            return false;
        }

        private static void HookLogs(Process p)
        {
            try
            {
                var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "FinLite", "logs");
                Directory.CreateDirectory(dir);
                var outLog = Path.Combine(dir, "backend.out.log");
                var errLog = Path.Combine(dir, "backend.err.log");
                p.OutputDataReceived += (_, e) => { if (e.Data != null) Append(outLog, e.Data); };
                p.ErrorDataReceived +=  (_, e) => { if (e.Data != null) Append(errLog, e.Data); };
                try { p.BeginOutputReadLine(); } catch { }
                try { p.BeginErrorReadLine(); } catch { }
                Trace.WriteLine($"[FinLite] Hooked backend logs: {outLog}, {errLog}");
            }
            catch { }
        }

        private static void Append(string path, string line)
        {
            try { File.AppendAllText(path, $"[{DateTime.Now:HH:mm:ss}] {line}{Environment.NewLine}"); } catch { }
        }

        private static string Quote(string s) => s.Contains(" ") ? $"\"{s}\"" : s;
    }
}
