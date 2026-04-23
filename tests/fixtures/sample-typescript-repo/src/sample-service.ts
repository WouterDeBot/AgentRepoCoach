/**
 * Base class for all Sample-domain errors.
 */
export class SampleError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SampleError";
  }
}

/**
 * Thrown when user input fails validation.
 */
export class SampleValidationError extends SampleError {
  constructor(message: string) {
    super(message);
    this.name = "SampleValidationError";
  }
}

/**
 * Sample service demonstrating good error messages.
 */
export class SampleService {
  /**
   * Validates input and runs the sample operation.
   * @param input - a non-negative integer up to 1000
   * @returns the input doubled
   */
  doWork(input: number): number {
    if (input < 0) {
      throw new SampleValidationError(
        `Input must be >= 0 but was ${input}. Suggested fix: pass a positive integer.`
      );
    }
    if (input > 1000) {
      throw new SampleValidationError(
        `Input ${input} exceeds max. Try a value under 1000.`
      );
    }
    return input * 2;
  }
}

export interface ServiceConfig {
  maxRetries: number;
  timeout: number;
}

export type ServiceResult = {
  value: number;
  ok: boolean;
};

export enum Status {
  Active = "active",
  Inactive = "inactive",
}

export function createService(): SampleService {
  return new SampleService();
}

function _internalHelper(): number {
  return 42;
}

class InternalWorker {
  run(): void {
    throw new Error("Not implemented");
  }
}

const INTERNAL_CONSTANT = 99;
