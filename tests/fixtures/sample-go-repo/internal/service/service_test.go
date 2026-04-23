package service

import "testing"

func TestDoWork_PositiveInput_ReturnsDouble(t *testing.T) {
	s := NewSampleService(1000)
	result, err := s.DoWork(5)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != 10 {
		t.Errorf("expected 10, got %d", result)
	}
}

func TestDoWork_NegativeInput_ReturnsError(t *testing.T) {
	s := NewSampleService(1000)
	_, err := s.DoWork(-1)
	if err == nil {
		t.Fatal("expected error for negative input")
	}
}

func TestParseConfig_EmptyPath_ReturnsError(t *testing.T) {
	_, err := ParseConfig("")
	if err == nil {
		t.Fatal("expected error for empty path")
	}
}
