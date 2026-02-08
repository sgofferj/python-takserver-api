# Refactoring Explanation

This document explains the refactoring of the `python-takserver-api` module, specifically how the code structure was modernized to use classes and adhere to PEP-8 standards.

## 1. Reimplementing Files as Classes (Components)

Previously, the `Server` class utilized functions imported directly from separate topic files (Mixins). To improve modularity and state management, these files have been reimplemented as distinct classes (Components).

### Changes Made:

- **Class Encapsulation**: Each topic file now contains a class (e.g., `MissionApi`, `HomeApi`) that encapsulates related functionality.
- **Naming Conventions**: Converted names to `snake_case` for functions/variables and `CapWords` for classes, complying with PEP-8.
- **Asynchronous Design**: Maintained `async` definitions for non-blocking operations.

## 2. Passing the `self` Object

To allow these new component classes to interact with the main `Server` instance (e.g., to access shared configuration, the network session, or the base URL), we use a pattern where the `Server` instance is passed to the components upon initialization.

### Implementation Details:

1.  **In the Component Class:**
    The `__init__` method accepts a `server` argument. This is stored as an instance variable (`self.server`), allowing methods within the component to access the main server.

    ```python
    class MissionApi:
        def __init__(self, server):
            self.server = server  # Store reference to the main Server instance

        async def get_mission(self, name):
            # Access main server attributes via self.server
            url = self.server.api_base_url + f"/Marti/api/missions/{name}"
            # Access the shared connection helper via self.server
            await self.server.connection.request("get", url)
    ```

2.  **In the Main `Server` Class:**
    When the `Server` initializes, it instantiates these component classes, passing `self` (the current `Server` instance) to them.

    ```python
    class Server:
        def __init__(self, host, cert, key):
            # ... initialization ...

            # Initialize components and pass 'self'
            self.connection = ConnectionHelper(self)
            self.mission = MissionApi(self)

            # Now you can access mission methods via:
            # await server.mission.get_mission("name")
    ```

This approach (Composition) keeps the code organized while ensuring all parts of the application can communicate effectively.
