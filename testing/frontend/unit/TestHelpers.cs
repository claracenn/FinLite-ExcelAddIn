using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using NUnit.Framework;
using Moq;
using ExcelAddIn;
using Microsoft.Web.WebView2.Core;
using FinLiteTests.Unit.Stubs;            // Bring in test stub interfaces (IExcelRange, IBackendService, etc.)
using FinLiteTests.Unit.TestDoubles;      // Access WebView2TestScenario within helper namespace
using FluentAssertions;

namespace FinLiteTests.Unit.Helpers
{
    public static class TestHelpers
    {
        public static Mock<IExcelRange> CreateMockRange(string address, object[,] values = null)
        {
            var mockRange = new Mock<IExcelRange>();
            mockRange.Setup(x => x.Address).Returns(address);
            
            if (values != null)
            {
                mockRange.Setup(x => x.GetValues()).Returns(values);
            }
            
            return mockRange;
        }

        public static object[,] CreateSampleFinancialData()
        {
            return new object[,]
            {
                { "Company", "Revenue", "Net Income", "ROE" },
                { "AAPL", 394.3, 99.8, 1.58 },
                { "GOOGL", 307.4, 76.0, 0.247 },
                { "MSFT", 211.9, 72.4, 0.342 }
            };
        }

        public static Mock<IWebView2Core> CreateMockWebView2()
        {
            var mock = new Mock<IWebView2Core>();
            var messageEvents = new List<string>();
            
            mock.Setup(x => x.PostWebMessageAsJson(It.IsAny<string>()))
                .Callback<string>(message => messageEvents.Add(message));
            
            mock.Setup(x => x.Navigate(It.IsAny<string>()))
                .Verifiable();
                
            mock.Setup(x => x.NavigateToString(It.IsAny<string>()))
                .Verifiable();
            
            return mock;
        }

        public static Mock<IHttpClientWrapper> CreateMockHttpClient()
        {
            var mock = new Mock<IHttpClientWrapper>();
            
            mock.Setup(x => x.GetAsync("/health"))
                .ReturnsAsync(CreateMockHttpResponse("OK"));
            
            mock.Setup(x => x.PostAsync("/chat", It.IsAny<string>()))
                .ReturnsAsync(CreateMockHttpResponse("{\"response\":\"Mock AI response\"}"));
            
            mock.Setup(x => x.GetAsync("/history/unified?limit=10"))
                .ReturnsAsync(CreateMockHttpResponse("[]"));
            
            return mock;
        }

        public static WebView2TestScenario CreateWebView2TestScenario(string scenarioType)
        {
            switch (scenarioType)
            {
                case "basic_ask":
                    return new WebView2TestScenario
                    {
                        Message = "{\"type\":\"ask\",\"prompt\":\"What is ROE?\",\"session_id\":\"test1\"}",
                        ExpectedResponse = "answer",
                        ExpectedBackendCall = "/chat"
                    };
                case "history_request":
                    return new WebView2TestScenario
                    {
                        Message = "{\"type\":\"history\"}",
                        ExpectedResponse = "history-data",
                        ExpectedBackendCall = "/history/unified?limit=10"
                    };
                case "help_request":
                    return new WebView2TestScenario
                    {
                        Message = "{\"type\":\"help\"}",
                        ExpectedResponse = "help-data",
                        ExpectedBackendCall = null
                    };
                default:
                    throw new ArgumentException($"Unknown scenario type: {scenarioType}");
            }
        }

        public static System.Net.Http.HttpResponseMessage CreateMockHttpResponse(string content, System.Net.HttpStatusCode statusCode = System.Net.HttpStatusCode.OK)
        {
            return new System.Net.Http.HttpResponseMessage(statusCode)
            {
                Content = new System.Net.Http.StringContent(content)
            };
        }

        public static string CreateChatResponseJson(string response)
        {
            return $"{{\"response\":\"{response}\"}}";
        }

        public static async Task<bool> CompletesWithinTimeout(Task task, TimeSpan timeout)
        {
            var completedTask = await Task.WhenAny(task, Task.Delay(timeout));
            return completedTask == task;
        }
    }

    public static class CustomAssertions
    {
        public static async Task ShouldCompleteWithinAsync(this Task task, TimeSpan timeout)
        {
            var completed = await TestHelpers.CompletesWithinTimeout(task, timeout);
            completed.Should().BeTrue($"Task did not complete within {timeout}");
        }

        public static async Task<T> ShouldThrowAsync<T>(this Task task) where T : Exception
        {
            try
            {
                await task;
                throw new AssertionException($"Expected exception of type {typeof(T).Name} but none was thrown");
            }
            catch (T exception)
            {
                return exception;
            }
            catch (Exception exception)
            {
                throw new AssertionException($"Expected exception of type {typeof(T).Name} but got {exception.GetType().Name}");
            }
        }
    }

    public class TestDataBuilder
    {
        private readonly List<object[]> _rows = new List<object[]>();
        private string[] _headers;

        public TestDataBuilder WithHeaders(params string[] headers)
        {
            _headers = headers;
            return this;
        }

        public TestDataBuilder AddRow(params object[] values)
        {
            _rows.Add(values);
            return this;
        }

        public TestDataBuilder AddFinancialCompany(string company, double revenue, double netIncome, double roe)
        {
            _rows.Add(new object[] { company, revenue, netIncome, roe });
            return this;
        }

        public object[,] Build()
        {
            var totalRows = _headers != null ? _rows.Count + 1 : _rows.Count;
            var totalCols = _headers?.Length ?? _rows[0]?.Length ?? 0;
            
            var result = new object[totalRows, totalCols];
            
            var currentRow = 0;
            if (_headers != null)
            {
                for (int col = 0; col < _headers.Length; col++)
                {
                    result[currentRow, col] = _headers[col];
                }
                currentRow++;
            }

            foreach (var row in _rows)
            {
                for (int col = 0; col < row.Length; col++)
                {
                    result[currentRow, col] = row[col];
                }
                currentRow++;
            }

            return result;
        }
    }
}

namespace FinLiteTests.Unit.TestDoubles
{
    public class FakeBackendService : IBackendService
    {
        public bool IsStarted { get; private set; }
        public bool ShouldThrowOnStart { get; set; }
        public TimeSpan StartupDelay { get; set; } = TimeSpan.Zero;
    public string LastInitializedWorkbook { get; private set; }

        public async Task EnsureStartedAsync()
        {
            if (ShouldThrowOnStart)
            {
                throw new InvalidOperationException("Simulated startup failure");
            }

            if (StartupDelay > TimeSpan.Zero)
            {
                await Task.Delay(StartupDelay);
            }

            IsStarted = true;
        }

        public void Stop()
        {
            IsStarted = false;
        }

        public Task<bool> IsHealthyAsync(TimeSpan timeout)
        {
            return Task.FromResult(IsStarted);
        }

        public Task<bool> InitializeWorkbookAsync(string path)
        {
            LastInitializedWorkbook = path;
            return Task.FromResult(true);
        }
    }

    public class FakeHttpClientWrapper : IHttpClientWrapper
    {
        public Dictionary<string, string> ResponseMap { get; } = new Dictionary<string, string>();
        public List<(string endpoint, string content)> SentRequests { get; } = new List<(string, string)>();
        public bool ShouldThrowException { get; set; }

        public async Task<System.Net.Http.HttpResponseMessage> PostAsync(string endpoint, string content)
        {
            SentRequests.Add((endpoint, content));

            if (ShouldThrowException)
            {
                throw new System.Net.Http.HttpRequestException("Simulated network error");
            }

            await Task.Delay(10);

            if (ResponseMap.TryGetValue(endpoint, out var response))
            {
                return new System.Net.Http.HttpResponseMessage(System.Net.HttpStatusCode.OK)
                {
                    Content = new System.Net.Http.StringContent(response)
                };
            }

            return new System.Net.Http.HttpResponseMessage(System.Net.HttpStatusCode.NotFound);
        }

        public void Dispose()
        {
        }

        public Task<System.Net.Http.HttpResponseMessage> GetAsync(string endpoint)
        {
            if (ShouldThrowException)
            {
                throw new System.Net.Http.HttpRequestException("Simulated network error");
            }

            if (ResponseMap.TryGetValue(endpoint, out var response))
            {
                return Task.FromResult(new System.Net.Http.HttpResponseMessage(System.Net.HttpStatusCode.OK)
                {
                    Content = new System.Net.Http.StringContent(response)
                });
            }
            return Task.FromResult(new System.Net.Http.HttpResponseMessage(System.Net.HttpStatusCode.NotFound));
        }
    }

    public class WebView2TestScenario
    {
        public string Message { get; set; }
        public string ExpectedResponse { get; set; }
        public string ExpectedBackendCall { get; set; }
    }
}
