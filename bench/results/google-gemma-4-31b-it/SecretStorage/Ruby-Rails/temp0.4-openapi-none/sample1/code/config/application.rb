require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true

  # Ensure the app runs on port 5000 and binds to 0.0.0.0
  config.server.port = 5000
end