using System;
using System.Threading.Tasks;
using NUnit.Framework;
using Moq;
using FluentAssertions;
using ExcelAddIn;
using FinLiteTests.Unit.Stubs;
using System.Net.Http;
using System.Net;

namespace FinLiteTests.Unit
{
    [TestFixture]
    public class WebView2PaneTests
    {
        [Test]
        public void WebView2Pane_Constructor_ShouldNotThrow()
        {
            // Test that WebView2Pane can be constructed without throwing
            WebView2Pane pane = null;
            
            Assert.DoesNotThrow(() => 
            {
                pane = new WebView2Pane();
            });
            
            pane?.Dispose();
        }

        [Test]
        public void SendSelection_WithValidData_ShouldNotThrow()
        {
            // Test the SendSelection method with valid data
            using (var pane = new WebView2Pane())
            {
                var testData = "Company\tRevenue\tProfit\nAAPL\t100\t20\nGOOGL\t200\t30";
                
                Assert.DoesNotThrow(() => 
                {
                    pane.SendSelection(testData);
                });
            }
        }

        [Test]
        public void SendSelection_WithNullData_ShouldNotThrow()
        {
            // Test the SendSelection method with null data
            using (var pane = new WebView2Pane())
            {
                Assert.DoesNotThrow(() => 
                {
                    pane.SendSelection(null);
                });
            }
        }

        [Test]
        public void SendSelection_WithEmptyData_ShouldNotThrow()
        {
            // Test the SendSelection method with empty data
            using (var pane = new WebView2Pane())
            {
                Assert.DoesNotThrow(() => 
                {
                    pane.SendSelection("");
                });
            }
        }

        [Test]
        public void InitializeWorkbookAsync_WithValidPath_ShouldNotThrow()
        {
            // Test the InitializeWorkbookAsync method
            using (var pane = new WebView2Pane())
            {
                var testPath = @"C:\test\workbook.xlsx";
                
                Assert.DoesNotThrowAsync(async () => 
                {
                    await pane.InitializeWorkbookAsync(testPath);
                });
            }
        }

        [Test]
        public void InitializeWorkbookAsync_WithNullPath_ShouldNotThrow()
        {
            // Test the InitializeWorkbookAsync method with null path
            using (var pane = new WebView2Pane())
            {
                Assert.DoesNotThrowAsync(async () => 
                {
                    await pane.InitializeWorkbookAsync(null);
                });
            }
        }

        [Test]
        public void Dispose_ShouldNotThrow()
        {
            // Test that Dispose works correctly
            var pane = new WebView2Pane();
            
            Assert.DoesNotThrow(() => 
            {
                pane.Dispose();
            });
        }

        [Test]
        public void MultipleDispose_ShouldNotThrow()
        {
            // Test that multiple Dispose calls don't throw
            var pane = new WebView2Pane();
            
            Assert.DoesNotThrow(() => 
            {
                pane.Dispose();
                pane.Dispose();
            });
        }
    }

    public interface IWebView2Wrapper
    {
        Task InitializeAsync();
        void SendMessage(string message);
        void NavigateToString(string html);
        event EventHandler<string> MessageReceived;
    }

    public interface IHttpClientWrapper : IDisposable
    {
        Task<HttpResponseMessage> GetAsync(string endpoint);
        Task<HttpResponseMessage> PostAsync(string endpoint, string content);
    }
}
