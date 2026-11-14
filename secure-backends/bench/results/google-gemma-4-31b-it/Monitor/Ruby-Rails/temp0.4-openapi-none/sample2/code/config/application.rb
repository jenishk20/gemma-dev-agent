require_relative "boot"

require "rails/all"

# Require the Rails engines to be loaded.
require "active_storage/engine"

module MonitorService
  class Application < Rails::Application
    config.load_defaults 8.0.1

    # Configure the app to run as an API
    config.api_only = true

    # Ensure the server binds to 0.0.0.0 and port 5000 as requested
    config.server.bind = "0.0.0.0"
    config.server.port = 5000
  end
end