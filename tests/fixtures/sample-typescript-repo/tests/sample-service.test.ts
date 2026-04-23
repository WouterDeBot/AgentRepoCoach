import { SampleService, SampleValidationError } from "../src/sample-service";

describe("SampleService", () => {
  it("should return double for positive input", () => {
    const service = new SampleService();
    expect(service.doWork(5)).toBe(10);
  });

  it("should throw validation error for negative input", () => {
    const service = new SampleService();
    expect(() => service.doWork(-1)).toThrow(SampleValidationError);
  });

  test("doWork over max throws validation error", () => {
    const service = new SampleService();
    expect(() => service.doWork(5000)).toThrow(SampleValidationError);
  });
});
