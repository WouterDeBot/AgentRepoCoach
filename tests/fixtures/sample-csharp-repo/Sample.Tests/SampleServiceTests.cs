using Xunit;

namespace Sample.Tests;

public sealed class SampleServiceTests
{
    [Fact]
    public void DoWork_PositiveInput_ReturnsDouble()
    {
        var service = new Sample.Core.SampleService();
        Assert.Equal(10, service.DoWork(5));
    }

    [Fact]
    public void DoWork_NegativeInput_Throws()
    {
        var service = new Sample.Core.SampleService();
        Assert.Throws<Sample.Core.SampleValidationException>(() => service.DoWork(-1));
    }

    [Fact]
    public void DoWork_OverMax_Throws()
    {
        var service = new Sample.Core.SampleService();
        Assert.Throws<Sample.Core.SampleValidationException>(() => service.DoWork(5000));
    }
}
