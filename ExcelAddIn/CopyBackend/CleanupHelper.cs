using System;
using System.Diagnostics;
using System.IO;

namespace CopyBackend
{
    public static class CleanupHelper
    {
        public static void CreateCleanupFlag()
        {
            try
            {
                var flagPath = Path.Combine(Path.GetTempPath(), "FinLite_Cleanup.flag");
                File.WriteAllText(flagPath, DateTime.UtcNow.ToString("O"));
                Console.WriteLine($"Created cleanup flag: {flagPath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error creating cleanup flag: {ex.Message}");
            }
        }

        public static void PerformCleanup()
        {
            try
            {
                var finLiteDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "FinLite");
                if (Directory.Exists(finLiteDir))
                {
                    Console.WriteLine($"Cleaning up FinLite data directory: {finLiteDir}");
                    
                    // Wait a moment for any running processes to close
                    System.Threading.Thread.Sleep(2000);
                    
                    try
                    {
                        Directory.Delete(finLiteDir, true);
                        Console.WriteLine("Successfully cleaned up FinLite data");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error during cleanup: {ex.Message}");
                        // Try to clean up individual files if directory deletion fails
                        CleanupDirectoryContents(finLiteDir);
                    }
                }
                else
                {
                    Console.WriteLine("No FinLite data directory found");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error during FinLite cleanup: {ex.Message}");
            }
        }

        private static void CleanupDirectoryContents(string dirPath)
        {
            try
            {
                if (!Directory.Exists(dirPath)) return;

                // Delete all files
                foreach (var file in Directory.GetFiles(dirPath, "*", SearchOption.AllDirectories))
                {
                    try
                    {
                        File.SetAttributes(file, FileAttributes.Normal);
                        File.Delete(file);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Failed to delete file {file}: {ex.Message}");
                    }
                }

                // Delete all directories
                var dirs = Directory.GetDirectories(dirPath, "*", SearchOption.AllDirectories);
                Array.Sort(dirs, (a, b) => b.Length.CompareTo(a.Length)); // Sort by length descending
                
                foreach (var dir in dirs)
                {
                    try
                    {
                        Directory.Delete(dir, false);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Failed to delete directory {dir}: {ex.Message}");
                    }
                }

                // Finally try to delete the root directory
                try
                {
                    Directory.Delete(dirPath, false);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to delete root directory {dirPath}: {ex.Message}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error during directory contents cleanup: {ex.Message}");
            }
        }
    }
}
