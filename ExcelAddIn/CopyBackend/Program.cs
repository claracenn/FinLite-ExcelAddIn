using System;
using System.IO;

namespace CopyBackend
{
    class Program
    {
        static int Main(string[] args)
        {
            try
            {
                if (args == null || args.Length < 2)
                {
                    Log("[ERROR] Not enough args. Expect: <MSI_or_SourceDir> <InstallDir>");
                    return 2;
                }

                var rawA = args[0];
                var rawB = args[1];
                Log("[ARGS] A=" + rawA + " | B=" + rawB);

                string sourceRoot = TrimSlash(rawA);
                if (File.Exists(sourceRoot) &&
                    string.Equals(Path.GetExtension(sourceRoot), ".msi", StringComparison.OrdinalIgnoreCase))
                {
                    var msiDir = Path.GetDirectoryName(sourceRoot);
                    if (msiDir == null)
                    {
                        Log("[ERROR] Cannot resolve MSI directory from: " + sourceRoot);
                        return 4;
                    }
                    sourceRoot = TrimSlash(msiDir);
                    Log("[INFO] A is MSI file. Use its directory: " + sourceRoot);
                }

                string targetRoot = TrimSlash(rawB);

                string src = Path.Combine(sourceRoot, "backend");
                string dst = Path.Combine(targetRoot, "backend");

                Log("[RESOLVED] src=" + src);
                Log("[RESOLVED] dst=" + dst);

                if (!Directory.Exists(src))
                {
                    Log("[ERROR] Source backend not found: " + src);
                    return 3;
                }

                CopyDirectory(src, dst);
                Log("[OK] Copied backend => " + dst);
                return 0;
            }
            catch (Exception ex)
            {
                Log("[ERROR] " + ex);
                return 1;
            }
        }

        static void CopyDirectory(string sourceDir, string destDir)
        {
            Directory.CreateDirectory(destDir);

            string[] allDirs = Directory.GetDirectories(sourceDir, "*", SearchOption.AllDirectories);
            for (int i = 0; i < allDirs.Length; i++)
            {
                string dir = allDirs[i];
                string rel = dir.Substring(sourceDir.Length).TrimStart(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                Directory.CreateDirectory(Path.Combine(destDir, rel));
            }

            string[] allFiles = Directory.GetFiles(sourceDir, "*", SearchOption.AllDirectories);
            for (int i = 0; i < allFiles.Length; i++)
            {
                string file = allFiles[i];
                string rel = file.Substring(sourceDir.Length).TrimStart(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                string dst = Path.Combine(destDir, rel);
                string parent = Path.GetDirectoryName(dst);
                if (parent != null) Directory.CreateDirectory(parent);
                File.Copy(file, dst, true);
            }
        }

        static string TrimSlash(string p)
        {
            if (p == null) return string.Empty;
            p = p.Trim().Trim('"');
            while (p.EndsWith("\\") || p.EndsWith("/"))
                p = p.Substring(0, p.Length - 1);
            return p;
        }

        static void Log(string msg)
        {
            try
            {
                string log = Path.Combine(Path.GetTempPath(), "CopyBackend.log");
                File.AppendAllText(log, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss ") + msg + Environment.NewLine);
            }
            catch
            {
            }
        }
    }
}
