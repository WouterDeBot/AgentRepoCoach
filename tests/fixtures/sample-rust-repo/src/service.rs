use std::fmt;

/// A domain-specific validation error.
pub struct ValidationError {
    pub field: String,
    pub message: String,
}

impl fmt::Display for ValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "validation failed on {}: {}", self.field, self.message)
    }
}

/// The sample service that performs operations.
pub struct SampleService {
    max_value: i32,
}

impl SampleService {
    /// Creates a new SampleService with the given maximum value.
    pub fn new(max: i32) -> Self {
        SampleService { max_value: max }
    }

    /// Validates the input and returns double its value.
    ///
    /// Returns a ValidationError if the input is out of range.
    pub fn do_work(&self, input: i32) -> Result<i32, ValidationError> {
        if input < 0 {
            return Err(ValidationError {
                field: "input".to_string(),
                message: format!(
                    "must be >= 0 but was {}. Suggested fix: pass a positive integer",
                    input
                ),
            });
        }
        if input > self.max_value {
            return Err(ValidationError {
                field: "input".to_string(),
                message: format!("exceeds max {}. Try a value under {}", self.max_value, self.max_value),
            });
        }
        Ok(input * 2)
    }
}

/// Parses configuration from the given path.
pub fn parse_config(path: &str) -> Result<(), String> {
    if path.is_empty() {
        panic!("path must not be empty. Check your config file location");
    }
    Ok(())
}

fn internal_helper() -> i32 {
    42
}

struct InternalWorker {
    name: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_do_work_positive_input_returns_double() {
        let svc = SampleService::new(1000);
        assert_eq!(svc.do_work(5).unwrap(), 10);
    }

    #[test]
    fn test_do_work_negative_input_returns_error() {
        let svc = SampleService::new(1000);
        assert!(svc.do_work(-1).is_err());
    }

    #[test]
    fn test_parse_config_empty_panics() {
        let result = std::panic::catch_unwind(|| parse_config(""));
        assert!(result.is_err());
    }
}
