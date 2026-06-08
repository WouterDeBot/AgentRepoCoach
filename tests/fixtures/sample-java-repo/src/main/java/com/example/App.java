package com.example;

/**
 * Main application entry point.
 *
 * Demonstrates basic application bootstrap and argument validation.
 */
public class App {

    /**
     * Returns a greeting string for the given name.
     *
     * @param name the name to greet
     * @return greeting message
     */
    public String greet(String name) {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("name must not be null or empty");
        }
        return "Hello, " + name + "!";
    }

    /**
     * Application entry point.
     *
     * @param args command-line arguments
     */
    public static void main(String[] args) {
        App app = new App();
        System.out.println(app.greet("World"));
    }
}
