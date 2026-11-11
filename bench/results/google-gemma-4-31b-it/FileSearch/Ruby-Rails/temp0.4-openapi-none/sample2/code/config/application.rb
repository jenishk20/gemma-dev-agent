require_relative "boot"

require "rails/all"

# The request to use only standard library and provided gems
# ensures we don't need extra engines, but we include standard API setup.

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0.1
  config.api_only = true

  # Ensure the server binds to 0.0.0.0 and port 5000 as requested
  config.server.bind = "0.0.0.0"
  config.server.port = 5000
end