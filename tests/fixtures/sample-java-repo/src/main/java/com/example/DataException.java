package com.example;

/**
 * Domain exception for data validation errors.
 *
 * Thrown when input data fails validation rules.  Always includes a
 * descriptive message with a suggested fix.
 */
public class DataException extends RuntimeException {

    /**
     * Constructs a DataException with the given message.
     *
     * @param message human-readable error description
     */
    public DataException(String message) {
        super(message);
    }

    /**
     * Constructs a DataException with a message and cause.
     *
     * @param message human-readable error description
     * @param cause   the underlying cause
     */
    public DataException(String message, Throwable cause) {
        super(message, cause);
    }
}
