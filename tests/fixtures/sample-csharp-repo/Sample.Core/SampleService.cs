using System;

namespace Sample.Core;

/// <summary>
/// Sample service demonstrating good error messages.
/// </summary>
public sealed class SampleService
{
    /// <summary>Validates input and runs the sample operation.</summary>
    public int DoWork(int input)
    {
        if (input < 0)
        {
            throw new SampleValidationException(
                $"Input must be >= 0 but was {input}. Suggested fix: pass a positive integer.");
        }
        if (input > 1000)
        {
            throw new SampleValidationException(
                $"Input {input} exceeds max. Try a value under 1000.");
        }
        return input * 2;
    }
}

/// <summary>Base class for all Sample-domain exceptions.</summary>
public class SampleException : Exception
{
    public SampleException(string message) : base(message) { }
}

/// <summary>Thrown when user input fails validation.</summary>
public sealed class SampleValidationException : SampleException
{
    public SampleValidationException(string message) : base(message) { }
}

internal sealed class SampleInternalHelper
{
    public int Helper() => 42;
}
