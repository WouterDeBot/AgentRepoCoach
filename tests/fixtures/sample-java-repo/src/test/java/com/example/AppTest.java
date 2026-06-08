package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for App.
 */
public class AppTest {

    @Test
    public void testGreetReturnsMessage() {
        App app = new App();
        String result = app.greet("Alice");
        assertEquals("Hello, Alice!", result);
    }

    @Test
    public void testGreetThrowsOnNullName() {
        App app = new App();
        assertThrows(IllegalArgumentException.class, () -> app.greet(null));
    }
}
