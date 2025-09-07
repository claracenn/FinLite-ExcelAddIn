using System;
using System.IO;
using System.Threading.Tasks;
using NUnit.Framework;
using Moq;
using FluentAssertions;
using ExcelAddIn;
using System.Net.Http;
using System.Diagnostics;

namespace FinLiteTests.Unit
{
    [TestFixture]
    public class BackendServiceTests
    {
        private Mock<IProcessService> _mockProcessService;
        private Mock<IHttpService> _mockHttpService;
        private Mock<IFileService> _mockFileService;

        [SetUp]
        public void Setup()
        {
            _mockProcessService = new Mock<IProcessService>();
            _mockHttpService = new Mock<IHttpService>();
            _mockFileService = new Mock<IFileService>();
        }

        [Test]
        public async Task EnsureStartedAsync_CanBeCalledWithoutException()
        {
            // Test that EnsureStartedAsync can be called without throwing
            Assert.DoesNotThrowAsync(async () => await BackendService.EnsureStartedAsync());
        }

        [Test] 
        public void Stop_CanBeCalledWithoutException()
        {
            // Test that Stop() can be called without throwing
            Assert.DoesNotThrow(() => BackendService.Stop());
        }

        [Test]
        public void CleanupLocalData_CanBeCalledWithoutException()
        {
            // Test that CleanupLocalData() can be called without throwing
            Assert.DoesNotThrow(() => BackendService.CleanupLocalData());
        }

        [Test]
        public async Task EnsureStartedAsync_ThenStop_ShouldNotThrow()
        {
            // Test the typical lifecycle of start then stop
            Assert.DoesNotThrowAsync(async () => 
            {
                await BackendService.EnsureStartedAsync();
                BackendService.Stop();
            });
        }

        [Test]
        public async Task MultipleEnsureStartedAsync_ShouldNotThrow()
        {
            // Test that calling EnsureStartedAsync multiple times doesn't cause issues
            Assert.DoesNotThrowAsync(async () => 
            {
                await BackendService.EnsureStartedAsync();
                await BackendService.EnsureStartedAsync();
                await BackendService.EnsureStartedAsync();
            });
        }

        [Test]
        public void MultipleStop_ShouldNotThrow()
        {
            // Test that calling Stop multiple times doesn't cause issues
            Assert.DoesNotThrow(() => 
            {
                BackendService.Stop();
                BackendService.Stop();
                BackendService.Stop();
            });
        }
    }

    public interface IProcessService
    {
        bool IsProcessRunning(string processName);
        Process StartProcess(string fileName, string arguments);
        Process GetCurrentProcess();
    }

    public interface IHttpService
    {
        Task<bool> IsHealthyAsync(TimeSpan timeout);
    }

    public interface IFileService
    {
        bool FileExists(string path);
    }
}
