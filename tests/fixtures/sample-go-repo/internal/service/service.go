// Package service provides the sample domain service.
package service

import (
	"errors"
	"fmt"
)

// ValidationError is a domain-specific error for input validation failures.
type ValidationError struct {
	Field   string
	Message string
}

// Error implements the error interface.
func (e *ValidationError) Error() string {
	return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}

// SampleService performs sample operations.
type SampleService struct {
	maxValue int
}

// NewSampleService creates a new SampleService with the given max.
func NewSampleService(max int) *SampleService {
	return &SampleService{maxValue: max}
}

// DoWork validates the input and returns double its value.
// Returns a ValidationError if the input is out of range.
func (s *SampleService) DoWork(input int) (int, error) {
	if input < 0 {
		return 0, &ValidationError{
			Field:   "input",
			Message: fmt.Sprintf("must be >= 0 but was %d. Suggested fix: pass a positive integer", input),
		}
	}
	if input > s.maxValue {
		return 0, &ValidationError{
			Field:   "input",
			Message: fmt.Sprintf("exceeds max %d. Try a value under %d", s.maxValue, s.maxValue),
		}
	}
	return input * 2, nil
}

// ParseConfig reads configuration from the given path.
func ParseConfig(path string) (map[string]string, error) {
	if path == "" {
		return nil, errors.New("path must not be empty. Check your config file location")
	}
	return nil, fmt.Errorf("config file %s not found. See docs/configuration.md for setup", path)
}

// internalHelper is an unexported helper function.
func internalHelper() int {
	return 42
}

type internalWorker struct {
	name string
}
