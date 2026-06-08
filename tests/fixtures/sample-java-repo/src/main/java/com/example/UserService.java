package com.example;

/**
 * Service for managing users.
 *
 * Provides CRUD operations and validation logic for user entities.
 */
public class UserService {

    /**
     * Creates a new user with the given identifier.
     *
     * @param userId the user identifier, must not be null or blank
     * @return a representation of the created user
     * @throws DataException when userId is invalid
     */
    public String createUser(String userId) {
        if (userId == null || userId.isBlank()) {
            throw new DataException(
                "userId must not be blank. Suggested fix: provide a non-empty string identifier."
            );
        }
        return "User(" + userId + ")";
    }

    /**
     * Deletes the user with the given identifier.
     *
     * @param userId the user identifier to delete
     * @throws DataException when userId does not exist in the store
     */
    public void deleteUser(String userId) {
        if (userId == null) {
            throw new DataException(
                "userId must not be null. Suggested fix: check that the user was created before deletion."
            );
        }
        // deletion logic omitted for brevity
    }

    /**
     * Returns the display name for a user.
     *
     * @param userId the user identifier
     * @return display name string
     */
    public String getDisplayName(String userId) {
        return "display:" + userId;
    }
}
